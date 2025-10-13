# 🚀 BGE-M3 Custom Inference Space

Native **sparse + dense** vector generation for Pentagent CVE RAG system.

## ✨ Features

- ✅ **Native Sparse Vectors** (BGE-M3 lexical_weights - NOT approximation!)
- ✅ **Dense Embeddings** (1024 dimensions)
- ✅ **ColBERT Multi-Vectors** (optional)
- ✅ **FastAPI REST API**
- ✅ **HuggingFace Space Ready**

## 📦 What's Inside

```
bge-m3-inference-space/
├── Dockerfile          # Container setup
├── requirements.txt    # Python dependencies
├── app.py             # FastAPI inference API
└── README.md          # This file
```

## 🌐 Deploy to HuggingFace Space

### Step 1: Create New Space

1. Go to: https://huggingface.co/new-space
2. **Space name**: `bge-m3-inference` (veya istediğin isim)
3. **License**: Apache 2.0
4. **Space SDK**: Docker
5. **Visibility**: Public (ücretsiz) veya Private (PRO plan)
6. Click **Create Space**

### Step 2: Upload Files

**Option A: Git Push (Önerilen)**

```bash
# HF Space'i clone et
git clone https://huggingface.co/spaces/YOUR_USERNAME/bge-m3-inference
cd bge-m3-inference

# Dosyaları kopyala
cp /path/to/bge-m3-inference-space/* .

# Commit ve push
git add .
git commit -m "Initial BGE-M3 inference API"
git push
```

**Option B: Web Interface**

1. Space sayfasında **Files** tab'ına git
2. **Add file** → **Upload files**
3. `Dockerfile`, `requirements.txt`, `app.py`, `README.md` yükle
4. **Commit** butonu

### Step 3: Wait for Build

- HF Space otomatik build başlatır (~5-10 dakika)
- Build logs'u görebilirsin
- Status: **Building** → **Running**

### Step 4: Test API

Space hazır olunca endpoint'i test et:

```bash
# Health check
curl https://YOUR_USERNAME-bge-m3-inference.hf.space/health

# Encoding test
curl -X POST https://YOUR_USERNAME-bge-m3-inference.hf.space/encode \
  -H "Content-Type: application/json" \
  -d '{
    "inputs": "SQL injection vulnerability",
    "return_dense": true,
    "return_sparse": true
  }'
```

## 🔌 API Endpoints

### `POST /encode`

Generate embeddings (dense + sparse)

**Request:**
```json
{
  "inputs": "Your query text here",
  "return_dense": true,
  "return_sparse": true,
  "return_colbert_vecs": false
}
```

**Response:**
```json
{
  "dense_vecs": [0.123, 0.456, ...],  // 1024 dimensions
  "lexical_weights": {
    "1234": 0.89,  // token_id: weight
    "5678": 0.67,
    ...
  },
  "colbert_vecs": null  // if not requested
}
```

### `GET /health`

Health check

**Response:**
```json
{
  "status": "healthy",
  "model": "BAAI/bge-m3",
  "device": "cpu"
}
```

## 🔧 Integrate with Pentagent

Update `cve_search.py`:

```python
# _encode_with_hf_api fonksiyonunu değiştir:

def _encode_with_hf_api(self, query: str) -> Tuple[List[float], models.SparseVector]:
    """Custom HF Space endpoint kullan"""
    
    # Custom endpoint URL
    custom_endpoint = "https://YOUR_USERNAME-bge-m3-inference.hf.space/encode"
    
    # Request
    response = requests.post(
        custom_endpoint,
        json={
            "inputs": query,
            "return_dense": True,
            "return_sparse": True
        },
        timeout=30
    )
    
    if response.status_code != 200:
        raise Exception(f"API error: {response.status_code}")
    
    data = response.json()
    
    # Dense vector
    dense_vec = data["dense_vecs"]
    
    # GERÇEK sparse vector (native BGE-M3!)
    lexical_weights = data["lexical_weights"]
    sparse_vec = models.SparseVector(
        indices=list(lexical_weights.keys()),
        values=list(lexical_weights.values())
    )
    
    return dense_vec, sparse_vec
```

## 💰 Cost & Performance

### HuggingFace Space Free Tier:
- ✅ 2 CPU cores
- ✅ 16GB RAM
- ✅ Cold start (~30 saniye ilk istek)
- ✅ Ücretsiz (public space)

### Performance:
- **Dense + Sparse**: ~500ms/query (warm)
- **First request** (cold start): ~30 saniye
- **Capacity**: ~100 requests/dakika

### Upgrade to PRO ($9/month):
- 🚀 4 CPU cores
- 🚀 32GB RAM
- 🚀 No cold start
- 🚀 Private space option

## 🐛 Troubleshooting

### Build hatası:
```bash
# Logs'u kontrol et
# HF Space → Logs tab
```

### Out of memory:
```dockerfile
# Dockerfile'da fp16 kullan (GPU varsa)
use_fp16=True
```

### Cold start çok uzun:
- PRO plan'e upgrade et
- Veya keep-alive ping ekle

## 📚 Resources

- [HuggingFace Spaces Docs](https://huggingface.co/docs/hub/spaces)
- [BGE-M3 Model Card](https://huggingface.co/BAAI/bge-m3)
- [FlagEmbedding GitHub](https://github.com/FlagOpen/FlagEmbedding)

## 🎯 Expected Performance

With native sparse vectors:
- **CVE_DIRECT**: ~100% ✅
- **PURE_SEMANTIC**: ~82% ✅
- **VERSION_BASED**: ~78% ✅
- **HYBRID**: ~75% ✅
- **COMPLEX**: ~80% ✅

**Overall**: ~82% (test ortamıyla aynı!)

---

**Made with ❤️ for Pentagent RAG System**


