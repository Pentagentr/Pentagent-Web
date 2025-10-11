# CVE RAG Projesi - Proje Akış Diyagramı

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           CVE RAG PROJESİ - VERİ AKIŞI                        │
└─────────────────────────────────────────────────────────────────────────────────┘

📁 HAM VERİ TOPLAMA
┌─────────────────┐
│ ham_veriler/    │
│ ├─ nvdcve-2.0-  │
│ │   2022.json   │
│ ├─ nvdcve-2.0-  │
│ │   2023.json   │
│ └─ nvdcve-2.0-  │
│     2024.json   │
└─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🔄 VERİ ZENGİNLEŞTİRME VE TEMİZLEME SÜRECİ                                    │
└─────────────────────────────────────────────────────────────────────────────────┘

📄 jsonlar/veri_cekme.py
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 1. Ham CVE      │───▶│ 2. Akıllı      │───▶│ 3. En İyi      │
│    Verilerini   │    │    Referans    │    │    Referansı   │
│    Oku          │    │    Çekme       │    │    Seçme       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ • NVD JSON      │    │ • Trafilatura   │    │ • Tek Kaynak    │
│ • CVE Metadata  │    │ • BeautifulSoup │    │   Garantisi     │
│ • References    │    │ • URL Filtresi  │    │ • Kalite        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🧹 VERİ TEMİZLEME VE OPTİMİZASYON                                             │
└─────────────────────────────────────────────────────────────────────────────────┘

📄 veri_hazirlik/dataclean.py
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 1. Karmaşık     │───▶│ 2. RAG Formatı  │───▶│ 3. Metadata     │
│    JSON'u       │    │    Dönüşümü     │    │    Çıkarımı     │
│    Sadeleştir   │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ • CVE Objesi    │    │ • id, content,  │    │ • Severity      │
│ • Nested Data   │    │   metadata      │    │ • Attack Vector │
│ • References    │    │ • Qdrant Ready  │    │ • Base Score    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
📄 veri_hazirlik/veri-son-hazirlik.py
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 1. Dil Filtresi │───▶│ 2. Gürültü     │───▶│ 3. Final        │
│    (İngilizce)  │    │    Temizleme   │    │    Optimizasyon │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ • LangDetect    │    │ • PGP Temizleme │    │ • Paragraf      │
│ • EN Only       │    │ • Email Headers │    │   Tekrarı       │
│ • Quality Check │    │ • PoC Removal   │    │   Temizleme     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🤖 VEKTÖR ÜRETİMİ VE QDRANT ENTEGRASYONU                                      │
└─────────────────────────────────────────────────────────────────────────────────┘

📄 Qdrant/bge_vector_colab.py
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 1. BGE-M3       │───▶│ 2. Hybrid      │───▶│ 3. JSONL        │
│    Model        │    │    Vektörler   │    │    Format       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ • Dense Vectors │    │ • Dense +       │    │ • Batch         │
│ • Sparse Vectors│    │   Sparse        │    │   Processing    │
│ • ColBERT       │    │   Combined      │    │ • Fast I/O      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🐳 DOCKER VE QDRANT KURULUMU                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

📄 docker-compose.yml + setup_qdrant.sh
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 1. Docker       │───▶│ 2. Qdrant       │───▶│ 3. Health       │
│    Container    │    │    Başlatma     │    │    Check        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ • Port 6333     │    │ • Collection    │    │ • REST API      │
│ • Volume Mount  │    │   Creation      │    │ • Dashboard     │
│ • Config File   │    │ • Hybrid Setup  │    │ • Ready State   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
📄 Qdrant/upload.py
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 1. Vektör       │───▶│ 2. Batch        │───▶│ 3. Qdrant       │
│    Okuma        │    │    Upload       │    │    Storage      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ • JSONL Parse   │    │ • Parallel      │    │ • Dense Index    │
│ • Validation    │    │   Processing    │    │ • Sparse Index   │
│ • Error Handle  │    │ • Progress Bar  │    │ • Metadata      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🔍 HYBRID ARAMA SİSTEMİ VE WEB ARAYÜZÜ                                        │
└─────────────────────────────────────────────────────────────────────────────────┘

📄 Qdrant/hybrid_search.py
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 1. Query        │───▶│ 2. Dual        │───▶│ 3. Score        │
│    Processing   │    │    Search      │    │    Fusion       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ • BGE-M3        │    │ • Dense Search  │    │ • Weighted      │
│   Encoding      │    │ • Sparse Search │    │   Combination   │
│ • Vector        │    │ • Parallel      │    │ • Ranking       │
│   Generation    │    │   Execution     │    │ • Filtering     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
📄 Qdrant/web_app.py + templates/index.html
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ 1. Flask        │───▶│ 2. REST API     │───▶│ 3. Web UI      │
│    Server       │    │    Endpoints    │    │    Interface   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ • Port 5000     │    │ • /search       │    │ • Modern UI     │
│ • Auto-reload   │    │ • /cve/<id>     │    │ • Responsive    │
│ • Error Handle  │    │ • /health       │    │ • Real-time     │
└─────────────────┘    └─────────────────┘    └─────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│  📊 SONUÇ VE PERFORMANS                                                        │
└─────────────────────────────────────────────────────────────────────────────────┘

🎯 ANA ÖZELLİKLER:
• ✅ Hybrid Arama: Semantik + Keyword birleşimi
• ✅ BGE-M3 Modeli: Dense + Sparse vektörler
• ✅ Docker Entegrasyonu: Kolay kurulum ve yönetim
• ✅ Web Arayüzü: Modern ve kullanıcı dostu
• ✅ Batch Processing: Yüksek performans
• ✅ Error Handling: Güvenilir sistem
• ✅ Scalable: Büyük veri setleri için optimize

🚀 KULLANIM ADIMLARI:
1. ./setup_qdrant.sh          # Qdrant'ı Docker ile başlat
2. python Qdrant/upload.py     # Vektörleri yükle
3. python Qdrant/web_app.py   # Web arayüzünü başlat
4. http://localhost:5000       # Tarayıcıda aç

📈 PERFORMANS METRİKLERİ:
• Vektör Boyutu: 1024 (Dense) + Variable (Sparse)
• Batch Size: 256
• Search Types: Hybrid, Dense, Sparse
• Response Time: < 500ms (ortalama)
• Accuracy: Yüksek (BGE-M3 + Hybrid fusion)
```
