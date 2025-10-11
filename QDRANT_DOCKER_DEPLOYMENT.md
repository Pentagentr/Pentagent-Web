# 🐳 Qdrant Docker Deployment Rehberi (Açık Kaynak)

## 📋 Neden Docker Deploy?

✅ **Açık Kaynak**: Qdrant tamamen açık kaynak (Apache 2.0)  
✅ **Lisanslanabilir**: Projeyi lisanslarken sorun çıkmaz  
✅ **Kontrol**: Tam kontrol, SaaS modeli değil  
✅ **Ücretsiz**: Free tier'larda deploy edilebilir  

---

## 🎯 En İyi Seçenek: Fly.io (ÖNERİLEN)

### Neden Fly.io?

| Özellik | Free Tier | Qdrant İçin Uygun mu? |
|---------|-----------|------------------------|
| **Persistent Volume** | 3GB | ✅ Yeterli (95K vektör ~2-3GB) |
| **RAM** | 256MB shared | ⚠️ Sınırlı ama çalışır |
| **CPU** | Shared | ✅ Yeterli |
| **Docker** | Full destek | ✅ |
| **Network** | 160GB/ay | ✅ Yeterli |

---

## 🚀 ADIM 1: Fly.io Setup

### 1.1. Fly.io CLI Kur

**Windows (PowerShell):**
```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

**Veya Manuel:**
1. https://fly.io/docs/hands-on/install-flyctl/ 
2. İndir ve PATH'e ekle

### 1.2. Login

```bash
fly auth login
```

Browser'da açılır, GitHub ile giriş yap.

---

## 🚀 ADIM 2: Qdrant Dockerfile Hazırla

### 2.1. Qdrant için Dockerfile

```bash
cd C:\Users\Meryem\Desktop\PENTTT\pentagentMr\Pentagent\Rag-Pent
```

**`Dockerfile.qdrant` oluştur:**

```dockerfile
# Qdrant official image
FROM qdrant/qdrant:latest

# Production ayarları
ENV QDRANT__SERVICE__HTTP_PORT=8080
ENV QDRANT__SERVICE__GRPC_PORT=6334

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

EXPOSE 8080 6334

# Persistent storage için volume
VOLUME ["/qdrant/storage"]

# Start Qdrant
CMD ["./qdrant"]
```

### 2.2. Fly.io Config

**`fly.toml` oluştur:**

```toml
app = "pentagent-qdrant"
primary_region = "ams"  # Amsterdam (Avrupa'ya yakın)

[build]
  dockerfile = "Dockerfile.qdrant"

[env]
  QDRANT__SERVICE__HTTP_PORT = "8080"
  QDRANT__SERVICE__GRPC_PORT = "6334"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = false  # Uyumasın
  auto_start_machines = true
  min_machines_running = 1

  [[http_service.checks]]
    grace_period = "30s"
    interval = "15s"
    method = "get"
    path = "/health"
    protocol = "http"
    timeout = "5s"

[mounts]
  source = "qdrant_data"
  destination = "/qdrant/storage"
  initial_size = "3gb"  # Free tier max

[[services]]
  internal_port = 8080
  protocol = "tcp"

  [[services.ports]]
    port = 80
    handlers = ["http"]

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

[[services]]
  internal_port = 6334
  protocol = "tcp"

  [[services.ports]]
    port = 6334
```

---

## 🚀 ADIM 3: Qdrant'ı Fly.io'ya Deploy Et

### 3.1. App Oluştur

```bash
cd C:\Users\Meryem\Desktop\PENTTT\pentagentMr\Pentagent\Rag-Pent

# Fly app oluştur
fly apps create pentagent-qdrant
```

### 3.2. Volume Oluştur

```bash
# 3GB persistent volume
fly volumes create qdrant_data --region ams --size 3
```

### 3.3. Deploy!

```bash
fly deploy --config fly.toml --dockerfile Dockerfile.qdrant
```

**Deploy süresi:** ~5-10 dakika

### 3.4. Qdrant URL'i Al

```bash
fly status

# Output:
# URL: https://pentagent-qdrant.fly.dev
```

✅ **Qdrant URL:** `https://pentagent-qdrant.fly.dev`

---

## 🚀 ADIM 4: Vektörleri Fly.io Qdrant'a Yükle

### 4.1. Upload Script Güncelle

**`upload_to_fly.py` oluştur:**

```python
"""
Fly.io Qdrant'a Vektör Yükleme Scripti
"""

import os
from qdrant_client import QdrantClient
from qdrant_client.http import models
import orjson
from tqdm import tqdm
from uuid import uuid5, NAMESPACE_DNS

# ============= AYARLAR =============
QDRANT_URL = "https://pentagent-qdrant.fly.dev"  # ⬅️ Fly.io URL'in
COLLECTION_NAME = "cve_collection_hybrid"
VECTORS_FILE = "vectors.jsonl"
BATCH_SIZE = 100
# ===================================


def create_collection(client):
    """Collection oluştur"""
    try:
        collection = client.get_collection(COLLECTION_NAME)
        print(f"✅ Collection '{COLLECTION_NAME}' zaten var")
        print(f"   Mevcut point sayısı: {collection.points_count}")
        return True
    except:
        print(f"📦 Collection '{COLLECTION_NAME}' oluşturuluyor...")
        
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "text-dense": models.VectorParams(
                    size=1024,
                    distance=models.Distance.COSINE,
                    on_disk=True  # Disk kullan (RAM tasarrufu)
                )
            },
            sparse_vectors_config={
                "text-sparse": models.SparseVectorParams(
                    index={"on_disk": True}  # Disk kullan
                )
            },
            optimizers_config=models.OptimizersConfigDiff(
                indexing_threshold=0  # Hemen indexleme
            )
        )
        
        print(f"✅ Collection oluşturuldu!")
        return True


def upload_vectors(client, vectors_file):
    """Vektörleri yükle"""
    if not os.path.exists(vectors_file):
        print(f"❌ Vektör dosyası bulunamadı: {vectors_file}")
        return False
    
    print(f"\n📂 Vektörler yükleniyor: {vectors_file}")
    
    batch = []
    total = 0
    
    with open(vectors_file, 'rb') as f:
        for line in tqdm(f, desc="Yükleniyor", unit=" vektör"):
            try:
                data = orjson.loads(line)
                
                # UUID oluştur
                cve_id = data["payload"].get("cve_id", "")
                point_id = str(uuid5(NAMESPACE_DNS, cve_id)) if cve_id else data["id"]
                
                point = models.PointStruct(
                    id=point_id,
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
                
                if len(batch) >= BATCH_SIZE:
                    client.upsert(
                        collection_name=COLLECTION_NAME,
                        points=batch,
                        wait=False  # Async upload
                    )
                    total += len(batch)
                    batch = []
                    
            except Exception as e:
                print(f"\n⚠️  Satır parse hatası: {e}")
                continue
    
    # Son batch
    if batch:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=batch,
            wait=True  # Son batch'i bekle
        )
        total += len(batch)
    
    print(f"\n✅ {total:,} vektör başarıyla yüklendi!")
    return True


def main():
    """Ana fonksiyon"""
    print("="*70)
    print("   FLY.IO QDRANT VEKTÖR YÜKLEME")
    print("="*70)
    print()
    print(f"🌐 Qdrant URL: {QDRANT_URL}")
    print(f"📦 Collection: {COLLECTION_NAME}")
    print()
    
    try:
        # Qdrant'a bağlan (Fly.io - public, auth yok)
        print("🔌 Qdrant'a bağlanılıyor...")
        client = QdrantClient(
            url=QDRANT_URL,
            timeout=120,
            https=True
        )
        print("✅ Bağlantı başarılı!")
        
        # Collection oluştur
        if not create_collection(client):
            return
        
        # Vektörleri yükle
        upload_vectors(client, VECTORS_FILE)
        
        # Verify
        collection_info = client.get_collection(COLLECTION_NAME)
        print("\n" + "="*50)
        print(f"📊 Total Points: {collection_info.points_count:,}")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ HATA: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
```

### 4.2. Vektörleri Yükle

```bash
cd C:\Users\Meryem\Desktop\PENTTT\pentagentMr\Pentagent\Rag-Pent
python upload_to_fly.py
```

⏱️ **Süre:** 1-2 saat (95K vektör)

---

## 🚀 ADIM 5: Backend'i Güncelle

### 5.1. Backend Environment Variables

**Render.com'da:**

```env
QDRANT_HOST = https://pentagent-qdrant.fly.dev
QDRANT_PORT = 443
# QDRANT_API_KEY gerek yok (Fly.io public)
```

### 5.2. Backend Code Güncelle

`services/rag_service.py` zaten cloud desteği var:

```python
config = SearchConfig(
    qdrant_host=os.getenv("QDRANT_HOST", "localhost"),
    qdrant_port=int(os.getenv("QDRANT_PORT", "6333")),
    qdrant_api_key=os.getenv("QDRANT_API_KEY", None),  # None = public
)
```

✅ Kod değişikliği yok!

---

## 🚀 ADIM 6: Backend'i Render'a Deploy

```bash
cd C:\Users\Meryem\Desktop\PENTTT\pentagentMr\Pentagent

# Fly.io dosyalarını commit et
git add Rag-Pent/Dockerfile.qdrant
git add Rag-Pent/fly.toml
git add Rag-Pent/upload_to_fly.py
git commit -m "Add Fly.io Qdrant deployment"
git push

# Render otomatik redeploy eder
```

---

## 📊 Deployment Mimarisi

```
┌─────────────────────────────────────────────────────┐
│              DEPLOYMENT MİMARİSİ                    │
└─────────────────────────────────────────────────────┘

Frontend (Firebase Hosting) - $0
    ↓ HTTPS
Backend (Render.com) - $0
    ↓ HTTPS
Qdrant (Fly.io Docker) - $0
    └─ 3GB Persistent Volume
    └─ 95,237 CVE Vektörleri
```

### URL'ler

| Servis | URL | Port |
|--------|-----|------|
| Frontend | https://pentagent-b9007.web.app | 443 |
| Backend | https://pentagent-backend.onrender.com | 443 |
| Qdrant | https://pentagent-qdrant.fly.dev | 443 |

---

## 💰 Maliyet Analizi

| Servis | Plan | Maliyet | Limitler |
|--------|------|---------|----------|
| **Firebase Hosting** | Spark | $0 | 10GB, 360MB/day |
| **Render.com** | Free | $0 | 750h/ay, 512MB RAM |
| **Fly.io** | Free | $0 | 3GB volume, 256MB RAM |
| **TOPLAM** | | **$0** | ✅ Tamamen ücretsiz! |

---

## ⚠️ Önemli Notlar

### Fly.io Free Tier Limitleri

- **3GB Persistent Volume** ✅ Yeterli
- **256MB RAM (shared)** ⚠️ Sınırlı ama çalışır
- **160GB Network/ay** ✅ Yeterli
- **Auto-stop:** Hayır (her zaman açık)

### Qdrant Optimizasyonlar

1. **On-Disk Indexing**: RAM tasarrufu için
2. **Async Upload**: Daha hızlı yükleme
3. **HTTPS**: Güvenli bağlantı

---

## 🔧 Alternatif: Railway.app

Eğer Fly.io çalışmazsa:

### Railway.app (Daha Kolay)

```bash
# Railway CLI kur
npm install -g @railway/cli

# Login
railway login

# Deploy
cd C:\Users\Meryem\Desktop\PENTTT\pentagentMr\Pentagent\Rag-Pent
railway init
railway up

# URL'i al
railway domain
```

**Railway Avantajları:**
- ✅ $5 free credit/ay
- ✅ Kolay setup
- ✅ GitHub entegrasyon
- ✅ Daha fazla RAM (512MB)

**Railway Dezavantajları:**
- ❌ Free credit bitince ücretli
- ❌ Kredi kartı gerekebilir

---

## 🐛 Sorun Giderme

### Fly.io Deploy Başarısız

```bash
# Logs kontrol et
fly logs

# Status kontrol et
fly status

# SSH ile bağlan
fly ssh console
```

### Vektör Yükleme Hatası

```bash
# Qdrant health check
curl https://pentagent-qdrant.fly.dev/health

# Collection kontrol
curl https://pentagent-qdrant.fly.dev/collections/cve_collection_hybrid
```

### Backend Bağlanamıyor

```bash
# Backend'de test et
curl https://pentagent-backend.onrender.com/api/rag/stats
```

---

## 🎯 Deployment Checklist

- [ ] Fly.io CLI kuruldu
- [ ] Fly.io'ya login yapıldı
- [ ] `Dockerfile.qdrant` oluşturuldu
- [ ] `fly.toml` oluşturuldu
- [ ] Qdrant Fly.io'ya deploy edildi
- [ ] Vektörler yüklendi (95K)
- [ ] Backend environment variables güncellendi
- [ ] Backend Render'a deploy edildi
- [ ] Frontend Firebase'e deploy edildi
- [ ] Test edildi ✅

---

## 🚀 Sonraki Adım

Şimdi adım adım başlayalım:

```bash
# 1. Fly.io CLI kur
iwr https://fly.io/install.ps1 -useb | iex

# 2. Login
fly auth login

# 3. Deploy için dosyaları hazırla
cd C:\Users\Meryem\Desktop\PENTTT\pentagentMr\Pentagent\Rag-Pent

# Dockerfile.qdrant ve fly.toml oluştur (yukarıdaki içeriklerle)

# 4. Deploy!
fly apps create pentagent-qdrant
fly volumes create qdrant_data --region ams --size 3
fly deploy --config fly.toml --dockerfile Dockerfile.qdrant
```

**Hazır! 🎉**

