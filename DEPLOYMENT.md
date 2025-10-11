# 🚀 Pentagent Deployment Rehberi

## 📊 Deployment Mimarisi

```
Frontend (Firebase Hosting)
    ↓ HTTPS
Backend (Render.com)
    ↓ HTTPS + WebSocket
Qdrant (HuggingFace Space - Private)
    └─ 95,237 CVE Vektörleri
```

---

## ✅ ADIM 1: Qdrant (HuggingFace Space)

**Durum:** ✅ Tamamlandı
- **URL:** `https://meryemarpaci-pentagent-qdrant.hf.space`
- **Status:** Running
- **Vektörler:** 95,237 CVE

---

## ✅ ADIM 2: Backend (Render.com)

### 2.1. Render.com'da Web Service Oluştur

1. **https://render.com** → GitHub ile giriş yap
2. **Dashboard → "New +" → "Web Service"**
3. **Repo seç:** `Pentagent-Web`

### 2.2. Ayarlar

```
Name: pentagent-backend
Language: Python 3
Branch: main

Build Command:
pip install -r requirements.txt

Start Command:
uvicorn web_api:app --host 0.0.0.0 --port $PORT

Instance Type: Free
```

### 2.3. Environment Variables

```env
GEMINI_API_KEY
AIzaSyC9d-8SPEV1cupSiqS4wXR705MXo45ZJGs

ALLOWED_ORIGINS
https://pentagent-b9007.web.app

QDRANT_HOST
https://meryemarpaci-pentagent-qdrant.hf.space

QDRANT_PORT
443

HUGGINGFACE_TOKEN
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
```

### 2.4. Health Check Path

```
/health
```

### 2.5. Deploy

**"Deploy web service"** tıkla → 5-10 dakika bekle

**Backend URL:** `https://pentagent-backend-xxxx.onrender.com`

---

## ✅ ADIM 3: Frontend (Firebase Hosting)

### 3.1. Backend URL'ini Ayarla

```bash
cd C:\Users\Meryem\Desktop\PENTTT\pentagentMr\Pentagent\pentagent-frontend

# Backend URL'ini gir (Render'dan al)
echo VITE_API_URL=https://pentagent-backend-xxxx.onrender.com > .env.production
```

### 3.2. Build ve Deploy

```bash
npm run build

cd ..
firebase deploy --only hosting
```

**Frontend URL:** `https://pentagent-b9007.web.app`

---

## 🧪 Test

### 1. Qdrant Test
```bash
curl -H "Authorization: Bearer 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" \
  https://meryemarpaci-pentagent-qdrant.hf.space/health
```

### 2. Backend Test
```bash
curl https://pentagent-backend-xxxx.onrender.com/health
```

**Beklenen:**
```json
{
  "status": "healthy",
  "rag_available": true,
  "rag_cves": 95237
}
```

### 3. RAG Test
```bash
curl -X POST "https://pentagent-backend-xxxx.onrender.com/api/rag/search" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"SQL injection\",\"limit\":3}"
```

### 4. Frontend Test
1. `https://pentagent-b9007.web.app` aç
2. Pentest taraması yap
3. `/rag-search` → CVE ara
4. ContextPanel → CVE Suggestions kontrol et

---

## 📁 Proje Dosyaları

### Tutulması Gerekenler
- ✅ `README.md` - Ana readme
- ✅ `RAG_INTEGRATION_README.md` - RAG kullanım rehberi
- ✅ `HUGGINGFACE_QDRANT_DEPLOYMENT.md` - Qdrant deployment
- ✅ `PRIVATE_SPACE_SOLUTION.md` - Private Space çözümü
- ✅ `LICENSE` - Lisans
- ✅ `requirements.txt` - Python dependencies
- ✅ `web_api.py` - Backend API
- ✅ `services/` - Servisler (RAG dahil)
- ✅ `agent_core/` - AI agent mantığı
- ✅ `tools/` - Security tools
- ✅ `pentagent-frontend/` - React frontend
- ✅ `Rag-Pent/Qdrant/` - RAG search modülleri

### Silinen Gereksizler
- ❌ Eski deployment dosyaları (10+ MD)
- ❌ Deploy script'leri (bat/sh)
- ❌ Docker compose dosyaları
- ❌ Fly.io dosyaları

---

## 💰 Maliyet

| Servis | Maliyet |
|--------|---------|
| HuggingFace Space | $0 |
| Render.com | $0 |
| Firebase Hosting | $0 |
| **TOPLAM** | **$0** |

---

## 🚦 Deployment Durumu

- ✅ **Qdrant:** Running
- 🔄 **Backend:** Deploy edilecek
- 🔄 **Frontend:** Deploy edilecek

**Sonraki adım:** Render.com'da backend'i deploy et! 🚀

