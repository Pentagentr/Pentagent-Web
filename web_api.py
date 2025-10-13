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
                
                if target:
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
        results = rag_service.analyze_scan_results(scan_results)
        results = results[:limit]  # Limit uygula
        
        return {
            "success": True,
            "total_results": len(results),
            "results": [r.to_dict() for r in results]
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
