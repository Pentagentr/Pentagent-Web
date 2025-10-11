# 📁 Proje Klasörünü Yeniden Adlandır

## ⚠️ Erişim Reddedildi Hatası

Klasör kullanımda olduğu için otomatik yeniden adlandırma başarısız.

## ✅ Manuel Olarak Yap (30 saniye)

### 1. Tüm Terminal ve VS Code'ları Kapat
- VS Code'u kapat
- Tüm PowerShell/Terminal'leri kapat
- Backend/Frontend çalışıyorsa durdur (Ctrl+C)

### 2. Windows Explorer'da Yeniden Adlandır
```
C:\Users\Meryem\Desktop\PENTTT\pentagentMr\

PentAgentVersion02 klasörüne sağ tıkla → Rename → "Pentagent" yaz
```

### 3. VS Code'u Yeni Klasörle Aç
```
File → Open Folder → Pentagent klasörünü seç
```

### 4. GitHub'a Push Et
```bash
cd C:\Users\Meryem\Desktop\PENTTT\pentagentMr\Pentagent

git init
git add .
git commit -m "Pentagent ready for deployment"
git remote add origin https://github.com/meryemarpaci8/pentagent-backend.git
git branch -M main
git push -u origin main
```

---

**Sonra QUICK_DEPLOY_GUIDE.md dosyasına dön ve deployment'a devam et!**

