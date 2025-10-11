# 🛡️ Pentagent - AI-Powered Autonomous Penetration Testing Framework

Pentagent, yapay zeka destekli otonom penetrasyon testi gerçekleştiren gelişmiş bir güvenlik testi çerçevesidir. OWASP Top 10 zafiyetlerini tespit eder, teknoloji stack'lerini analiz eder ve kapsamlı güvenlik raporları oluşturur.

## ✨ Özellikler

-  **AI-Powered**: Yapay zeka destekli otonom karar verme
-  **Comprehensive Scanning**: OWASP Top 10 zafiyet taraması
<<<<<<< HEAD
-  **25+ Security Tools**: Kapsamlı güvenlik araçları koleksiyonu
=======
-  **28+ Security Tools**: Kapsamlı güvenlik araçları koleksiyonu
>>>>>>> 01c0227 (Add RAG integration and HuggingFace Space support)
-  **Real-time Analysis**: Gerçek zamanlı analiz ve raporlama
-  **Web Interface**: Modern React.js web arayüzü
-  **RAG Integration**: Retrieval Augmented Generation desteği
-  **Dynamic Recommendations**: Dinamik öneri sistemi
-  **403 Bypass**: Cloudflare ve bot korumasını aşma
-  **Multi-layer Reconnaissance**: Pasif ve aktif keşif teknikleri
-  **Cloud Security**: AWS, Azure, Google Cloud güvenlik testleri
-  **API Security**: REST/GraphQL API güvenlik analizi
-  **Responsive Design**: Mobil uyumlu modern arayüz
-  **WebSocket Support**: Gerçek zamanlı iletişim
-  **Live AI Thinking**: Canlı AI düşünce süreçleri
-  **Agentic Workflow**: Tam otonom penetrasyon testi

## 🚀 Hızlı Başlangıç

### Gereksinimler

- Python 3.8+
- Node.js 16+ (Frontend için)
- Chrome/Chromium (Selenium için)

### Kurulum

1. **Repository'yi klonlayın:**
```bash
git clone https://github.com/Pentagentr/Pentagent-Web.git
cd Pentagent-Web
```

2. **Backend bağımlılıklarını yükleyin:**
```bash
pip install -r requirements.txt
```

3. **Frontend bağımlılıklarını yükleyin:**
```bash
cd pentagent-frontend
npm install
```

### Kullanım

#### 🚀 Hızlı Başlatma (Önerilen)

**Linux/Mac:**
```bash
chmod +x quick_start.sh
./quick_start.sh
```

**Windows:**
```cmd
quick_start.bat
```

#### 🔧 Manuel Başlatma

**1. Web Interface (Önerilen)**
```bash
# Terminal 1: Backend
python web_api.py

# Terminal 2: Frontend
cd pentagent-frontend
npm run dev
```

**2. Debug Testi**
```bash
python debug_pentagent.py
```

**3. Autonomous Chat Testi**
```bash
python autonomous_chat.py
```

**4. CLI Mode**
```bash
python pentagent_cli.py --target example.com
```

#### 🌐 Erişim
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **Health Check**: http://localhost:8000/health

## 🛠️ Araçlar (25+ Security Tools)

### 🔍 Discovery & Enumeration
- `enum_tech_detector` - Teknoloji stack analizi (WordPress, Drupal, Node.js, etc.)
- `enum_port_scanner` - Port taraması ve servis keşfi
- `enum_web_crawler` - Web crawling ve endpoint keşfi
- `enum_directory_bruteforce` - Dizin ve dosya keşfi
- `enum_subdomain_bruteforcer` - Subdomain brute force saldırısı
- `enum_firewall_detector` - Firewall ve güvenlik duvarı tespiti

### 🛡️ Vulnerability Assessment
- `verify_sqli` - SQL Injection testi ve exploit
- `verify_xss` - Cross-Site Scripting (XSS) testi
- `verify_lfi` - Local File Inclusion (LFI) testi
- `vuln_http_header_analyzer` - HTTP header güvenlik analizi
- `vuln_idor_tester` - IDOR (Insecure Direct Object Reference) testi
- `vul_depency_scanner` - Dependency ve bağımlılık zafiyet taraması

### 🔎 Reconnaissance & Intelligence
- `recon_passive_subfinder_tool` - Pasif subdomain keşfi
- `recon_whois_tool` - WHOIS bilgi analizi
- `recon_dns_analyzer` - DNS kayıt analizi ve keşfi
- `recon_origin_ip_finder` - Origin IP keşfi ve CDN bypass
- `recon_api_endpoint_finder` - API endpoint keşfi
- `rec_intel_code_scanner` - Kaynak kod analizi
- `rec_intel_historical_analyzer` - Tarihsel veri analizi
- `rec_audit_email_security` - Email güvenlik denetimi

### 🌐 API Security Testing
- `api_finder_active` - Aktif API keşfi
- `api_vuln_idor_scanner` - API IDOR zafiyet taraması
- `api_vuln_jwt_tester` - JWT token güvenlik testi

### ☁️ Cloud & Infrastructure Security
- `cloud_s3_bucket_scanner` - AWS S3 bucket güvenlik taraması
- `infra_exposed_panels_finder` - Açık admin panelleri keşfi

## 🏗️ Mimari

```
pentagent/
├── 🧠 agent_core/           # AI beyin merkezi
│   ├── dynamic_orchestrator.py  # Ana karar verme sistemi
│   ├── planner.py               # Stratejik planlama
│   ├── executor.py              # Tool yürütme
│   ├── analyzer.py              # Sonuç analizi
│   └── state.py                 # Hafıza yönetimi
├── 🛠️ tools/                # 28+ güvenlik aracı
├── 🌐 pentagent-frontend/   # React.js web arayüzü
├── 📊 reports/              # Güvenlik raporları
└── 🔧 mcp_server/           # Tool koordinasyonu
```

## 📊 Raporlama

Pentagent, aşağıdaki formatlarda raporlar oluşturur:

- **JSON**: Yapılandırılmış veri
- **PDF**: Detaylı güvenlik raporu
- **HTML**: Web tabanlı rapor
- **CSV**: Veri analizi için

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

## 🔧 Sorun Giderme

### Bağlantı Sorunları

**WebSocket Bağlantı Hatası:**
```bash
# Bağlantı testi yapın
python test_connection.py

# Port kontrolü
netstat -an | grep 8000
```

**Frontend Bağlantı Sorunu:**
```bash
# Frontend yeniden başlatın
cd pentagent-frontend
npm run dev
```

**Backend Başlatma Hatası:**
```bash
# Dependencies kontrolü
pip install -r requirements.txt

# Port kontrolü
lsof -i :8000
```

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

## 📊 Proje İstatistikleri

### 🛠️ Geliştirilen Araçlar
- ✅ **25+ Security Tools** - Kapsamlı güvenlik araçları koleksiyonu
- ✅ **6 Kategori** - Discovery, Vulnerability, Reconnaissance, API, Cloud, Infrastructure
- ✅ **AI-Powered** - Yapay zeka destekli otonom karar verme
- ✅ **Real-time** - Gerçek zamanlı analiz ve raporlama

### 🛡️ Güvenlik Yetenekleri
- ✅ **OWASP Top 10** - Tüm kritik zafiyetler
- ✅ **403 Bypass** - Cloudflare ve bot korumasını aşma
- ✅ **Multi-layer Recon** - Pasif ve aktif keşif teknikleri
- ✅ **API Security** - REST/GraphQL API güvenlik analizi
- ✅ **Cloud Security** - AWS, Azure, Google Cloud testleri

---

**⚠️ Uyarı**: Bu araç sadece eğitim ve yetkili güvenlik testleri için tasarlanmıştır. Kötü niyetli kullanım yasaktır.
