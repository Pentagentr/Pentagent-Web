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
            # WebSocket state kontrolü ekle
            if websocket in self.active_connections:
                # WebSocket bağlantı durumunu kontrol et
                try:
                    await websocket.send_text(message)
                except RuntimeError as re:
                    # "WebSocket is not connected" hatası
                    logger.warning(f"WebSocket bağlantısı kapalı: {re}")
                    self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Mesaj gönderme hatası: {e}")
            logger.error(f"WebSocket hatası: {type(e).__name__}: {str(e)}")
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

@app.get("/")
async def root():
    return {"message": "Pentagent API Server", "status": "running"}

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
        # UnifiedLLM kullanır (Groq API key'i env'den alır)
        scan_orchestrator = DynamicAgentOrchestrator(api_key=None)  # api_key ignored, uses env
        logger.info(f"✅ Scan {scan_id} için yeni orchestrator oluşturuldu (Groq)")
        
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
    global llm_model
    
    if not llm_model:
        logger.warning("LLM model yok, query optimize edilmeden kullanılacak")
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

        response = await llm_model.generate_content_async(optimization_prompt)
        
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
        state.findings = []  # Findings listesini başlat
        state.discovered_information = {}  # Discovered information'ı başlat
        
        # ÖNCELİKLE: Gerçek tarama bulgularını ekle (scan_results'tan)
        logger.info(f"Scan results tipi: {type(scan_results)}, içerik: {list(scan_results.keys()) if isinstance(scan_results, dict) else 'dict değil'}")
        
        # scan_results'dan bulguları çıkar - GELİŞTİRİLMİŞ PARSING
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
                        
                        # Zafiyetleri bul
                        vulnerabilities = tool_data.get('vulnerabilities', [])
                        findings = tool_data.get('findings', [])
                        results = tool_data.get('results', [])
                        
                        # Tüm bulguları işle
                        for item in (vulnerabilities + findings + results):
                            if isinstance(item, dict):
                                # Severity'yi daha agresif belirle
                                severity = item.get('severity', 'medium').lower()
                                title = item.get('title') or item.get('name') or item.get('vulnerability', 'Tespit Edilen Zafiyet')
                                
                                # Kritik kelimeler varsa severity'yi yükselt
                                critical_keywords = ['critical', 'kritik', 'high', 'yüksek', 'exploit', 'rce', 'sql injection', 'xss', 'lfi', 'rfi']
                                if any(keyword in title.lower() for keyword in critical_keywords):
                                    severity = 'high'
                                
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
                                logger.info(f"🔍 Bulgu eklendi: {title} - Severity: {severity}")
                    
                    # EĞER TOOL DATA'DA VULNERABILITIES/FINDINGS YOKSA - TOOL'A ÖZEL PARSING
                    elif value.get('success') and isinstance(value.get('data'), dict):
                        tool_data = value.get('data', {})
                        
                        # RAG analysis data'dan bulguları çıkar
                        if 'rag_analysis_data' in tool_data:
                            rag_data = tool_data['rag_analysis_data']
                            scan_metadata = rag_data.get('scan_metadata', {})
                            
                            # Endpoint sayısına göre bulgu oluştur
                            total_endpoints = scan_metadata.get('total_endpoints_found', 0)
                            if total_endpoints > 0:
                                if total_endpoints >= 20:
                                    severity = 'critical'
                                    cvss = '9.0'
                                elif total_endpoints >= 15:
                                    severity = 'high'
                                    cvss = '8.0'
                                elif total_endpoints >= 10:
                                    severity = 'high'
                                    cvss = '7.5'
                                else:
                                    severity = 'medium'
                                    cvss = '6.0'
                                
                                finding = {
                                    'title': f'Çok Fazla Endpoint Bulundu: {total_endpoints} endpoint',
                                    'severity': severity,
                                    'description': f'Web crawler {total_endpoints} endpoint tespit etti. Bu geniş saldırı yüzeyi oluşturur.',
                                    'cvss_score': cvss,
                                    'cve_id': None,
                                    'evidence': f'Total endpoints: {total_endpoints}, Pages crawled: {scan_metadata.get("total_pages_crawled", 0)}',
                                    'recommendation_summary': 'Endpoint sayısını azaltın ve gereksiz sayfaları kaldırın',
                                    'business_impact': 'Geniş saldırı yüzeyi güvenlik riski oluşturur',
                                    'exploitability': 'High',
                                    'target': target,
                                    'technology': 'Web Application'
                                }
                                state.findings.append(finding)
                                findings_added += 1
                            
                            # Form sayısına göre bulgu oluştur
                            total_forms = scan_metadata.get('total_forms_found', 0)
                            if total_forms > 0:
                                if total_forms >= 10:
                                    severity = 'critical'
                                    cvss = '9.0'
                                elif total_forms >= 5:
                                    severity = 'high'
                                    cvss = '8.0'
                                else:
                                    severity = 'medium'
                                    cvss = '6.5'
                                
                                finding = {
                                    'title': f'Çok Fazla Form Bulundu: {total_forms} form',
                                    'severity': severity,
                                    'description': f'Web crawler {total_forms} form tespit etti. Formlar potansiyel saldırı vektörüdür.',
                                    'cvss_score': cvss,
                                    'cve_id': None,
                                    'evidence': f'Total forms: {total_forms}',
                                    'recommendation_summary': 'Form güvenliğini kontrol edin ve input validation uygulayın',
                                    'business_impact': 'Formlar injection saldırıları için hedef olabilir',
                                    'exploitability': 'High',
                                    'target': target,
                                    'technology': 'Web Application'
                                }
                                state.findings.append(finding)
                                findings_added += 1
                            
                            # Kritik endpoint'leri kontrol et
                            endpoints_for_analysis = rag_data.get('endpoints_for_analysis', [])
                            critical_endpoints = []
                            for endpoint in endpoints_for_analysis:
                                path = endpoint.get('path', '').lower()
                                if any(keyword in path for keyword in ['login', 'admin', 'auth', 'api', 'user', 'cart', 'signup', 'payment']):
                                    critical_endpoints.append(path)
                            
                            if critical_endpoints:
                                finding = {
                                    'title': f'Kritik Endpoint\'ler Bulundu: {len(critical_endpoints)} kritik endpoint',
                                    'severity': 'critical',
                                    'description': f'Kritik endpoint\'ler tespit edildi: {", ".join(critical_endpoints[:5])}',
                                    'cvss_score': '9.5',
                                    'cve_id': None,
                                    'evidence': f'Critical endpoints: {critical_endpoints}',
                                    'recommendation_summary': 'Kritik endpoint\'lerin güvenliğini artırın',
                                    'business_impact': 'Kritik endpoint\'ler yüksek risk taşır',
                                    'exploitability': 'High',
                                    'target': target,
                                    'technology': 'Web Application'
                                }
                                state.findings.append(finding)
                                findings_added += 1
                            # Teknoloji tespiti sonuçlarından finding oluştur
                            technologies = tool_data.get('technologies', [])
                            if technologies:
                                finding = {
                                    'title': f'Teknoloji Tespiti: {len(technologies)} teknoloji bulundu',
                                    'severity': 'low',
                                    'description': f'Tespit edilen teknolojiler: {", ".join(technologies[:5])}',
                                    'cvss_score': 'N/A',
                                    'cve_id': None,
                                    'evidence': f'Technologies: {technologies}',
                                    'recommendation_summary': 'Tespit edilen teknolojilerin güvenlik güncellemelerini kontrol edin',
                                    'business_impact': 'Bilinen teknolojiler potansiyel güvenlik riskleri taşıyabilir',
                                    'exploitability': 'Information Gathering',
                                    'target': target,
                                    'technology': 'Technology Detection'
                                }
                                state.findings.append(finding)
                                findings_added += 1
                        
                        elif key == 'enum_directory_bruteforce':
                            # Directory bruteforce sonuçlarından finding oluştur - HER DİZİN İÇİN AYRI
                            directories = tool_data.get('directories', [])
                            files = tool_data.get('files', [])
                            
                            # Her dizin için ayrı finding oluştur
                            for dir_info in directories:
                                path = dir_info.get('path', '')
                                if 'admin' in path.lower() or 'login' in path.lower() or 'dashboard' in path.lower():
                                    severity = 'critical'
                                    cvss = '9.0'
                                elif 'api' in path.lower() or 'config' in path.lower() or 'backup' in path.lower():
                                    severity = 'high'
                                    cvss = '7.5'
                                else:
                                    severity = 'medium'
                                    cvss = '5.0'
                                
                                finding = {
                                    'title': f'Dizin Bulundu: {path}',
                                    'severity': severity,
                                    'description': f'Dizin tespit edildi: {path}',
                                    'cvss_score': cvss,
                                    'cve_id': None,
                                    'evidence': f'Directory: {path}, Status: {dir_info.get("status", "Unknown")}',
                                    'recommendation_summary': 'Dizin erişimini kontrol edin',
                                    'business_impact': 'Dizin keşfi bilgi toplama aşamasında kullanılabilir',
                                    'exploitability': 'Medium',
                                    'target': target,
                                    'technology': 'Web Application'
                                }
                                state.findings.append(finding)
                                findings_added += 1
                            
                            # Her dosya için ayrı finding oluştur
                            for file_info in files:
                                path = file_info.get('path', '')
                                if '.env' in path.lower() or '.git' in path.lower():
                                    severity = 'critical'
                                    cvss = '9.5'
                                elif 'backup' in path.lower() or 'config' in path.lower() or 'database' in path.lower():
                                    severity = 'high'
                                    cvss = '8.0'
                                else:
                                    severity = 'medium'
                                    cvss = '5.5'
                                
                                finding = {
                                    'title': f'Dosya Bulundu: {path}',
                                    'severity': severity,
                                    'description': f'Dosya tespit edildi: {path}',
                                    'cvss_score': cvss,
                                    'cve_id': None,
                                    'evidence': f'File: {path}, Status: {file_info.get("status", "Unknown")}',
                                    'recommendation_summary': 'Dosya erişimini kontrol edin',
                                    'business_impact': 'Dosya keşfi bilgi toplama aşamasında kullanılabilir',
                                    'exploitability': 'Medium',
                                    'target': target,
                                    'technology': 'Web Application'
                                }
                                state.findings.append(finding)
                                findings_added += 1
                            
                            # Normal dizinler için finding oluştur
                            normal_dirs = [d for d in directories if d not in critical_dirs]
                            if normal_dirs:
                                finding = {
                                    'title': f'Dizin Keşfi: {len(normal_dirs)} dizin bulundu',
                                    'severity': 'medium',
                                    'description': f'Tespit edilen dizinler: {", ".join([d.get("path", "") for d in normal_dirs[:5]])}',
                                    'cvss_score': '4.0',
                                    'cve_id': None,
                                    'evidence': f'Directories: {[d.get("path") for d in normal_dirs]}',
                                    'recommendation_summary': 'Gereksiz dizinleri kaldırın ve directory listing\'i devre dışı bırakın',
                                    'business_impact': 'Dizin keşfi bilgi toplama aşamasında kullanılabilir',
                                    'exploitability': 'Low',
                                    'target': target,
                                    'technology': 'Web Application'
                                }
                                state.findings.append(finding)
                                findings_added += 1
                            
                            # Kritik dosyalar için finding oluştur
                            critical_files = [f for f in files if any(keyword in f.get('path', '').lower() 
                                                                    for keyword in ['.env', '.git', 'backup', 'config', 'database'])]
                            
                            if critical_files:
                                for file_info in critical_files:
                                    finding = {
                                        'title': f'Kritik Dosya Bulundu: {file_info.get("path", "Unknown")}',
                                        'severity': 'critical',
                                        'description': f'Kritik dosya tespit edildi: {file_info.get("path")}',
                                        'cvss_score': '8.5',
                                        'cve_id': None,
                                        'evidence': f'File: {file_info.get("path")}, Status: {file_info.get("status", "Unknown")}',
                                        'recommendation_summary': 'Kritik dosyaları public erişimden kaldırın',
                                        'business_impact': 'Kritik dosyalar sistem güvenliğini tehlikeye atabilir',
                                        'exploitability': 'High',
                                        'target': target,
                                        'technology': 'Web Application'
                                    }
                                    state.findings.append(finding)
                                    findings_added += 1
                            # XSS test sonuçlarından finding oluştur
                            vulnerabilities = tool_data.get('vulnerabilities', [])
                            if vulnerabilities:
                                for vuln in vulnerabilities:
                                    finding = {
                                        'title': f'XSS Zafiyeti: {vuln.get("type", "Reflected XSS")}',
                                        'severity': vuln.get('severity', 'high').lower(),
                                        'description': vuln.get('description', 'XSS zafiyeti tespit edildi'),
                                        'cvss_score': vuln.get('cvss_score', '7.5'),
                                        'cve_id': vuln.get('cve_id'),
                                        'evidence': vuln.get('evidence', 'XSS payload başarılı'),
                                        'recommendation_summary': 'Input validation ve output encoding uygulayın',
                                        'business_impact': 'XSS saldırıları kullanıcı verilerini tehlikeye atabilir',
                                        'exploitability': 'High',
                                        'target': target,
                                        'technology': 'Web Application'
                                    }
                                    state.findings.append(finding)
                                    findings_added += 1
                            else:
                                # XSS bulunamadı ama test yapıldı
                                finding = {
                                    'title': 'XSS Testi Tamamlandı',
                                    'severity': 'info',
                                    'description': 'Reflected XSS testi yapıldı, kritik zafiyet bulunamadı',
                                    'cvss_score': 'N/A',
                                    'cve_id': None,
                                    'evidence': 'XSS test payloadları gönderildi, pozitif yanıt alınmadı',
                                    'recommendation_summary': 'Düzenli XSS testleri yapın',
                                    'business_impact': 'XSS koruması aktif görünüyor',
                                    'exploitability': 'Low',
                                    'target': target,
                                    'technology': 'Web Application'
                                }
                                state.findings.append(finding)
                                findings_added += 1
                        
                        elif key == 'enum_subdomain_bruteforcer':
                            # Subdomain enumeration sonuçlarından finding oluştur - HER SUBDOMAIN İÇİN AYRI
                            subdomains = tool_data.get('subdomains', [])
                            for subdomain in subdomains:
                                subdomain_name = subdomain.get('subdomain', str(subdomain))
                                if 'admin' in subdomain_name.lower() or 'login' in subdomain_name.lower():
                                    severity = 'critical'
                                    cvss = '9.0'
                                elif 'api' in subdomain_name.lower() or 'dev' in subdomain_name.lower():
                                    severity = 'high'
                                    cvss = '7.5'
                                else:
                                    severity = 'medium'
                                    cvss = '5.0'
                                
                                finding = {
                                    'title': f'Subdomain Bulundu: {subdomain_name}',
                                    'severity': severity,
                                    'description': f'Subdomain tespit edildi: {subdomain_name}',
                                    'cvss_score': cvss,
                                    'cve_id': None,
                                    'evidence': f'Subdomain: {subdomain_name}',
                                    'recommendation_summary': 'Subdomain güvenliğini kontrol edin',
                                    'business_impact': 'Subdomain keşfi saldırı yüzeyini genişletir',
                                    'exploitability': 'Medium',
                                    'target': target,
                                    'technology': 'DNS'
                                }
                                state.findings.append(finding)
                                findings_added += 1
                        
                        elif key == 'enum_port_scanner':
                            # Port tarama sonuçlarından finding oluştur - HER PORT İÇİN AYRI
                            open_ports = tool_data.get('open_ports', [])
                            for port_info in open_ports:
                                port = port_info.get('port', '')
                                service = port_info.get('service', '')
                                if port in ['22', '3389', '5900']:  # SSH, RDP, VNC
                                    severity = 'high'
                                    cvss = '8.0'
                                elif port in ['21', '23', '25', '53', '80', '443']:  # Common services
                                    severity = 'medium'
                                    cvss = '5.0'
                                else:
                                    severity = 'low'
                                    cvss = '3.0'
                                
                                finding = {
                                    'title': f'Açık Port Bulundu: {port} ({service})',
                                    'severity': severity,
                                    'description': f'Açık port tespit edildi: {port} - {service}',
                                    'cvss_score': cvss,
                                    'cve_id': None,
                                    'evidence': f'Port: {port}, Service: {service}',
                                    'recommendation_summary': 'Gereksiz portları kapatın',
                                    'business_impact': 'Açık portlar saldırı yüzeyini artırır',
                                    'exploitability': 'Medium',
                                    'target': target,
                                    'technology': 'Network'
                                }
                                state.findings.append(finding)
                                findings_added += 1
                        
                        elif key == 'enum_directory_bruteforce':
                            # Directory bruteforce sonuçlarından finding oluştur
                            directories = tool_data.get('directories', [])
                            if directories:
                                finding = {
                                    'title': f'Directory Keşfi: {len(directories)} dizin bulundu',
                                    'severity': 'low',
                                    'description': f'Tespit edilen dizinler: {", ".join(directories[:5])}',
                                    'cvss_score': 'N/A',
                                    'cve_id': None,
                                    'evidence': f'Directories: {directories}',
                                    'recommendation_summary': 'Gereksiz dizinleri gizleyin veya kaldırın',
                                    'business_impact': 'Hassas bilgilerin açığa çıkmasına neden olabilir',
                                    'exploitability': 'Low',
                                    'target': target,
                                    'technology': 'Web Application'
                                }
                                state.findings.append(finding)
                                findings_added += 1
                        
                        elif key == 'enum_web_crawler':
                            # Web crawler sonuçlarından finding oluştur
                            endpoints = tool_data.get('endpoints', [])
                            if endpoints:
                                finding = {
                                    'title': f'Web Crawling: {len(endpoints)} endpoint bulundu',
                                    'severity': 'low',
                                    'description': f'Tespit edilen endpointler: {", ".join(endpoints[:5])}',
                                    'cvss_score': 'N/A',
                                    'cve_id': None,
                                    'evidence': f'Endpoints: {endpoints}',
                                    'recommendation_summary': 'Endpointleri güvenlik açısından kontrol edin',
                                    'business_impact': 'Genişletilmiş saldırı yüzeyi oluşturabilir',
                                    'exploitability': 'Information Gathering',
                                    'target': target,
                                    'technology': 'Web Application'
                                }
                                state.findings.append(finding)
                                findings_added += 1
                        
                        elif key == 'enum_firewall_detector':
                            # Firewall detection sonuçlarından finding oluştur
                            firewall_info = tool_data.get('firewall_info', {})
                            if firewall_info:
                                finding = {
                                    'title': f'Firewall Tespiti: {firewall_info.get("type", "Unknown")}',
                                    'severity': 'info',
                                    'description': f'Firewall tespit edildi: {firewall_info}',
                                    'cvss_score': 'N/A',
                                    'cve_id': None,
                                    'evidence': f'Firewall info: {firewall_info}',
                                    'recommendation_summary': 'Firewall konfigürasyonunu gözden geçirin',
                                    'business_impact': 'Firewall koruması aktif',
                                    'exploitability': 'Information Gathering',
                                    'target': target,
                                    'technology': 'Network Security'
                                }
                                state.findings.append(finding)
                                findings_added += 1
                        
                        # GENEL TOOL SONUCU - Eğer yukarıdaki tool'lardan hiçbiri değilse
                        else:
                            # Tool'un genel sonucundan finding oluştur
                            if tool_data:
                                finding = {
                                    'title': f'{key.replace("_", " ").title()} Testi',
                                    'severity': 'info',
                                    'description': f'{key} testi tamamlandı',
                                    'cvss_score': 'N/A',
                                    'cve_id': None,
                                    'evidence': f'Tool data: {str(tool_data)[:200]}',
                                    'recommendation_summary': f'{key} test sonuçları incelenmeli',
                                    'business_impact': 'Test sonuçları güvenlik değerlendirmesi için önemli',
                                    'exploitability': 'Information Gathering',
                                    'target': target,
                                    'technology': 'Security Testing'
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
        
        # AI ile geliştirilmiş rapor oluştur
        ai_report_content = await report_gen.generate_ai_enhanced_report(state, scan_results, cve_results)
        
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
                scan_results=scan_results
            )
            
            # LLM raporunu da kaydet
            llm_md_path = f"{report_path}_llm.md"
            with open(llm_md_path, 'w', encoding='utf-8') as f:
                f.write(llm_report)
            logger.info(f"✅ LLM raporu oluşturuldu: {llm_md_path}")
            
        except Exception as e:
            logger.error(f"❌ LLM rapor üretimi hatası: {e}", exc_info=True)
            llm_report = "LLM raporu oluşturulamadı"
        
        # Rapor oluştur (TÜM TOOL ÇIKTILARI İLE)
        success = await report_gen.generate_report(state, report_path)
        
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
        
        # Risk skoru hesapla (tüm bulgulardan)
        all_findings = state.findings  # Tüm bulguları al
        logger.info(f"📊 RAPOR GENERATİON - Toplam bulgu sayısı: {len(all_findings)}")
        logger.info(f"📊 Bulgular detayı: {[(f.get('title'), f.get('severity')) for f in all_findings[:5]]}")
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
        
        # Eğer hiç bulgu yoksa, scan_results'tan AGRESİF parse et
        if len(state.findings) == 0:
            logger.warning("⚠️ Hiç bulgu bulunamadı, scan_results AGRESİF parse ediliyor")
            # Scan results'tan bulguları tekrar parse et - DAHA AGRESİF
            if isinstance(scan_results, dict):
                for key, value in scan_results.items():
                    # Meta alanları atla
                    if key in {'target', 'user_task', 'start_time', 'end_time', 'execution_time', 'status', 'conversation_id'}:
                        continue
                    
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
                            logger.info(f"🔍 Genel bulgu eklendi: {key}")
            
            # Hala bulgu yoksa, en az bir bulgu oluştur
            if len(state.findings) == 0:
                logger.warning("⚠️ Hala bulgu yok, minimum bulgu oluşturuluyor")
                finding = {
                    'title': 'Tarama Tamamlandı',
                    'severity': 'info',
                    'description': f'{target} için güvenlik taraması tamamlandı',
                    'cvss_score': 'N/A',
                    'cve_id': None,
                    'evidence': 'Tarama sonuçları analiz edildi',
                    'recommendation_summary': 'Düzenli güvenlik taramaları yapın',
                    'business_impact': 'Güvenlik taraması tamamlandı',
                    'exploitability': 'Low',
                    'target': target,
                    'technology': 'Security Assessment'
                }
                state.findings.append(finding)
                logger.info("🔍 Minimum bulgu eklendi")
        
        # all_findings'i güncelle - SADECE TOOL BULGULARI (CVE referansları risk skorunu çok artırmasın)
        all_findings = state.findings.copy()
        
        # NOT: CVE'leri risk hesaplamasına dahil ETMİYORUZ
        # Çünkü CVE'ler sadece referans için, tool bulgularına öncelik veriyoruz
        logger.info(f"📊 Risk skoru sadece tool bulgularıyla hesaplanacak: {len(all_findings)} bulgu")
        
        risk_score = report_gen._calculate_risk_score(all_findings)
        logger.info(f"📊 Hesaplanan risk skoru (SADECE tool bulguları): {risk_score} (Toplam bulgu: {len(all_findings)})")
        
        # Vulnerabilities objesini oluştur (frontend için)
        vulnerabilities = {
            'critical': len([f for f in all_findings if f.get('severity') == 'critical']),
            'high': len([f for f in all_findings if f.get('severity') == 'high']),
            'medium': len([f for f in all_findings if f.get('severity') == 'medium']),
            'low': len([f for f in all_findings if f.get('severity') == 'low']),
            'info': len([f for f in all_findings if f.get('severity') == 'info'])
        }
        logger.info(f"📊 Vulnerabilities objesi: {vulnerabilities}")
        logger.info(f"📊 Toplam zafiyet: {sum(vulnerabilities.values())}")
        
        # Risk skoru 0 ise ve bulgular varsa, minimum skor ver
        if risk_score == 0 and len(all_findings) > 0:
            severity_counts = {
                'critical': len([f for f in all_findings if f.get('severity') == 'critical']),
                'high': len([f for f in all_findings if f.get('severity') == 'high']),
                'medium': len([f for f in all_findings if f.get('severity') == 'medium']),
                'low': len([f for f in all_findings if f.get('severity') == 'low'])
            }
            if severity_counts['critical'] > 0:
                risk_score = 85
            elif severity_counts['high'] > 0:
                risk_score = 65
            elif severity_counts['medium'] > 0:
                risk_score = 45
            elif severity_counts['low'] > 0:
                risk_score = 25
            else:
                risk_score = 15
        elif risk_score == 0 and len(all_findings) == 0:
            risk_score = 5
        
        
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
            "formats_available": ["txt", "pdf", "json", "md"],
            "files": {
                "txt": f"{report_path}.txt",
                "pdf": f"{report_path}.pdf",
                "json": f"{report_path}.json",
                "md": f"{report_path}.md"
            },
            # Tüm rapor bölümleri
            "structured_data": structured_report,
            # Tool çıktılarını ekle
            "all_tool_outputs": all_tool_outputs
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
