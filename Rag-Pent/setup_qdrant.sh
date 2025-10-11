#!/bin/bash

# CVE RAG Projesi - Qdrant Docker Kurulum Scripti
# Bu script Qdrant'ı Docker ile kurar ve gerekli hazırlıkları yapar

echo "=========================================="
echo "🚀 CVE RAG Projesi - Qdrant Kurulumu"
echo "=========================================="

# Docker'ın çalışıp çalışmadığını kontrol et
if ! docker --version > /dev/null 2>&1; then
    echo "❌ HATA: Docker kurulu değil. Lütfen önce Docker'ı kurun."
    exit 1
fi

echo "✅ Docker bulundu: $(docker --version)"

# Docker Compose'un çalışıp çalışmadığını kontrol et
if ! docker-compose --version > /dev/null 2>&1; then
    echo "❌ HATA: Docker Compose kurulu değil. Lütfen önce Docker Compose'u kurun."
    exit 1
fi

echo "✅ Docker Compose bulundu: $(docker-compose --version)"

# Qdrant'ı başlat
echo ""
echo "🐳 Qdrant container'ı başlatılıyor..."
docker-compose up -d

# Container'ın hazır olmasını bekle
echo ""
echo "⏳ Qdrant'ın hazır olması bekleniyor..."
sleep 10

# Health check
echo ""
echo "🔍 Qdrant sağlık kontrolü yapılıyor..."
max_attempts=30
attempt=1

while [ $attempt -le $max_attempts ]; do
    if curl -f http://localhost:6333/health > /dev/null 2>&1; then
        echo "✅ Qdrant başarıyla çalışıyor!"
        break
    else
        echo "⏳ Deneme $attempt/$max_attempts - Qdrant henüz hazır değil..."
        sleep 2
        attempt=$((attempt + 1))
    fi
done

if [ $attempt -gt $max_attempts ]; then
    echo "❌ HATA: Qdrant başlatılamadı. Logları kontrol edin:"
    echo "docker-compose logs qdrant"
    exit 1
fi

echo ""
echo "=========================================="
echo "🎉 KURULUM TAMAMLANDI!"
echo "=========================================="
echo ""
echo "📊 Qdrant Dashboard: http://localhost:6333/dashboard"
echo "🔗 REST API: http://localhost:6333"
echo "🔗 gRPC API: http://localhost:6334"
echo ""
echo "📝 Sonraki adımlar:"
echo "1. Vektörleri yüklemek için: python Qdrant/upload.py"
echo "2. Arama testi için: python Qdrant/search_test.py"
echo ""
echo "🛑 Qdrant'ı durdurmak için: docker-compose down"
echo "=========================================="

