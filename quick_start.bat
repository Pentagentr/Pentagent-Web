@echo off
REM Pentagent Hızlı Başlatma ve Debug Scripti (Windows)

echo 🚀 Pentagent Hızlı Başlatma ve Debug
echo =====================================

REM Backend'i başlat
echo 🔧 Backend başlatılıyor...
start /B python web_api.py

REM Backend'in başlamasını bekle
echo ⏳ Backend'in başlaması bekleniyor...
timeout /t 5 /nobreak > nul

REM Debug testi çalıştır
echo 🧪 Debug testi çalıştırılıyor...
python debug_pentagent.py

REM Frontend'i başlat
echo 🌐 Frontend başlatılıyor...
cd pentagent-frontend
start /B npm run dev

REM Ana dizine geri dön
cd ..

echo.
echo 🎉 Pentagent başlatıldı!
echo 🌐 Frontend: http://localhost:5173
echo 🔧 Backend: http://localhost:8000
echo.
echo 🛑 Durdurmak için Ctrl+C basın

pause
