"""
Pentagent Reranker API - HuggingFace Space
mixedbread-ai/mxbai-rerank-xsmall-v1 model serving
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn
from sentence_transformers import CrossEncoder
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Pentagent Reranker API",
    description="Reranking service using mixedbread-ai/mxbai-rerank-xsmall-v1",
    version="1.0.0"
)

# CORS - Allow all origins (production'da spesifik origin'ler ekle)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model instance - Load once at startup
model = None

@app.on_event("startup")
async def load_model():
    """Load reranker model at startup"""
    global model
    try:
        logger.info("🔄 Loading mxbai-rerank-xsmall-v1 model...")
        model = CrossEncoder('mixedbread-ai/mxbai-rerank-xsmall-v1', max_length=512)
        logger.info("✅ Model loaded successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        raise

class RerankRequest(BaseModel):
    query: str
    documents: List[str]
    top_k: int = 5

class RerankResponse(BaseModel):
    scores: List[float]
    top_k_indices: List[int]

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "model": "mixedbread-ai/mxbai-rerank-xsmall-v1",
        "service": "Pentagent Reranker API",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "model_name": "mixedbread-ai/mxbai-rerank-xsmall-v1"
    }

@app.post("/rerank", response_model=RerankResponse)
async def rerank_documents(request: RerankRequest):
    """
    Rerank documents based on query relevance
    
    Args:
        query: Search query
        documents: List of documents to rerank
        top_k: Number of top results to return
    
    Returns:
        scores: Relevance scores for all documents
        top_k_indices: Indices of top-k most relevant documents
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if not request.documents:
        raise HTTPException(status_code=400, detail="No documents provided")
    
    try:
        # Create query-document pairs
        pairs = [[request.query, doc] for doc in request.documents]
        
        # Get scores
        scores = model.predict(pairs)
        scores = scores.tolist()
        
        # Get top-k indices
        top_k = min(request.top_k, len(scores))
        top_k_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        logger.info(f"✅ Reranked {len(request.documents)} documents, top score: {max(scores):.4f}")
        
        return RerankResponse(
            scores=scores,
            top_k_indices=top_k_indices
        )
    
    except Exception as e:
        logger.error(f"❌ Reranking error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)

