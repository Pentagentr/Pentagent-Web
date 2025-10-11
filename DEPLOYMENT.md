# Pentagent Firebase Deployment Guide

## 📋 Ön Gereksinimler

1. **Firebase CLI Kurulumu:**
```bash
npm install -g firebase-tools
```

2. **Firebase Projesi Oluştur:**
- https://console.firebase.google.com adresine git
- Yeni proje oluştur
- Firebase Hosting ve Cloud Functions'ı etkinleştir

3. **Firebase Login:**
```bash
firebase login
```

## 🚀 Deployment Adımları

### 1. Backend (Cloud Functions / Cloud Run)

Firebase Functions Python desteği sınırlı olduğundan, backend için **Google Cloud Run** kullanmanızı öneririz:

#### Option A: Cloud Run (Önerilen)

```bash
# Google Cloud SDK kurulu olmalı
gcloud init

# Proje seç
gcloud config set project YOUR_PROJECT_ID

# Docker image oluştur
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/pentagent-backend

# Cloud Run'a deploy et
gcloud run deploy pentagent-backend \
  --image gcr.io/YOUR_PROJECT_ID/pentagent-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=your_key_here
```

#### Option B: Firebase Functions

```bash
cd functions
firebase deploy --only functions
```

### 2. Frontend (Firebase Hosting)

```bash
# Frontend'i build et
cd pentagent-frontend
npm install
npm run build

# Firebase'e deploy et
cd ..
firebase deploy --only hosting
```

### 3. Full Deployment (Tek komut)

```bash
./deploy.sh
```

## 🔐 Environment Variables Ayarlama

### Cloud Run için:
```bash
gcloud run services update pentagent-backend \
  --set-env-vars GEMINI_API_KEY=your_gemini_api_key_here
```

### Firebase Functions için:
```bash
firebase functions:config:set \
  gemini.api_key="your_gemini_api_key_here"
```

## 🌐 Domain Ayarlama

1. Firebase Console → Hosting → Custom Domain
2. Domain'inizi ekleyin
3. DNS kayıtlarını güncelleyin

## 📊 Monitoring

```bash
# Logs görüntüle (Cloud Run)
gcloud run services logs read pentagent-backend --limit=100

# Firebase logs
firebase functions:log
```

## 🔄 Güncelleme

```bash
# Backend güncelle
gcloud run deploy pentagent-backend --image gcr.io/YOUR_PROJECT_ID/pentagent-backend

# Frontend güncelle
cd pentagent-frontend && npm run build && cd .. && firebase deploy --only hosting
```

## ⚠️ Önemli Notlar

1. **API Keys:** Tüm API key'leri environment variables'a taşıyın
2. **CORS:** Backend'te CORS ayarlarını production domain'e göre güncelleyin
3. **Security:** Firebase Security Rules oluşturun
4. **Rate Limiting:** Cloud Run'da rate limiting ekleyin
5. **WebSocket:** Cloud Run WebSocket'leri destekler, Firebase Functions desteklemez

## 🐛 Troubleshooting

### Backend başlamıyor:
```bash
# Logs kontrol et
gcloud run services logs read pentagent-backend --limit=50

# Environment variables kontrol et
gcloud run services describe pentagent-backend
```

### Frontend bağlanamıyor:
- `pentagent-frontend/src/services/pentagentAPI.js` dosyasında backend URL'i güncelle
- CORS ayarlarını kontrol et

### WebSocket bağlantısı yok:
- Cloud Run kullanın (Firebase Functions WebSocket desteklemez)
- WSS (secure WebSocket) kullanın

## 📞 Destek

Sorun yaşarsanız GitHub issues açın veya dokümantasyona bakın.

