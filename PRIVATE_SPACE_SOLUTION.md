# 🔒 Private HuggingFace Space Çözümü

## ✅ SEÇENEK 1: Private Space + Token Authentication

Private Space kullanabilirsin! Backend'den HuggingFace token ile erişebiliriz.

### Adım 1: HuggingFace Token Al

1. https://huggingface.co/settings/tokens
2. **"New token"** tıkla
3. **Name:** `pentagent-backend`
4. **Type:** Read (yeterli)
5. Token'ı kopyala: `hf_xxxxxxxxxxxxx`

### Adım 2: Render.com Environment Variables

**Backend'de (Render.com):**
```env
QDRANT_HOST = https://YOUR_USERNAME-pentagent-qdrant.hf.space
QDRANT_PORT = 443
HUGGINGFACE_TOKEN = hf_xxxxxxxxxxxxx
```

### Adım 3: Backend Güncelle

Backend zaten hazır! `services/rag_service.py` otomatik olarak token'ı kullanır.

### Test

```bash
# Backend health check
curl https://pentagent-backend.onrender.com/health

# RAG test
curl -X POST "https://pentagent-backend.onrender.com/api/rag/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"SQL injection","limit":3}'
```

✅ **Private Space + Token = Güvenli + Çalışır!**

---

## ✅ SEÇENEK 2: Render.com Embedded (DAHA BASIT)

Private Space yerine, vektörleri backend içine gömelim!

### Nasıl Çalışır?

```
Backend başlar
    ↓
vectors.jsonl dosyasını yükler (GitHub'dan veya build sırasında)
    ↓
RAM'de mini in-memory vector store
    ↓
Arama yapılır
```

### Avantajları
- ✅ HuggingFace'e gerek yok
- ✅ Tek deployment (backend)
- ✅ Daha basit
- ✅ Tamamen private

### Dezavantajları
- ⚠️ Render 512MB RAM (sınırlı)
- ⚠️ Her restart'ta vektörleri yükler (~30 saniye)
- ⚠️ 95K vektörün hepsi sığmayabilir

### Uygulama

**1. Vektörleri GitHub'a Yükle (Git LFS ile)**

```bash
cd C:\Users\Meryem\Desktop\PENTTT\pentagentMr\Pentagent

# Git LFS kur
git lfs install

# Vektör dosyasını track et
git lfs track "Rag-Pent/vectors.jsonl"
git add .gitattributes

# Vektörleri ekle
git add Rag-Pent/vectors.jsonl
git commit -m "Add CVE vectors with Git LFS"
git push
```

**2. Backend'de In-Memory Vector Store**

`services/simple_vector_store.py` oluştur:

```python
"""
Basit in-memory vector store
Render.com için RAM'de çalışır
"""

import logging
import numpy as np
from typing import List, Dict, Any
import orjson

logger = logging.getLogger(__name__)


class SimpleVectorStore:
    """RAM'de çalışan basit vektör deposu"""
    
    def __init__(self):
        self.vectors = []
        self.metadata = []
        self.loaded = False
    
    def load_vectors(self, file_path: str, max_vectors: int = 50000):
        """Vektörleri dosyadan yükle"""
        logger.info(f"Vektörler yükleniyor: {file_path}")
        
        count = 0
        with open(file_path, 'rb') as f:
            for line in f:
                if count >= max_vectors:
                    break
                
                try:
                    data = orjson.loads(line)
                    
                    # Dense vektör
                    vector = np.array(data["vector"]["text-dense"], dtype=np.float32)
                    self.vectors.append(vector)
                    
                    # Metadata
                    self.metadata.append({
                        "cve_id": data["payload"].get("cve_id", ""),
                        "content": data["payload"].get("content", "")[:500],
                        "metadata": data["payload"].get("metadata", {})
                    })
                    
                    count += 1
                    
                except Exception as e:
                    logger.error(f"Vektör parse hatası: {e}")
                    continue
        
        self.vectors = np.array(self.vectors)
        self.loaded = True
        
        logger.info(f"✅ {count} vektör yüklendi (RAM: ~{self.vectors.nbytes / 1024 / 1024:.1f}MB)")
    
    def search(self, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Cosine similarity ile arama"""
        if not self.loaded:
            return []
        
        # Cosine similarity
        query = np.array(query_vector, dtype=np.float32)
        query = query / np.linalg.norm(query)
        
        similarities = np.dot(self.vectors, query)
        
        # Top-K
        top_indices = np.argsort(similarities)[-limit:][::-1]
        
        results = []
        for idx in top_indices:
            results.append({
                "cve_id": self.metadata[idx]["cve_id"],
                "score": float(similarities[idx]),
                "content": self.metadata[idx]["content"],
                "metadata": self.metadata[idx]["metadata"]
            })
        
        return results


# Global instance
_vector_store = None


def get_vector_store() -> SimpleVectorStore:
    """Singleton vector store"""
    global _vector_store
    if _vector_store is None:
        _vector_store = SimpleVectorStore()
    return _vector_store
```

**3. Backend'de Kullan**

`services/rag_service.py` güncelle:

```python
# Fallback: Simple vector store
try:
    from Qdrant.cve_search import CVESearchEngine
except ImportError:
    CVESearchEngine = None
    # Fallback'e geç
    from services.simple_vector_store import get_vector_store
```

**4. Vektörleri Yükle (Startup'ta)**

`web_api.py` içinde:

```python
@app.on_event("startup")
async def startup_event():
    """Startup'ta vektörleri yükle"""
    try:
        # ... mevcut kod ...
        
        # Simple vector store yükle
        from services.simple_vector_store import get_vector_store
        store = get_vector_store()
        
        vectors_file = "Rag-Pent/vectors.jsonl"
        if os.path.exists(vectors_file):
            # İlk 50K vektör (RAM tasarrufu)
            store.load_vectors(vectors_file, max_vectors=50000)
            logger.info("✅ In-memory vector store hazır")
        else:
            logger.warning("⚠️ vectors.jsonl bulunamadı")
            
    except Exception as e:
        logger.error(f"Startup hatası: {e}")
```

---

## 📊 Karşılaştırma

| | Private Space + Token | Embedded |
|---|----------------------|----------|
| **Kolay** | ⭐⭐⭐ | ⭐⭐ |
| **Hız** | ⚡⚡⚡ | ⚡⚡ |
| **RAM** | N/A | 512MB (sınırlı) |
| **Restart** | Hızlı | Yavaş (30s) |
| **Vektör Sayısı** | 95K | 50K (max) |

---

## 🎯 ÖNERİM

**Private Space + Token Kullan!**

Neden?
- ✅ Tam performans (95K vektör)
- ✅ Restart hızlı
- ✅ Qdrant'ın tüm özellikleri
- ✅ Güvenli (private)

Sadece Render.com'da bir environment variable eklemen yeterli:
```env
HUGGINGFACE_TOKEN = hf_xxxxxxxxxxxxx
```

---

## 🚀 Hızlı Başlangıç (Private Space)

```bash
# 1. HuggingFace token al
https://huggingface.co/settings/tokens
# → "New token" → Read → Copy

# 2. Render.com'da environment variable ekle
HUGGINGFACE_TOKEN = hf_xxxxxxxxxxxxx

# 3. Backend'i redeploy et
git push

# 4. Test et
curl https://pentagent-backend.onrender.com/api/rag/stats
```

**Hazır! 🎉**

Hangi seçeneği tercih edersin?
1. Private Space + Token (önerilen)
2. Embedded (daha basit ama sınırlı)

