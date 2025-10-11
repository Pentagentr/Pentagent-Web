# 🚀 Pentagent Firebase Deployment Rehberi

## 📋 Hızlı Başlangıç

### 1. Ön Hazırlık

```bash
# Firebase CLI kur
npm install -g firebase-tools

# Google Cloud SDK kur
# https://cloud.google.com/sdk/docs/install

# Login yap
firebase login
gcloud auth login
```

### 2. Firebase Projesi Oluştur

1. https://console.firebase.google.com adresine git
2. "Create Project" tıkla
3. Proje adı gir (örn: `pentagent-security`)
4. Firebase Hosting'i etkinleştir

### 3. Google Cloud Run Hazırlığı

```bash
# Google Cloud projesini seç
gcloud init
gcloud config set project YOUR_PROJECT_ID

# Cloud Run API'sini etkinleştir
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### 4. Environment Variables Ayarla

**`.env` dosyası oluştur:**
```bash
cd PentAgentVersion02
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac
```

**`.env` dosyasını düzenle:**
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
ALLOWED_ORIGINS=https://your-project-id.web.app,https://your-custom-domain.com
```

### 5. Deploy Et!

#### Windows:
```bash
deploy.bat
```

#### Linux/Mac:
```bash
chmod +x deploy.sh
./deploy.sh
```

## 🎯 Manuel Deployment

### Backend (Cloud Run)

```bash
# Docker image build
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/pentagent-backend

# Deploy
gcloud run deploy pentagent-backend \
  --image gcr.io/YOUR_PROJECT_ID/pentagent-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 600 \
  --set-env-vars GEMINI_API_KEY=your_key_here,ALLOWED_ORIGINS=https://your-frontend-url.web.app
```

### Frontend (Firebase Hosting)

```bash
# Build
cd pentagent-frontend
npm install
npm run build

# Firebase init (ilk kez)
cd ..
firebase init hosting
# Public directory: pentagent-frontend/dist
# Single-page app: Yes
# Automatic builds: No

# Deploy
firebase deploy --only hosting
```

## 🔧 Production Ayarları

### 1. Backend URL'i Frontend'e Bağla

Cloud Run deployment sonrası backend URL'i al:
```bash
gcloud run services describe pentagent-backend \
  --region us-central1 \
  --format 'value(status.url)'
```

Bu URL'i frontend'e ekle:
```bash
cd pentagent-frontend
echo "VITE_API_URL=https://your-backend-url.run.app" > .env.production
npm run build
cd ..
firebase deploy --only hosting
```

### 2. Custom Domain Ekle

**Firebase Hosting:**
1. Firebase Console → Hosting → Add custom domain
2. Domain'i doğrula
3. DNS kayıtlarını güncelle

**Cloud Run:**
```bash
gcloud run domain-mappings create \
  --service pentagent-backend \
  --domain api.yourdomain.com \
  --region us-central1
```

## 📊 Monitoring ve Logs

### Backend Logs:
```bash
gcloud run services logs read pentagent-backend --limit=100 --region=us-central1
```

### Frontend Logs:
Firebase Console → Hosting → Usage

### Real-time Monitoring:
```bash
gcloud run services logs tail pentagent-backend --region=us-central1
```

## 🔒 Güvenlik Ayarları

### 1. API Rate Limiting

`web_api.py` dosyasına ekle:
```python
from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)
```

### 2. CORS Kısıtlaması

`.env` dosyasında:
```env
ALLOWED_ORIGINS=https://your-domain.web.app,https://your-custom-domain.com
```

### 3. API Key Güvenliği

- ❌ API key'leri asla kod içinde bırakmayın
- ✅ Google Cloud Secret Manager kullanın
- ✅ Environment variables kullanın

## 💰 Maliyet Optimizasyonu

### Cloud Run:
- İlk 2M istek/ay ücretsiz
- Memory: 2Gi yeterli
- CPU: 2 vCPU yeterli
- Timeout: 600s (10 dakika)

### Firebase Hosting:
- 10GB storage ve 360MB/gün transfer ücretsiz
- CDN dahil

## 🐛 Sorun Giderme

### "Cloud Build failed"
```bash
# Dockerfile'ı kontrol et
docker build -t pentagent-test .
docker run -p 8000:8000 pentagent-test
```

### "WebSocket connection failed"
- Cloud Run kullanın (Functions WebSocket desteklemez)
- WSS (https) kullanın
- CORS ayarlarını kontrol edin

### "Gemini API key invalid"
```bash
# Environment variable'ı kontrol et
gcloud run services describe pentagent-backend --region us-central1
```

## 📞 Yardım

GitHub Issues: https://github.com/your-repo/pentagent/issues
Docs: https://your-docs-url.com

