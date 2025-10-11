# ✅ Firebase Deployment Kontrol Listesi

## 🎯 Deployment Öncesi Kontroller

### ✅ Temizlik Tamamlandı
- [x] Test dosyaları silindi (test_*.py)
- [x] Debug dosyaları silindi
- [x] Eski session/log dosyaları temizlendi
- [x] Gereksiz node_modules temizlendi

### ✅ Yapılandırma Dosyaları Oluşturuldu
- [x] `firebase.json` - Firebase hosting config
- [x] `Dockerfile` - Backend container
- [x] `docker-compose.yml` - Local development
- [x] `.dockerignore` - Docker build optimization
- [x] `.gitignore` - Git ignore rules
- [x] `deploy.sh` - Unix deployment script
- [x] `deploy.bat` - Windows deployment script
- [x] `Procfile` - Heroku uyumluluğu
- [x] `runtime.txt` - Python version

### ✅ Kod İyileştirmeleri
- [x] CORS production için güvenli hale getirildi
- [x] Frontend API URL'i environment-aware
- [x] WebSocket bağlantısı stabil
- [x] Tool sonuçları detaylı gösteriliyor

## 📋 Şimdi Ne Yapmalısın?

### 1. API Key'lerini Al

**Gemini API Key:**
1. https://makersuite.google.com/app/apikey adresine git
2. "Get API Key" tıkla
3. Key'i kopyala

**Opsiyonel (daha fazla özellik için):**
- Shodan API: https://account.shodan.io/
- VirusTotal API: https://www.virustotal.com/gui/my-apikey

### 2. Local Test Yap

```bash
# Backend başlat
cd PentAgentVersion02
python web_api.py

# Yeni terminal - Frontend başlat
cd PentAgentVersion02/pentagent-frontend
npm install
npm run dev
```

Tarayıcıda `http://localhost:5173` aç ve test et.

### 3. Firebase Deployment

#### A. Firebase CLI Kur
```bash
npm install -g firebase-tools
```

#### B. Google Cloud SDK Kur
Windows: https://cloud.google.com/sdk/docs/install#windows

#### C. Login Yap
```bash
firebase login
gcloud auth login
```

#### D. Firebase Projesi Oluştur
https://console.firebase.google.com → Create Project

#### E. Deploy Et!
```bash
# Windows
deploy.bat

# Mac/Linux
chmod +x deploy.sh
./deploy.sh
```

## 🎉 Deployment Sonrası

### Backend URL'i Al:
```bash
gcloud run services describe pentagent-backend --region us-central1 --format 'value(status.url)'
```

### Frontend'e Backend URL'i Ekle:
```bash
cd pentagent-frontend
echo "VITE_API_URL=<backend-url-buraya>" > .env.production
npm run build
cd ..
firebase deploy --only hosting
```

## 🔍 Kontrol Et

1. **Backend Health:**
   `https://your-backend-url.run.app/health`

2. **Frontend:**
   `https://your-project-id.web.app`

3. **WebSocket:**
   Browser console'da "WebSocket bağlantısı kuruldu" görmelisin

## 🆘 Sorun mu Var?

### Backend hatası:
```bash
gcloud run services logs read pentagent-backend --limit=50
```

### Frontend hatası:
- Browser console'u kontrol et
- Network tab'inde API isteklerini kontrol et

### WebSocket bağlanamıyor:
- Backend URL'in HTTPS olduğundan emin ol
- CORS ayarlarını kontrol et
- Cloud Run kullandığından emin ol (Functions değil!)

## 📚 Detaylı Dokümantasyon

- `DEPLOYMENT.md` - Detaylı deployment rehberi
- `FIREBASE_DEPLOYMENT.md` - Firebase spesifik bilgiler
- `README_DEPLOYMENT.md` - Hızlı başlangıç

---

**Başarılar! 🚀**

