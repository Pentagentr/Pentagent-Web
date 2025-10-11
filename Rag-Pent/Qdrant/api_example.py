"""
CVE Search API - Production Kullanım Örneği
Bu dosya canlı sisteme entegrasyon için örnek API gösterir.
FastAPI, Flask veya diğer web framework'lere entegre edilebilir.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import uvicorn

from cve_search import CVESearchEngine, SearchConfig, get_search_engine

# FastAPI uygulaması
app = FastAPI(
    title="CVE Search API",
    description="Hybrid search (sparse+dense) ile CVE arama API'si",
    version="1.0.0"
)


# Request/Response modelleri
class SearchRequest(BaseModel):
    """Arama isteği modeli"""
    query: str = Field(..., description="Arama sorgusu", min_length=1)
    limit: int = Field(10, description="Maksimum sonuç sayısı", ge=1, le=100)
    dense_weight: Optional[float] = Field(None, description="Dense vektör ağırlığı (0-1)", ge=0, le=1)
    sparse_weight: Optional[float] = Field(None, description="Sparse vektör ağırlığı (0-1)", ge=0, le=1)
    min_score: float = Field(0.0, description="Minimum skor eşiği", ge=0)


class SeveritySearchRequest(BaseModel):
    """Severity filtrelemeli arama isteği"""
    query: str = Field(..., description="Arama sorgusu", min_length=1)
    severity: str = Field(..., description="Severity seviyesi (CRITICAL, HIGH, MEDIUM, LOW)")
    limit: int = Field(10, description="Maksimum sonuç sayısı", ge=1, le=100)


class SearchResponse(BaseModel):
    """Arama yanıtı modeli"""
    success: bool
    total_results: int
    results: List[Dict[str, Any]]
    query: str
    execution_time_ms: Optional[float] = None


class HealthResponse(BaseModel):
    """Sağlık kontrolü yanıtı"""
    status: str
    healthy: bool
    stats: Dict[str, Any]


# Search engine instance'ı (uygulama başlangıcında oluşturulur)
search_engine: Optional[CVESearchEngine] = None


@app.on_event("startup")
async def startup_event():
    """Uygulama başlarken search engine'i başlat"""
    global search_engine
    try:
        # Config ayarları (production'da env variable'lardan alınabilir)
        config = SearchConfig(
            qdrant_host="localhost",  # Docker: "qdrant" service name kullanılabilir
            qdrant_port=6333,
            collection_name="cve_collection_hybrid",
            default_dense_weight=0.7,  # Semantik search öncelikli
            default_sparse_weight=0.3
        )
        search_engine = CVESearchEngine(config)
        print("✅ Search engine başlatıldı")
    except Exception as e:
        print(f"❌ Search engine başlatma hatası: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Uygulama kapanırken temizlik yap"""
    global search_engine
    search_engine = None
    print("🔒 Search engine kapatıldı")


@app.get("/", tags=["Root"])
async def root():
    """API ana sayfa"""
    return {
        "message": "CVE Search API",
        "version": "1.0.0",
        "endpoints": {
            "search": "/api/v1/search",
            "search_by_severity": "/api/v1/search/severity",
            "get_cve": "/api/v1/cve/{cve_id}",
            "health": "/api/v1/health",
            "stats": "/api/v1/stats"
        }
    }


@app.post("/api/v1/search", response_model=SearchResponse, tags=["Search"])
async def search(request: SearchRequest):
    """
    Hybrid search (dense + sparse) ile CVE arama yapar.
    
    Dense vektörler default olarak daha yüksek ağırlıktadır (semantik search öncelikli).
    """
    if search_engine is None:
        raise HTTPException(status_code=503, detail="Search engine hazır değil")
    
    try:
        import time
        start_time = time.time()
        
        # Arama yap
        results = search_engine.search(
            query=request.query,
            limit=request.limit,
            dense_weight=request.dense_weight,
            sparse_weight=request.sparse_weight,
            min_score=request.min_score
        )
        
        execution_time = (time.time() - start_time) * 1000  # ms
        
        return SearchResponse(
            success=True,
            total_results=len(results),
            results=[r.to_dict() for r in results],
            query=request.query,
            execution_time_ms=round(execution_time, 2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Arama hatası: {str(e)}")


@app.post("/api/v1/search/severity", response_model=SearchResponse, tags=["Search"])
async def search_by_severity(request: SeveritySearchRequest):
    """
    Severity filtresine göre CVE arama yapar.
    
    Allowed severity values: CRITICAL, HIGH, MEDIUM, LOW
    """
    if search_engine is None:
        raise HTTPException(status_code=503, detail="Search engine hazır değil")
    
    # Severity validasyonu
    allowed_severities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    if request.severity.upper() not in allowed_severities:
        raise HTTPException(
            status_code=400,
            detail=f"Geçersiz severity. Allowed: {', '.join(allowed_severities)}"
        )
    
    try:
        import time
        start_time = time.time()
        
        # Severity filtrelemeli arama
        results = search_engine.search_by_severity(
            query=request.query,
            severity=request.severity,
            limit=request.limit
        )
        
        execution_time = (time.time() - start_time) * 1000
        
        return SearchResponse(
            success=True,
            total_results=len(results),
            results=[r.to_dict() for r in results],
            query=f"{request.query} (severity={request.severity})",
            execution_time_ms=round(execution_time, 2)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Arama hatası: {str(e)}")


@app.get("/api/v1/cve/{cve_id}", tags=["CVE"])
async def get_cve(cve_id: str):
    """
    CVE ID'ye göre doğrudan CVE detaylarını getirir.
    
    Örnek: CVE-2024-12345
    """
    if search_engine is None:
        raise HTTPException(status_code=503, detail="Search engine hazır değil")
    
    try:
        result = search_engine.get_cve_by_id(cve_id)
        
        if result is None:
            raise HTTPException(status_code=404, detail=f"CVE bulunamadı: {cve_id}")
        
        return {
            "success": True,
            "cve": result.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")


@app.get("/api/v1/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Sistem sağlık kontrolü yapar.
    """
    if search_engine is None:
        return HealthResponse(
            status="unhealthy",
            healthy=False,
            stats={}
        )
    
    try:
        healthy = search_engine.health_check()
        stats = search_engine.get_stats() if healthy else {}
        
        return HealthResponse(
            status="healthy" if healthy else "unhealthy",
            healthy=healthy,
            stats=stats
        )
        
    except Exception as e:
        return HealthResponse(
            status="error",
            healthy=False,
            stats={"error": str(e)}
        )


@app.get("/api/v1/stats", tags=["System"])
async def get_stats():
    """
    Collection istatistiklerini döner.
    """
    if search_engine is None:
        raise HTTPException(status_code=503, detail="Search engine hazır değil")
    
    try:
        stats = search_engine.get_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats hatası: {str(e)}")


# Hata yönetimi
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global hata yakalayıcı"""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    """
    Development modunda çalıştırma:
    python api_example.py
    
    Production modunda çalıştırma:
    uvicorn api_example:app --host 0.0.0.0 --port 8000 --workers 4
    """
    print("🚀 CVE Search API başlatılıyor...")
    print("📖 Dokümantasyon: http://localhost:8000/docs")
    print("📊 ReDoc: http://localhost:8000/redoc")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

