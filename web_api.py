#!/usr/bin/env python3
"""
Pentagent Web API Server
Frontend ile backend arasında iletişim sağlar
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List
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
        try:
            if websocket in self.active_connections:
                await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Mesaj gönderme hatası: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Broadcast hatası: {e}")
                disconnected_connections.append(connection)
        
        # Disconnected connections'ları temizle
        for connection in disconnected_connections:
            self.disconnect(connection)

manager = ConnectionManager()

# Global LLM model (RAG query optimization için)
gemini_model = None

@app.on_event("startup")
async def startup_event():
    """Uygulama başlatıldığında API key kontrolü yap"""
    global gemini_model
    try:
        logger.info("Pentagent API başlatılıyor...")
        
        # Unified LLM model'i başlat (RAG query optimization için)
        # Uses env: MODEL_PROVIDER, GROQ_API_KEY, GROQ_MODEL
        gemini_model = UnifiedLLM()
        
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

@app.get("/")
async def root():
    return {"message": "Pentagent API Server", "status": "running"}

@app.get("/health")
async def health_check():
    """API health check"""
    api_key_valid = config.GEMINI_API_KEY and config.GEMINI_API_KEY != 'YOUR_GEMINI_API_KEY_HERE'
    
    # RAG servisi kontrolü
    rag_service = get_rag_service()
    rag_stats = rag_service.get_stats()
    
    return {
        "status": "healthy",
        "api_key_configured": api_key_valid,
        "active_connections": len(manager.active_connections),
        "rag_available": rag_stats.get("available", False),
        "rag_cves": rag_stats.get("total_cves", 0),
        "message": "Pentagent API is running"
    }

@app.post("/api/scan")
async def start_scan(request: Dict[str, Any]):
    """Yeni bir güvenlik taraması başlat - MODÜLER (her scan için yeni orchestrator)"""
    try:
        # API key kontrolü
        api_key = config.GEMINI_API_KEY
        if not api_key or api_key == 'YOUR_GEMINI_API_KEY_HERE':
            raise HTTPException(status_code=503, detail="GEMINI_API_KEY yapılandırılmamış")
        target = request.get("target", "")
        task = request.get("task", "")
        
        if not target:
            raise HTTPException(status_code=400, detail="Target gerekli")
        
        # Scan ID oluştur
        scan_id = f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Status callback fonksiyonu
        async def scan_status_callback(message: str, status_type: str = "info"):
            timestamp = datetime.now().strftime("%H:%M:%S")
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
        
    except Exception as e:
        logger.error(f"Scan başlatma hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_scan_async(scan_id: str, target: str, task: str, status_callback):
    """Async olarak scan çalıştır - MODÜLER (her scan için yeni orchestrator)"""
    try:
        logger.info(f"Scan başlatılıyor: {scan_id} - {target}")
        
        # Scan başlatma mesajı
        await status_callback(f"🎯 Scan başlatıldı: {target}", "info")
        
        # Her scan için YENİ orchestrator oluştur (modüler)
        api_key = config.GEMINI_API_KEY
        scan_orchestrator = DynamicAgentOrchestrator(api_key=api_key)
        logger.info(f"✅ Scan {scan_id} için yeni orchestrator oluşturuldu")
        
        # Orchestrator ile scan çalıştır - streaming düşünce ile
        result = await scan_orchestrator.run_autonomous_pentest_streaming(
            target=target,
            user_task=task or f"Kapsamlı güvenlik testi yap",
            status_callback=status_callback
        )
        
        # Scan tamamlanma mesajı
        await status_callback(f"✅ Scan tamamlandı: {scan_id}", "success")
        
        # Sonuçları broadcast et
        result_data = {
            "type": "scan_completed",
            "scan_id": scan_id,
            "result": result.to_dict() if hasattr(result, 'to_dict') else str(result),
            "timestamp": datetime.now().strftime("%H:%M:%S")
        }
        await manager.broadcast(json.dumps(result_data))
        
    except Exception as e:
        logger.error(f"Scan çalıştırma hatası: {e}")
        await status_callback(f"❌ Scan hatası: {str(e)}", "error")

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
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "message": "WebSocket bağlantısı kuruldu"
        }
        
        await manager.send_personal_message(
            json.dumps(connection_status),
            websocket
        )
        logger.info("Bağlantı durumu mesajı gönderildi")
        
        while True:
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
                        "timestamp": datetime.now().strftime("%H:%M:%S")
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
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
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
                                "timestamp": datetime.now().strftime("%H:%M:%S")
                            }
                            await manager.send_personal_message(json.dumps(ai_response_data), websocket)
                        else:
                            # Diğer mesajlar
                            status_data = {
                                "type": "scan_status",
                                "scan_id": scan_id,
                                "timestamp": datetime.now().strftime("%H:%M:%S"),
                                "message": msg,
                                "status_type": status_type
                            }
                            await manager.send_personal_message(json.dumps(status_data), websocket)
                    
                    # Async AI yanıt al
                    asyncio.create_task(run_scan_async(scan_id, "", task, ws_ai_callback))
                    logger.info("AI yanıt task başlatıldı")
            
    except WebSocketDisconnect:
        logger.info("WebSocket bağlantısı kapatıldı")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket hatası: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        manager.disconnect(websocket)

# ==================== RAG QUERY OPTIMIZATION ====================

async def optimize_rag_query(user_query: str) -> str:
    """
    🤖 AI ile RAG sorgusu optimize et
    
    Kullanıcının doğal dil sorgusu → CVE aramasına optimize edilmiş kısa sorgu
    
    Örnek:
        "SQL injection nasıl test edilir?" → "SQL injection CVE testing methods"
        "Apache için kritik güvenlik zafiyetleri" → "Apache critical security vulnerabilities"
    """
    global gemini_model
    
    if not gemini_model:
        logger.warning("Gemini model yok, query optimize edilmeden kullanılacak")
        return user_query
    
    try:
        optimization_prompt = f"""Sen bir CVE veritabanı arama uzmanısın. Kullanıcının doğal dil sorgusu veriliyor.

KULLANICI SORGUSU: "{user_query}"

GÖREV:
Kullanıcının sorgusunu CVE araması için OPTIMIZE ET. 

KURALLAR:
1. KISA ve NET olmalı (max 5-7 kelime)
2. CVE veritabanında kullanılan teknik terimleri kullan
3. Gereksiz kelimeleri kaldır ("nasıl", "neden", "ne", vb.)
4. İngilizce terimleri tercih et (CVE'ler İngilizce)
5. Sadece anahtar kelimeleri tut

ÖRNEKLER:
"SQL injection nasıl test edilir?" → "SQL injection testing methods"
"Apache için kritik güvenlik zafiyetleri" → "Apache critical vulnerabilities"
"WordPress eklentilerinde XSS" → "WordPress plugin XSS vulnerabilities"
"Kubernetes container escape" → "Kubernetes container escape CVE"
"Remote code execution Laravel" → "Laravel remote code execution"

SADECE OPTİMİZE EDİLMİŞ SORGUYU DÖNDÜR (açıklama yapma):"""

        response = await gemini_model.generate_content_async(optimization_prompt)
        
        # Response string veya object olabilir
        if isinstance(response, str):
            optimized = response.strip()
        elif hasattr(response, 'text'):
            optimized = response.text.strip()
        elif hasattr(response, 'get'):
            optimized = response.get('text', user_query).strip()
        else:
            logger.warning(f"Unexpected response type: {type(response)}")
            optimized = str(response).strip()
        
        # Tırnak işaretlerini temizle
        optimized = optimized.strip('"\'` ')
        
        # Çok uzunsa kes (max 100 karakter)
        if len(optimized) > 100:
            optimized = optimized[:100]
        
        logger.info(f"🤖 Query optimized: '{user_query}' → '{optimized}'")
        return optimized
        
    except Exception as e:
        logger.error(f"LLM query oluşturma hatası: {e}")
        logger.warning("LLM query oluşturamadı, basit query kullanılıyor")
        # Hata durumunda orijinal query'yi kullan
        return user_query


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
        limit = min(int(request.get("limit", 5)), 50)  # Max 50
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
        
        # 🤖 AI ile query'yi optimize et
        optimized_query = await optimize_rag_query(original_query)
        
        # CVE araması yap (optimize edilmiş query ile)
        results = rag_service.search_cve(optimized_query, limit=limit, severity=severity)
        
        return {
            "success": True,
            "original_query": original_query,
            "optimized_query": optimized_query,
            "query": optimized_query,  # Backward compatibility
            "total_results": len(results),
            "severity_filter": severity,
            "results": [r.to_dict() for r in results]
        }
        
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
        
        return {
            "success": True,
            "total_results": len(results),
            "results": [r.to_dict() for r in results],
            "llm_query": analysis_result.get('query', ''),
            "scan_summary": analysis_result.get('summary', '')
        }
        
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
            "json": "application/json"
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
        
        if not scan_results:
            raise HTTPException(status_code=400, detail="scan_results gerekli")
        
        logger.info(f"Rapor oluşturuluyor - Target: {target}, CVE count: {len(cve_results)}")
        
        # ReportGenerator'ı import et
        from agent_core.report_generator import ReportGenerator
        from agent_core.state import AgentState
        from datetime import datetime as dt
        
        # AgentState oluştur
        state = AgentState(target=target, user_task="Güvenlik raporu oluştur")
        state.start_time = dt.now()
        
        # ÖNCELİKLE: Gerçek tarama bulgularını ekle (scan_results'tan)
        logger.info(f"Scan results tipi: {type(scan_results)}, içerik: {list(scan_results.keys()) if isinstance(scan_results, dict) else 'dict değil'}")
        
        # scan_results'dan bulguları çıkar
        findings_added = 0
        if isinstance(scan_results, dict):
            # Tool sonuçlarını kontrol et
            for key, value in scan_results.items():
                if isinstance(value, dict):
                    # Tool sonucu mu?
                    if value.get('success') and value.get('data'):
                        tool_data = value.get('data', {})
                        
                        # Zafiyetleri bul
                        vulnerabilities = tool_data.get('vulnerabilities', [])
                        findings = tool_data.get('findings', [])
                        results = tool_data.get('results', [])
                        
                        # Tüm bulguları işle
                        for item in (vulnerabilities + findings + results):
                            if isinstance(item, dict):
                                finding = {
                                    'title': item.get('title') or item.get('name') or item.get('vulnerability', 'Tespit Edilen Zafiyet'),
                                    'severity': item.get('severity', 'medium').lower(),
                                    'description': item.get('description') or item.get('details') or 'Zafiyet tespit edildi',
                                    'cvss_score': item.get('cvss_score') or item.get('cvss', 'N/A'),
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
        
        logger.info(f"Tarama sonuçlarından {findings_added} bulgu eklendi")
        
        # EĞER HİÇ BULGU YOKSA - scan_results'ı direkt parse et
        if findings_added == 0:
            logger.warning("⚠️ Hiç bulgu bulunamadı, scan_results direkt parse ediliyor")
            logger.info(f"📊 scan_results FULL: {scan_results}")
            
            # SAÇMALIK FİLTRESİ: user_task, start_time, target gibi meta alanları atla
            SKIP_KEYS = {'target', 'user_task', 'start_time', 'end_time', 'execution_time', 'status', 'conversation_id'}
            
            # Basit format: {"tool_name": "result_string"} veya nested
            for key, value in scan_results.items():
                # Meta alanları atla
                if key in SKIP_KEYS:
                    continue
                    
                # String sonuç mu ve anlamlı mı?
                if isinstance(value, str) and len(value) > 10:
                    finding = {
                        'title': f"{key} Sonucu",
                        'severity': 'medium',
                        'description': value[:500],
                        'cvss_score': 'N/A',
                        'cve_id': None,
                        'evidence': value,
                        'recommendation_summary': f"{key} sonuçları incelenmeli",
                        'business_impact': 'Tespit edilen bulgular güvenlik riski oluşturabilir',
                        'exploitability': 'Unknown',
                        'target': target,
                        'technology': key
                    }
                    state.findings.append(finding)
                    findings_added += 1
        
        logger.info(f"✅ TOPLAM BULGU: {len(state.findings)}")
        
        # SONRA: RAG CVE sonuçlarını referans olarak ekle (sadece ilişkili CVE'ler)
        for i, cve in enumerate(cve_results[:3], 1):  # En yakın 3 CVE
            # CVSS skorunu doğru çek
            cvss_score = cve.get('cvss_score') or cve.get('base_score') or cve.get('cvss') or cve.get('baseScore', 'N/A')
            
            finding = {
                'title': f"Iliskili CVE: {cve.get('cve_id', f'CVE-{i}')}",
                'severity': _map_cvss_to_severity(cvss_score),
                'description': cve.get('description', 'Açıklama mevcut değil')[:500],  # İlk 500 karakter
                'cvss_score': cvss_score,
                'cve_id': cve.get('cve_id', 'N/A'),
                'evidence': f"RAG Eşleşme Skoru: %{cve.get('score', 0)*100:.1f}\n\nCVSS Vektör: {cve.get('cvss_vector') or cve.get('vector', 'N/A')}\n\n{cve.get('description', 'Açıklama yok')}",
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
                    rag_results = await rag_service.search(optimized_query)
                    
                    if rag_results:
                        logger.info(f"🎯 RAG'dan {len(rag_results)} CVE bulundu")
                        # CVE'leri findings'e ekle
                        for i, cve in enumerate(rag_results[:3], 1):
                            # CVEResult objesini dict'e çevir
                            if hasattr(cve, 'to_dict'):
                                cve_dict = cve.to_dict()
                            else:
                                cve_dict = cve
                            
                            finding = {
                                'title': f"RAG CVE: {cve_dict.get('cve_id', f'CVE-{i}')}",
                                'severity': _map_cvss_to_severity(cve_dict.get('base_score', 5.0)),
                                'description': cve_dict.get('description', 'Açıklama mevcut değil')[:500],
                                'cvss_score': cve_dict.get('base_score', 'N/A'),
                                'cve_id': cve_dict.get('cve_id', 'N/A'),
                                'evidence': f"RAG Query: {optimized_query}\n\n{cve_dict.get('description', 'Açıklama yok')}",
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
        
        # ReportGenerator oluştur
        report_gen = ReportGenerator(rag_client=None, llm_api_key=None)
        
        # Rapor oluştur (PDF, TXT, JSON)
        from datetime import datetime as dt
        report_id = f"report_{dt.now().strftime('%Y%m%d_%H%M%S')}"
        report_path = f"reports/{report_id}"
        
        # reports dizinini oluştur
        import os
        os.makedirs("reports", exist_ok=True)
        
        # Rapor oluştur (TÜM TOOL ÇIKTILARI İLE)
        success = await report_gen.generate_report(state, report_path)
        
        if not success:
            raise HTTPException(status_code=500, detail="Rapor oluşturulamadı")
        
        # TÜM TOOL ÇIKTILARINI RAPOR İÇİN HAZIRLA
        all_tool_outputs = {}
        if hasattr(state, 'discovered_information'):
            for key, value in state.discovered_information.items():
                if key.startswith("tool_"):
                    tool_name = key[5:]  # "tool_" prefix'ini kaldır
                    all_tool_outputs[tool_name] = value
        
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
        
        # Rapor için zenginleştirilmiş veri hazırla
        enriched_data = {
            "findings": state.findings,
            "target": state.target,
            "user_task": state.user_task,
            "all_tool_outputs": all_tool_outputs,
            "discovered_information": state.discovered_information,
            "execution_summary": {
                "tools_executed": list(all_tool_outputs.keys()),
                "successful_tools": list(all_tool_outputs.keys()),
                "total_findings": len(state.findings),
                "scan_duration": "N/A"
            }
        }
        
        # Profesyonel rapor oluştur
        report_content = report_gen.generate_comprehensive_report(enriched_data)
        
        # Risk skoru hesapla (tüm bulgulardan)
        all_findings = state.findings  # Tüm bulguları al
        risk_score = report_gen._calculate_risk_score(all_findings)
        
        # Zafiyet sayıları
        vulnerabilities = {
            "critical": len([f for f in state.findings if f.get('severity') == 'critical']),
            "high": len([f for f in state.findings if f.get('severity') == 'high']),
            "medium": len([f for f in state.findings if f.get('severity') == 'medium']),
            "low": len([f for f in state.findings if f.get('severity') == 'low']),
        }
        
        # Yapılandırılmış rapor verisini al (tool bulguları + CVE tablosu)
        structured_report = report_gen.get_structured_report_data_with_cves(state, cve_findings)
        
        logger.info(f"✅ Rapor başarıyla oluşturuldu: {report_id}")
        
        # Datetime import'u burada yap
        from datetime import datetime as dt
        
        return {
            "success": True,
            "report_id": report_id,
            "target": target,
            "risk_score": risk_score,
            "vulnerabilities": vulnerabilities,
            "pages": len(report_content.split('\n')) // 50,  # Tahmini sayfa sayısı
            "createdAt": dt.now().isoformat(),
            "download_url": f"/api/reports/{report_id}/download",
            "report_content": report_content[:5000],  # İlk 5000 karakter
            "formats_available": ["txt", "pdf", "json"],
            "files": {
                "txt": f"{txt_path}",
                "pdf": f"{report_path}.pdf",
                "json": f"{report_path}.json"
            },
            # Tüm rapor bölümleri
            "structured_data": structured_report
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rapor oluşturma hatası: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Rapor oluşturma hatası: {str(e)}")

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
