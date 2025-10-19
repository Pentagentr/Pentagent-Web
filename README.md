# 🛡️ Pentagent - Yapay Zeka Destekli Güvenlik Test Platformu

<div align="center">

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![React](https://img.shields.io/badge/react-18+-61dafb.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)

**Pentagent**, güvenlik testlerini otomatikleştiren, yapay zeka ile güçlendirilmiş, yeni nesil bir penetrasyon testi platformudur.

[Özellikler](#-özellikler) •
[Kurulum](#-kurulum) •
[Kullanım](#-kullanım) •
[Mimarı](#-mimari) •
[Katkıda Bulun](#-katkıda-bulunma)

</div>

---

## 🎯 Genel Bakış

**Pentagent**, siber güvenlik uzmanları için geliştirilmiş, tamamen otonom bir penetrasyon testi platformudur:

- 🤖 **AI Destekli Karar Alma** - GPT OSS 120B modeli ile akıllı test stratejileri
- 🔍 **RAG Entegrasyonu** - 95,000+ CVE veritabanı ile anlık zafiyet analizi (HuggingFace Space: [Pentagent Qdrant](https://huggingface.co/spaces/meryemarpaci/pentagent-qdrant))
- 🎯 **Reranker Optimizasyonu** - mixedbread-ai/mxbai-rerank-base-v1 ile 10x score boost
- 📊 **Dinamik Risk Skoru** - Tool çıktılarına dayalı akıllı risk hesaplama
- 📊 **Otomatik Raporlama** - PDF/TXT/JSON/MD formatlarında LLM-destekli profesyonel raporlar
- 🎨 **Modern Arayüz** - Real-time WebSocket güncellemeleri ile kullanıcı dostu UI
- 🛠️ **30+ Güvenlik Aracı** - Kapsamlı zafiyet tespit ve doğrulama araçları

---

## ✨ Temel Özellikler

### 🤖 Yapay Zeka Odaklı Test
- **Otonom Karar Mekanizması**: AI, hedef sistemi analiz eder ve en uygun test stratejisini belirler
- **Dinamik Orkestrasyon**: Tool seçimi ve sıralama yapay zeka tarafından optimize edilir
- **Hata Yönetimi**: Başarısız araçlar için otomatik fallback stratejileri

### 🔍 RAG (Retrieval-Augmented Generation) Sistemi
- **95K+ CVE Veritabanı**: MITRE ve NVD kaynaklı güncel zafiyet bilgileri
- **HuggingFace Space**: Deployed on [meryemarpaci/pentagent-qdrant](https://huggingface.co/spaces/meryemarpaci/pentagent-qdrant)
- **Semantik Arama**: BGE-M3 embeddings ile anlam tabanlı CVE eşleştirme
- **Reranker Entegrasyonu**: mixedbread-ai/mxbai-rerank-base-v1 ile 10x score boost
- **Sorgu Optimizasyonu**: GPT OSS 120B ile kullanıcı sorgularının otomatik iyileştirilmesi
- **Hızlı Yanıt**: Hybrid scoring (15% vector + 85% reranker) ile <500ms yanıt süresi
- **Graceful Fallback**: Reranker API hataları için otomatik fallback mekanizması

### 📊 Raporlama Sistemi
- **RAG-Entegreli Raporlar**: En alakalı CVE'ler otomatik olarak rapora eklenir
- **LLM-Enhanced Reports**: LLM ile AI-destekli rapor oluşturma
- **Dinamik Risk Skoru**: Tool çıktılarına göre (endpoints, forms, ports) akıllı skorlama
- **CVSS Detayları**: Her CVE için CVSS skoru, vektör ve detaylı açıklama
- **Çoklu Format**: PDF, TXT, JSON ve Markdown formatlarında export
- **OWASP Uyumlu**: OWASP Top 10 kategorilerine göre sınıflandırma
- **Kurumsal Tasarım**: Profesyonel raporlama

### 🛠️ Güvenlik Araçları (30+)
**Keşif & Tarama:**
- Port Scanner (SYN/Connect/UDP)
- Subdomain Enumeration (passive + bruteforce)
- Web Crawler (Selenium + BeautifulSoup)
- Technology Detection (Wappalyzer benzeri)
- Directory Bruteforce

**Zafiyet Tespiti:**
- SQL Injection Scanner
- XSS Detector (HTTP + Selenium)
- IDOR Tester
- LFI/RFI Scanner
- JWT Vulnerability Checker

**Altyapı Analizi:**
- Firewall Detector
- Origin IP Finder (CDN bypass)
- HTTP Header Analyzer
- Exposed Panel Finder
- Cloud Bucket Scanner (S3/GCS/Azure)

**Recon & Intelligence:**
- WHOIS Lookup
- DNS Analyzer
- Email Security Audit
- Historical Data Analyzer
- Code Intelligence Scanner

---

## 🏗️ Sistem Mimarisi

```
┌──────────────────────────────────────────────────────┐
│              PENTAGENT MİMARİSİ                     │
└──────────────────────────────────────────────────────┘

React Frontend (Firebase Hosting)
    ↓ HTTPS / WebSocket
FastAPI Backend (Render.com)
    ├─ AI Orchestrator (GPT OSS 120B)
    │   ├─ Dynamic Tool Selection
    │   ├─ Strategy Planning
    │   └─ Error Recovery
    │
    ├─ Security Tools (25 modules)
    │   ├─ Recon Tools
    │   ├─ Scanning Tools
    │   ├─ Verification Tools
    │   └─ Analysis Tools
    │
    ├─ Report Generator
    │   ├─ Dynamic Risk Score Calculator
    │   ├─ LLM-Enhanced MD Reports
    │   └─ Multi-Format Export (PDF/TXT/JSON/MD)
    │
    └─ RAG Service
        ↓ REST API
Qdrant Vector DB (HuggingFace Space: meryemarpaci/pentagent-qdrant)
    ├─ 95K+ CVE Embeddings (BGE-M3)
    ├─ Hybrid Search (Sparse + Dense)
    └─ Reranker (mixedbread-ai/mxbai-rerank-base-v1)
```

### 🔄 RAG İş Akışı

```
1. Kullanıcı Sorgusu → GPT OSS 120B Optimizasyonu
2. Optimize Sorgu → BGE-M3 Embedding
3. Hybrid Search → Qdrant (Sparse 40% + Dense 60%, Top 20 sonuç)
4. Reranking → mixedbread-ai/mxbai-rerank-base-v1 (10x score boost)
5. Hybrid Scoring → 15% vector + 85% reranker (boosted)
6. Final Results → En alakalı CVE'ler (CVSS detayları ile)
7. Graceful Fallback → Reranker hatası durumunda orijinal sıralama
```

### 🎯 Risk Skoru Hesaplama (Yeni)

```
Tool Çıktılarına Dayalı Dinamik Skorlama:
├─ Severity Ağırlıkları
│   ├─ Critical: +15
│   ├─ High: +10
│   ├─ Medium: +5
│   └─ Low/Info: +2/+1
│
├─ Tool Çıktısı Bonusları
│   ├─ 50+ endpoints → +30 (kritik saldırı yüzeyi)
│   ├─ 10+ forms → +25 (injection riski)
│   ├─ 20+ subdomains → +20 (geniş yüzey)
│   ├─ 10+ open ports → +20
│   └─ Critical dirs (admin, config) → +20
│
├─ Gerçek Zafiyet Bulguları
│   └─ SQL/XSS/RCE → +20 each (max +50)
│
└─ Kritik Yol/Endpoint
    └─ admin, login, api → +20 (5+ adet)

Sonuç: 0-100 arası normalize skor, minimum 15 (bulgu varsa)
```

---

## 🚀 Hızlı Başlangıç

### Gereksinimler

**Backend:**
- Python 3.9+
- FastAPI
- Qdrant (HuggingFace Space veya local)

**Frontend:**
- Node.js 16+
- React 18+
- Vite

**API Keys:**
- `GROQ_API_KEY` - GPT OSS 120B için
- `HUGGINGFACE_TOKEN` - RAG servisi için 

### 📦 Kurulum

#### 1. Projeyi Klonlayın

```bash
git clone https://github.com/Pentagentr/Pentagent-Web.git
cd Pentagent-Web
```

#### 2. Backend Kurulumu

```bash
# Python sanal ortamı oluştur
python -m venv venv

# Sanal ortamı aktif et
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# Ortam değişkenlerini ayarla
# .env dosyası oluştur ve aşağıdaki değerleri ekle:
```

**.env Örneği:**
```env
# Zorunlu
GROQ_API_KEY=your_groq_api_key_here
MODEL_PROVIDER=groq
GROQ_MODEL=gpt-4o

# RAG Sistemi (Opsiyonel)
HUGGINGFACE_TOKEN=your_hf_token_here
QDRANT_HOST=https://your-qdrant-space.hf.space
EMBEDDING_API_URL=https://your-embedding-space.hf.space/embed

# Reranker (Opsiyonel - varsayılan değerler)
USE_RERANKER=true
RERANKER_MODEL=mixedbread-ai/mxbai-rerank-base-v1
RERANKER_TOP_K=5

# Server
PORT=8000
ALLOWED_ORIGINS=http://localhost:5173,https://your-frontend.web.app
```

```bash
# Backend'i başlat
python web_api.py
```

Backend şimdi `http://localhost:8000` adresinde çalışıyor.

#### 3. Frontend Kurulumu

```bash
# Frontend dizinine geç
cd pentagent-frontend

# Bağımlılıkları yükle
npm install

# Ortam değişkenlerini ayarla
# .env.local dosyası oluştur:
```

**.env.local Örneği:**
```env
VITE_API_URL=http://localhost:8000
VITE_FIREBASE_API_KEY=your_firebase_api_key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
```

```bash
# Development sunucusunu başlat
npm run dev
```

Frontend şimdi `http://localhost:5173` adresinde çalışıyor.

#### 4. Firebase Deployment (Opsiyonel)

```bash
# Firebase CLI'yi yükle
npm install -g firebase-tools

# Firebase'e giriş yap
firebase login

# Projeyi başlat (ilk defa)
firebase init hosting

# Build oluştur
npm run build

# Deploy et
firebase deploy --only hosting
```

**firebase.json Yapılandırması:**
```json
{
  "hosting": {
    "public": "dist",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ]
  }
}
```

---

## 💻 Kullanım

### 1. Temel Tarama

```bash
# Web arayüzünde
1. http://localhost:5173 adresine git
2. Giriş yap veya kayıt ol
3. Chat sayfasında hedef ve isteğini gir: "example.com sitesini taramanı istiyorum"
4. AI otomatik olarak uygun araçları seçer ve taramayı başlatır
```

### 2. RAG CVE Araması

```python
# Programatik kullanım
from services.rag_service import get_rag_service

rag = get_rag_service()

# CVE ara
results = rag.search_cve("SQL injection", limit=5)

for cve in results:
    print(f"CVE: {cve.cve_id}")
    print(f"CVSS: {cve.base_score}")
    print(f"Severity: {cve.severity}")
    print(f"Match Score: {cve.score}")
```

### 3. Rapor Oluşturma

```bash
# Web arayüzünde
1. Tarama tamamlandıktan sonra
2. Sağ panelde "Generate Report" butonuna tıkla
3. Rapor otomatik olarak oluşturulur (PDF/TXT/JSON)
4. "Download" butonu ile indir
```

### 4. API Kullanımı

```python
import requests

# Tarama başlat
response = requests.post("http://localhost:8000/api/scan", json={
    "target": "example.com",
    "task": "Kapsamlı güvenlik testi yap"
})

scan_id = response.json()["scan_id"]

# RAG CVE ara
response = requests.post("http://localhost:8000/api/rag/search", json={
    "query": "SQL injection WordPress",
    "limit": 5,
    "severity": "CRITICAL"
})

cves = response.json()["results"]

# Rapor oluştur
response = requests.post("http://localhost:8000/api/generate-report", json={
    "target": "example.com",
    "scan_results": {"vulnerabilities": [...]},
    "cve_results": cves[:3]
})

report = response.json()
```

---

## 🔧 Teknoloji Stack

### Backend
- **Framework:** FastAPI (async Python)
- **AI Model:** GPT OSS 120B (Groq API) + Gemini fallback
- **Vector Store:** Qdrant ([HuggingFace Space](https://huggingface.co/spaces/meryemarpaci/pentagent-qdrant))
- **Embeddings:** BGE-M3 (BAAI/bge-m3, 1024-dim)
- **Reranker:** mixedbread-ai/mxbai-rerank-base-v1 (10x score boost)
- **WebSocket:** Native FastAPI support with error handling
- **PDF Generation:** ReportLab
- **LLM Reports:** Gemini/Groq for AI-enhanced markdown reports

### Frontend
- **Framework:** React 18
- **Build Tool:** Vite
- **Styling:** TailwindCSS + Custom CSS
- **State Management:** Context API
- **Routing:** React Router v6
- **Icons:** Lucide React
- **Deploy:** Firebase Hosting

### Veritabanı & ML
- **Vector DB:** Qdrant ([Deployed on HuggingFace](https://huggingface.co/spaces/meryemarpaci/pentagent-qdrant))
- **Embedding Model:** BAAI/bge-m3 (1024-dim, hybrid scoring)
- **Reranker Model:** mixedbread-ai/mxbai-rerank-base-v1 (10x boost + fallback)
- **LLM:** GPT OSS 120B 
- **CVE Data:** MITRE + NVD (95,000+ records)
- **Risk Scoring:** Dynamic tool-based calculation

---

## 📊 Performans Metrikleri

| Metrik | Değer | Açıklama |
|--------|-------|----------|
| RAG Yanıt Süresi | <500ms | Reranker dahil ortalama süre |
| CVE Veritabanı | 95,000+ | MITRE ve NVD kaynakları |
| Embedding Boyutu | 1024-dim | BGE-M3 vektör boyutu |
| Reranker Score Boost | 10x | mixedbread-ai model ile boost |
| Hybrid Scoring | 15/85 | Vector (15%) vs Reranker (85%) ağırlığı |
| Reranker Fallback | ✅ | Graceful degradation on API errors |
| Risk Score Accuracy | Dynamic | Tool output-based calculation |
| Tool Success Rate | ~85% | Ortalama başarı oranı |
| LLM Token Optimization | 60% | Prompt size reduction (3000→1500 words) |

---

## 🗂️ Proje Yapısı

```
Pentagent/
├── agent_core/              # AI orkestrasyonu
│   ├── dynamic_orchestrator.py  # Ana AI karar motoru
│   ├── planner.py               # Strateji planlayıcı
│   ├── analyzer.py              # Sonuç analizörü
│   ├── report_generator.py      # RAG-entegreli raporlama
│   └── state.py                 # Durum yönetimi
│
├── tools/                   # Güvenlik araçları (30+)
│   ├── enum_*.py           # Keşif araçları
│   ├── verify_*.py         # Doğrulama araçları
│   ├── recon_*.py          # Recon araçları
│   └── vuln_*.py           # Zafiyet tarayıcıları
│
├── services/               # Servisler
│   └── rag_service.py      # RAG + Reranker sistemi
│
├── mcp_server/            # Tool registry
│   ├── tool_registry.py    # Merkezi tool kaydı
│   └── enhanced_mcp_tools.py
│
├── pentagent-frontend/    # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/          # Chat arayüzü
│   │   │   ├── reports/       # Rapor görüntüleme
│   │   │   ├── layout/        # Layout bileşenleri
│   │   │   └── common/        # Ortak bileşenler
│   │   ├── pages/
│   │   │   ├── ChatPage.jsx   # Ana pentest sayfası
│   │   │   ├── Reports.jsx    # Rapor sayfası
│   │   │   └── RagSearch.jsx  # RAG arama sayfası
│   │   ├── services/
│   │   │   └── pentagentAPI.js # Backend API client
│   │   └── contexts/
│   │       └── AuthContext.jsx # Auth yönetimi
│   └── dist/              # Build output
│
├── reports/               # Oluşturulan raporlar
├── logs/                  # Sistem logları
├── web_api.py            # FastAPI backend server
├── config.py             # Konfigürasyon
├── requirements.txt      # Python bağımlılıkları
└── README.md            # Bu dosya
```

---

## 🔐 Güvenlik Notları

- ✅ Kendi sistemlerinizi test edin
- ✅ Yazılı izin alınmış sistemleri test edin
- ✅ CTF ve eğitim ortamlarında kullanın
- ❌ İzinsiz sistemlere karşı kullanmayın
- ❌ Sistem kaynaklarını kötüye kullanmayın

---

## 📈 Roadmap

### v2.0 (Mevcut) ✅
- [x] RAG sistemi entegrasyonu (HuggingFace Space)
- [x] mixedbread-ai/mxbai-rerank-base-v1 optimizasyonu (10x boost)
- [x] GPT OSS 120B model entegrasyonu
- [x] Dinamik risk skoru hesaplama (tool-based)
- [x] LLM-enhanced markdown raporlar
- [x] Otomatik rapor oluşturma (PDF/TXT/JSON/MD)
- [x] 30+ güvenlik aracı
- [x] WebSocket real-time updates + error handling
- [x] Graceful fallback mekanizmaları (Reranker, LLM)
- [x] Token optimization (60% azaltma)

### v2.1 (Planlanan) 🚧
- [ ] Multi-target scanning
- [ ] Custom wordlist yönetimi
- [ ] Export to Burp Suite
- [ ] Scheduled scans
- [ ] Email bildirimler

### v3.0 (Gelecek) 🔮
- [ ] Machine learning CVE predictor
- [ ] Exploit generator
- [ ] API fuzzing
- [ ] Mobile app security
- [ ] Cloud security scanner

---

## 📄 Lisans

Bu proje Apache License 2.0 altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

**Öne Çıkan Özellikler:**
- ✅ Ticari kullanım izni
- ✅ Değişiklik yapma izni
- ✅ Dağıtım izni
- ✅ Patent kullanım izni
- ⚠️ Sorumluluk ve garanti feragati

---

## 🙏 Teşekkürler

- **GPT OSS 120B** - AI reasoning modeli (Groq API üzerinden)
- **Qdrant** - Vector database motoru ([HuggingFace Space deployment](https://huggingface.co/spaces/meryemarpaci/pentagent-qdrant))
- **BAAI** - BGE-M3 embeddings
- **mixedbread-ai** - mxbai-rerank-base-v1 reranker model
- **HuggingFace** - Model hosting & inference API
- **NVD/MITRE** - CVE veri kaynağı
- **FastAPI** - High-performance backend framework
- **React** - Modern frontend framework
- **Firebase** - Frontend hosting & authentication

---

Made with by Pentagent

</div>
