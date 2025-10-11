# 🎨 Pentagent Frontend

Modern React.js tabanlı web arayüzü ile Pentagent'ın güçlü güvenlik testi özelliklerini kullanın.

## ✨ Özellikler

- 🚀 **Real-time Chat**: AI ile gerçek zamanlı etkileşim
- 📊 **Live Dashboard**: Canlı güvenlik testi durumu
- 🎯 **Target Management**: Hedef yönetimi
- 📈 **Analytics**: Detaylı analiz ve raporlama
- 🌙 **Dark Mode**: Karanlık tema desteği
- 📱 **Responsive**: Mobil uyumlu tasarım

## 🚀 Hızlı Başlangıç

### Gereksinimler
- Node.js 16+
- npm veya yarn

### Kurulum

1. **Bağımlılıkları yükleyin:**
```bash
npm install
```

2. **Geliştirme sunucusunu başlatın:**
```bash
npm run dev
```

3. **Tarayıcıda açın:**
```
http://localhost:3000
```

## 🛠️ Komutlar

```bash
# Geliştirme
npm run dev

# Build
npm run build

# Preview
npm run preview

# Lint
npm run lint

# Test
npm run test
```

## 🏗️ Proje Yapısı

```
src/
├── components/          # React bileşenleri
│   ├── chat/           # Chat arayüzü
│   ├── dashboard/      # Dashboard bileşenleri
│   ├── common/         # Ortak bileşenler
│   └── layout/         # Layout bileşenleri
├── pages/              # Sayfa bileşenleri
├── services/           # API servisleri
├── styles/             # CSS dosyaları
└── utils/              # Yardımcı fonksiyonlar
```

## 🎨 Bileşenler

### Chat Interface
- Real-time AI chat
- Tool execution status
- Streaming responses
- Message history

### Dashboard
- Security metrics
- Active scans
- Vulnerability charts
- AI recommendations

### Common Components
- Button, Input, Card
- Loading animations
- Status indicators

## 🔧 Konfigürasyon

### Environment Variables
```bash
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

### API Integration
```javascript
// services/api.js
export const api = {
  chat: {
    send: (message) => fetch('/api/chat', { method: 'POST', body: JSON.stringify(message) })
  }
}
```

## 🎯 Kullanım

### 1. Chat Mode
- AI ile doğrudan etkileşim
- Güvenlik testi komutları
- Real-time sonuçlar

### 2. Dashboard Mode
- Görsel analiz
- Metrikler ve grafikler
- Rapor görüntüleme

### 3. Target Management
- Hedef ekleme/düzenleme
- Test geçmişi
- Sonuç karşılaştırma

## 🚀 Deployment

### Vercel
```bash
npm run build
vercel --prod
```

### Netlify
```bash
npm run build
netlify deploy --prod --dir=dist
```

### Docker
```dockerfile
FROM node:16-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun
3. Değişikliklerinizi commit edin
4. Pull request oluşturun

## 📝 Lisans

MIT License - Detaylar için `LICENSE` dosyasına bakın.

---

**🎨 Pentagent Frontend** - Modern, hızlı ve kullanıcı dostu güvenlik testi arayüzü
