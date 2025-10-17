# 🔐 Pentagent Firebase Authentication

## ✨ Özellikler

- ✅ Firebase Authentication ile güvenli giriş/kayıt sistemi
- ✅ Firestore Database entegrasyonu
- ✅ Otomatik oturum yönetimi (persistent login)
- ✅ Protected routes - sadece giriş yapanlar erişebilir
- ✅ Profesyonel dark lacivert UI tasarımı
- ✅ Buz kristali efektleri ve glassmorphism
- ✅ Responsive tasarım
- ✅ Gerçek zamanlı kullanıcı profili

## 📁 Yapı

```
src/
├── config/
│   └── firebase.js              # Firebase config ve servis tanımlamaları
├── contexts/
│   ├── AuthContext.jsx          # Kullanıcı oturum yönetimi Context
│   └── index.js                 # Context exports
├── components/
│   └── auth/
│       ├── ProtectedRoute.jsx   # Korumalı route wrapper
│       └── index.js             # Auth component exports
├── pages/
│   ├── LoginPage.jsx            # Giriş sayfası
│   └── RegisterPage.jsx         # Kayıt sayfası
└── styles/
    └── auth.css                 # Auth sayfaları için özel CSS
```

## 🚀 Kurulum ve Çalıştırma

### 1. Firebase Console Ayarları

Firebase Console'da aşağıdaki ayarları yapın:

#### Authentication Ayarları
1. Firebase Console > Authentication > Sign-in method
2. Email/Password metodunu etkinleştir

#### Firestore Database Ayarları
1. Firebase Console > Firestore Database
2. Database oluştur (Test mode veya Production mode)
3. Aşağıdaki güvenlik kurallarını ekle:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Kullanıcı koleksiyonu
    match /users/{userId} {
      // Kullanıcı kendi dökümanını okuyabilir
      allow read: if request.auth != null && request.auth.uid == userId;
      
      // Yeni kullanıcı oluşturma (signup sırasında)
      allow create: if request.auth != null && request.auth.uid == userId;
      
      // Kullanıcı kendi dökümanını güncelleyebilir
      allow update: if request.auth != null && request.auth.uid == userId;
      
      // Silme işlemi sadece admin yapabilir
      allow delete: if false;
    }
    
    // Diğer koleksiyonlar için kurallar
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

### 2. Projeyi Çalıştırma

```bash
cd Pentagent/pentagent-frontend
npm install
npm run dev
```

### 3. İlk Kullanım

1. Tarayıcıda `http://localhost:5173` adresine gidin
2. Kayıt sayfasından yeni hesap oluşturun
3. Otomatik olarak giriş yapılacak ve ana sayfaya yönlendirileceksiniz

## 🔒 Güvenlik Özellikleri

### Korumalı Rotalar (Protected Routes)
Tüm uygulama rotaları `ProtectedRoute` component'i ile korunuyor:
- Giriş yapmamış kullanıcılar otomatik olarak `/login` sayfasına yönlendirilir
- Giriş yapan kullanıcılar direkt olarak uygulamaya erişebilir

### Oturum Yönetimi
- **Persistent Login**: Kullanıcı bir kez giriş yaptığında, tarayıcıyı kapatsa bile oturum açık kalır
- **Otomatik Token Yenileme**: Firebase SDK token'ları otomatik olarak yeniler
- **Güvenli Çıkış**: Logout butonu ile güvenli çıkış

### Kullanıcı Profili
Her kullanıcı için Firestore'da şu bilgiler saklanır:
```javascript
{
  uid: "user-id",
  email: "user@email.com",
  displayName: "Kullanıcı Adı",
  createdAt: Timestamp,
  lastLogin: Timestamp,
  role: "user",
  status: "active"
}
```

## 🎨 UI/UX Özellikleri

### Tasarım Elementleri
- **Dark Lacivert Gradient**: Modern ve profesyonel görünüm
- **Buz Kristalleri**: Animasyonlu arka plan efektleri
- **Glassmorphism**: Cam efektli form panelleri
- **Glow Effects**: Hover ve focus durumlarında parlama efektleri
- **Smooth Animations**: Tüm geçişler ve animasyonlar akıcı

### Responsive Tasarım
- Mobil, tablet ve masaüstü cihazlarda mükemmel görünüm
- Touch-friendly butonlar ve input'lar

## 📝 Kullanım Örnekleri

### AuthContext Kullanımı
```jsx
import { useAuth } from '../contexts/AuthContext';

function MyComponent() {
  const { currentUser, userProfile, logout } = useAuth();

  return (
    <div>
      <p>Hoş geldin, {userProfile?.displayName}!</p>
      <button onClick={logout}>Çıkış Yap</button>
    </div>
  );
}
```

### Protected Route Kullanımı
```jsx
import { ProtectedRoute } from '../components/auth';

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route 
        path="/dashboard" 
        element={
          <ProtectedRoute>
            <DashboardPage />
          </ProtectedRoute>
        } 
      />
    </Routes>
  );
}
```

## 🔧 Özelleştirme

### Renk Teması Değiştirme
`src/styles/auth.css` dosyasında gradient ve renk değerlerini değiştirebilirsiniz:

```css
.auth-background {
  background: linear-gradient(135deg, 
    #0f172a 0%,    /* Dark Navy */
    #082f49 25%,   /* Deep Blue */
    #0c4a6e 50%,   /* Ocean Blue */
    #075985 75%,   /* Cyan Blue */
    #0f172a 100%   /* Dark Navy */
  );
}
```

### Form Validasyonu Ayarlama
`RegisterPage.jsx` içindeki `validateForm` fonksiyonunu düzenleyebilirsiniz:

```javascript
const validateForm = () => {
  // Minimum şifre uzunluğu
  if (password.length < 8) {
    setError('Şifre en az 8 karakter olmalıdır');
    return false;
  }
  
  // Özel validasyonlarınızı ekleyin
  // ...
};
```

## 🚀 Production Deployment

### Firebase Hosting'e Deploy

```bash
# Build oluştur
cd Pentagent/pentagent-frontend
npm run build

# Firebase'e deploy et
cd ..
firebase deploy
```

### Önemli Notlar
- Production'da mutlaka Firestore güvenlik kurallarını gözden geçirin
- Firebase Console'dan Authentication limitlerini kontrol edin
- Rate limiting ve abuse prevention ayarlarını yapın

## 📊 Veritabanı Yapısı

### users koleksiyonu
```
users/
  └── {userId}/
      ├── uid: string
      ├── email: string
      ├── displayName: string
      ├── createdAt: timestamp
      ├── lastLogin: timestamp
      ├── role: string ('user', 'admin')
      └── status: string ('active', 'inactive')
```

## 🐛 Hata Ayıklama

### Yaygın Hatalar

1. **"auth/operation-not-allowed"**
   - Firebase Console > Authentication > Sign-in method
   - Email/Password metodunu etkinleştirin

2. **"Missing or insufficient permissions"**
   - Firestore Database güvenlik kurallarını kontrol edin
   - Yukarıdaki güvenlik kurallarını ekleyin

3. **"Network request failed"**
   - İnternet bağlantınızı kontrol edin
   - Firebase config ayarlarını doğrulayın

## 📞 Destek

Herhangi bir sorun yaşarsanız:
1. Console'daki hata mesajlarını kontrol edin
2. Firebase Console > Authentication > Users bölümünden kullanıcıları görüntüleyin
3. Firestore Database'i kontrol edin

## 🎉 Başarılı Kurulum!

Artık projeniz Firebase Authentication ile entegre ve kullanıma hazır! 🚀





















