@echo off
REM Pentagent Firebase Deployment Script (Windows)

echo 🚀 Pentagent Firebase Deployment Başlıyor...

REM 1. Environment check
if not exist ".env" (
    echo ❌ .env dosyası bulunamadı!
    echo Lütfen .env.example dosyasını .env olarak kopyalayın ve API key'leri doldurun.
    exit /b 1
)

echo ✅ Environment variables kontrol edildi

REM 2. Google Cloud Project kontrol
for /f "tokens=*" %%i in ('gcloud config get-value project') do set PROJECT_ID=%%i

if "%PROJECT_ID%"=="" (
    echo ❌ Google Cloud projesi seçilmemiş!
    echo Lütfen 'gcloud init' komutunu çalıştırın.
    exit /b 1
)

echo ✅ Google Cloud Project: %PROJECT_ID%

REM 3. Docker image build
echo 🔨 Docker image build ediliyor...
gcloud builds submit --tag gcr.io/%PROJECT_ID%/pentagent-backend

REM 4. Cloud Run'a deploy
echo ☁️ Cloud Run'a deploy ediliyor...
gcloud run deploy pentagent-backend ^
  --image gcr.io/%PROJECT_ID%/pentagent-backend ^
  --platform managed ^
  --region us-central1 ^
  --allow-unauthenticated ^
  --memory 2Gi ^
  --cpu 2 ^
  --timeout 600

REM 5. Backend URL al
for /f "tokens=*" %%i in ('gcloud run services describe pentagent-backend --region us-central1 --format "value(status.url)"') do set BACKEND_URL=%%i
echo ✅ Backend deployed: %BACKEND_URL%

REM 6. Frontend build
echo 🎨 Frontend build ediliyor...
cd pentagent-frontend

REM Backend URL'i frontend'e aktar
echo VITE_API_URL=%BACKEND_URL% > .env.production

call npm install
call npm run build

cd ..

REM 7. Firebase Hosting'e deploy
echo 🔥 Firebase Hosting'e deploy ediliyor...
firebase deploy --only hosting

echo.
echo ✅ ✅ ✅ DEPLOYMENT TAMAMLANDI! ✅ ✅ ✅
echo.
echo 🌐 Backend URL: %BACKEND_URL%
echo 🌐 Frontend URL: https://%PROJECT_ID%.web.app
echo.
echo 📝 Sonraki adımlar:
echo 1. Firebase Console'dan custom domain ekleyin
echo 2. Backend API key'lerini kontrol edin
echo 3. CORS ayarlarını production domain için güncelleyin
echo.

pause

