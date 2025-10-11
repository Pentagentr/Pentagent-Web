# 🛡️ Pentagent - AI-Powered Security Testing Platform

> Autonomous penetration testing platform powered by advanced AI and RAG-enhanced vulnerability intelligence.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18+-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/)

---

## 🎯 Overview

**Pentagent** is an autonomous security testing platform that combines:
- 🤖 **AI-Driven Testing** - Powered by Google Gemini for intelligent decision-making
- 🔍 **RAG-Enhanced Intelligence** - 95K+ CVE database with semantic search
- 🎨 **Modern Interface** - Real-time scanning with WebSocket updates
- 🛠️ **30+ Security Tools** - Automated vulnerability detection and verification

---

## ✨ Key Features

### 🤖 Autonomous AI Agent
- Dynamic orchestration with self-improving workflows
- Context-aware tool selection
- Real-time reasoning and decision-making
- Adaptive testing strategies

### 🔍 RAG CVE Intelligence
- **95,000+ CVE vectors** from NVD database
- **Hybrid search** (Dense 70% + Sparse 30%)
- **Semantic similarity** matching with BGE-M3 embeddings
- **Real-time suggestions** based on scan results

### 🛠️ Security Tools (30+)

**Enumeration:**
- Port Scanner (Nmap integration)
- Subdomain Bruteforcer
- Directory Bruteforce
- Web Crawler
- Technology Detector
- Firewall Detector

**Vulnerability Scanning:**
- SQL Injection Tester
- XSS Detector
- LFI/RFI Scanner
- IDOR Tester
- JWT Vulnerability Tester
- Dependency Scanner
- HTTP Header Analyzer

**Infrastructure:**
- Cloud S3 Bucket Scanner
- Exposed Admin Panel Finder
- API Endpoint Discovery

**Reconnaissance:**
- WHOIS Lookup
- DNS Analyzer
- Email Security Audit
- Historical Data Analyzer
- Origin IP Finder
- Passive Subdomain Finder

### 🎨 Modern UI/UX
- Real-time scan progress with WebSocket
- Interactive chat interface
- Context panel with live updates
- CVE suggestion sidebar
- Dedicated RAG search page
- Responsive design with dark theme

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│            SYSTEM ARCHITECTURE              │
└─────────────────────────────────────────────┘

React Frontend (Firebase Hosting)
    ↓ HTTPS / WebSocket
FastAPI Backend (Render.com)
    ├─ AI Orchestrator (Google Gemini)
    ├─ Security Tools (30+ modules)
    └─ RAG Service
        ↓ REST API
Qdrant Vector DB (HuggingFace Space)
    └─ 95K+ CVE Embeddings (BGE-M3)
```

---

## 🚀 Quick Start

### Local Development

**Prerequisites:**
- Python 3.11+
- Node.js 18+
- Docker (for Qdrant)

**1. Clone Repository**
```bash
git clone https://github.com/Pentagentr/Pentagent-Web.git
cd Pentagent-Web
```

**2. Start Qdrant (Optional - for RAG features)**
```bash
cd Rag-Pent
docker-compose up -d
cd ..
```

**3. Backend Setup**
```bash
# Install dependencies
pip install -r requirements.txt

# Set API key
export GEMINI_API_KEY="your_gemini_api_key"

# Start backend
python web_api.py
```

**4. Frontend Setup**
```bash
cd pentagent-frontend
npm install
npm run dev
```

**5. Access Application**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 🌐 Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete deployment guide.

**Stack:**
- **Frontend:** Firebase Hosting (Free)
- **Backend:** Render.com (Free)
- **Vector DB:** HuggingFace Space (Free)

**Total Cost:** $0 with free tiers

---

## 📖 Usage

### 1. Autonomous Pentest

1. Open the chat interface
2. Enter target URL
3. AI agent automatically:
   - Plans testing strategy
   - Executes security tools
   - Analyzes results
   - Generates comprehensive report

### 2. CVE Search

Navigate to `/rag-search` page:
- Search 95K+ CVE database
- Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)
- View related vulnerabilities
- Access NVD references

### 3. Scan Analysis

After pentest completion:
- View results in real-time
- Check CVE Suggestions tab
- Get relevant CVE recommendations
- Export detailed reports

---

## 🔧 Technology Stack

### Backend
- **Framework:** FastAPI (async Python)
- **AI:** Google Gemini API
- **Vector Store:** Qdrant
- **Embeddings:** BGE-M3 (BAAI)
- **WebSocket:** Native FastAPI support

### Frontend
- **Framework:** React 18
- **Build Tool:** Vite
- **Styling:** TailwindCSS
- **Routing:** React Router
- **State:** React Hooks

### Infrastructure
- **Hosting:** Firebase Hosting + Render.com
- **Vector DB:** HuggingFace Spaces (Docker)
- **CI/CD:** GitHub integration

---

## 📊 RAG System

### CVE Database
- **Total CVEs:** 95,237 (NVD 2022-2024)
- **Embedding Model:** BGE-M3 (1024 dimensions)
- **Search Type:** Hybrid (Dense + Sparse)
- **Response Time:** <300ms average

### Search Capabilities
- Semantic similarity matching
- Keyword-based search
- Severity filtering
- CVSS score integration
- Attack vector classification

**Learn more:** [RAG_INTEGRATION_README.md](RAG_INTEGRATION_README.md)

---

## 🔒 Security & Compliance

### Best Practices
- All API keys stored as environment variables
- CORS protection with whitelist
- WebSocket authentication
- Private vector database option
- Input validation and sanitization

### Responsible Use
⚠️ **Important:** This tool is for authorized security testing only.
- Always obtain proper authorization
- Follow responsible disclosure practices
- Comply with local laws and regulations
- Use in controlled environments

---

## 📁 Project Structure

```
Pentagent/
├── agent_core/              # AI orchestration logic
│   ├── dynamic_orchestrator.py
│   ├── planner.py
│   ├── analyzer.py
│   └── executor.py
├── tools/                   # Security testing modules (30+)
├── services/               
│   └── rag_service.py      # RAG integration
├── Rag-Pent/               # Vector database system
│   └── Qdrant/             # Search engine
├── pentagent-frontend/     # React application
│   ├── src/
│   │   ├── pages/          # ChatPage, RagSearch
│   │   ├── components/     # Reusable UI components
│   │   └── services/       # API integration
├── web_api.py              # FastAPI backend
├── config.py               # Configuration
└── requirements.txt        # Python dependencies
```

---

## 🚀 Features Roadmap

### Current Features ✅
- [x] Autonomous AI-driven pentesting
- [x] 30+ integrated security tools
- [x] Real-time WebSocket updates
- [x] RAG-enhanced CVE search
- [x] Interactive chat interface
- [x] Context-aware scanning

### Planned Features 🔮
- [ ] Multi-target scanning
- [ ] Custom tool integration
- [ ] Advanced reporting (PDF/CSV export)
- [ ] Scan history and bookmarks
- [ ] Team collaboration features
- [ ] API rate limiting
- [ ] Enhanced caching

---

## 📚 Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
- [RAG_INTEGRATION_README.md](RAG_INTEGRATION_README.md) - RAG system details
- [LICENSE](LICENSE) - Apache 2.0 License

---

## 🤝 Contributing

Contributions are welcome! This is an open-source project.

**How to contribute:**
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📝 License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

**Key points:**
- ✅ Commercial use allowed
- ✅ Modification allowed
- ✅ Distribution allowed
- ✅ Patent use allowed
- ⚠️ Liability and warranty disclaimers apply

---

## 🙏 Acknowledgments

- **Google Gemini** - AI orchestration
- **Qdrant** - Vector database
- **BAAI BGE-M3** - Embedding model
- **NVD/MITRE** - CVE data
- **FastAPI** - Backend framework
- **React** - Frontend framework

---

## 📞 Contact & Support

- **GitHub:** [@Pentagentr](https://github.com/Pentagentr)
- **Repository:** [Pentagent-Web](https://github.com/Pentagentr/Pentagent-Web)
- **Issues:** [GitHub Issues](https://github.com/Pentagentr/Pentagent-Web/issues)

---

## ⚠️ Disclaimer

This tool is designed for **authorized security testing only**. Users are responsible for:
- Obtaining proper authorization before testing
- Complying with applicable laws and regulations
- Using the tool ethically and responsibly

The developers assume no liability for misuse.

---

**Built with ❤️ for the security community**
