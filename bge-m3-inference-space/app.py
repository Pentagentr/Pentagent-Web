"""
BGE-M3 Custom Inference API
Native Sparse + Dense Vector Generation

Endpoints:
- POST /encode - Generate embeddings
- GET /health - Health check
"""

import logging
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# BGE-M3 Model
try:
    from FlagEmbedding import BGEM3FlagModel
    import torch
except ImportError as e:
    logging.error(f"FlagEmbedding import error: {e}")
    raise

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="BGE-M3 Custom Inference API",
    description="Native sparse + dense vector generation for CVE RAG",
    version="1.0.0"
)

# Global model instance
model = None


def load_model():
    """Load BGE-M3 model (singleton)"""
    global model
    if model is None:
        logger.info("Loading BGE-M3 model...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        use_fp16 = device == "cuda"
        model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=use_fp16)
        logger.info(f"✅ BGE-M3 model loaded (device: {device})")
    return model


# Request/Response models
class EncodeRequest(BaseModel):
    """Encoding request"""
    inputs: str  # Single query or list
    return_dense: bool = True
    return_sparse: bool = True
    return_colbert_vecs: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "inputs": "SQL injection vulnerability in Apache 2.4.49",
                "return_dense": True,
                "return_sparse": True
            }
        }


class EncodeResponse(BaseModel):
    """Encoding response"""
    dense_vecs: List[float] = None
    lexical_weights: Dict[int, float] = None
    colbert_vecs: List[List[float]] = None


@app.on_event("startup")
async def startup_event():
    """Load model on startup"""
    try:
        load_model()
        logger.info("🚀 BGE-M3 Inference API is ready!")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "BGE-M3 Custom Inference API",
        "status": "running",
        "endpoints": {
            "encode": "POST /encode",
            "health": "GET /health"
        },
        "model": "BAAI/bge-m3",
        "features": [
            "Native sparse vectors (lexical_weights)",
            "Dense embeddings (1024 dim)",
            "ColBERT multi-vectors (optional)"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        if model is None:
            return {"status": "loading", "model": "not_ready"}
        return {
            "status": "healthy",
            "model": "BAAI/bge-m3",
            "device": "cuda" if torch.cuda.is_available() else "cpu"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {e}")


@app.post("/encode", response_model=EncodeResponse)
async def encode(request: EncodeRequest):
    """
    Generate BGE-M3 embeddings (dense + sparse)
    
    Native sparse vector support (lexical_weights) - NOT approximation!
    """
    try:
        # Load model if not loaded
        m = load_model()
        
        # Validate input
        if not request.inputs or not request.inputs.strip():
            raise HTTPException(status_code=400, detail="Empty input")
        
        query = request.inputs.strip()
        logger.info(f"📝 Encoding query: '{query[:100]}...'")
        
        # Prepare response
        response = EncodeResponse()
        
        # Generate dense embeddings
        if request.return_dense:
            try:
                dense_output = m.encode(
                    [query],
                    return_dense=True,
                    return_sparse=False,
                    return_colbert_vecs=False
                )
                response.dense_vecs = dense_output['dense_vecs'][0].tolist()
                logger.info(f"  ✅ Dense: {len(response.dense_vecs)} dimensions")
            except Exception as e:
                logger.error(f"Dense encoding error: {e}")
                raise HTTPException(status_code=500, detail=f"Dense encoding failed: {e}")
        
        # Generate sparse embeddings (lexical_weights)
        if request.return_sparse:
            try:
                sparse_output = m.encode(
                    [query],
                    return_dense=False,
                    return_sparse=True,
                    return_colbert_vecs=False
                )
                # Convert to dict (token_id -> weight)
                lexical_weights = sparse_output['lexical_weights'][0]
                response.lexical_weights = {
                    int(k): float(v) for k, v in lexical_weights.items()
                }
                logger.info(f"  ✅ Sparse: {len(response.lexical_weights)} tokens")
            except Exception as e:
                logger.error(f"Sparse encoding error: {e}")
                raise HTTPException(status_code=500, detail=f"Sparse encoding failed: {e}")
        
        # Generate ColBERT multi-vectors (optional)
        if request.return_colbert_vecs:
            try:
                colbert_output = m.encode(
                    [query],
                    return_dense=False,
                    return_sparse=False,
                    return_colbert_vecs=True
                )
                response.colbert_vecs = colbert_output['colbert_vecs'][0].tolist()
                logger.info(f"  ✅ ColBERT: {len(response.colbert_vecs)} vectors")
            except Exception as e:
                logger.error(f"ColBERT encoding error: {e}")
                raise HTTPException(status_code=500, detail=f"ColBERT encoding failed: {e}")
        
        logger.info(f"✅ Encoding complete")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Encoding error: {e}")
        raise HTTPException(status_code=500, detail=f"Encoding failed: {str(e)}")


if __name__ == "__main__":
    # Local development
    uvicorn.run(app, host="0.0.0.0", port=7860)



