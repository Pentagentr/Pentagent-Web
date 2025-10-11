# CVE Search Modülü - Kullanım Kılavuzu

## 📋 Genel Bakış

Bu modül, Qdrant veritabanı üzerinde **hybrid search** (dense + sparse vektörler) ile CVE araması yapar. 

**Önemli:** Dense vektörler daha yüksek ağırlıktadır (70%), yani semantik search önceliklidir.

---

## 🏗️ Modül Yapısı

```
Qdrant/
├── cve_search.py       # Ana search engine modülü (production-ready)
├── api_example.py      # FastAPI entegrasyon örneği
├── hybrid_search.py    # Eski test dosyası (kullanılmıyor)
└── SEARCH_USAGE.md     # Bu dosya
```

---

## 🚀 Hızlı Başlangıç

### 1. Temel Kullanım (Python Modülü Olarak)

```python
from Qdrant.cve_search import CVESearchEngine, SearchConfig

# Engine'i başlat (default ayarlarla)
engine = CVESearchEngine()

# Basit arama
results = engine.search("SQL injection vulnerability", limit=10)

# Sonuçları işle
for result in results:
    print(f"{result.cve_id}: {result.score:.4f}")
    print(f"  Severity: {result.severity}")
    print(f"  Description: {result.description[:100]}...")
    print()
```

### 2. Custom Yapılandırma

```python
from Qdrant.cve_search import CVESearchEngine, SearchConfig

# Özel config oluştur
config = SearchConfig(
    qdrant_host="localhost",
    qdrant_port=6333,
    collection_name="cve_collection_hybrid",
    default_dense_weight=0.7,   # Dense: %70 (semantik öncelikli)
    default_sparse_weight=0.3   # Sparse: %30
)

engine = CVESearchEngine(config)
```

---

## 🔍 Arama Fonksiyonları

### 1. `search()` - Hybrid Arama

En temel ve güçlü arama fonksiyonu.

```python
results = engine.search(
    query="buffer overflow",
    limit=10,                    # Maksimum sonuç sayısı
    dense_weight=0.3,            # Opsiyonel: Dense ağırlık
    sparse_weight=0.7,           # Opsiyonel: Sparse ağırlık
    min_score=0.5                # Opsiyonel: Minimum skor eşiği
)
```

**Dönen Veri:**
- `SearchResult` objesi listesi
- Her obje şunları içerir:
  - `cve_id`: CVE ID
  - `score`: Hybrid skor
  - `dense_score`: Semantik skor
  - `sparse_score`: Keyword skor
  - `severity`: Severity seviyesi
  - `base_score`: CVSS base score
  - `attack_vector`: Saldırı vektörü
  - `description`: CVE açıklaması
  - `published_date`: Yayın tarihi
  - `metadata`: Ek metadata

### 2. `search_by_severity()` - Severity Filtrelemeli Arama

Belirli severity seviyesine göre arama yapar.

```python
results = engine.search_by_severity(
    query="remote code execution",
    severity="CRITICAL",         # CRITICAL, HIGH, MEDIUM, LOW
    limit=10
)
```

### 3. `get_cve_by_id()` - CVE ID ile Direkt Getirme

CVE ID'yi biliyorsanız direkt getirir.

```python
cve = engine.get_cve_by_id("CVE-2024-12345")

if cve:
    print(f"CVE bulundu: {cve.cve_id}")
    print(f"Severity: {cve.severity}")
else:
    print("CVE bulunamadı")
```

### 4. `health_check()` - Sistem Kontrolü

Qdrant bağlantısını ve collection'ı kontrol eder.

```python
if engine.health_check():
    print("✅ Sistem sağlıklı")
else:
    print("❌ Sistem hatası")
```

### 5. `get_stats()` - İstatistikler

Collection hakkında bilgi verir.

```python
stats = engine.get_stats()
print(f"Toplam CVE: {stats['points_count']}")
print(f"Collection: {stats['collection_name']}")
```

---

## 🌐 API Entegrasyonu (FastAPI)

### API'yi Başlatma

```bash
# Development modu
python Qdrant/api_example.py

# Production modu
uvicorn Qdrant.api_example:app --host 0.0.0.0 --port 8000 --workers 4
```

### Endpoint'ler

#### 1. POST `/api/v1/search` - Hybrid Search

**Request:**
```json
{
  "query": "SQL injection",
  "limit": 10,
  "dense_weight": 0.3,
  "sparse_weight": 0.7,
  "min_score": 0.0
}
```

**Response:**
```json
{
  "success": true,
  "total_results": 10,
  "query": "SQL injection",
  "execution_time_ms": 234.56,
  "results": [
    {
      "cve_id": "CVE-2024-12345",
      "score": 0.8765,
      "dense_score": 0.7543,
      "sparse_score": 0.9123,
      "severity": "CRITICAL",
      "base_score": 9.8,
      "attack_vector": "NETWORK",
      "description": "SQL injection vulnerability in...",
      "published_date": "2024-01-15",
      "metadata": {...}
    }
  ]
}
```

#### 2. POST `/api/v1/search/severity` - Severity Filtrelemeli Arama

**Request:**
```json
{
  "query": "buffer overflow",
  "severity": "CRITICAL",
  "limit": 10
}
```

#### 3. GET `/api/v1/cve/{cve_id}` - CVE Detayı

**Örnek:**
```
GET /api/v1/cve/CVE-2024-12345
```

#### 4. GET `/api/v1/health` - Sağlık Kontrolü

```json
{
  "status": "healthy",
  "healthy": true,
  "stats": {
    "collection_name": "cve_collection_hybrid",
    "points_count": 50000
  }
}
```

#### 5. GET `/api/v1/stats` - İstatistikler

---

## 🐳 Docker Entegrasyonu

### Docker Compose ile Çalıştırma

Mevcut `docker-compose.yml` kullanılabilir:

```bash
# Qdrant'ı başlat
docker-compose up -d

# API'yi başlat (ayrı terminal)
python Qdrant/api_example.py
```

### API'yi de Docker'a Eklemek İsterseniz

`docker-compose.yml`'ye ekleyin:

```yaml
services:
  # ... mevcut qdrant service ...
  
  cve-api:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: cve_search_api
    ports:
      - "8000:8000"
    environment:
      - QDRANT_HOST=qdrant  # Docker network içinde service name
      - QDRANT_PORT=6333
    depends_on:
      - qdrant
    restart: unless-stopped
```

---

## 🔧 Konfigürasyon

### Environment Variables

Production ortamında environment variable kullanılabilir:

```python
import os
from Qdrant.cve_search import SearchConfig, CVESearchEngine

config = SearchConfig(
    qdrant_host=os.getenv("QDRANT_HOST", "localhost"),
    qdrant_port=int(os.getenv("QDRANT_PORT", "6333")),
    collection_name=os.getenv("COLLECTION_NAME", "cve_collection_hybrid"),
    default_dense_weight=float(os.getenv("DENSE_WEIGHT", "0.3")),
    default_sparse_weight=float(os.getenv("SPARSE_WEIGHT", "0.7")),
)

engine = CVESearchEngine(config)
```

---

## 📊 Dense vs Sparse Ağırlıkları

**Default Ayarlar:**
- Dense (Semantik): **70%** ← Öncelikli
- Sparse (Keyword): **30%**

**Ne Zaman Dense Ağırlığı Arttırılır?**
- Anlam benzerliği aranıyorsa
- Farklı kelimelerle aynı kavramları bulma
- Örnek: "SQL injection" → "database code injection"

**Ne Zaman Sparse Ağırlığı Arttırılır?**
- Tam kelime eşleşmesi önemliyse
- Teknik terimler aranıyorsa
- Örnek: "CVE-2024-1234" gibi exact match'ler

**Özel Ağırlıklar:**
```python
# Tam semantik arama için (default zaten semantik öncelikli)
results = engine.search(
    query="authentication bypass",
    dense_weight=0.8,
    sparse_weight=0.2
)

# Keyword arama için
results = engine.search(
    query="CVE-2024 Apache",
    dense_weight=0.3,
    sparse_weight=0.7
)
```

---

## 🧪 Test Etme

### Modülü Test Etme

```bash
# Ana modülü test et
python Qdrant/cve_search.py

# API'yi test et
python Qdrant/api_example.py
```

### cURL ile API Test

```bash
# Basit arama
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "SQL injection",
    "limit": 5
  }'

# Severity filtrelemeli
curl -X POST "http://localhost:8000/api/v1/search/severity" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "buffer overflow",
    "severity": "CRITICAL",
    "limit": 5
  }'

# CVE detayı
curl "http://localhost:8000/api/v1/cve/CVE-2024-12345"

# Health check
curl "http://localhost:8000/api/v1/health"
```

---

## 🔒 Production Önerileri

### 1. Güvenlik
- Rate limiting ekleyin (FastAPI middleware)
- API key authentication kullanın
- CORS ayarlarını yapılandırın

### 2. Performance
- Connection pooling kullanın
- Cache mekanizması ekleyin (Redis)
- Qdrant'ı ayrı sunucuda çalıştırın

### 3. Monitoring
- Logging yapılandırın (structlog, loguru)
- Prometheus metrics ekleyin
- Error tracking (Sentry)

### 4. Scalability
- Horizontal scaling için multiple workers
- Load balancer (nginx, traefik)
- Distributed tracing

---

## 📝 Örnek Entegrasyon (Flask)

```python
from flask import Flask, request, jsonify
from Qdrant.cve_search import get_search_engine

app = Flask(__name__)
engine = get_search_engine()

@app.route('/search', methods=['POST'])
def search():
    data = request.json
    query = data.get('query')
    limit = data.get('limit', 10)
    
    results = engine.search(query, limit=limit)
    
    return jsonify({
        'success': True,
        'results': [r.to_dict() for r in results]
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

---

## 🆘 Troubleshooting

### Hata: "Collection bulunamadı"
**Çözüm:** Vektörleri yükleyin:
```bash
python Qdrant/upload.py
```

### Hata: "Qdrant bağlantı hatası"
**Çözüm:** Docker'ı başlatın:
```bash
docker-compose up -d
```

### Hata: "Model yüklenemedi"
**Çözüm:** FlagEmbedding kurulumunu kontrol edin:
```bash
pip install FlagEmbedding torch
```

---

## 📚 İlgili Dosyalar

- `cve_search.py` - Ana search engine
- `api_example.py` - FastAPI entegrasyon örneği
- `upload.py` - Vektör yükleme scripti
- `bge_vector_colab.py` - Vektör oluşturma scripti
- `docker-compose.yml` - Qdrant yapılandırması

---

## 🎯 Özet

✅ **Kullanım:** `from Qdrant.cve_search import CVESearchEngine`  
✅ **API:** FastAPI ile production-ready  
✅ **Hybrid Search:** Dense (70%) + Sparse (30%) - Semantik öncelikli  
✅ **Docker:** docker-compose ile kolay kurulum  
✅ **Modüler:** Kolay entegrasyon ve özelleştirme  

**İyi aramalar! 🚀**

