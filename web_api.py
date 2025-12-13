#!/usr/bin/env python3
"""
Pentagent Web API Server
Frontend ile backend arasında iletişim sağlar
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Project root'u path'e ekle
import os
import sys
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from agent_core.dynamic_orchestrator import DynamicAgentOrchestrator
from config import config
from services.rag_service import get_rag_service
from model_wrapper import UnifiedLLM

# Logging konfigürasyonu
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Pentagent API", version="1.0.0")

# CORS middleware - Production için güvenli
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
if allowed_origins == ["*"]:
    # Development mode
    allowed_origins = ["*"]
else:
    # Production mode - specific origins
    allowed_origins = [origin.strip() for origin in allowed_origins]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connection manager (orchestrator her scan için yeni oluşturulacak - modüler)
active_connections: List[WebSocket] = []

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket bağlantısı kuruldu. Toplam: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket bağlantısı kesildi. Toplam: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """WebSocket'e mesaj gönder - geliştirilmiş hata yönetimi"""
        try:
            # WebSocket state kontrolü ekle
            if websocket not in self.active_connections:
                logger.debug("WebSocket bağlantısı aktif değil, mesaj gönderilmedi")
                return
            
            # WebSocket bağlantı durumunu kontrol et
            try:
                await websocket.send_text(message)
            except WebSocketDisconnect:
                # Normal disconnect - INFO seviyesinde logla
                logger.info("WebSocket bağlantısı kapatıldı (mesaj gönderilirken)")
                self.disconnect(websocket)
            except RuntimeError as re:
                # "WebSocket is not connected" hatası - normal durum
                error_msg = str(re) if re else "WebSocket bağlantısı kapalı"
                logger.debug(f"WebSocket bağlantısı kapalı: {error_msg}")
                self.disconnect(websocket)
            except ConnectionResetError:
                # Bağlantı resetlendi - normal durum
                logger.debug("WebSocket bağlantısı resetlendi")
                self.disconnect(websocket)
        except WebSocketDisconnect:
            # Normal disconnect - INFO seviyesinde logla
            logger.info("WebSocket bağlantısı kapatıldı (send_personal_message)")
            self.disconnect(websocket)
        except Exception as e:
            # Gerçek hatalar için detaylı log
            error_type = type(e).__name__
            error_msg = str(e) if str(e) else f"{error_type} hatası oluştu"
            # Sadece gerçek hatalar için ERROR logla
            if error_type not in ['WebSocketDisconnect', 'RuntimeError', 'ConnectionResetError']:
                logger.warning(f"WebSocket mesaj gönderme hatası ({error_type}): {error_msg}")
            else:
                logger.debug(f"WebSocket bağlantı durumu ({error_type}): {error_msg}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        """Tüm aktif bağlantılara mesaj gönder - geliştirilmiş hata yönetimi"""
        disconnected_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except (WebSocketDisconnect, RuntimeError, ConnectionResetError) as e:
                # Normal disconnect durumları - DEBUG seviyesinde logla
                logger.debug(f"Broadcast sırasında bağlantı kapatıldı: {type(e).__name__}")
                disconnected_connections.append(connection)
            except Exception as e:
                # Gerçek hatalar için WARNING logla
                error_msg = str(e) if str(e) else f"{type(e).__name__} hatası"
                logger.warning(f"Broadcast hatası ({type(e).__name__}): {error_msg}")
                disconnected_connections.append(connection)
        
        # Disconnected connections'ları temizle
        for connection in disconnected_connections:
            self.disconnect(connection)

manager = ConnectionManager()

# Global LLM model (RAG query optimization için)
llm_model = None

@app.on_event("startup")
async def startup_event():
    """Uygulama başlatıldığında API key kontrolü yap"""
    global llm_model
    try:
        logger.info("Pentagent API başlatılıyor...")
        
        # Unified LLM model'i başlat (RAG query optimization için)
        # Uses env: MODEL_PROVIDER, GROQ_API_KEY, GROQ_MODEL
        llm_model = UnifiedLLM()
        
        logger.info(f"✅ LLM provider hazır (MODEL_PROVIDER={config.MODEL_PROVIDER})")
        logger.info("✅ Pentagent API başarıyla başlatıldı!")
        logger.info("💡 Her scan için yeni orchestrator instance oluşturulacak (modüler)")
        
        # RAG servisini başlat (lazy loading - ilk kullanımda yüklenecek)
        try:
            logger.info("RAG servisi lazy loading modunda - ilk kullanımda yüklenecek")
            # Startup'ta yükleme - optional
            # rag_service = get_rag_service()
            # if rag_service.is_available():
            #     stats = rag_service.get_stats()
            #     logger.info(f"✅ RAG servisi hazır: {stats.get('total_cves', 0)} CVE yüklü")
        except Exception as e:
            logger.warning(f"⚠️ RAG servisi startup'ta yüklenemedi: {e}")
        
    except Exception as e:
        logger.error(f"❌ Pentagent API başlatma hatası: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

@app.on_event("shutdown")
async def shutdown_event():
    """Uygulama kapatılırken cleanup yap - MEMORY LEAK PREVENTION"""
    try:
        logger.info("🔄 Pentagent API kapatılıyor, cleanup başlıyor...")
        
        # RAG servisini kapat - aiohttp session cleanup
        try:
            rag_service = get_rag_service()
            if rag_service._session and not rag_service._session.closed:
                await rag_service._close_session()
                logger.info("✅ RAG service session kapatıldı")
        except Exception as e:
            logger.warning(f"⚠️ RAG session cleanup hatası: {e}")
        
        # WebSocket connections cleanup
        try:
            for connection in manager.active_connections:
                try:
                    await connection.close()
                except:
                    pass
            manager.active_connections.clear()
            logger.info("✅ WebSocket connections temizlendi")
        except Exception as e:
            logger.warning(f"⚠️ WebSocket cleanup hatası: {e}")
        
        logger.info("✅ Pentagent API başarıyla kapatıldı")
        
    except Exception as e:
        logger.error(f"❌ Shutdown hatası: {e}")

@app.get("/")
async def root():
    return {"message": "Pentagent API Server", "status": "running"}

@app.head("/")
async def root_head():
    """HEAD request support - Render health check"""
    return {"status": "ok"}

@app.get("/health")
async def health_check():
    """API health check"""
    # Groq API key kontrolü
    groq_api_key_valid = config.GROQ_API_KEY and config.GROQ_API_KEY != ''
    
    # RAG servisi kontrolü
    rag_service = get_rag_service()
    rag_stats = rag_service.get_stats()
    
    return {
        "status": "healthy",
        "llm_provider": config.MODEL_PROVIDER,
        "groq_api_key_configured": groq_api_key_valid,
        "active_connections": len(manager.active_connections),
        "rag_available": rag_stats.get("available", False),
        "rag_cves": rag_stats.get("total_cves", 0),
        "message": "Pentagent API is running"
    }

@app.post("/api/scan")
async def start_scan(request: Dict[str, Any]):
    """Yeni bir güvenlik taraması başlat - MODÜLER (her scan için yeni orchestrator)"""
    try:
        # Groq API key kontrolü
        groq_api_key = config.GROQ_API_KEY
        if not groq_api_key or groq_api_key == '':
            raise HTTPException(status_code=503, detail="GROQ_API_KEY yapılandırılmamış")
        
        target = request.get("target", "").strip()
        task = request.get("task", "")
        
        if not target:
            raise HTTPException(status_code=400, detail="Target gerekli")
        
        # Basit URL format kontrolü
        import re
        from urllib.parse import urlparse
        
        # URL'den hostname çıkar
        if target.startswith(('http://', 'https://')):
            parsed = urlparse(target)
            hostname = parsed.netloc
        else:
            hostname = target.split('/')[0].split(':')[0]
        
        # Hostname boş mu?
        if not hostname or len(hostname) < 3:
            raise HTTPException(
                status_code=400, 
                detail="❌ Geçersiz URL\n\nLütfen geçerli bir domain girin.\n\n✅ Örnek: https://example.com"
            )
        
        # Basit domain formatı kontrolü
        if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', hostname):
            raise HTTPException(
                status_code=400,
                detail="❌ Geçersiz Domain Formatı\n\nDomain geçersiz karakterler içeriyor.\n\n✅ Örnek: example.com"
            )
        
        # DNS kontrolü - Domain var mı?
        import socket
        try:
            socket.gethostbyname(hostname)
            logger.info(f"✅ DNS başarılı: {hostname}")
        except socket.gaierror:
            raise HTTPException(
                status_code=400,
                detail=f"❌ Domain Bulunamadı: {hostname}\n\nBu domain DNS kayıtlarında bulunamadı.\n\n💡 Kontrol edin:\n  • Domain adını doğru yazdınız mı?\n  • Domain gerçekten var mı?\n\n✅ Örnek: https://example.com"
            )
        
        # Scan ID oluştur
        scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Status callback fonksiyonu
        async def scan_status_callback(message: str, status_type: str = "info"):
            timestamp = datetime.now(timezone.utc).isoformat()
            status_data = {
                "type": "scan_status",
                "scan_id": scan_id,
                "timestamp": timestamp,
                "message": message,
                "status_type": status_type
            }
            await manager.broadcast(json.dumps(status_data))
        
        # Async olarak scan başlat
        asyncio.create_task(run_scan_async(scan_id, target, task, scan_status_callback))
        
        return {
            "scan_id": scan_id,
            "status": "started",
            "target": target,
            "task": task,
            "message": "Scan başlatıldı"
        }
        
    except HTTPException:
        # HTTPException'ı olduğu gibi fırlat (400, 503 vb.)
        raise
    except Exception as e:
        # Hataları daha iyi yönet - sistem çökmesini önle
        error_type = type(e).__name__
        error_msg = str(e) if str(e) else f"{error_type} hatası oluştu"
        logger.warning(f"Scan başlatma hatası ({error_type}): {error_msg}")
        # Kullanıcıya anlamlı hata mesajı gönder
        raise HTTPException(
            status_code=500, 
            detail=f"Tarama başlatılamadı: {error_msg[:200]}"
        )

async def run_scan_async(scan_id: str, target: str, task: str, status_callback):
    """Async olarak scan çalıştır - MODÜLER (her scan için yeni orchestrator)"""
    try:
        logger.info(f"Scan başlatılıyor: {scan_id} - {target}")
        
        # Scan başlatma mesajı - Safe callback
        try:
            await status_callback(f"🎯 Scan başlatıldı: {target}", "info")
        except Exception as cb_err:
            logger.error(f"Status callback hatası: {cb_err}")
        
        # Her scan için YENİ orchestrator oluştur (modüler)
        # UnifiedLLM kullanır (Groq API key'i env'den alır)
        scan_orchestrator = DynamicAgentOrchestrator(api_key=None)  # api_key ignored, uses env
        logger.info(f"✅ Scan {scan_id} için yeni orchestrator oluşturuldu (Groq)")
        
        # Safe status callback wrapper
        async def safe_status_callback(msg: str, status_type: str = "info"):
            """WebSocket hatalarını yakalayan güvenli callback"""
            try:
                await status_callback(msg, status_type)
            except (RuntimeError, WebSocketDisconnect, ConnectionResetError) as re:
                # Normal disconnect durumları - DEBUG seviyesinde logla
                logger.debug(f"WebSocket bağlantısı kapalı, mesaj gönderilemedi: {msg[:50]}...")
            except Exception as e:
                # Diğer hatalar için WARNING seviyesi
                error_type = type(e).__name__
                error_msg = str(e) if str(e) else f"{error_type} hatası"
                logger.warning(f"Status callback hatası ({error_type}): {error_msg}")
        
        # Orchestrator ile scan çalıştır - streaming düşünce ile (safe callback)
        result = await scan_orchestrator.run_autonomous_pentest_streaming(
            target=target,
            user_task=task or f"Kapsamlı güvenlik testi yap",
            status_callback=safe_status_callback
        )
        
        # Scan tamamlanma mesajı
        try:
            await safe_status_callback(f"✅ Scan tamamlandı: {scan_id}", "success")
        except Exception as cb_err:
            logger.error(f"Completion callback hatası: {cb_err}")
        
        # Sonuçları broadcast et
        try:
            result_data = {
                "type": "scan_completed",
                "scan_id": scan_id,
                "result": result.to_dict() if hasattr(result, 'to_dict') else str(result),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await manager.broadcast(json.dumps(result_data))
        except Exception as broadcast_err:
            # Broadcast hataları normal olabilir - WARNING seviyesinde logla
            error_msg = str(broadcast_err) if str(broadcast_err) else f"{type(broadcast_err).__name__} hatası"
            logger.warning(f"Broadcast hatası (normal olabilir): {error_msg}")
        
    except asyncio.TimeoutError as e:
        # Timeout normal bir durum olabilir - WARNING seviyesinde logla
        logger.warning(f"⏱️ Scan timeout hatası: {scan_id} - normal durum olabilir")
        try:
            await status_callback(f"⏱️ Scan zaman aşımına uğradı", "warning")
        except Exception as cb_err:
            logger.debug(f"Timeout callback hatası (normal olabilir): {cb_err}")
    except Exception as e:
        # Hataları daha iyi yönet - sistem çökmesini önle
        error_type = type(e).__name__
        error_msg = str(e) if str(e) else f"{error_type} hatası oluştu"
        logger.warning(f"Scan çalıştırma hatası ({error_type}): {error_msg}")
        try:
            await status_callback(f"⚠️ Scan hatası: {error_msg[:100]}", "error")
        except Exception as cb_err:
            logger.debug(f"Error callback hatası (normal olabilir): {cb_err}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint - Real-time iletişim"""
    logger.info(f"WebSocket bağlantı isteği geldi: {websocket.client}")
    
    try:
        await manager.connect(websocket)
        logger.info("WebSocket bağlantısı manager'a eklendi")
        
        # Bağlantı kurulduğunda hemen status gönder
        connection_status = {
            "type": "connection_status",
            "status": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "WebSocket bağlantısı kuruldu"
        }
        
        await manager.send_personal_message(
            json.dumps(connection_status),
            websocket
        )
        logger.info("Bağlantı durumu mesajı gönderildi")
        
        while True:
            try:
                # Client'tan mesaj bekle
                data = await websocket.receive_text()
                message = json.loads(data)
                logger.info(f"WebSocket mesajı alındı: {message.get('type', 'unknown')}")
                
                # Mesaj tipine göre işle
                if message.get("type") == "ping":
                    logger.info("Ping mesajı alındı, pong gönderiliyor")
                    await manager.send_personal_message(
                        json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}),
                        websocket
                    )
                elif message.get("type") == "start_scan":
                    # WebSocket üzerinden scan başlat
                    target = message.get("target", "")
                    task = message.get("task", "")
                    
                    logger.info(f"Scan başlatma isteği: target={target}, task={task}")
                    
                    # TARGET VAR MI KONTROL ET
                    if target and target.strip():
                        # TARGET VAR - Normal scan başlat
                        scan_id = f"ws_scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        
                        # Scan başlatma mesajı
                        scan_started = {
                            "type": "scan_started",
                            "scan_id": scan_id,
                            "target": target,
                            "task": task,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        await manager.send_personal_message(
                            json.dumps(scan_started),
                            websocket
                        )
                        logger.info(f"Scan başlatıldı: {scan_id}")
                        
                        async def ws_status_callback(msg: str, status_type: str = "info"):
                            status_data = {
                                "type": "scan_status",
                                "scan_id": scan_id,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "message": msg,
                                "status_type": status_type
                            }
                            await manager.send_personal_message(json.dumps(status_data), websocket)
                        
                        # Async scan başlat
                        asyncio.create_task(run_scan_async(scan_id, target, task, ws_status_callback))
                        logger.info("Async scan task başlatıldı")
                    else:
                        # TARGET YOK - Sadece AI yanıt ver
                        logger.info(f"Target yok, AI yanıt veriliyor: {task}")
                        
                        scan_id = f"ws_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        
                        async def ws_ai_callback(msg: str, status_type: str = "info"):
                            """AI yanıtları için callback"""
                            if status_type == "ai_response":
                                # AI yanıtını direkt gönder
                                ai_response_data = {
                                    "type": "ai_response",
                                    "message": msg,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }
                                await manager.send_personal_message(json.dumps(ai_response_data), websocket)
                            else:
                                # Diğer mesajlar
                                status_data = {
                                    "type": "scan_status",
                                    "scan_id": scan_id,
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                    "message": msg,
                                    "status_type": status_type
                                }
                                await manager.send_personal_message(json.dumps(status_data), websocket)
                        
                        # Async AI yanıt al
                        asyncio.create_task(run_scan_async(scan_id, "", task, ws_ai_callback))
                        logger.info("AI yanıt task başlatıldı")
            except WebSocketDisconnect:
                # WebSocket client disconnected - normal durum
                logger.info("WebSocket client disconnected (normal)")
                break
            except RuntimeError as re:
                # WebSocket bağlantısı kesildiğinde oluşan hata - normal durum
                error_msg = str(re) if str(re) else "WebSocket bağlantısı kapatıldı"
                logger.info(f"WebSocket bağlantısı kapatıldı (RuntimeError): {error_msg}")
                break
            except ConnectionResetError:
                # Bağlantı resetlendi - normal durum
                logger.info("WebSocket bağlantısı resetlendi")
                break
            except Exception as e:
                # Diğer hatalar - log et ama devam et
                error_type = type(e).__name__
                error_msg = str(e) if str(e) else f"{error_type} hatası oluştu"
                logger.warning(f"WebSocket message loop hatası ({error_type}): {error_msg}")
                # DEVAM ET - sistemi crash ettirme!
                break
            
    except WebSocketDisconnect:
        logger.info("✅ WebSocket bağlantısı normal şekilde kapatıldı")
    except (RuntimeError, ConnectionResetError) as re:
        error_msg = str(re) if str(re) else type(re).__name__
        logger.info(f"✅ WebSocket bağlantısı kapatıldı ({type(re).__name__}): {error_msg}")
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e) if str(e) else f"{error_type} hatası oluştu"
        logger.warning(f"WebSocket endpoint hatası ({error_type}): {error_msg}")
        # Sadece gerçek beklenmeyen hatalar için traceback göster
        if error_type not in ['WebSocketDisconnect', 'RuntimeError', 'ConnectionResetError']:
            import traceback
            logger.debug(f"Traceback: {traceback.format_exc()}")
        # HATA YAKALA - Sistemi crash ettirme!
    finally:
        try:
            manager.disconnect(websocket)
        except Exception as disc_err:
            # Disconnect hatası normal olabilir - DEBUG seviyesinde logla
            logger.debug(f"Disconnect hatası (normal olabilir): {disc_err}")

# ==================== RAG QUERY OPTIMIZATION ====================

async def optimize_rag_query(user_query: str) -> Dict[str, Any]:
    """
    🤖 AI ile RAG sorgusu optimize et ve query bilgilerini çıkar
    
    Kullanıcının doğal dil sorgusu → CVE aramasına optimize edilmiş kısa sorgu + filtre bilgileri
    
    Returns:
        {
            'query': str,  # Optimize edilmiş sorgu
            'year': Optional[int],  # Yıl bilgisi (varsa)
            'product': Optional[str],  # Ürün adı (varsa)
            'vendor': Optional[str],  # Vendor adı (varsa)
            'exact_product_match': bool  # Kesin ürün eşleşmesi gerekiyor mu?
        }
    """
    global llm_model
    
    # Default response
    default_response = {
        'query': user_query,
        'year': None,
        'product': None,
        'vendor': None,
        'domain': None,
        'language': None,  # python, java, php, javascript
        'protocol_type': None,  # protocol, product, os_mechanism
        'negative_keywords': [],
        'exact_product_match': False,
        'is_pickle_query': False  # Pickle-specific query flag
    }
    
    if not llm_model:
        logger.warning("LLM model yok, query optimize edilmeden kullanılacak")
        return default_response
    
    try:
        optimization_prompt = f"""Sen bir CVE veritabanı arama uzmanısın. Kullanıcının doğal dil sorgusu veriliyor.

KULLANICI SORGUSU: "{user_query}"

GÖREV:
1. Kullanıcının sorgusunu CVE araması için OPTIMIZE ET
2. Sorgudan YIL, ÜRÜN ADI, VENDOR, DOMAIN ve NEGATIVE KEYWORDS bilgilerini çıkar
3. Kesin eşleşme gerekip gerekmediğini belirle

KURALLAR:
1. KISA ve NET sorgu (max 5-7 kelime)
2. YIL varsa MUTLAKA çıkar (örn: "2021", "2024") - CVE ID'den veya published date'ten
3. ÜRÜN ADI varsa çıkar (örn: "Log4j", "WordPress", "Kubernetes", "Django")
4. VENDOR varsa çıkar (örn: "Apache", "Microsoft", "TP-Link")
5. DOMAIN belirle: container/kubernetes → "container", os/kernel → "os", cloud → "cloud", iot/router → "iot"
6. LANGUAGE/ECOSYSTEM belirle:
   - Django/Flask/FastAPI → "python"
   - Spring/Dubbo → "java"
   - ThinkPHP/Laravel → "php"
   - React/Vue/Angular → "javascript"
7. PICKLE QUERY tespiti:
   - Eğer query'de "pickle" geçiyorsa → is_pickle_query: true
   - Bu durumda sadece Python pickle CVE'leri kabul edilir
8. NEGATIVE KEYWORDS: Benzer ama farklı ürünleri belirle
   - Log4j → ["logback", "slf4j", "java.util.logging"]
   - Kubernetes → ["windows kernel", "linux kernel"]
   - Core → [".NET Core", "ASP.NET Core"] (eğer query'de "core" başka bir şeyse)
9. Kesin eşleşme: Eğer spesifik ürün adı varsa (örn: "Apache Log4j"), sadece o ürüne ait CVE'ler isteniyor demektir
10. Gereksiz kelimeleri kaldır ("nasıl", "neden", "ne", vb.)
11. İngilizce terimleri tercih et

ÖRNEKLER:
"Apache Log4j 2021" → query: "Apache Log4j", product: "Log4j", vendor: "Apache", year: 2021, exact_product_match: true, negative_keywords: ["logback", "slf4j"]
"TP-Link router authentication bypass" → query: "TP-Link router authentication bypass", vendor: "TP-Link", product: "router", exact_product_match: true, domain: "iot"
"Kubernetes privilege escalation" → query: "Kubernetes privilege escalation", product: "Kubernetes", exact_product_match: true, domain: "container", negative_keywords: ["windows kernel", "linux kernel"]
"WordPress XSS 2024" → query: "WordPress XSS", product: "WordPress", year: 2024, exact_product_match: true
"SQL injection" → query: "SQL injection", exact_product_match: false

JSON formatında döndür:
{{
    "query": "optimize edilmiş sorgu (genel kelimeler çıkarılmış)",
    "year": yıl sayısı veya null,
    "product": "ürün/protokol adı" veya null,
    "vendor": "vendor adı" veya null,
    "domain": "web|container|os|cloud|iot" veya null,
    "language": "python|java|php|javascript" veya null,
    "protocol_type": "protocol|product|os_mechanism" veya null,
    "negative_keywords": ["Windows", "Kernel", "OLE"] veya [],
    "is_pickle_query": true/false,
    "exact_product_match": true/false
}}

ÖNEMLİ:
- "authentication", "authorization", "security" gibi genel kelimeleri query'den ÇIKAR
- Sorguda geçmeyen vendor/product/domain keyword'lerini negative_keywords'a ekle
- OAuth2 gibi protokoller için domain="web" ve negative_keywords=["Windows", "Kernel", "OLE"] olmalı
}}"""

        response = await llm_model.generate_content_async(optimization_prompt)
        
        # Response string veya object olabilir
        response_text = ""
        if isinstance(response, str):
            response_text = response.strip()
        elif hasattr(response, 'text'):
            response_text = response.text.strip()
        elif hasattr(response, 'get'):
            response_text = response.get('text', user_query).strip()
        else:
            response_text = str(response).strip()
        
        # JSON parse et
        import json
        import re
        
        # JSON bloğunu bul
        json_match = re.search(r'\{[^}]+\}', response_text, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                optimized_query = parsed.get('query', user_query).strip('"\'` ')
                year = parsed.get('year')
                if year:
                    try:
                        year = int(year)
                    except:
                        year = None
                product = parsed.get('product')
                if product:
                    product = product.strip('"\'` ')
                vendor = parsed.get('vendor')
                if vendor:
                    vendor = vendor.strip('"\'` ')
                domain = parsed.get('domain')
                if domain:
                    domain = domain.strip('"\'` ')
                language = parsed.get('language')
                if language:
                    language = language.strip('"\'` ')
                protocol_type = parsed.get('protocol_type')
                if protocol_type:
                    protocol_type = protocol_type.strip('"\'` ')
                negative_keywords = parsed.get('negative_keywords', [])
                if isinstance(negative_keywords, str):
                    # String ise listeye çevir
                    negative_keywords = [kw.strip('"\'` ') for kw in negative_keywords.split(',') if kw.strip()]
                elif isinstance(negative_keywords, list):
                    negative_keywords = [str(kw).strip('"\'` ') for kw in negative_keywords if kw]
                else:
                    negative_keywords = []
                is_pickle_query = parsed.get('is_pickle_query', False)
                exact_match = parsed.get('exact_product_match', False)
                
                # Query'den genel kelimeleri çıkar (authentication, authorization, security)
                general_words = ['authentication', 'authorization', 'security', 'vulnerability', 'exploit']
                query_words = optimized_query.lower().split()
                optimized_query = ' '.join([w for w in query_words if w not in general_words])
                if not optimized_query.strip():
                    optimized_query = user_query  # Eğer hepsi çıkarıldıysa orijinali kullan
                
                # Çok uzunsa kes (max 100 karakter)
                if len(optimized_query) > 100:
                    optimized_query = optimized_query[:100]
                
                result = {
                    'query': optimized_query,
                    'year': year,
                    'product': product,
                    'vendor': vendor,
                    'domain': domain,
                    'language': language,
                    'protocol_type': protocol_type,
                    'negative_keywords': negative_keywords,
                    'is_pickle_query': is_pickle_query,
                    'exact_product_match': exact_match
                }
                
                logger.info(f"🤖 Query optimized: '{user_query}' → '{optimized_query}'")
                logger.info(f"   📅 Year: {year}, 📦 Product: {product}, 🏢 Vendor: {vendor}, 🌐 Domain: {domain}, 💻 Language: {language}, 🔐 Protocol: {protocol_type}, 🥒 Pickle: {is_pickle_query}, 🚫 Negative: {negative_keywords}, 🎯 Exact match: {exact_match}")
                return result
            except json.JSONDecodeError:
                logger.warning("JSON parse edilemedi, basit query kullanılıyor")
        
        # Fallback: Basit query - Yıl ve ürün bilgilerini manuel çıkar
        optimized_query = response_text.strip('"\'` ')
        if len(optimized_query) > 100:
            optimized_query = optimized_query[:100]
        
        # Fallback: Yıl ve ürün bilgilerini query'den çıkar
        import re
        fallback_year = None
        fallback_product = None
        fallback_vendor = None
        fallback_domain = None
        fallback_language = None
        fallback_protocol_type = None
        fallback_negative = []
        fallback_is_pickle = False
        
        # Query'den genel kelimeleri çıkar
        general_words = ['authentication', 'authorization', 'security', 'vulnerability', 'exploit']
        query_words = optimized_query.lower().split()
        optimized_query_clean = ' '.join([w for w in query_words if w not in general_words])
        if optimized_query_clean.strip():
            optimized_query = optimized_query_clean
        
        # Yıl çıkar (4 haneli sayı)
        year_match = re.search(r'\b(19|20)\d{2}\b', user_query)
        if year_match:
            try:
                fallback_year = int(year_match.group(0))
            except:
                pass
        
        query_lower = user_query.lower()
        
        # Protocol/Product/OS Mechanism ayrımı
        protocol_keywords = ['oauth2', 'oauth', 'saml', 'ldap', 'kerberos', 'jwt', 'openid']
        os_mechanism_keywords = ['windows authentication', 'linux pam', 'pam', 'ntlm']
        
        if any(kw in query_lower for kw in protocol_keywords):
            fallback_protocol_type = 'protocol'
            fallback_domain = 'web'
            # OAuth2/SAML gibi protokoller için Windows/Kernel negative
            fallback_negative = ['windows', 'kernel', 'ole', 'windows runtime', 'os']
        elif any(kw in query_lower for kw in os_mechanism_keywords):
            fallback_protocol_type = 'os_mechanism'
            fallback_domain = 'os'
        else:
            # Ürün olarak kabul et
            fallback_protocol_type = 'product'
        
        # Domain çıkar
        if any(kw in query_lower for kw in ['kubernetes', 'container', 'docker', 'pod']):
            fallback_domain = 'container'
            if not fallback_negative:
                fallback_negative = ['windows kernel', 'linux kernel']
        elif any(kw in query_lower for kw in ['kernel', 'driver', 'os ', 'operating system']) and fallback_domain != 'web':
            fallback_domain = 'os'
        elif any(kw in query_lower for kw in ['router', 'firmware', 'iot']):
            fallback_domain = 'iot'
        elif any(kw in query_lower for kw in ['cloud', 'aws', 'azure', 'gcp']):
            fallback_domain = 'cloud'
        
        # Language/Ecosystem çıkar
        if any(kw in query_lower for kw in ['django', 'flask', 'fastapi', 'python']):
            fallback_language = 'python'
            if not fallback_negative:
                fallback_negative = ['windows', 'java', 'php']
        elif any(kw in query_lower for kw in ['spring', 'dubbo', 'java']):
            fallback_language = 'java'
            if not fallback_negative:
                fallback_negative = ['windows', 'python', 'php']
        elif any(kw in query_lower for kw in ['thinkphp', 'laravel', 'php']):
            fallback_language = 'php'
            if not fallback_negative:
                fallback_negative = ['windows', 'python', 'java']
        elif any(kw in query_lower for kw in ['react', 'vue', 'angular', 'javascript', 'node']):
            fallback_language = 'javascript'
            if not fallback_negative:
                fallback_negative = ['windows', 'python', 'java', 'php']
        
        # Pickle query tespiti
        if 'pickle' in query_lower:
            fallback_is_pickle = True
            fallback_language = 'python'  # Pickle Python-specific
        
        # Negative keywords (Log4j için)
        if 'log4j' in query_lower:
            fallback_negative = ['logback', 'slf4j', 'java.util.logging']
        
        # Eğer domain web ise ve Windows geçmiyorsa Windows negative
        if fallback_domain == 'web' and 'windows' not in query_lower:
            if 'windows' not in fallback_negative:
                fallback_negative.append('windows')
        
        default_response['query'] = optimized_query
        default_response['year'] = fallback_year
        default_response['domain'] = fallback_domain
        default_response['language'] = fallback_language
        default_response['protocol_type'] = fallback_protocol_type
        default_response['is_pickle_query'] = fallback_is_pickle
        default_response['negative_keywords'] = fallback_negative
        logger.info(f"🤖 Query optimized (fallback): '{user_query}' → '{optimized_query}'")
        logger.info(f"   📅 Year: {fallback_year}, 🌐 Domain: {fallback_domain}, 💻 Language: {fallback_language}, 🔐 Protocol: {fallback_protocol_type}, 🥒 Pickle: {fallback_is_pickle}, 🚫 Negative: {fallback_negative}")
        return default_response
        
    except Exception as e:
        logger.error(f"LLM query oluşturma hatası: {e}")
        logger.warning("LLM query oluşturamadı, basit query kullanılıyor")
        return default_response


def _filter_cve_results(results: List[Any], query_info: Dict[str, Any]) -> List[Any]:
    """
    CVE sonuçlarını query bilgilerine göre KATI kurallarla filtrele
    
    Filtreleme kuralları:
    1. Vendor ZORUNLU: Query'de vendor varsa, sonuçlardaki vendor TAM EŞLEŞMELİ
    2. Product HARD FILTER: CVE.description VEYA CPE içinde sorgudaki ürün geçmiyorsa → DROP
    3. Language/Ecosystem FILTER: Django → Python only, Spring → Java only, ThinkPHP → PHP only
    4. Pickle FILTER: Pickle sorgusu varsa sadece Python pickle CVE'leri (pickle, __reduce__, joblib, cloudpickle, marshal)
    5. Domain Ayrımı: Container/Kubernetes sorgularında OS kernel CVE'leri drop
    6. Negative Keywords: Log4j sorgusunda logback, slf4j gibi benzer ürünleri drop
    7. Year FILTER: CVE.year != query.year → DROP (published_date öncelikli)
    8. Generic CVE Boost: Domain uyumu yoksa relevance = 0 (false positive önleme)
    """
    if not results or not query_info:
        return results
    
    year = query_info.get('year')
    product = query_info.get('product')
    vendor = query_info.get('vendor')
    exact_match = query_info.get('exact_product_match', False)
    domain = query_info.get('domain')  # container, os, cloud, iot, web
    language = query_info.get('language')  # python, java, php, javascript
    protocol_type = query_info.get('protocol_type')  # protocol, product, os_mechanism
    is_pickle_query = query_info.get('is_pickle_query', False)
    negative_keywords = query_info.get('negative_keywords', [])  # Drop edilecek kelimeler
    
    filtered = []
    
    for result in results:
        result_cve_id = result.cve_id or result.get('cve_id', '')
        result_product = result.product or result.get('product', '')
        result_vendor = result.vendor or result.get('vendor', '')
        description = result.description or result.get('description', '')
        published_date = result.published_date or result.get('published_date')
        
        # Normalize et (case-insensitive)
        result_product_lower = result_product.lower() if result_product else ''
        result_vendor_lower = result_vendor.lower() if result_vendor else ''
        description_lower = description.lower() if description else ''
        
        # 1️⃣ VENDOR ZORUNLU FİLTRE
        if vendor:
            vendor_lower = vendor.lower()
            # Vendor TAM EŞLEŞMELİ olmalı
            vendor_match = (
                vendor_lower == result_vendor_lower or
                vendor_lower in result_vendor_lower or
                result_vendor_lower in vendor_lower
            )
            
            if not vendor_match:
                logger.debug(f"⏭️  CVE {result_cve_id} vendor uyuşmuyor: query='{vendor}' != result='{result_vendor}'")
                continue
        
        # 2️⃣ PRODUCT HARD FILTER (EN KRİTİK)
        # CVE.description VEYA CPE içinde sorgudaki ürün geçmiyorsa → DROP
        if product:
            product_lower = product.lower()
            
            # Product retrieved.product VEYA description'da olmalı
            product_in_product_field = (
                product_lower in result_product_lower or
                result_product_lower in product_lower
            )
            
            product_in_description = product_lower in description_lower
            
            # CPE bilgisi metadata'da olabilir (cvss_vector veya metadata'dan çıkarılabilir)
            # Şimdilik description ve product field'larına bakıyoruz
            
            # HARD FILTER: Product description VEYA product field'da OLMALI
            if not (product_in_product_field or product_in_description):
                logger.debug(f"⏭️  CVE {result_cve_id} PRODUCT HARD FILTER: query='{product}' not in product='{result_product}' or description → DROP")
                continue
            
            # Kesin eşleşme gerekiyorsa sadece product field'da olmalı
            if exact_match:
                if not product_in_product_field:
                    logger.debug(f"⏭️  CVE {result_cve_id} product kesin eşleşmiyor: query='{product}' not in product='{result_product}'")
                    continue
        
        # 3️⃣ LANGUAGE/ECOSYSTEM FILTER
        # Cross-language CVE = false positive
        if language:
            language_lower = language.lower()
            
            # Python ecosystem keywords
            python_keywords = ['python', 'django', 'flask', 'fastapi', 'pickle', '__reduce__', 'joblib', 'cloudpickle', 'marshal', 'pypi']
            # Java ecosystem keywords
            java_keywords = ['java', 'spring', 'dubbo', 'maven', 'gradle', 'jvm', 'jre', 'jdk']
            # PHP ecosystem keywords
            php_keywords = ['php', 'thinkphp', 'laravel', 'symfony', 'composer', 'pear']
            # JavaScript ecosystem keywords
            js_keywords = ['javascript', 'node', 'react', 'vue', 'angular', 'npm', 'yarn', 'typescript']
            
            # Description ve product'ta language-specific keyword var mı?
            has_language_keyword = False
            
            if language_lower == 'python':
                has_language_keyword = any(kw in description_lower or kw in result_product_lower for kw in python_keywords)
                # Eğer Java/PHP/JS keyword'ü varsa drop
                if any(kw in description_lower or kw in result_product_lower for kw in java_keywords + php_keywords + js_keywords):
                    if not has_language_keyword:
                        logger.debug(f"⏭️  CVE {result_cve_id} LANGUAGE FILTER: Python query but Java/PHP/JS keyword found")
                        continue
            elif language_lower == 'java':
                has_language_keyword = any(kw in description_lower or kw in result_product_lower for kw in java_keywords)
                # Eğer Python/PHP/JS keyword'ü varsa drop
                if any(kw in description_lower or kw in result_product_lower for kw in python_keywords + php_keywords + js_keywords):
                    if not has_language_keyword:
                        logger.debug(f"⏭️  CVE {result_cve_id} LANGUAGE FILTER: Java query but Python/PHP/JS keyword found")
                        continue
            elif language_lower == 'php':
                has_language_keyword = any(kw in description_lower or kw in result_product_lower for kw in php_keywords)
                # Eğer Python/Java/JS keyword'ü varsa drop
                if any(kw in description_lower or kw in result_product_lower for kw in python_keywords + java_keywords + js_keywords):
                    if not has_language_keyword:
                        logger.debug(f"⏭️  CVE {result_cve_id} LANGUAGE FILTER: PHP query but Python/Java/JS keyword found")
                        continue
            elif language_lower == 'javascript':
                has_language_keyword = any(kw in description_lower or kw in result_product_lower for kw in js_keywords)
                # Eğer Python/Java/PHP keyword'ü varsa drop
                if any(kw in description_lower or kw in result_product_lower for kw in python_keywords + java_keywords + php_keywords):
                    if not has_language_keyword:
                        logger.debug(f"⏭️  CVE {result_cve_id} LANGUAGE FILTER: JavaScript query but Python/Java/PHP keyword found")
                        continue
            
            # Language keyword yoksa ve language belirtilmişse drop
            if not has_language_keyword:
                logger.debug(f"⏭️  CVE {result_cve_id} LANGUAGE FILTER: {language} query but no {language} keyword found")
                continue
        
        # 3️⃣ PICKLE-SPECIFIC FILTER
        # "pickle" ≠ "deserialization" - Pickle Python-specific
        if is_pickle_query:
            pickle_keywords = ['pickle', '__reduce__', 'joblib', 'cloudpickle', 'marshal']
            has_pickle_keyword = any(kw in description_lower or kw in result_product_lower for kw in pickle_keywords)
            
            if not has_pickle_keyword:
                logger.debug(f"⏭️  CVE {result_cve_id} PICKLE FILTER: Pickle query but no pickle keyword found")
                continue
            
            # Java deserialization veya PHP unserialize varsa drop
            if 'java deserialization' in description_lower or 'php unserialize' in description_lower:
                logger.debug(f"⏭️  CVE {result_cve_id} PICKLE FILTER: Pickle query but Java/PHP deserialization found")
                continue
        
        # 4️⃣ DOMAIN AYIRIMI
        if domain:
            # Container/Kubernetes sorgularında OS kernel CVE'leri drop
            if domain in ['container', 'kubernetes', 'docker']:
                # OS kernel keywords
                kernel_keywords = ['kernel', 'linux kernel', 'windows kernel', 'driver', 'privilege escalation os']
                if any(kw in description_lower for kw in kernel_keywords):
                    # Ama Kubernetes/container keyword'ü yoksa drop
                    container_keywords = ['kubernetes', 'container', 'docker', 'pod', 'namespace']
                    if not any(ck in description_lower for ck in container_keywords):
                        logger.debug(f"⏭️  CVE {result_cve_id} domain uyuşmuyor: OS kernel CVE dropped (domain={domain})")
                        continue
            
            # OS sorgularında container CVE'leri drop
            elif domain == 'os':
                container_keywords = ['kubernetes', 'container', 'docker', 'pod']
                if any(ck in description_lower for ck in container_keywords):
                    logger.debug(f"⏭️  CVE {result_cve_id} domain uyuşmuyor: Container CVE dropped (domain={domain})")
                    continue
        
        # 5️⃣ NEGATIVE KEYWORD DROP RULES (KRİTİK)
        # Sorguda geçmeyen vendor/product/domain keyword'leri varsa → DROP
        if negative_keywords:
            should_drop = False
            for neg_keyword in negative_keywords:
                neg_lower = neg_keyword.lower()
                # Description, product, vendor veya CVE ID'de negative keyword varsa drop
                if (neg_lower in description_lower or 
                    neg_lower in result_product_lower or 
                    neg_lower in result_vendor_lower or
                    neg_lower in result_cve_id.lower()):
                    logger.debug(f"⏭️  CVE {result_cve_id} NEGATIVE FILTER: Negative keyword '{neg_keyword}' found → DROP")
                    should_drop = True
                    break
            
            if should_drop:
                continue
        
        # 6️⃣ PROTOCOL/PRODUCT/OS MECHANISM AYRIMI
        # OAuth2 ≠ Windows Authentication
        if protocol_type:
            if protocol_type == 'protocol':
                # Protocol sorgusu (OAuth2, SAML, LDAP) - OS mechanism keyword'leri drop
                os_mechanism_keywords = ['windows authentication', 'ntlm', 'pam', 'linux pam', 'os authentication']
                if any(kw in description_lower or kw in result_product_lower for kw in os_mechanism_keywords):
                    logger.debug(f"⏭️  CVE {result_cve_id} PROTOCOL FILTER: Protocol query but OS mechanism keyword found → DROP")
                    continue
            
            elif protocol_type == 'os_mechanism':
                # OS mechanism sorgusu - Protocol keyword'leri drop (eğer OS keyword yoksa)
                protocol_keywords = ['oauth2', 'oauth', 'saml', 'ldap', 'jwt', 'openid']
                os_keywords = ['windows authentication', 'ntlm', 'pam', 'linux pam', 'os authentication']
                has_protocol_keyword = any(kw in description_lower or kw in result_product_lower for kw in protocol_keywords)
                has_os_keyword = any(kw in description_lower or kw in result_product_lower for kw in os_keywords)
                
                if has_protocol_keyword and not has_os_keyword:
                    logger.debug(f"⏭️  CVE {result_cve_id} OS MECHANISM FILTER: OS mechanism query but protocol keyword found (no OS keyword) → DROP")
                    continue
        
        # 7️⃣ YEAR FILTER (GERÇEKTEN UYGULANSIN)
        # CVE.year != query.year → DROP
        if year:
            published_year = None
            cve_id_year = None
            
            # ÖNCELİK: published_date'e bak
            if published_date:
                try:
                    # Yıl formatı: "2021-12-10" veya "2021"
                    published_year = int(str(published_date)[:4])
                except:
                    pass
            
            # CVE ID'den yıl çıkar
            try:
                if 'CVE-' in result_cve_id:
                    cve_id_year = int(result_cve_id.split('-')[1])
            except:
                pass
            
            # KATI YIL FİLTRESİ: published_year == query_year VEYA cve_id_year == query_year
            year_match = False
            
            if published_year is not None:
                # Published yılı varsa öncelik ver - TAM EŞLEŞME GEREKLİ
                if published_year == year:
                    year_match = True
            elif cve_id_year is not None:
                # Published yılı yoksa CVE ID yılına bak - TAM EŞLEŞME GEREKLİ
                if cve_id_year == year:
                    year_match = True
            
            # Yıl eşleşmiyorsa KESİNLİKLE DROP
            if not year_match:
                logger.debug(f"⏭️  CVE {result_cve_id} YEAR FILTER: published={published_year}, cve_id={cve_id_year}, query={year} → DROP")
                continue
        
        # 8️⃣ GENERIC CVE BOOST KAPATILMASI
        # Domain uyumu yoksa relevance = 0 (false positive önleme)
        # Generic CVE'ler ("critical", "network", "deserialization") domain uyumu olmadan boost edilmemeli
        if domain:
            domain_keywords = {
                'container': ['kubernetes', 'container', 'docker', 'pod', 'namespace'],
                'os': ['kernel', 'driver', 'operating system', 'os'],
                'cloud': ['cloud', 'aws', 'azure', 'gcp', 'managed service'],
                'iot': ['router', 'firmware', 'iot', 'embedded']
            }
            
            generic_keywords = ['critical', 'network', 'deserialization']
            has_generic_keyword = any(kw in description_lower for kw in generic_keywords)
            
            if domain in domain_keywords:
                has_domain_keyword = any(kw in description_lower for kw in domain_keywords[domain])
                
                # Generic keyword varsa ama domain keyword yoksa → DROP (false positive)
                if has_generic_keyword and not has_domain_keyword:
                    logger.debug(f"⏭️  CVE {result_cve_id} GENERIC CVE BOOST: Generic keyword found but no domain={domain} keyword → DROP")
                    continue
        
        filtered.append(result)
    
    logger.info(f"🔍 KATI Filtreleme: {len(results)} → {len(filtered)} sonuç (yıl={year}, product={product}, vendor={vendor}, domain={domain}, language={language}, protocol={protocol_type}, pickle={is_pickle_query}, exact={exact_match}, negative={len(negative_keywords)})")
    return filtered


# ==================== RAG ENDPOINTS ====================

@app.post("/api/rag/search")
async def rag_search(request: Dict[str, Any]):
    """
    RAG sistemi üzerinde CVE araması yap (AI ile query optimization).
    
    Body:
        - query: Arama sorgusu (AI ile optimize edilecek)
        - limit: Maksimum sonuç sayısı (default: 5)
        - severity: Opsiyonel severity filtresi (CRITICAL, HIGH, MEDIUM, LOW)
    """
    try:
        original_query = request.get("query", "").strip()
        requested_limit = int(request.get("limit", 5))
        limit = min(requested_limit, 5)  # Max 5 - Reranker için sabit
        severity = request.get("severity")
        
        if not original_query:
            raise HTTPException(status_code=400, detail="Query gerekli")
        
        # RAG servisini al
        rag_service = get_rag_service()
        if not rag_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="RAG servisi kullanılamıyor. Qdrant'ın çalıştığından emin olun."
            )
        
        logger.info(f"🔍 RAG Search: query='{original_query}', limit={limit} (requested={requested_limit})")
        
        # 🤖 AI ile query'yi optimize et ve filtre bilgilerini çıkar
        query_info = await optimize_rag_query(original_query)
        optimized_query = query_info.get('query', original_query)
        
        # CVE araması yap (optimize edilmiş query ile, reranker ZORUNLU)
        # Daha fazla sonuç çek (filtreleme için)
        results = rag_service.search_cve(
            optimized_query, 
            limit=limit * 3,  # Daha fazla sonuç çek (filtreleme için)
            severity=severity, 
            use_reranker=True,
            query_info=query_info  # Filtre bilgilerini geç
        )
        
        # Sonuçları filtrele (yıl, ürün, vendor kontrolü)
        results = _filter_cve_results(results, query_info)
        
        # Limit'e göre kes
        results = results[:limit]
        
        logger.info(f"✅ RAG Search tamamlandı: {len(results)} sonuç döndürülüyor (reranker aktif)")
        
        # Response body size kontrolü - Memory protection (0.6 MB limit)
        response_data = {
            "success": True,
            "original_query": original_query,
            "optimized_query": optimized_query,
            "query": optimized_query,  # Backward compatibility
            "query_info": query_info,  # Filtre bilgileri
            "total_results": len(results),
            "severity_filter": severity,
            "results": [r.to_dict() for r in results]
        }
        
        # Response size kontrolü - max 500KB
        import sys
        response_size = sys.getsizeof(str(response_data))
        if response_size > 500_000:  # 500KB
            logger.warning(f"⚠️ Response çok büyük ({response_size} bytes), truncate ediliyor")
            # Truncate results if too large
            response_data["results"] = response_data["results"][:3]
            response_data["truncated"] = True
            response_data["total_results"] = len(response_data["results"])
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RAG arama hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rag/cve/{cve_id}")
async def get_cve_by_id(cve_id: str):
    """
    CVE ID ile direkt CVE detayı getir.
    
    Args:
        cve_id: CVE ID (ör: CVE-2024-12345)
    """
    try:
        rag_service = get_rag_service()
        if not rag_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="RAG servisi kullanılamıyor"
            )
        
        result = rag_service.get_cve_by_id(cve_id)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"CVE bulunamadı: {cve_id}")
        
        return {
            "success": True,
            "cve": result.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CVE getirme hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rag/analyze-scan")
async def analyze_scan_results(request: Dict[str, Any]):
    """
    Tarama sonuçlarını analiz edip ilgili CVE'leri bul.
    
    Body:
        - scan_results: Tarama sonuçları
        - limit: Maksimum sonuç sayısı (default: 5)
    """
    try:
        scan_results = request.get("scan_results", {})
        limit = min(int(request.get("limit", 5)), 20)
        
        if not scan_results:
            raise HTTPException(status_code=400, detail="scan_results gerekli")
        
        rag_service = get_rag_service()
        if not rag_service.is_available():
            raise HTTPException(
                status_code=503,
                detail="RAG servisi kullanılamıyor"
            )
        
        # Scan sonuçlarını analiz et
        analysis_result = rag_service.analyze_scan_results(scan_results)
        results = analysis_result.get('results', [])
        results = results[:limit]  # Limit uygula
        
        # Response data hazırla
        response_data = {
            "success": True,
            "total_results": len(results),
            "results": [r.to_dict() for r in results],
            "llm_query": analysis_result.get('query', ''),
            "scan_summary": analysis_result.get('summary', '')
        }
        
        # Response size kontrolü - Memory protection (max 500KB)
        import sys
        response_size = sys.getsizeof(str(response_data))
        if response_size > 500_000:  # 500KB
            logger.warning(f"⚠️ Analyze response çok büyük ({response_size} bytes), truncate ediliyor")
            # Truncate
            response_data["results"] = response_data["results"][:2]
            response_data["scan_summary"] = response_data["scan_summary"][:500]  # İlk 500 karakter
            response_data["truncated"] = True
            response_data["total_results"] = len(response_data["results"])
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scan analizi hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/rag/stats")
async def get_rag_stats():
    """RAG servis istatistikleri"""
    try:
        rag_service = get_rag_service()
        stats = rag_service.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Stats hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/reports/{report_id}/download")
async def download_report(report_id: str, format: str = "pdf"):
    """
    Raporu belirtilen formatta indir.
    
    Params:
        - report_id: Rapor ID'si
        - format: İndirme formatı (pdf, txt, json)
    """
    try:
        import os
        from fastapi.responses import FileResponse
        
        # Dosya yolunu oluştur
        report_path = f"reports/{report_id}.{format}"
        
        if not os.path.exists(report_path):
            raise HTTPException(status_code=404, detail="Rapor dosyası bulunamadı")
        
        # Dosya tipine göre media type belirle
        media_types = {
            "pdf": "application/pdf",
            "txt": "text/plain",
            "json": "application/json",
            "md": "text/markdown"
        }
        
        media_type = media_types.get(format, "application/octet-stream")
        
        return FileResponse(
            path=report_path,
            media_type=media_type,
            filename=f"{report_id}.{format}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rapor indirme hatası: {e}")
        raise HTTPException(status_code=500, detail=f"Rapor indirilemedi: {str(e)}")

def _map_cvss_to_severity(cvss_score):
    """CVSS skorunu severity'e map et"""
    try:
        score = float(cvss_score)
        if score >= 9.0:
            return 'critical'
        elif score >= 7.0:
            return 'high'
        elif score >= 4.0:
            return 'medium'
        else:
            return 'low'
    except:
        return 'medium'

@app.post("/api/generate-report")
async def generate_security_report(request: Dict[str, Any]):
    """
    RAG CVE entegrasyonu ile güvenlik raporu oluştur.
    
    Body:
        - target: Hedef sistem
        - scan_results: Tarama sonuçları
        - cve_results: RAG'dan gelen en alakalı CVE'ler (top 3)
    """
    try:
        target = request.get("target", "Unknown Target")
        scan_results = request.get("scan_results", {})
        cve_results = request.get("cve_results", [])
        llm_query = request.get("llm_query", "")  # LLM'in oluşturduğu sorgu
        scan_summary = request.get("scan_summary", "")  # Tarama özeti
        
        if not scan_results:
            raise HTTPException(status_code=400, detail="scan_results gerekli")
        
        logger.info(f"Rapor oluşturuluyor - Target: {target}, CVE count: {len(cve_results)}")
        logger.info(f"LLM Query: {llm_query[:100] if llm_query else 'Yok'}...")
        logger.info(f"Scan Summary: {scan_summary[:100] if scan_summary else 'Yok'}...")
        
        # ReportGenerator'ı import et
        from agent_core.report_generator import ReportGenerator
        from agent_core.state import AgentState
        from datetime import datetime as dt
        
        # AgentState oluştur
        state = AgentState(target=target, user_task="Güvenlik raporu oluştur")
        state.start_time = dt.now()
        state.findings = []  # Findings listesini başlat
        state.discovered_information = {}  # Discovered information'ı başlat
        
        # ÖNCELİKLE: Gerçek tarama bulgularını ekle (scan_results'tan)
        logger.info(f"Scan results tipi: {type(scan_results)}, içerik: {list(scan_results.keys()) if isinstance(scan_results, dict) else 'dict değil'}")
        
        # scan_results'dan SADECE GERÇEK BULGULARI çıkar - TEMİZ PARSING
        findings_added = 0
        if isinstance(scan_results, dict):
            logger.info(f"🔍 Scan results keys: {list(scan_results.keys())}")
            
            # Tool sonuçlarını kontrol et
            for key, value in scan_results.items():
                if isinstance(value, dict):
                    logger.info(f"📊 Processing tool: {key}")
                    
                    # Tool sonucu mu?
                    if value.get('success') and value.get('data'):
                        tool_data = value.get('data', {})
                        logger.info(f"📋 Tool {key} data keys: {list(tool_data.keys()) if isinstance(tool_data, dict) else 'not dict'}")
                        
                        # SADECE GERÇEK ZAFİYETLERİ BUL - vulnerabilities/findings/results
                        vulnerabilities = tool_data.get('vulnerabilities', [])
                        findings = tool_data.get('findings', [])
                        results = tool_data.get('results', [])
                        
                        # Directory bruteforce findings dict formatını kontrol et
                        if key == 'enum_directory_bruteforce' and isinstance(tool_data.get('findings'), dict):
                            findings_dict = tool_data.get('findings', {})
                            critical_findings = findings_dict.get('critical', [])
                            high_findings = findings_dict.get('high', [])
                            info_findings = findings_dict.get('informational', [])
                            
                            # Tüm findings'leri birleştir
                            all_dir_findings = critical_findings + high_findings + info_findings
                            for dir_finding in all_dir_findings:
                                if isinstance(dir_finding, dict):
                                    path = dir_finding.get('path', '')
                                    url = dir_finding.get('url', '')
                                    status = dir_finding.get('status_code', 200)
                                    
                                    # Severity belirle
                                    if dir_finding in critical_findings:
                                        severity = 'critical'
                                        cvss = '9.0'
                                    elif dir_finding in high_findings:
                                        severity = 'high'
                                        cvss = '7.5'
                                    else:
                                        severity = 'info'
                                        cvss = 'N/A'
                                    
                                    finding = {
                                        'title': f'Dizin/Dosya Bulundu: {path}',
                                        'severity': severity,
                                        'description': f'Dizin veya dosya erişilebilir: {path} (Status: {status})',
                                        'cvss_score': cvss,
                                        'cve_id': None,
                                        'evidence': f'URL: {url}, Status: {status}, Size: {dir_finding.get("content_length", "N/A")}',
                                        'recommendation_summary': 'Hassas dizin ve dosyalara erişimi kısıtlayın' if severity in ['critical', 'high'] else 'Dizin listelerini kontrol edin',
                                        'business_impact': 'Hassas bilgilere yetkisiz erişim riski' if severity in ['critical', 'high'] else 'Sistem yapısı hakkında bilgi sızıntısı',
                                        'exploitability': 'High' if severity in ['critical', 'high'] else 'Low',
                                        'target': url or target,
                                        'technology': 'Web Server'
                                    }
                                    state.findings.append(finding)
                                    findings_added += 1
                                    logger.info(f"✅ Directory bruteforce bulgusu eklendi: {path} - Severity: {severity}")
                        
                        # Port tarama sonuçlarını da kontrol et
                        open_ports = tool_data.get('open_ports', [])
                        if open_ports and isinstance(open_ports, list) and len(open_ports) > 0:
                            port_count = len(open_ports)
                            critical_ports = [p for p in open_ports if isinstance(p, dict) and str(p.get('port', '')).strip() in ['22', '3389', '5900', '23', '21']]
                            severity = 'high' if critical_ports else 'medium'
                            cvss = '7.5' if critical_ports else '5.0'
                            
                            port_details = ', '.join([f"{p.get('port', 'N/A')}/{p.get('service', 'unknown')}" for p in open_ports[:10] if isinstance(p, dict)])
                            
                            finding = {
                                'title': f'Açık Portlar: {port_count} port tespit edildi',
                                'severity': severity,
                                'description': f'Sistemde {port_count} açık port bulundu. Kritik portlar: {len(critical_ports)} adet. Portlar: {port_details}',
                                'cvss_score': cvss,
                                'cve_id': None,
                                'evidence': f'Open ports: {port_details}',
                                'recommendation_summary': 'Gereksiz portları kapatın ve güvenlik duvarı kurallarını gözden geçirin',
                                'business_impact': 'Açık portlar saldırı yüzeyini artırır',
                                'exploitability': 'High' if critical_ports else 'Medium',
                                'target': target,
                                'technology': 'Network Services'
                            }
                            state.findings.append(finding)
                            findings_added += 1
                            logger.info(f"✅ Port tarama bulgusu eklendi: {port_count} açık port")
                        
                        # Subdomain sonuçlarını kontrol et
                        subdomains = tool_data.get('subdomains', [])
                        if subdomains and isinstance(subdomains, list) and len(subdomains) > 0:
                            # Subdomain'ler dict veya string olabilir
                            subdomain_list = []
                            for sub in subdomains:
                                if isinstance(sub, dict):
                                    subdomain_list.append(sub.get('subdomain', sub.get('url', str(sub))))
                                elif isinstance(sub, str):
                                    subdomain_list.append(sub)
                            
                            if subdomain_list:
                                subdomain_count = len(subdomain_list)
                                subdomain_str = ', '.join(subdomain_list[:10])
                                
                                finding = {
                                    'title': f'Subdomain Keşfi: {subdomain_count} subdomain bulundu',
                                    'severity': 'medium',
                                    'description': f'{subdomain_count} subdomain tespit edildi, saldırı yüzeyi genişledi. Subdomainler: {subdomain_str}',
                                    'cvss_score': '5.0',
                                    'cve_id': None,
                                    'evidence': f'Subdomains: {subdomain_str}',
                                    'recommendation_summary': 'Tüm subdomainlerin güvenliğini kontrol edin',
                                    'business_impact': 'Genişletilmiş saldırı yüzeyi',
                                    'exploitability': 'Medium',
                                    'target': target,
                                    'technology': 'DNS'
                                }
                                state.findings.append(finding)
                                findings_added += 1
                                logger.info(f"✅ Subdomain bulgusu eklendi: {subdomain_count} subdomain")
                        
                        # Tüm gerçek bulguları işle
                        all_real_findings = vulnerabilities + findings + results
                        for item in all_real_findings:
                            if isinstance(item, dict):
                                # Severity belirle
                                severity = item.get('severity', 'medium').lower()
                                title = item.get('title') or item.get('name') or item.get('vulnerability', 'Tespit Edilen Zafiyet')
                                
                                # CVSS skoruna göre severity belirle
                                cvss_score = item.get('cvss_score') or item.get('cvss', 'N/A')
                                if cvss_score != 'N/A':
                                    try:
                                        cvss_float = float(cvss_score)
                                        if cvss_float >= 9.0:
                                            severity = 'critical'
                                        elif cvss_float >= 7.0:
                                            severity = 'high'
                                        elif cvss_float >= 4.0:
                                            severity = 'medium'
                                        else:
                                            severity = 'low'
                                    except:
                                        pass
                                
                                finding = {
                                    'title': title,
                                    'severity': severity,
                                    'description': item.get('description') or item.get('details') or 'Zafiyet tespit edildi',
                                    'cvss_score': cvss_score,
                                    'cve_id': item.get('cve_id') or item.get('cve'),
                                    'evidence': item.get('evidence') or item.get('proof') or item.get('payload', 'Detay mevcut'),
                                    'recommendation_summary': item.get('recommendation') or item.get('remediation', 'Zafiyet kapatılmalıdır'),
                                    'business_impact': item.get('business_impact', 'Güvenlik riski oluşturmaktadır'),
                                    'exploitability': item.get('exploitability', 'Unknown'),
                                    'target': item.get('url') or item.get('endpoint') or target,
                                    'technology': item.get('technology') or item.get('service')
                                }
                                state.findings.append(finding)
                                findings_added += 1
                                logger.info(f"✅ Gerçek bulgu eklendi: {title} - Severity: {severity}")
                    
                    # EĞER TOOL DATA'DA VULNERABILITIES/FINDINGS YOKSA - SADECE KRİTİK BULGULAR
                    elif value.get('success') and isinstance(value.get('data'), dict):
                        tool_data = value.get('data', {})
                        
                        # SADECE GERÇEK KRİTİK BULGULAR - Bilgi toplama değil!
                        # Kritik dosyalar (.env, .git, backup dosyaları)
                        if key == 'enum_directory_bruteforce':
                            files = tool_data.get('files', [])
                            critical_files = [f for f in files if isinstance(f, dict) and 
                                             any(keyword in f.get('path', '').lower() 
                                                 for keyword in ['.env', '.git', '.gitignore', 'backup.sql', 'database.sql', 'config.php', 'wp-config.php'])]
                            
                            for file_info in critical_files:
                                path = file_info.get('path', '')
                                finding = {
                                    'title': f'Kritik Dosya Erişilebilir: {path}',
                                    'severity': 'critical',
                                    'description': f'Kritik dosya public erişime açık: {path}',
                                    'cvss_score': '9.0',
                                    'cve_id': None,
                                    'evidence': f'File accessible: {path}, Status: {file_info.get("status", "200")}',
                                    'recommendation_summary': 'Kritik dosyaları public erişimden kaldırın',
                                    'business_impact': 'Kritik dosyalar sistem güvenliğini tehlikeye atabilir',
                                    'exploitability': 'High',
                                    'target': target,
                                    'technology': 'Web Application'
                                }
                                state.findings.append(finding)
                                findings_added += 1
                                logger.info(f"✅ Kritik dosya bulundu: {path}")
                        
                        # RAG analysis data'dan SADECE kritik endpoint'leri kontrol et (bulgu değil, bilgi)
                        elif 'rag_analysis_data' in tool_data:
                            # Bu bilgi toplama, bulgu değil - skip et
                            logger.debug(f"RAG data bulundu ama bulgu değil, skip ediliyor: {key}")
                            pass
                        
                        # Diğer tool'lar - SADECE GERÇEK BULGULAR (vulnerabilities/findings/results zaten yukarıda işlendi)
                        # Bilgi toplama sonuçları bulgu değildir - skip et
                        else:
                            logger.debug(f"Tool {key} - vulnerabilities/findings/results yok, skip ediliyor")
        
        logger.info(f"Tarama sonuçlarından {findings_added} bulgu eklendi")
        
        # EĞER HİÇ BULGU YOKSA - Bu normal, yapay bulgu üretme!
        if findings_added == 0:
            logger.debug(f"Hiç bulgu bulunamadı - Bu normal bir durum.")
            # Bulgu yoksa bulgu yok - yapay bulgu üretme!
        
        logger.info(f"✅ TOPLAM BULGU: {len(state.findings)}")
        
        # SONRA: RAG CVE sonuçlarını referans olarak ekle (sadece ilişkili CVE'ler)
        logger.info(f"🔍 CVE Results: {cve_results}")
        for i, cve in enumerate(cve_results[:3], 1):  # En yakın 3 CVE
            # CVSS skorunu doğru çek
            cvss_score = cve.get('cvss_score') or cve.get('base_score') or cve.get('cvss') or cve.get('baseScore', 'N/A')
            
            # CVE açıklamasını düzgün çek
            description = cve.get('description', 'Açıklama mevcut değil')
            if description == 'Açıklama mevcut değil' or not description or description.strip() == '':
                # RAG servisinden CVE detayını çek
                try:
                    rag_service = get_rag_service()
                    if rag_service.is_available():
                        cve_id = cve.get('cve_id', f'CVE-{i}')
                        logger.info(f"🔍 CVE ID için detay çekiliyor: {cve_id}")
                        cve_detail = rag_service.get_cve_by_id(cve_id)
                        if cve_detail:
                            description = cve_detail.description or f"{cve_id} güvenlik açığı tespit edildi"
                            cvss_score = cve_detail.base_score or cvss_score
                            logger.info(f"✅ CVE detayı çekildi: {description[:100]}...")
                        else:
                            description = f"{cve_id} güvenlik açığı tespit edildi"
                            logger.warning(f"⚠️ CVE detayı bulunamadı: {cve_id}")
                except Exception as e:
                    logger.warning(f"CVE detayı çekilemedi: {e}")
                    description = f"{cve.get('cve_id', f'CVE-{i}')} güvenlik açığı tespit edildi"
            
            finding = {
                'title': f"Iliskili CVE: {cve.get('cve_id', f'CVE-{i}')}",
                'severity': _map_cvss_to_severity(cvss_score),
                'description': description[:500],  # İlk 500 karakter
                'cvss_score': cvss_score,
                'cve_id': cve.get('cve_id', 'N/A'),
                'evidence': f"RAG Eşleşme Skoru: %{cve.get('score', 0)*100:.1f}\n\nCVSS Vektör: {cve.get('cvss_vector') or cve.get('vector', 'N/A')}\n\n{description}",
                'recommendation_summary': f"Bu CVE ile ilişkili zafiyetleri kontrol edin. CVSS Skoru: {cvss_score}",
                'business_impact': f"Bu zafiyet, CVSS skoru {cvss_score} olan bilinen bir güvenlik açığıdır.",
                'exploitability': 'Known CVE',
                'target': target,
                'technology': cve.get('affected_product') or cve.get('product')
            }
            state.findings.append(finding)
        
        logger.info(f"Toplam {len(state.findings)} bulgu raporda yer alacak")
        
        # Bulguları ayır: Tool sonuçları ve CVE'ler
        tool_findings = [f for f in state.findings if not f.get('title', '').startswith('Iliskili CVE')]
        cve_findings = [f for f in state.findings if f.get('title', '').startswith('Iliskili CVE')]
        
        logger.info(f"Tool bulguları: {len(tool_findings)}, CVE bulguları: {len(cve_findings)}")
        
        # RAG ENTEGRASYONU - Tool bulgularını RAG'a gönder
        if tool_findings:
            try:
                logger.info(f"🔍 {len(tool_findings)} tool bulgusu RAG'a gönderiliyor...")
                
                # RAG servisini al
                rag_service = await get_rag_service()
                
                # Scan results formatında hazırla
                scan_results_for_rag = {
                    "target": target,
                    "findings": tool_findings
                }
                
                # Tool sonuçlarını da ekle
                for key, value in scan_results.items():
                    if key not in {'target', 'user_task', 'start_time', 'end_time', 'execution_time', 'status', 'conversation_id'}:
                        scan_results_for_rag[f"tool_{key}"] = value
                
                # RAG'dan optimize query oluştur
                optimized_query = await rag_service.generate_optimized_query(scan_results_for_rag)
                
                if optimized_query and optimized_query != "web application security vulnerability exploitation":
                    logger.info(f"✅ RAG query oluşturuldu: {optimized_query}")
                    
                    # RAG'dan CVE'leri ara
                    rag_results = rag_service.search_cve(optimized_query, limit=3)
                    
                    if rag_results:
                        logger.info(f"🎯 RAG'dan {len(rag_results)} CVE bulundu")
                        # CVE'leri findings'e ekle
                        for i, cve in enumerate(rag_results[:3], 1):
                            # CVEResult objesini dict'e çevir
                            if hasattr(cve, 'to_dict'):
                                cve_dict = cve.to_dict()
                            else:
                                cve_dict = cve
                            
                            # CVE açıklamasını kontrol et
                            description = cve_dict.get('description', 'Açıklama mevcut değil')
                            if not description or description.strip() == '' or description == 'Açıklama mevcut değil':
                                description = f"{cve_dict.get('cve_id', f'CVE-{i}')} güvenlik açığı tespit edildi"
                            
                            finding = {
                                'title': f"RAG CVE: {cve_dict.get('cve_id', f'CVE-{i}')}",
                                'severity': _map_cvss_to_severity(cve_dict.get('base_score', 5.0)),
                                'description': description[:500],
                                'cvss_score': cve_dict.get('base_score', 'N/A'),
                                'cve_id': cve_dict.get('cve_id', 'N/A'),
                                'evidence': f"RAG Query: {optimized_query}\n\n{description}",
                                'recommendation_summary': f"Bu CVE ile ilişkili zafiyetleri kontrol edin. CVSS: {cve_dict.get('base_score', 'N/A')}",
                                'business_impact': f"RAG ile tespit edilen bilinen güvenlik açığı. CVSS: {cve_dict.get('base_score', 'N/A')}",
                                'exploitability': 'Known CVE',
                                'target': target,
                                'technology': cve_dict.get('product') or 'Unknown'
                            }
                            tool_findings.append(finding)
                    else:
                        logger.warning("⚠️ RAG'dan CVE bulunamadı")
                else:
                    logger.warning("⚠️ RAG query oluşturulamadı veya generic query döndü")
                    
            except Exception as e:
                logger.error(f"❌ RAG entegrasyonu hatası: {e}")
        
        # State'e tüm bulguları koy (tool + RAG CVE'ler)
        state.findings = tool_findings
        
        # Execution time
        state.execution_time = 0  # Rapor oluşturma süresi
        
        # Context summary (opsiyonel)
        state.context_summary = {
            "target": target,
            "scan_type": "rag_integrated",
            "cve_count": len(cve_results),
            "finding_count": len(tool_findings)
        }
        
        # ReportGenerator oluştur - LLM entegrasyonu ile
        report_gen = ReportGenerator(rag_client=None, llm_api_key="dummy_key")  # LLM'i aktifleştir
        
        # Rapor oluştur (PDF, TXT, JSON, MD)
        from datetime import datetime as dt
        report_id = f"report_{dt.now().strftime('%Y%m%d_%H%M%S')}"
        report_path = f"reports/{report_id}"
        
        # reports dizinini oluştur
        import os
        os.makedirs("reports", exist_ok=True)
        
        # AI ile geliştirilmiş rapor oluştur - TIMEOUT KORUMASLI
        import asyncio
        ai_report_content = None
        try:
            # 45 saniye timeout - Render için optimize edilmiş
            ai_report_content = await asyncio.wait_for(
                report_gen.generate_ai_enhanced_report(state, scan_results, cve_results),
                timeout=45.0
            )
            logger.info("✅ AI enhanced report başarıyla oluşturuldu")
        except asyncio.TimeoutError:
            logger.warning("⏱️ AI report timeout (45s) - Fallback kullanılıyor")
            ai_report_content = None
        except Exception as ai_err:
            logger.warning(f"⚠️ AI enhanced report hatası: {type(ai_err).__name__}: {str(ai_err)[:100]}")
            ai_report_content = None
        
        # Fallback: Basit, hızlı rapor oluştur
        if not ai_report_content:
            logger.info("📄 Basit rapor formatı kullanılıyor (hızlı)")
            try:
                enriched_data = {
                    "target": target,
                    "findings": state.findings[:50] if hasattr(state, 'findings') and isinstance(state.findings, list) else [],  # İlk 50 finding
                    "cve_results": cve_results[:10] if isinstance(cve_results, list) else [],  # İlk 10 CVE
                    "scan_results": scan_results if isinstance(scan_results, dict) else {}
                }
                ai_report_content = report_gen.generate_comprehensive_report_sync(enriched_data)
                logger.info("✅ Basit rapor başarıyla oluşturuldu")
            except Exception as fallback_err:
                logger.error(f"❌ Basit rapor hatası: {fallback_err}")
                # Son fallback - minimal rapor
                ai_report_content = f"""# Güvenlik Raporu

## Hedef
{target}

## Özet
Tarama tamamlandı. {len(state.findings) if hasattr(state, 'findings') else 0} bulgu tespit edildi.

## Durum
Detaylı rapor oluşturulurken teknik bir sorun oluştu. Tarama verileri kaydedildi.
"""
        
        # TÜM TOOL ÇIKTILARINI ÖNCE TOPLA - TEKRARLANMASIN
        all_tool_outputs = {}
        if hasattr(state, 'discovered_information'):
            for key, value in state.discovered_information.items():
                if key.startswith("tool_"):
                    tool_name = key[5:]  # "tool_" prefix'ini kaldır
                    all_tool_outputs[tool_name] = value
        
        # scan_results'tan da tool çıktılarını al
        if isinstance(scan_results, dict):
            for key, value in scan_results.items():
                if key.startswith("tool_") or key in ["execution_results", "tool_outputs"]:
                    if key.startswith("tool_"):
                        tool_name = key[5:]
                        all_tool_outputs[tool_name] = value
                    elif key == "execution_results" and isinstance(value, list):
                        # Execution results'tan tool çıktılarını çıkar
                        for result in value:
                            if isinstance(result, dict) and "tool" in result:
                                tool_name = result["tool"]
                                all_tool_outputs[tool_name] = result
                            elif isinstance(result, str):
                                # String result'ları atla
                                logger.warning(f"⚠️ String execution result atlandı: {result[:100]}...")
                                continue
                    elif key == "tool_outputs" and isinstance(value, dict):
                        all_tool_outputs.update(value)
        
        # Tool outputs dosyasından da çıktıları al
        try:
            import json
            import os
            import glob
            from datetime import datetime
            
            # En son tool outputs dosyasını bul
            tool_outputs_dir = "tool_outputs"
            if os.path.exists(tool_outputs_dir):
                # En son dosyayı bul
                pattern = f"{tool_outputs_dir}/*_tool_outputs.json"
                files = glob.glob(pattern)
                if files:
                    # En son dosyayı al (modification time'a göre)
                    latest_file = max(files, key=os.path.getmtime)
                    
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        file_outputs = json.load(f)
                        if "tool_outputs" in file_outputs:
                            all_tool_outputs.update(file_outputs["tool_outputs"])
                            logger.info(f"📁 {len(file_outputs['tool_outputs'])} tool çıktısı dosyadan alındı: {latest_file}")
                else:
                    logger.warning("Tool outputs dosyası bulunamadı")
            else:
                logger.warning("Tool outputs dizini bulunamadı")
        except Exception as e:
            logger.warning(f"Tool outputs dosyası okuma hatası: {e}")
        
        # CVE'leri enriched_data'ya ekle
        cve_findings = []
        if cve_results:
            for cve in cve_results:
                if isinstance(cve, dict):
                    cve_findings.append(cve)
                else:
                    # CVEResult object ise dict'e çevir
                    cve_findings.append(cve.to_dict() if hasattr(cve, 'to_dict') else str(cve))
        
        # Rapor için zenginleştirilmiş veri hazırla - CVE'LER DAHİL
        enriched_data = {
            "findings": state.findings,
            "target": state.target,
            "user_task": state.user_task,
            "all_tool_outputs": all_tool_outputs,
            "discovered_information": state.discovered_information,
            "cve_results": cve_findings,  # CVE'leri ekle
            "execution_summary": {
                "tools_executed": list(all_tool_outputs.keys()),
                "successful_tools": list(all_tool_outputs.keys()),
                "total_findings": len(state.findings),
                "total_cves": len(cve_findings),
                "scan_duration": "N/A"
            }
        }
        
        # Profesyonel rapor oluştur - SYNC VERSİYON KULLAN (sadece enriched_data)
        report_content = report_gen.generate_comprehensive_report_sync(enriched_data)
        
        # LLM ile gelişmiş rapor üret - TÜM TOOL ÇIKTILARI İLE
        try:
            logger.info("🤖 LLM ile gelişmiş rapor üretiliyor...")
            logger.info(f"📊 LLM'e gönderilen tool sayısı: {len(all_tool_outputs)}")
            logger.info(f"📊 Tool isimleri: {list(all_tool_outputs.keys())}")
            
            llm_report = report_gen.generate_llm_enhanced_report(
                findings=state.findings,
                target=target,
                cve_results=cve_findings,
                tool_outputs=all_tool_outputs,
                scan_results=scan_results,
                llm_query=llm_query,  # LLM sorgusu
                scan_summary=scan_summary  # Tarama özeti
            )
            
            # LLM raporunu da kaydet
            llm_md_path = f"{report_path}_llm.md"
            with open(llm_md_path, 'w', encoding='utf-8') as f:
                f.write(llm_report)
            logger.info(f"✅ LLM raporu oluşturuldu: {llm_md_path}")
            
        except Exception as e:
            logger.error(f"❌ LLM rapor üretimi hatası: {e}", exc_info=True)
            llm_report = "LLM raporu oluşturulamadı"
        
        # Rapor oluştur (TÜM TOOL ÇIKTILARI İLE) - hata yönetimi ile
        try:
            success = await report_gen.generate_report(state, report_path)
        except Exception as report_err:
            logger.warning(f"Rapor oluşturma hatası: {report_err}")
            # Fallback: Basit rapor oluştur
            try:
                enriched_data = {
                    "target": target,
                    "findings": state.findings if hasattr(state, 'findings') and isinstance(state.findings, list) else [],
                    "cve_results": cve_results if isinstance(cve_results, list) else [],
                    "scan_results": scan_results if isinstance(scan_results, dict) else {}
                }
                simple_report = report_gen.generate_comprehensive_report_sync(enriched_data)
                # Basit raporu dosyaya yaz
                txt_path = f"{report_path}.txt"
                with open(txt_path, 'w', encoding='utf-8') as f:
                    f.write(simple_report if isinstance(simple_report, str) else str(simple_report))
                success = True
            except Exception as fallback_err:
                logger.warning(f"Fallback rapor oluşturma hatası: {fallback_err}")
                success = False
        
        # Markdown raporu da oluştur (AI ile geliştirilmiş)
        md_path = f"{report_path}.md"
        try:
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(ai_report_content)
            logger.info(f"AI ile geliştirilmiş Markdown raporu oluşturuldu: {md_path}")
        except Exception as e:
            logger.error(f"Markdown raporu oluşturulamadı: {e}")
        
        if not success:
            raise HTTPException(status_code=500, detail="Rapor oluşturulamadı")
        
        # Risk skoru hesapla (tüm bulgulardan) - GÜNCELLENMİŞ
        all_findings = state.findings if hasattr(state, 'findings') and isinstance(state.findings, list) else []
        logger.info(f"📊 RAPOR GENERATİON - Toplam bulgu sayısı: {len(all_findings)}")
        if len(all_findings) > 0:
            logger.info(f"📊 Bulgular detayı (ilk 10): {[(f.get('title', 'N/A')[:50], f.get('severity', 'N/A')) for f in all_findings[:10]]}")
            # Severity dağılımını logla
            severity_counts = {}
            for f in all_findings:
                sev = f.get('severity', 'info').lower()
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
            logger.info(f"📊 Severity dağılımı: {severity_counts}")
        logger.info(f"📊 Scan results keys: {list(scan_results.keys()) if isinstance(scan_results, dict) else 'Not dict'}")
        logger.info(f"📊 All tool outputs keys: {list(all_tool_outputs.keys())}")
        
        # CVE detaylarını zenginleştir - RAG'dan tüm bilgileri çek (GÜVENLİ)
        logger.info("🔍 CVE detayları zenginleştiriliyor...")
        enriched_cve_findings = []
        for cve in cve_findings:
            cve_id = cve.get('cve_id')
            if cve_id and cve_id != 'N/A':
                try:
                    # RAG'dan CVE detaylarını çek
                    rag_service = get_rag_service()
                    if rag_service.is_available():
                        cve_detail = rag_service.get_cve_by_id(cve_id)
                        if cve_detail:
                            # CVE'yi zenginleştir - GÜVENLİ ALAN ERİŞİMİ
                            enriched_cve = cve.copy()
                            
                            # Her alanı güvenli şekilde al
                            safe_fields = {
                                'description': getattr(cve_detail, 'description', None) or cve.get('description', ''),
                                'base_score': getattr(cve_detail, 'base_score', None) or cve.get('base_score') or cve.get('cvss_score'),
                                'severity': getattr(cve_detail, 'severity', None) or cve.get('severity'),
                                'published_date': getattr(cve_detail, 'published_date', None) or cve.get('published_date'),
                                'modified_date': getattr(cve_detail, 'modified_date', None) or cve.get('modified_date'),
                                'references': getattr(cve_detail, 'references', None) or cve.get('references', []),
                                'cwe_id': getattr(cve_detail, 'cwe_id', None) or cve.get('cwe_id'),
                                'vendor': getattr(cve_detail, 'vendor', None) or cve.get('vendor'),
                                'product': getattr(cve_detail, 'product', None) or cve.get('product'),
                                'cvss_vector': getattr(cve_detail, 'cvss_vector', None) or cve.get('cvss_vector'),
                                'exploitability_score': getattr(cve_detail, 'exploitability_score', None) or cve.get('exploitability_score'),
                                'impact_score': getattr(cve_detail, 'impact_score', None) or cve.get('impact_score'),
                                'attack_vector': getattr(cve_detail, 'attack_vector', None) or cve.get('attack_vector')
                            }
                            
                            # Sadece None olmayan alanları ekle
                            for key, value in safe_fields.items():
                                if value is not None:
                                    enriched_cve[key] = value
                            
                            enriched_cve_findings.append(enriched_cve)
                            logger.info(f"✅ CVE zenginleştirildi: {cve_id}")
                        else:
                            enriched_cve_findings.append(cve)
                            logger.warning(f"⚠️ CVE detayı bulunamadı: {cve_id}")
                except Exception as e:
                    logger.error(f"❌ CVE zenginleştirme hatası ({cve_id}): {e}", exc_info=True)
                    enriched_cve_findings.append(cve)
            else:
                enriched_cve_findings.append(cve)
        
        # Zenginleştirilmiş CVE'leri kullan
        cve_findings = enriched_cve_findings
        logger.info(f"✅ {len(enriched_cve_findings)} CVE zenginleştirildi")
        
        # HER ZAMAN scan_results'tan tool bulgularını çıkar ve ekle
        # (findings_added == 0 kontrolünü kaldırdık - her zaman tool bulgularını ekle)
        logger.debug("Scan_results'tan tool bulguları çıkarılıyor...")
        # Scan results'tan tool data'larını tekrar kontrol et
        if isinstance(scan_results, dict):
                for key, value in scan_results.items():
                    # Dict ve success kontrolü
                    if isinstance(value, dict):
                        # Success varsa data'dan çıkar
                        if value.get('success'):
                            tool_data = value.get('data', {})
                            
                            # Tool data içinden bulgu oluştur - DETAYLI
                            if isinstance(tool_data, dict) and tool_data:
                                # Directory bruteforce findings (high, critical, informational)
                                if 'findings' in tool_data and isinstance(tool_data['findings'], dict):
                                    dir_findings = tool_data['findings']
                                    
                                    # Critical directories
                                    if dir_findings.get('critical'):
                                        for item in dir_findings['critical']:
                                            finding = {
                                                'title': f'Kritik Dizin: {item.get("path", "N/A")}',
                                                'severity': 'critical',
                                                'description': f'Kritik dizin tespit edildi: {item.get("path")} ({item.get("status_code")})',
                                                'cvss_score': '9.0',
                                                'cve_id': None,
                                                'evidence': f'URL: {item.get("url")}, Status: {item.get("status_code")}, Size: {item.get("content_length")}',
                                                'recommendation_summary': 'Kritik dizinlere erişimi kısıtlayın',
                                                'business_impact': 'Hassas bilgilere yetkisiz erişim riski',
                                                'exploitability': 'High',
                                                'target': item.get("url", target),
                                                'technology': 'Web Server'
                                            }
                                            state.findings.append(finding)
                                            findings_added += 1
                                            logger.info(f"🔍 CRITICAL dizin bulgusu: {item.get('path')}")
                                    
                                    # High risk directories (admin, config, etc.)
                                    if dir_findings.get('high'):
                                        for item in dir_findings['high']:
                                            finding = {
                                                'title': f'Yüksek Riskli Dizin: {item.get("path", "N/A")}',
                                                'severity': 'high',
                                                'description': f'Yüksek riskli dizin tespit edildi: {item.get("path")} ({item.get("status_code")})',
                                                'cvss_score': '7.5',
                                                'cve_id': None,
                                                'evidence': f'URL: {item.get("url")}, Status: {item.get("status_code")}, Size: {item.get("content_length")}',
                                                'recommendation_summary': 'Hassas dizinleri koruyun ve erişim kontrolü ekleyin',
                                                'business_impact': 'Hassas dosya ve dizinlere erişim riski',
                                                'exploitability': 'High',
                                                'target': item.get("url", target),
                                                'technology': 'Web Server'
                                            }
                                            state.findings.append(finding)
                                            findings_added += 1
                                            logger.info(f"🔍 HIGH dizin bulgusu: {item.get('path')}")
                                    
                                    # Informational directories
                                    if dir_findings.get('informational'):
                                        info_count = len(dir_findings['informational'])
                                        finding = {
                                            'title': f'Bilgilendirici Dizinler: {info_count} dizin bulundu',
                                            'severity': 'info',
                                            'description': f'{info_count} bilgilendirici dizin tespit edildi',
                                            'cvss_score': 'N/A',
                                            'cve_id': None,
                                            'evidence': f'Directories: {[d.get("path") for d in dir_findings["informational"][:5]]}',
                                            'recommendation_summary': 'Dizin listelerini kontrol edin',
                                            'business_impact': 'Sistem yapısı hakkında bilgi sızıntısı',
                                            'exploitability': 'Low',
                                            'target': target,
                                            'technology': 'Web Server'
                                        }
                                        state.findings.append(finding)
                                        findings_added += 1
                                        logger.info(f"🔍 INFO dizin bulgusu: {info_count} dizin")
                                
                                # API Endpoints tespit edildi mi?
                                if 'discovered_endpoints' in tool_data and tool_data['discovered_endpoints']:
                                    endpoints = tool_data['discovered_endpoints']
                                    endpoint_count = len(endpoints) if isinstance(endpoints, list) else 0
                                    
                                    # Yüksek riskli endpoint'leri say (ai_risk_score >= 5)
                                    high_risk_endpoints = [e for e in endpoints if isinstance(e, dict) and e.get('ai_risk_score', 0) >= 5]
                                    high_risk_count = len(high_risk_endpoints)
                                    
                                    if endpoint_count > 0:
                                        severity = 'high' if high_risk_count > 0 else 'medium' if endpoint_count >= 10 else 'low'
                                        cvss = '7.5' if high_risk_count > 0 else '5.0' if endpoint_count >= 10 else '3.0'
                                        
                                        finding = {
                                            'title': f'API Endpoint Keşfi: {endpoint_count} endpoint bulundu ({high_risk_count} yüksek riskli)',
                                            'severity': severity,
                                            'description': f'{endpoint_count} API endpoint tespit edildi. {high_risk_count} tanesi yüksek riskli olarak işaretlendi.',
                                            'cvss_score': cvss,
                                            'cve_id': None,
                                            'evidence': f'Endpoints: {[e.get("url") for e in endpoints[:5]]}, High risk: {[e.get("url") for e in high_risk_endpoints[:3]]}',
                                            'recommendation_summary': 'Yüksek riskli API endpointleri authentication ve authorization kontrollerine tabi tutun',
                                            'business_impact': 'API endpointler unauthorized access riski taşıyor',
                                            'exploitability': 'High' if high_risk_count > 0 else 'Medium',
                                            'target': target,
                                            'technology': 'API'
                                        }
                                        state.findings.append(finding)
                                        findings_added += 1
                                        logger.info(f"🔍 API Endpoint bulgusu eklendi: {endpoint_count} endpoint ({high_risk_count} yüksek riskli)")
                                
                                # Web Crawler sonuçları (pages, paths, forms)
                                if any(k in tool_data for k in ['pages', 'paths', 'forms']):
                                    pages = tool_data.get('pages', [])
                                    paths = tool_data.get('paths', [])
                                    forms = tool_data.get('forms', [])
                                    
                                    page_count = len(pages) if isinstance(pages, list) else 0
                                    path_count = len(paths) if isinstance(paths, list) else 0
                                    form_count = len(forms) if isinstance(forms, list) else 0
                                    
                                    if page_count > 0 or path_count > 0 or form_count > 0:
                                        # Risk seviyesi belirleme
                                        severity = 'high' if form_count >= 5 or path_count >= 15 else 'medium' if form_count >= 3 or path_count >= 10 else 'low'
                                        cvss = '7.0' if form_count >= 5 else '5.5' if form_count >= 3 else '4.0'
                                        
                                        finding = {
                                            'title': f'Web Crawling Sonuçları: {page_count} sayfa, {path_count} yol, {form_count} form',
                                            'severity': severity,
                                            'description': f'Site taramasında {page_count} sayfa analiz edildi, {path_count} yol ve {form_count} form tespit edildi. Saldırı yüzeyi geniş.',
                                            'cvss_score': cvss,
                                            'cve_id': None,
                                            'evidence': f'Pages: {page_count}, Paths: {path_count}, Forms: {form_count}',
                                            'recommendation_summary': f'Formları input validation ile koruyun. {form_count} form injection saldırılarına açık olabilir.',
                                            'business_impact': f'{form_count} form ve {path_count} yol saldırı yüzeyini artırıyor',
                                            'exploitability': 'High' if form_count >= 5 else 'Medium',
                                            'target': target,
                                            'technology': 'Web Application'
                                        }
                                        state.findings.append(finding)
                                        findings_added += 1
                                        logger.info(f"🔍 Web Crawler bulgusu eklendi: {page_count} sayfa, {path_count} yol, {form_count} form")
                                
                                # Teknoloji tespit edildi mi?
                                if 'technologies' in tool_data and tool_data['technologies']:
                                    tech_list = tool_data['technologies']
                                    tech_count = len(tech_list) if isinstance(tech_list, list) else 0
                                    if tech_count > 0:
                                        finding = {
                                            'title': f'Teknoloji Tespiti: {tech_count} teknoloji bulundu',
                                            'severity': 'info',
                                            'description': f'Tespit edilen teknolojiler: {", ".join(str(t) for t in tech_list[:5])}',
                                            'cvss_score': 'N/A',
                                            'cve_id': None,
                                            'evidence': f'Technologies: {tech_list}',
                                            'recommendation_summary': 'Tespit edilen teknolojilerin güvenlik güncellemelerini kontrol edin',
                                            'business_impact': 'Teknoloji bilgisi saldırganlar için değerlidir',
                                            'exploitability': 'Information Gathering',
                                            'target': target,
                                            'technology': 'Technology Detection'
                                        }
                                        state.findings.append(finding)
                                        findings_added += 1
                                        logger.info(f"🔍 Teknoloji bulgusu eklendi: {tech_count} teknoloji")
                                
                                # Port taraması var mı?
                                if 'open_ports' in tool_data and tool_data['open_ports']:
                                    ports = tool_data['open_ports']
                                    port_count = len(ports) if isinstance(ports, list) else 0
                                    if port_count > 0:
                                        # Kritik portlar var mı?
                                        critical_ports = [p for p in (ports if isinstance(ports, list) else []) 
                                                        if str(p).strip() in ['22', '3389', '5900', '23', '21']]
                                        severity = 'high' if critical_ports else 'medium'
                                        cvss = '7.5' if critical_ports else '5.0'
                                        
                                        finding = {
                                            'title': f'Açık Portlar: {port_count} port tespit edildi',
                                            'severity': severity,
                                            'description': f'Sistemde {port_count} açık port bulundu. Kritik portlar: {critical_ports if critical_ports else "Yok"}',
                                            'cvss_score': cvss,
                                            'cve_id': None,
                                            'evidence': f'Open ports: {ports}',
                                            'recommendation_summary': 'Gereksiz portları kapatın ve güvenlik duvarı kurallarını gözden geçirin',
                                            'business_impact': 'Açık portlar saldırı yüzeyini artırır',
                                            'exploitability': 'High' if critical_ports else 'Medium',
                                            'target': target,
                                            'technology': 'Network Services'
                                        }
                                        state.findings.append(finding)
                                        findings_added += 1
                                        logger.info(f"🔍 Port bulgusu eklendi: {port_count} port")
                                
                                # Subdomain var mı?
                                if 'subdomains' in tool_data and tool_data['subdomains']:
                                    subdomains = tool_data['subdomains']
                                    subdomain_count = len(subdomains) if isinstance(subdomains, list) else 0
                                    if subdomain_count > 0:
                                        finding = {
                                            'title': f'Subdomain Keşfi: {subdomain_count} subdomain bulundu',
                                            'severity': 'medium',
                                            'description': f'{subdomain_count} subdomain tespit edildi, saldırı yüzeyi genişledi',
                                            'cvss_score': '5.0',
                                            'cve_id': None,
                                            'evidence': f'Subdomains: {subdomains[:10]}',
                                            'recommendation_summary': 'Tüm subdomainlerin güvenliğini kontrol edin',
                                            'business_impact': 'Genişletilmiş saldırı yüzeyi',
                                            'exploitability': 'Medium',
                                            'target': target,
                                            'technology': 'DNS'
                                        }
                                        state.findings.append(finding)
                                        findings_added += 1
                                        logger.info(f"🔍 Subdomain bulgusu eklendi: {subdomain_count} subdomain")
                                
                                # Endpoint var mı?
                                if 'endpoints' in tool_data and tool_data['endpoints']:
                                    endpoints = tool_data['endpoints']
                                    endpoint_count = len(endpoints) if isinstance(endpoints, list) else 0
                                    if endpoint_count > 0:
                                        severity = 'high' if endpoint_count >= 20 else 'medium'
                                        cvss = '7.0' if endpoint_count >= 20 else '5.0'
                                        
                                        finding = {
                                            'title': f'Endpoint Keşfi: {endpoint_count} endpoint bulundu',
                                            'severity': severity,
                                            'description': f'{endpoint_count} endpoint tespit edildi, geniş saldırı yüzeyi',
                                            'cvss_score': cvss,
                                            'cve_id': None,
                                            'evidence': f'Endpoints: {endpoints[:10]}',
                                            'recommendation_summary': 'Endpoint sayısını azaltın ve gereksiz olanları kaldırın',
                                            'business_impact': 'Çok fazla endpoint güvenlik riski oluşturur',
                                            'exploitability': 'High' if endpoint_count >= 20 else 'Medium',
                                            'target': target,
                                            'technology': 'Web Application'
                                        }
                                        state.findings.append(finding)
                                        findings_added += 1
                                        logger.info(f"🔍 Endpoint bulgusu eklendi: {endpoint_count} endpoint")
                                
                                # Form var mı?
                                if 'forms' in tool_data and tool_data['forms']:
                                    forms = tool_data['forms']
                                    form_count = len(forms) if isinstance(forms, list) else 0
                                    if form_count > 0:
                                        severity = 'high' if form_count >= 10 else 'medium'
                                        cvss = '7.5' if form_count >= 10 else '5.5'
                                        
                                        finding = {
                                            'title': f'Form Tespiti: {form_count} form bulundu',
                                            'severity': severity,
                                            'description': f'{form_count} form tespit edildi, injection saldırı riski',
                                            'cvss_score': cvss,
                                            'cve_id': None,
                                            'evidence': f'Forms: {form_count} found',
                                            'recommendation_summary': 'Form güvenliğini kontrol edin ve input validation uygulayın',
                                            'business_impact': 'Formlar injection saldırıları için hedef olabilir',
                                            'exploitability': 'High',
                                            'target': target,
                                            'technology': 'Web Application'
                                        }
                                        state.findings.append(finding)
                                        findings_added += 1
                                        logger.info(f"🔍 Form bulgusu eklendi: {form_count} form")
                        
                        # Success olmasa bile data varsa genel bulgu oluştur
                        elif value:
                            finding = {
                                'title': f'{key.replace("_", " ").title()} Tool Sonucu',
                                'severity': 'info',
                                'description': f'{key} aracı çalıştırıldı',
                                'cvss_score': 'N/A',
                                'cve_id': None,
                                'evidence': f'Tool: {key}, Data: {str(value)[:200]}',
                                'recommendation_summary': 'Tool sonuçlarını inceleyin',
                                'business_impact': 'Bilgi toplama aşaması',
                                'exploitability': 'Low',
                                'target': target,
                                'technology': 'Security Tool'
                            }
                            state.findings.append(finding)
                            findings_added += 1
                            logger.info(f"🔍 Genel bulgu eklendi: {key}")
            
            # Bulgu yoksa bulgu yok - yapay bulgu üretme!
            if findings_added == 0:
                logger.debug("Scan results'tan hiç bulgu çıkarılamadı - Bu normal bir durum")
                logger.info(f"✅ Detaylı analiz sonrası toplam bulgu: {len(state.findings)}")
        
        # all_findings'i güncelle - SADECE TOOL BULGULARI (CVE referansları risk skorunu çok artırmasın)
        all_findings = state.findings.copy() if hasattr(state, 'findings') and isinstance(state.findings, list) else []
        
        # Findings'leri temizle ve normalize et - severity'leri standartlaştır
        cleaned_findings = []
        for f in all_findings:
            if isinstance(f, dict):
                # Severity'yi normalize et
                severity = f.get('severity', 'info')
                if isinstance(severity, str):
                    severity = severity.lower().strip()
                    # Türkçe severity'leri İngilizce'ye çevir
                    severity_map = {
                        'kritik': 'critical',
                        'yüksek': 'high',
                        'orta': 'medium',
                        'düşük': 'low',
                        'bilgilendirme': 'info',
                        'information': 'info'
                    }
                    severity = severity_map.get(severity, severity)
                    f['severity'] = severity
                cleaned_findings.append(f)
        
        # NOT: CVE'leri risk hesaplamasına dahil ETMİYORUZ
        # Çünkü CVE'ler sadece referans için, tool bulgularına öncelik veriyoruz
        logger.info(f"📊 Risk skoru sadece tool bulgularıyla hesaplanacak: {len(cleaned_findings)} bulgu")
        if len(cleaned_findings) > 0:
            severity_dist = {}
            for finding in cleaned_findings:
                sev = finding.get('severity', 'info').lower()
                # Normalize severity: 'informational' -> 'info'
                if sev == 'informational':
                    sev = 'info'
                severity_dist[sev] = severity_dist.get(sev, 0) + 1
            logger.info(f"📊 Severity dağılımı: {severity_dist}")
        
        # Normalize severity for risk score calculation
        normalized_findings = []
        for finding in cleaned_findings:
            normalized_finding = finding.copy()
            severity = finding.get('severity', 'info').lower()
            if severity == 'informational':
                normalized_finding['severity'] = 'info'
            normalized_findings.append(normalized_finding)
        
        risk_score = report_gen._calculate_risk_score(normalized_findings)
        logger.info(f"📊 Hesaplanan risk skoru (SADECE tool bulguları): {risk_score} (Toplam bulgu: {len(cleaned_findings)})")
        
        # Vulnerabilities objesini oluştur (frontend için) - normalized severity ile
        vulnerabilities = {
            'critical': len([f for f in cleaned_findings if f.get('severity', '').lower() == 'critical']),
            'high': len([f for f in cleaned_findings if f.get('severity', '').lower() == 'high']),
            'medium': len([f for f in cleaned_findings if f.get('severity', '').lower() == 'medium']),
            'low': len([f for f in cleaned_findings if f.get('severity', '').lower() == 'low']),
            'info': len([f for f in cleaned_findings if f.get('severity', '').lower() == 'info'])
        }
        logger.info(f"📊 Vulnerabilities objesi: {vulnerabilities}")
        logger.info(f"📊 Toplam zafiyet: {sum(vulnerabilities.values())}")
        
        # Risk skoru artık _calculate_risk_score içinde hesaplanıyor, fallback mantığı kaldırıldı
        
        
        # Yapılandırılmış rapor verisini al (tool bulguları + CVE tablosu + detaylı çıktılar)
        structured_report = report_gen.get_structured_report_data_with_cves(state, cve_findings)
        
        # Executive summary oluştur
        critical_findings = [f for f in state.findings if f.get('severity') == 'critical']
        high_findings = [f for f in state.findings if f.get('severity') == 'high']
        medium_findings = [f for f in state.findings if f.get('severity') == 'medium']
        low_findings = [f for f in state.findings if f.get('severity') == 'low']
        
        executive_summary = {
            "risk_skoru": risk_score,
            "genel_degerlendirme": f"{target} sistemine yönelik penetrasyon testi tamamlanmıştır. Toplam {len(state.findings)} güvenlik bulgusu tespit edilmiştir.",
            "kritik_bulgular": critical_findings[:3],  # İlk 3 kritik bulgu
            "toplam_bulgu": len(state.findings),
            "bulgu_dagilimi": {
                "kritik": len(critical_findings),
                "yuksek": len(high_findings),
                "orta": len(medium_findings),
                "dusuk": len(low_findings)
            }
        }
        
        # CVE'leri zenginleştirilmiş şekilde structured_report'a ekle
        enriched_cve_references = []
        for cve in cve_findings:
            enriched_cve_references.append({
                "cve_id": cve.get("cve_id", "N/A"),
                "cvss_skoru": cve.get("base_score") or cve.get("cvss_score", "N/A"),
                "severity": cve.get("severity", "unknown"),
                "aciklama": cve.get("description", ""),
                "etkilenen_sistem": cve.get("product") or cve.get("technology") or cve.get("target", "N/A"),
                "published_date": cve.get("published_date", "N/A"),
                "modified_date": cve.get("modified_date", "N/A"),
                "references": cve.get("references", []),
                "cwe_id": cve.get("cwe_id", "N/A"),
                "vendor": cve.get("vendor", "N/A"),
                "cvss_vector": cve.get("cvss_vector", "N/A"),
                "exploitability_score": cve.get("exploitability_score", "N/A"),
                "impact_score": cve.get("impact_score", "N/A"),
                "attack_vector": cve.get("attack_vector", "N/A")
            })
        
        # Structured report'a tool çıktılarını da ekle
        if structured_report:
            structured_report["all_tool_outputs"] = all_tool_outputs
            structured_report["execution_summary"] = enriched_data["execution_summary"]
            structured_report["findings"] = state.findings  # Bulguları ekle
            structured_report["cve_results"] = enriched_cve_references  # Zenginleştirilmiş CVE'leri ekle
            structured_report["cve_references"] = enriched_cve_references  # CVE referanslarını da ekle
            structured_report["executive_summary"] = executive_summary  # Executive summary ekle
            structured_report["risk_score"] = risk_score  # Risk skoru ekle - KRİTİK!
            structured_report["vulnerabilities"] = vulnerabilities  # Vulnerabilities ekle - KRİTİK!
            
            # Frontend'in beklediği detailed_findings formatına çevir
            detailed_findings = []
            for i, finding in enumerate(state.findings, 1):
                detailed_findings.append({
                    "id": i,
                    "baslik": finding.get("title", "Bulgu"),
                    "severity": finding.get("severity", "medium"),
                    "aciklama": finding.get("description", "Açıklama bulunamadı"),
                    "kanit": finding.get("evidence", "Kanıt bulunamadı"),
                    "is_etkisi": finding.get("business_impact") or finding.get("impact", "Etki analizi yapılamadı"),
                    "cozum": finding.get("recommendation_summary") or finding.get("recommendation", "Çözüm önerisi bulunamadı"),
                    "cvss_skoru": finding.get("cvss_score", "N/A"),
                    "cve_id": finding.get("cve_id", "N/A"),
                    "hedef": finding.get("target") or finding.get("affected_component", state.target)
                })
            structured_report["detailed_findings"] = detailed_findings
        
        logger.info(f"✅ Rapor başarıyla oluşturuldu: {report_id}")
        
        # Datetime import'u burada yap
        from datetime import datetime as dt
        
        # Response data'sını optimize et - SADECE ANLAMLI DATA GÖNDER
        # Tool outputs'u filtrele: Sadece bulgu içerenleri gönder
        limited_tool_outputs = {}
        if all_tool_outputs:
            import json
            tool_count = 0
            for tool_name, tool_output in all_tool_outputs.items():
                if tool_count >= 10:  # Maksimum 10 tool
                    break
                
                # Tool output'ta anlamlı data var mı kontrol et
                has_meaningful_data = False
                if isinstance(tool_output, dict):
                    # Bulgu, zafiyet, port, subdomain gibi anlamlı datalar var mı?
                    meaningful_keys = ['vulnerabilities', 'findings', 'results', 'ports', 'subdomains', 
                                      'technologies', 'endpoints', 'forms', 'discovered_paths']
                    for key in meaningful_keys:
                        if key in tool_output and tool_output[key]:
                            # Liste ise ve boş değilse, dict ise ve boş değilse
                            if (isinstance(tool_output[key], list) and len(tool_output[key]) > 0) or \
                               (isinstance(tool_output[key], dict) and len(tool_output[key]) > 0):
                                has_meaningful_data = True
                                break
                
                # Anlamlı data yoksa skip et
                if not has_meaningful_data:
                    logger.debug(f"⏭️ {tool_name} skipped (no meaningful data)")
                    continue
                
                # Anlamlı data varsa ekle (serialize edilebilir hale getir)
                try:
                    serialized = json.dumps(tool_output)
                    if len(serialized) > 3000:  # 3KB limit
                        # Sadece önemli alanları al
                        filtered_output = {}
                        for key in meaningful_keys:
                            if key in tool_output:
                                filtered_output[key] = tool_output[key][:20] if isinstance(tool_output[key], list) else tool_output[key]
                        limited_tool_outputs[tool_name] = filtered_output
                    else:
                        limited_tool_outputs[tool_name] = tool_output
                    tool_count += 1
                except:
                    logger.warning(f"⚠️ {tool_name} serialize edilemedi, skipped")
        
        # Structured data'yı optimize et - Sadece dolu alanlar
        if structured_report:
            # Boş alanları temizle
            structured_report = {k: v for k, v in structured_report.items() if v}
            
            # Findings'i sınırla (max 50)
            if "detailed_findings" in structured_report and len(structured_report["detailed_findings"]) > 50:
                structured_report["detailed_findings"] = structured_report["detailed_findings"][:50]
                structured_report["findings_truncated"] = True
            
            # CVE'leri sınırla (max 20)
            if "cve_results" in structured_report and len(structured_report["cve_results"]) > 20:
                structured_report["cve_results"] = structured_report["cve_results"][:20]
                structured_report["cve_truncated"] = True
        
        findings_count = len(state.findings) if hasattr(state, 'findings') else 0
        tools_count = len(limited_tool_outputs)
        logger.info(f"📊 Response optimized: {findings_count} findings, {tools_count} tools with data, {len(cve_results)} CVEs")
        
        # Final response - sadece dolu alanlar
        response_data = {
            "success": True,
            "report_id": report_id,
            "target": target,
            "risk_score": risk_score,
            "vulnerabilities": vulnerabilities,
            "pages": len(report_content.split('\n')) // 50 if report_content else 1,
            "createdAt": dt.now().isoformat(),
            "download_url": f"/api/reports/{report_id}/download",
            "formats_available": ["txt", "pdf", "json", "md"],
            "files": {
                "txt": f"{report_path}.txt",
                "pdf": f"{report_path}.pdf",
                "json": f"{report_path}.json",
                "md": f"{report_path}.md"
            }
        }
        
        # Report content sadece varsa ekle (ilk 3000 karakter)
        if report_content and len(report_content.strip()) > 0:
            response_data["report_content"] = report_content[:3000]
        
        # Structured data sadece bulgu varsa ekle
        if structured_report and any(key in structured_report and structured_report[key] 
                                     for key in ['detailed_findings', 'vulnerabilities', 'cve_results']):
            response_data["structured_data"] = structured_report
        
        # Tool outputs sadece anlamlı data varsa ekle
        if limited_tool_outputs and len(limited_tool_outputs) > 0:
            response_data["all_tool_outputs"] = limited_tool_outputs
        
        # Scan history'ye kaydet (opsiyonel - hata durumunda devam et)
        try:
            user_id = request.get("user_id") or request.get("userId")
            if user_id:
                # Frontend'e scan_history kaydı için bilgi gönder
                # Frontend kendi scanHistoryService'i ile kaydedecek
                response_data["scan_history_data"] = {
                    "target": target,
                    "findingsCount": len(cleaned_findings),
                    "riskLevel": "HIGH" if risk_score >= 70 else "MEDIUM" if risk_score >= 40 else "LOW",
                    "riskScore": risk_score,
                    "vulnerabilities": vulnerabilities
                }
        except Exception as scan_history_err:
            logger.debug(f"Scan history kayıt hazırlığı hatası (normal olabilir): {scan_history_err}")
        
        logger.info(f"✅ Response ready: {len(str(response_data))} bytes")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        # Hataları daha iyi yönet - sistem çökmesini önle
        error_type = type(e).__name__
        error_msg = str(e) if str(e) else f"{error_type} hatası oluştu"
        logger.warning(f"Rapor oluşturma hatası ({error_type}): {error_msg}")
        import traceback
        logger.debug(f"Traceback: {traceback.format_exc()}")
        # Kullanıcıya anlamlı hata mesajı gönder
        raise HTTPException(
            status_code=500, 
            detail=f"Rapor oluşturma hatası: {error_msg[:200]}"
        )

@app.get("/api/debug/test-qdrant")
async def test_qdrant_connection():
    """Debug: Render'dan HuggingFace Space'e bağlantı testi"""
    import httpx
    import os
    from qdrant_client import QdrantClient
    
    qdrant_url = os.getenv('QDRANT_HOST', 'localhost')
    hf_token = os.getenv('HUGGINGFACE_TOKEN')
    
    results = {
        "qdrant_host_env": qdrant_url,
        "hf_token_set": hf_token is not None,
        "tests": []
    }
    
    # Test 1: Root endpoint (httpx)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(qdrant_url)
            results["tests"].append({
                "test": "Root endpoint (httpx)",
                "url": qdrant_url,
                "status": response.status_code,
                "success": True,
                "response": response.json() if response.status_code == 200 else None
            })
    except Exception as e:
        results["tests"].append({
            "test": "Root endpoint (httpx)",
            "url": qdrant_url,
            "success": False,
            "error": str(e)
        })
    
    # Test 2: Collections endpoint (httpx)
    try:
        collections_url = f"{qdrant_url}/collections"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(collections_url)
            results["tests"].append({
                "test": "Collections endpoint (httpx)",
                "url": collections_url,
                "status": response.status_code,
                "success": True,
                "response": response.json() if response.status_code == 200 else None
            })
    except Exception as e:
        results["tests"].append({
            "test": "Collections endpoint (httpx)",
            "url": collections_url,
            "success": False,
            "error": str(e)
        })
    
    # Test 3: QdrantClient initialization (default settings)
    try:
        client = QdrantClient(
            url=qdrant_url,
            timeout=10,
            prefer_grpc=False,
            https=False
        )
        
        collections = client.get_collections()
        results["tests"].append({
            "test": "QdrantClient (default)",
            "success": True,
            "collections_found": len(collections.collections),
            "collection_names": [c.name for c in collections.collections]
        })
    except Exception as e:
        import traceback
        results["tests"].append({
            "test": "QdrantClient (default)",
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()[:500]
        })
    
    # Test 4: QdrantClient with optimized settings
    try:
        import httpx
        
        # Custom httpx client with longer timeout
        http_client = httpx.Client(
            timeout=httpx.Timeout(60.0, connect=60.0, read=60.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        
        client = QdrantClient(
            url=qdrant_url,
            timeout=60,
            prefer_grpc=False,
            https=False,
            # Use custom http client
            http_client=http_client
        )
        
        collections = client.get_collections()
        results["tests"].append({
            "test": "QdrantClient (optimized)",
            "success": True,
            "collections_found": len(collections.collections),
            "collection_names": [c.name for c in collections.collections]
        })
    except Exception as e:
        import traceback
        results["tests"].append({
            "test": "QdrantClient (optimized)",
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()[:500]
        })
    
    return results

if __name__ == "__main__":
    uvicorn.run(
        "web_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
