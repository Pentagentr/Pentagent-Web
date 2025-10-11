# 🚀 Pentagent - Tam Deployment Rehberi (Ücretsiz)

## 📋 Deployment Mimarisi

```
┌─────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT MİMARİSİ                      │
└─────────────────────────────────────────────────────────────┘

Frontend (Firebase Hosting)
    ↓ HTTPS
Backend (Render.com - Free)
    ↓ WebSocket + REST
RAG/Qdrant (Qdrant Cloud - Free 1GB)
```

### Ücretsiz Servisler

| Katman | Servis | Plan | Limitler |
|--------|--------|------|----------|
| **Frontend** | Firebase Hosting | Free | 10GB storage, 360MB/day transfer |
| **Backend** | Render.com | Free | 750 saat/ay, 15 dk sonra uyur |
| **RAG/Qdrant** | Qdrant Cloud | Free | 1GB cluster, 1M vectors |

---

## 🎯 ADIM 1: RAG/Qdrant Cloud'a Deploy

### 1.1. Qdrant Cloud Hesabı Oluştur

1. https://cloud.qdrant.io/ adresine git
2. **"Sign Up"** ile kayıt ol (GitHub/Google ile)
3. **"Create Cluster"** tıkla

**Ayarlar:**
- **Plan:** Free (1GB)
- **Region:** en yakın bölge seç
- **Cluster Name:** `pentagent-cve-rag`

4. Cluster oluştuktan sonra:
   - **API Key** al (güvenli yerde sakla)
   - **Cluster URL** not al (örn: `https://xyz.cloud.qdrant.io`)

### 1.2. Vektörleri Qdrant Cloud'a Yükle

**Qdrant Cloud'a vektör yükleme scripti oluştur:**

```python
# upload_to_cloud.py
import os
from qdrant_client import QdrantClient
from qdrant_client.http import models
import orjson
from tqdm import tqdm

# Qdrant Cloud credentials
QDRANT_URL = "https://xyz.cloud.qdrant.io"  # Senin cluster URL'in
QDRANT_API_KEY = "your-api-key-here"  # API key buraya

# Collection config
COLLECTION_NAME = "cve_collection_hybrid"

def upload_vectors():
    """Vektörleri Qdrant Cloud'a yükle"""
    
    # Cloud client
    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        timeout=60
    )
    
    print(f"Qdrant Cloud'a bağlanılıyor: {QDRANT_URL}")
    
    # Collection oluştur
    try:
        client.get_collection(COLLECTION_NAME)
        print(f"Collection '{COLLECTION_NAME}' zaten var")
    except:
        print(f"Collection '{COLLECTION_NAME}' oluşturuluyor...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "text-dense": models.VectorParams(
                    size=1024,
                    distance=models.Distance.COSINE
                )
            },
            sparse_vectors_config={
                "text-sparse": models.SparseVectorParams()
            }
        )
        print("Collection oluşturuldu!")
    
    # Local vektörleri yükle
    vectors_file = r"C:\Users\Meryem\Desktop\PENTTT\pentagentMr\Pentagent\Rag-Pent\vectors.jsonl"
    
    if not os.path.exists(vectors_file):
        print(f"❌ Vektör dosyası bulunamadı: {vectors_file}")
        return
    
    print(f"Vektörler yükleniyor: {vectors_file}")
    
    batch = []
    batch_size = 100  # Cloud için daha küçük batch
    total = 0
    
    with open(vectors_file, 'rb') as f:
        for line in tqdm(f, desc="Yükleniyor"):
            data = orjson.loads(line)
            
            point = models.PointStruct(
                id=data["id"],
                payload=data["payload"],
                vector={
                    "text-dense": data["vector"]["text-dense"],
                    "text-sparse": models.SparseVector(
                        indices=data["vector"]["text-sparse"]["indices"],
                        values=data["vector"]["text-sparse"]["values"]
                    )
                }
            )
            
            batch.append(point)
            
            if len(batch) >= batch_size:
                client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=batch
                )
                total += len(batch)
                batch = []
    
    # Son batch
    if batch:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=batch
        )
        total += len(batch)
    
    print(f"\n✅ {total} vektör başarıyla yüklendi!")
    
    # Verify
    collection_info = client.get_collection(COLLECTION_NAME)
    print(f"✅ Collection'da {collection_info.points_count} point var")

if __name__ == "__main__":
    upload_vectors()
```

**Yükle:**
```bash
cd C:\Users\Meryem\Desktop\PENTTT\pentagentMr\Pentagent\Rag-Pent
python upload_to_cloud.py
```

⚠️ **Not:** 95K vektör yüklemesi 1-2 saat sürebilir.

---

## 🎯 ADIM 2: Frontend'i Firebase'e Deploy Et

### 2.1. Frontend Build

```bash
cd C:\Users\Meryem\Desktop\PENTTT\pentagentMr\Pentagent\pentagent-frontend

# Environment variable ayarla (Backend URL sonra güncellenecek)
echo VITE_API_URL=https://pentagent-backend.onrender.com > .env.production

# Build
npm run build
```

### 2.2. Firebase Deploy

```bash
cd ..
firebase deploy --only hosting
```

✅ **Frontend URL:** `https://pentagent-b9007.web.app` (senin mevcut URL'in)

---

## 🎯 ADIM 3: Backend'i Render.com'a Deploy Et

### 3.1. GitHub Repository Hazırla

**Backend için GitHub repo oluştur:**

```bash
cd C:\Users\Meryem\Desktop\PENTTT\pentagentMr\Pentagent

# .gitignore oluştur (eğer yoksa)
echo "__pycache__/" > .gitignore
echo "*.pyc" >> .gitignore
echo ".env" >> .gitignore
echo "venv/" >> .gitignore
echo "Rag-Pent/qdrant_storage/" >> .gitignore

# Git init
git init
git add .
git commit -m "Pentagent backend ready for deployment"

# GitHub'da yeni repo oluştur: pentagent-backend
# Sonra:
git remote add origin https://github.com/YOUR_USERNAME/pentagent-backend.git
git branch -M main
git push -u origin main
```

### 3.2. Render.com Deployment

1. **https://render.com** → Sign Up with GitHub

2. **Dashboard → "New +" → "Web Service"**

3. **Repo seç:** `pentagent-backend`

4. **Ayarlar:**
   ```
   Name: pentagent-backend
   Region: Frankfurt (veya en yakın)
   Branch: main
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn web_api:app --host 0.0.0.0 --port $PORT
   Instance Type: Free
   ```

5. **Environment Variables Ekle:**
   ```
   GEMINI_API_KEY = AIzaSyBOKe4Et5zHvAjlOfuFOCZzWOFw5YFZiqk
   ALLOWED_ORIGINS = https://pentagent-b9007.web.app
   QDRANT_HOST = https://xyz.cloud.qdrant.io
   QDRANT_API_KEY = your-qdrant-cloud-api-key
   QDRANT_PORT = 443
   ```

6. **"Create Web Service"** → Bekle (5-10 dakika)

7. **Backend URL:** `https://pentagent-backend.onrender.com` (otomatik atanır)

### 3.3. Backend RAG Servisi Güncelle

Backend'de `services/rag_service.py` dosyasını environment variables'ları kullanacak şekilde güncelle:

```python
# services/rag_service.py içinde

@dataclass
class SearchConfig:
    """Arama yapılandırma ayarları"""
    qdrant_host: str = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6333"))
    qdrant_api_key: str = os.getenv("QDRANT_API_KEY", None)
    collection_name: str = "cve_collection_hybrid"
    model_name: str = "BAAI/bge-m3"
    default_dense_weight: float = 0.7
    default_sparse_weight: float = 0.3
    max_retries: int = 3
    timeout: int = 30

class CVESearchEngine:
    def _initialize(self):
        """Qdrant client ve BGE-M3 modelini başlat"""
        try:
            # Qdrant bağlantısı (Cloud veya Local)
            logger.info(f"Qdrant'a bağlanılıyor: {self.config.qdrant_host}:{self.config.qdrant_port}")
            
            # Cloud için API key kullan
            if self.config.qdrant_api_key:
                self._client = QdrantClient(
                    url=self.config.qdrant_host,
                    api_key=self.config.qdrant_api_key,
                    timeout=self.config.timeout,
                    https=True
                )
            else:
                # Local için
                self._client = QdrantClient(
                    host=self.config.qdrant_host,
                    port=self.config.qdrant_port,
                    timeout=self.config.timeout
                )
            
            # ... rest of the code
```

**Güncellemeyi commit et:**
```bash
git add services/rag_service.py
git commit -m "Update RAG service for cloud deployment"
git push
```

Render otomatik olarak yeniden deploy eder.

---

## 🎯 ADIM 4: Frontend'i Backend'e Bağla

### 4.1. Backend URL'ini Güncelle

```bash
cd pentagent-frontend

# .env.production güncelle
echo VITE_API_URL=https://pentagent-backend.onrender.com > .env.production

# Rebuild
npm run build

# Redeploy
cd ..
firebase deploy --only hosting
```

---

## 🎯 ADIM 5: Test ve Doğrulama

### 5.1. Backend Health Check

```bash
curl https://pentagent-backend.onrender.com/health
```

**Beklenen yanıt:**
```json
{
  "status": "healthy",
  "api_key_configured": true,
  "active_connections": 0,
  "rag_available": true,
  "rag_cves": 95237,
  "message": "Pentagent API is running"
}
```

### 5.2. RAG Sistemi Test

```bash
curl -X POST "https://pentagent-backend.onrender.com/api/rag/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"SQL injection","limit":3}'
```

### 5.3. Frontend Test

1. **https://pentagent-b9007.web.app** aç
2. Normal pentest taraması yap
3. RAG arama sayfasına git: `/rag-search`
4. CVE araması yap

---

## 📊 Deployment Özeti

### URL'ler

| Servis | URL | Durum |
|--------|-----|-------|
| **Frontend** | https://pentagent-b9007.web.app | ✅ Deployed |
| **Backend** | https://pentagent-backend.onrender.com | 🔄 Deploy edilecek |
| **RAG/Qdrant** | https://xyz.cloud.qdrant.io | 🔄 Vektörler yüklenecek |
| **WebSocket** | wss://pentagent-backend.onrender.com/ws | ✅ Auto |

### Environment Variables

**Backend (Render.com):**
```env
GEMINI_API_KEY=AIzaSyBOKe4Et5zHvAjlOfuFOCZzWOFw5YFZiqk
ALLOWED_ORIGINS=https://pentagent-b9007.web.app
QDRANT_HOST=https://xyz.cloud.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
QDRANT_PORT=443
```

**Frontend (.env.production):**
```env
VITE_API_URL=https://pentagent-backend.onrender.com
```

---

## 🔧 Alternatif: Docker'ı Render'da Deploy (Qdrant dahil)

Eğer Qdrant Cloud kullanmak istemezsen, Render'da Docker olarak da deploy edebilirsin:

### Dockerfile.qdrant

```dockerfile
FROM qdrant/qdrant:latest

# Vektörleri kopyala (opsiyonel)
# COPY ./qdrant_storage /qdrant/storage

EXPOSE 6333 6334
```

### Render'da Qdrant Service

1. **Render Dashboard → "New +" → "Web Service"**
2. **Docker** seç
3. **Dockerfile:** `Dockerfile.qdrant`
4. **Port:** 6333
5. **Plan:** Free (ama RAM limitli)

**Not:** Render free tier'da Qdrant için yeterli RAM olmayabilir. Qdrant Cloud önerilir.

---

## ⚠️ Önemli Notlar

### 1. Render Free Tier Limitleri
- **750 saat/ay** (31 gün = 744 saat, yeterli)
- **15 dakika inactivity sonra uyur**
- **İlk istek 30-60 saniye sürer** (cold start)
- **512MB RAM** (yeterli ama BGE-M3 model için sınırda)

### 2. Qdrant Cloud Free Tier
- **1GB storage** (yaklaşık 50K-100K vektör)
- **95K vektör için yeterli mi?** → Evet, sıkıştırmayla
- **Alternatif:** Daha az vektör yükle (sadece son yıllar)

### 3. Firebase Hosting
- **10GB storage** yeterli
- **CDN dahil** (hızlı)
- **Custom domain** eklenebilir

---

## 🚨 Sorun Giderme

### Backend başlamıyor?
```bash
# Render logs
# Render Dashboard → Service → Logs

# Kontrol et:
# - GEMINI_API_KEY doğru mu?
# - requirements.txt tam mı?
# - Start command doğru mu?
```

### RAG çalışmıyor?
```bash
# Backend'de kontrol et:
curl https://pentagent-backend.onrender.com/api/rag/stats

# Qdrant Cloud kontrol:
# Dashboard'da collection'ı kontrol et
```

### Frontend bağlanamıyor?
```bash
# .env.production kontrol et
# CORS ayarlarını kontrol et (ALLOWED_ORIGINS)
# Browser console'da network tab'ı kontrol et
```

---

## 💰 Maliyet Analizi (Ücretsiz)

| Servis | Aylık Maliyet | Limitler |
|--------|---------------|----------|
| Firebase Hosting | $0 | 10GB + 360MB/day yeterli |
| Render.com | $0 | 750 saat/ay (yeterli) |
| Qdrant Cloud | $0 | 1GB (95K vektör sığar) |
| **TOPLAM** | **$0** | ✅ Tamamen ücretsiz! |

---

## 🎯 Sonraki Adımlar

1. ✅ Qdrant Cloud hesabı aç
2. ✅ Vektörleri Qdrant Cloud'a yükle (1-2 saat)
3. ✅ Backend'i GitHub'a push et
4. ✅ Render.com'da deploy et
5. ✅ Environment variables ayarla
6. ✅ Frontend'i rebuild et
7. ✅ Firebase'e deploy et
8. ✅ Test et!

**Hazırsın! 🚀**

Tamamen ücretsiz, production-ready deployment!

