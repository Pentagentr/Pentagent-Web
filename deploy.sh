#!/bin/bash

# Pentagent Firebase Deployment Script
set -e

echo "🚀 Pentagent Firebase Deployment Başlıyor..."

# 1. Environment check
if [ ! -f ".env" ]; then
    echo "❌ .env dosyası bulunamadı!"
    echo "Lütfen .env.example dosyasını .env olarak kopyalayın ve API key'leri doldurun."
    exit 1
fi

echo "✅ Environment variables kontrol edildi"

# 2. Backend için Docker build (Cloud Run için)
echo "📦 Backend Docker image oluşturuluyor..."
PROJECT_ID=$(gcloud config get-value project)

if [ -z "$PROJECT_ID" ]; then
    echo "❌ Google Cloud projesi seçilmemiş!"
    echo "Lütfen 'gcloud init' komutunu çalıştırın."
    exit 1
fi

echo "✅ Google Cloud Project: $PROJECT_ID"

# Docker image build
echo "🔨 Docker image build ediliyor..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/pentagent-backend

# Cloud Run'a deploy
echo "☁️ Cloud Run'a deploy ediliyor..."
gcloud run deploy pentagent-backend \
  --image gcr.io/$PROJECT_ID/pentagent-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 600 \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY

# Backend URL'i al
BACKEND_URL=$(gcloud run services describe pentagent-backend --region us-central1 --format 'value(status.url)')
echo "✅ Backend deployed: $BACKEND_URL"

# 3. Frontend build
echo "🎨 Frontend build ediliyor..."
cd pentagent-frontend

# Backend URL'i frontend'e aktar
export VITE_API_URL=$BACKEND_URL
echo "VITE_API_URL=$BACKEND_URL" > .env.production

npm install
npm run build

cd ..

# 4. Firebase Hosting'e deploy
echo "🔥 Firebase Hosting'e deploy ediliyor..."
firebase deploy --only hosting

echo ""
echo "✅ ✅ ✅ DEPLOYMENT TAMAMLANDI! ✅ ✅ ✅"
echo ""
echo "🌐 Backend URL: $BACKEND_URL"
echo "🌐 Frontend URL: https://YOUR_PROJECT_ID.web.app"
echo ""
echo "📝 Sonraki adımlar:"
echo "1. Firebase Console'dan custom domain ekleyin"
echo "2. Backend API key'lerini kontrol edin"
echo "3. CORS ayarlarını production domain için güncelleyin"
echo ""

