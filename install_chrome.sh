#!/bin/bash
# Render.com için Chrome ve bağımlılıklarını kurulum scripti

echo "🔧 Chrome ve Nmap kurulumu başlatılıyor..."

# Sistem güncellemesi
apt-get update

# Nmap kurulumu
echo "📦 Nmap kuruluyor..."
apt-get install -y nmap

# Chrome bağımlılıkları
echo "📦 Chrome bağımlılıkları kuruluyor..."
apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    xdg-utils \
    libu2f-udev \
    libvulkan1

# Chrome kurulumu
echo "📦 Google Chrome kuruluyor..."
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list
apt-get update
apt-get install -y google-chrome-stable

echo "✅ Kurulum tamamlandı!"
which nmap
which google-chrome

