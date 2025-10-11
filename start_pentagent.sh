#!/bin/bash
# Pentagent Başlatma Scripti

echo "🚀 Pentagent Başlatılıyor..."
echo "================================"

# Python dependencies kontrolü
echo "📦 Python dependencies kontrol ediliyor..."
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt bulunamadı!"
    exit 1
fi

# Virtual environment kontrolü
if [ ! -d "venv" ]; then
    echo "🔧 Virtual environment oluşturuluyor..."
    python -m venv venv
fi

# Virtual environment aktifleştir
echo "🔌 Virtual environment aktifleştiriliyor..."
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows için

# Dependencies yükle
echo "📥 Dependencies yükleniyor..."
pip install -r requirements.txt

# Frontend dependencies kontrolü
echo "🎨 Frontend dependencies kontrol ediliyor..."
cd pentagent-frontend
if [ ! -d "node_modules" ]; then
    echo "📦 Node modules yükleniyor..."
    npm install
fi

# Frontend'i başlat (arka planda)
echo "🌐 Frontend başlatılıyor..."
npm run dev &
FRONTEND_PID=$!

# Ana dizine geri dön
cd ..

# Backend'i başlat
echo "🔧 Backend başlatılıyor..."
python web_api.py &
BACKEND_PID=$!

# Başlatma kontrolü
echo "⏳ Servislerin başlaması bekleniyor..."
sleep 5

# Bağlantı testi
echo "🧪 Bağlantı testi yapılıyor..."
python test_connection.py

echo ""
echo "🎉 Pentagent başarıyla başlatıldı!"
echo "🌐 Frontend: http://localhost:5173"
echo "🔧 Backend API: http://localhost:8000"
echo "📊 Health Check: http://localhost:8000/health"
echo ""
echo "🛑 Durdurmak için Ctrl+C basın"

# Cleanup fonksiyonu
cleanup() {
    echo ""
    echo "🛑 Pentagent durduruluyor..."
    kill $FRONTEND_PID 2>/dev/null
    kill $BACKEND_PID 2>/dev/null
    echo "✅ Servisler durduruldu"
    exit 0
}

# Signal trap
trap cleanup SIGINT SIGTERM

# Servislerin çalışmasını bekle
wait
