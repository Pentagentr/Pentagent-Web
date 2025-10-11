# 🎯 Pentagent - Ne Yapmalısın?

## ✅ Hazırlık Tamamlandı!

Proje Firebase deployment için hazır. İşte yapman gerekenler:

## 📝 Adım Adım Deployment

### 1️⃣ Firebase Projesi Oluştur

```bash
# Firebase Console'a git
https://console.firebase.google.com

# Yeni proje oluştur
- Proje adı: pentagent-security (veya istediğin)
- Analytics: İsteğe bağlı
```

### 2️⃣ Google Cloud SDK Kur

**Windows:**
https://cloud.google.com/sdk/docs/install#windows

**Mac/Linux:**
```bash
curl https://sdk.cloud.google.com | bash
```

### 3️⃣ Login ve Init

```bash
# Firebase login
firebase login

# Google Cloud login
gcloud auth login

# Proje seç
firebase init
# Hosting seç (Spacebar ile seç, Enter ile onayla)
# Existing project seç
# Public directory: pentagent-frontend/dist
# Single-page app: Yes
# GitHub actions: No

gcloud init
# Proje seç: Az önce oluşturduğun Firebase projesini seç
```

### 4️⃣ API Key'lerini Ayarla

**Local test için** `config.py` dosyasını düzenle:
```python
GEMINI_API_KEY = "your_gemini_api_key_here"
```

**Production için** Cloud Run environment variables kullan (deploy sırasında)

### 5️⃣ Local Test

```bash
# Backend test
cd PentAgentVersion02
python web_api.py

# Yeni terminal
cd PentAgentVersion02/pentagent-frontend
npm install
npm run dev
```

Tarayıcıda `http://localhost:5173` aç ve test et.

### 6️⃣ Deploy!

**Windows:**
```bash
cd PentAgentVersion02
deploy.bat
```

**Linux/Mac:**
```bash
cd PentAgentVersion02
chmod +x deploy.sh
./deploy.sh
```

## 🎉 Deployment Tamamlandı!

Script şunları otomatik yapacak:
1. ✅ Backend Docker image oluştur
2. ✅ Cloud Run'a deploy et
3. ✅ Frontend build et
4. ✅ Firebase Hosting'e deploy et

## 🌐 URL'ler

Deployment sonrası şunları alacaksın:

**Backend:**
```
https://pentagent-backend-xxxxx-uc.a.run.app
```

**Frontend:**
```
https://your-project-id.web.app
```

## 🔧 Production Ayarları

### 1. Frontend'te Backend URL'i Güncelle

`pentagent-frontend/.env.production` oluştur:
```env
VITE_API_URL=https://pentagent-backend-xxxxx-uc.a.run.app
```

Yeniden build ve deploy:
```bash
cd pentagent-frontend
npm run build
cd ..
firebase deploy --only hosting
```

### 2. Custom Domain Ekle (Opsiyonel)

Firebase Console → Hosting → Add custom domain

## ⚠️ Önemli Notlar

1. **API Keys:** Asla GitHub'a push etme!
2. **CORS:** Production domain'leri `ALLOWED_ORIGINS`'e ekle
3. **Maliyet:** Cloud Run ücretsiz kotası: 2M istek/ay
4. **WebSocket:** Cloud Run WebSocket'leri destekler ✅

## 🆘 Sorun mu Yaşıyorsun?

1. **Backend başlamıyor:**
   ```bash
   gcloud run services logs read pentagent-backend --limit=50
   ```

2. **Frontend bağlanamıyor:**
   - Backend URL'i kontrol et
   - CORS ayarlarını kontrol et

3. **WebSocket hatası:**
   - HTTPS (wss://) kullandığından emin ol
   - Cloud Run kullandığından emin ol

## 📚 Daha Fazla Bilgi

- `DEPLOYMENT.md` - Detaylı deployment rehberi
- `FIREBASE_DEPLOYMENT.md` - Firebase spesifik bilgiler
- `config.py` - Backend konfigürasyonu

---

**Hazırsın! Deployment'a başla! 🚀**

