#!/bin/bash
# Pentagent Hızlı Başlatma ve Debug Scripti

echo "🚀 Pentagent Hızlı Başlatma ve Debug"
echo "====================================="

# Backend'i başlat
echo "🔧 Backend başlatılıyor..."
python web_api.py &
BACKEND_PID=$!

# Backend'in başlamasını bekle
echo "⏳ Backend'in başlaması bekleniyor..."
sleep 5

# Debug testi çalıştır
echo "🧪 Debug testi çalıştırılıyor..."
python debug_pentagent.py

# Frontend'i başlat
echo "🌐 Frontend başlatılıyor..."
cd pentagent-frontend
npm run dev &
FRONTEND_PID=$!

# Ana dizine geri dön
cd ..

echo ""
echo "🎉 Pentagent başlatıldı!"
echo "🌐 Frontend: http://localhost:5173"
echo "🔧 Backend: http://localhost:8000"
echo ""
echo "🛑 Durdurmak için Ctrl+C basın"

# Cleanup fonksiyonu
cleanup() {
    echo ""
    echo "🛑 Pentagent durduruluyor..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ Servisler durduruldu"
    exit 0
}

# Signal trap
trap cleanup SIGINT SIGTERM

# Servislerin çalışmasını bekle
wait
