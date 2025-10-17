# Pentagent Firebase Deployment Script
# PowerShell script for Windows

Write-Host "🚀 Pentagent Deployment Başlıyor..." -ForegroundColor Cyan
Write-Host ""

# Frontend klasörüne git
Write-Host "📦 Frontend build oluşturuluyor..." -ForegroundColor Yellow
Set-Location "pentagent-frontend"

# Dependencies kontrol
if (-not (Test-Path "node_modules")) {
    Write-Host "📥 Dependencies yükleniyor..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ npm install başarısız!" -ForegroundColor Red
        exit 1
    }
}

# Build oluştur
Write-Host "🔨 Production build oluşturuluyor..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build başarısız!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Build başarılı!" -ForegroundColor Green
Write-Host ""

# Ana klasöre dön
Set-Location ".."

# Firebase deploy
Write-Host "🚀 Firebase'e deploy ediliyor..." -ForegroundColor Yellow
firebase deploy

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Deploy başarılı!" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 Uygulamanız yayında:" -ForegroundColor Cyan
    Write-Host "   https://pentagent-b9007.web.app" -ForegroundColor White
    Write-Host ""
    Write-Host "📊 Firebase Console:" -ForegroundColor Cyan
    Write-Host "   https://console.firebase.google.com/project/pentagent-b9007" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Deploy başarısız!" -ForegroundColor Red
    Write-Host "Lütfen hata mesajlarını kontrol edin." -ForegroundColor Yellow
    exit 1
}























