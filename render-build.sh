#!/bin/bash
# Render.com build script - Nmap ve Chrome kurulumu

set -e

echo "🚀 Render Build Script başlatılıyor..."

# Sistem paketi kurulumları (Render free tier'da root erişimi varsa)
if [ "$RENDER_SERVICE_TYPE" = "web" ]; then
    echo "📦 Sistem bağımlılıkları kuruluyor..."
    
    # Nmap kurulumu
    if ! command -v nmap &> /dev/null; then
        echo "📦 Nmap kuruluyor..."
        apt-get update -qq
        apt-get install -y -qq nmap
        echo "✅ Nmap kuruldu: $(which nmap)"
    else
        echo "✅ Nmap zaten kurulu"
    fi
    
    # Chrome kurulumu (ağır ama XSS araçları için gerekli)
    if ! command -v google-chrome &> /dev/null; then
        echo "📦 Chrome kuruluyor (bu biraz sürebilir)..."
        wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
        echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
        apt-get update -qq
        apt-get install -y -qq google-chrome-stable
        echo "✅ Chrome kuruldu: $(which google-chrome)"
    else
        echo "✅ Chrome zaten kurulu"
    fi
fi

# Python bağımlılıklarını kur
echo "📦 Python bağımlılıkları kuruluyor..."
pip install --no-cache-dir -r requirements.txt

echo "✅ Build tamamlandı!"




