# 🛡️ Pentagent - AI-Powered Security Testing Platform

<div align="center">

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![React](https://img.shields.io/badge/react-18+-61dafb.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)

**Pentagent** is an AI-powered, next-generation penetration testing platform that automates security testing with advanced artificial intelligence.

[Features](#-features) •
[Installation](#-installation) •
[Usage](#-usage) •
[Architecture](#-architecture) •

</div>

---

## 🎯 Overview

**Pentagent** is a fully autonomous penetration testing platform designed for cybersecurity professionals:

- 🤖 **AI-Driven Decision Making** - Intelligent test strategies with GPT OSS 120B model
- 🔍 **RAG Integration** - Real-time vulnerability analysis with 95,000+ CVE database (HuggingFace Space: [Pentagent Qdrant](https://huggingface.co/spaces/meryemarpaci/pentagent-qdrant))
- 🎯 **Reranker Optimization** - 10x score boost with mixedbread-ai/mxbai-rerank-base-v1
- 📊 **Dynamic Risk Scoring** - Intelligent risk calculation based on tool outputs
- 📊 **Automated Reporting** - LLM-powered professional reports
- 🎨 **Modern Interface** - User-friendly UI with real-time WebSocket updates
- 🛠️ **30+ Security Tools** - Comprehensive vulnerability detection and validation tools

---

## ✨ Key Features

### 🤖 AI-Focused Testing
- **Autonomous Decision Mechanism**: AI analyzes target systems and determines optimal test strategies
- **Dynamic Orchestration**: Tool selection and sequencing optimized by artificial intelligence
- **Error Management**: Automatic fallback strategies for failed tools

### 🔍 RAG (Retrieval-Augmented Generation) System
- **95K+ CVE Database**: Up-to-date vulnerability information from NVD sources
- **Docker Deployment**: Local database setup
- **HuggingFace Space**: Deployed on [meryemarpaci/pentagent-qdrant](https://huggingface.co/spaces/meryemarpaci/pentagent-qdrant)
- **Semantic Search**: Meaning-based CVE matching with BGE-M3 embeddings
- **Reranker Integration**: 10x score boost with mixedbread-ai/mxbai-rerank-base-v1
- **Query Optimization**: Automatic query improvement with GPT OSS 120B
- **Fast Response**: <500ms response time with hybrid scoring (15% vector + 85% reranker)
- **Graceful Fallback**: Automatic fallback mechanism for Reranker API errors

### 📊 Reporting System
- **RAG-Integrated Reports**: Most relevant CVEs automatically added to reports
- **LLM-Enhanced Reports**: AI-powered report generation with LLM
- **Dynamic Risk Scoring**: Intelligent scoring based on tool outputs (endpoints, forms, ports)
- **CVSS Details**: CVSS score, vector, and detailed description for each CVE
- **Multi-Format Export**: PDF, TXT, JSON, and Markdown formats
- **OWASP Compliant**: Classification according to OWASP Top 10 categories
- **Professional Design**: Enterprise-grade reporting

### 🛠️ Security Tools (25)
**Discovery & Scanning:**
- Port Scanner (SYN/Connect/UDP)
- Subdomain Enumeration (passive + bruteforce)
- Web Crawler (Selenium + BeautifulSoup)
- Technology Detection (Wappalyzer-like)
- Directory Bruteforce

**Vulnerability Detection:**
- SQL Injection Scanner
- XSS Detector (HTTP + Selenium)
- IDOR Tester
- LFI/RFI Scanner
- JWT Vulnerability Checker

**Infrastructure Analysis:**
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

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────┐
│              PENTAGENT ARCHITECTURE                 │
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
    │   └─ LLM-Enhanced MD Reports
    │
    └─ RAG Service
        ↓ REST API
Docker Qdrant Vector DB (HuggingFace Space: meryemarpaci/pentagent-qdrant)
    ├─ 95K+ CVE Embeddings (BGE-M3)
    ├─ Hybrid Search (Sparse + Dense)
    └─ Reranker (mixedbread-ai/mxbai-rerank-base-v1)
```

### 🔄 RAG Workflow

```
1. User Query → GPT OSS 120B Optimization
2. Optimized Query → BGE-M3 Embedding
3. Hybrid Search → Qdrant (Sparse 40% + Dense 60%, Top 20 results)
4. Reranking → mixedbread-ai/mxbai-rerank-base-v1 (10x score boost)
5. Hybrid Scoring → 15% vector + 85% reranker (boosted)
6. Final Results → Most relevant CVEs (with CVSS details)
7. Graceful Fallback → Original ranking on Reranker errors
```

### 🎯 Risk Score Calculation (New)

```
Dynamic Scoring Based on Tool Outputs:
├─ Severity Weights
│   ├─ Critical: +15
│   ├─ High: +10
│   ├─ Medium: +5
│   └─ Low/Info: +2/+1
│
├─ Tool Output Bonuses
│   ├─ 50+ endpoints → +30 (critical attack surface)
│   ├─ 10+ forms → +25 (injection risk)
│   ├─ 20+ subdomains → +20 (wide surface)
│   ├─ 10+ open ports → +20
│   └─ Critical dirs (admin, config) → +20
│
├─ Real Vulnerability Findings
│   └─ SQL/XSS/RCE → +20 each (max +50)
│
└─ Critical Path/Endpoint
    └─ admin, login, api → +20 (5+ instances)

Result: 0-100 normalized score, minimum 15 (if findings exist)
```

---

**API Keys:**
- `GROQ_API_KEY` - For GPT OSS 120B
- `HUGGINGFACE_TOKEN` - For RAG service

### 📦 Installation

#### 1. Clone the Project

```bash
git clone https://github.com/Pentagentr/Pentagent-Web.git
cd Pentagent-Web
```

#### 2. Backend Setup

```bash
# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
# Create .env file with the following values:
```

**.env Example:**
```env
# Required
GROQ_API_KEY=your_groq_api_key_here
MODEL_PROVIDER=groq
GROQ_MODEL=gpt-oss-120b

# RAG System (Optional)
HUGGINGFACE_TOKEN=your_hf_token_here
QDRANT_HOST=https://your-qdrant-space.hf.space
EMBEDDING_API_URL=https://your-embedding-space.hf.space/embed

# Reranker (Optional - default values)
USE_RERANKER=true
RERANKER_MODEL=mixedbread-ai/mxbai-rerank-base-v1
RERANKER_TOP_K=5

# Server
PORT=8000
ALLOWED_ORIGINS=http://localhost:5173,https://your-frontend.web.app
```

```bash
# Start backend
python web_api.py
```

Backend is now running at `http://localhost:8000`.

#### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd pentagent-frontend

# Install dependencies
npm install

# Set environment variables
# Create .env.local file:
```

**.env.local Example:**
```env
VITE_API_URL=http://localhost:8000
VITE_FIREBASE_API_KEY=your_firebase_api_key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
```

```bash
# Start development server
npm run dev
```

Frontend is now running at `http://localhost:5173`.

#### 4. Docker Qdrant Setup (Local Development)

For local development, you can run Qdrant with Docker:

```bash
# Pull and run Qdrant
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant

# Or use docker-compose
docker-compose up -d
```

**docker-compose.yml:**
```yaml
version: '3.8'
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - ./qdrant_storage:/qdrant/storage
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
```

#### 5. Firebase Deployment (Optional)

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login to Firebase
firebase login

# Initialize project (first time)
firebase init hosting

# Build project
npm run build

# Deploy
firebase deploy --only hosting
```

**firebase.json Configuration:**
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

## 💻 Usage

### 1. Basic Scanning

```bash
# Web interface
1. Go to http://localhost:5173
2. Login or register
3. Enter target and request in chat page: "I want to scan example.com"
4. AI automatically selects appropriate tools and starts the scan
```

### 2. RAG CVE Search

```python
# Programmatic usage
from services.rag_service import get_rag_service

rag = get_rag_service()

# Search CVEs
results = rag.search_cve("SQL injection", limit=5)

for cve in results:
    print(f"CVE: {cve.cve_id}")
    print(f"CVSS: {cve.base_score}")
    print(f"Severity: {cve.severity}")
    print(f"Match Score: {cve.score}")
```

### 3. Report Generation

```bash
# Web interface
1. After scan completion
2. Click "Generate Report" button in right panel
3. Report is automatically generated (PDF/TXT/JSON)
4. Download with "Download" button
```

### 4. API Usage

```python
import requests

# Start scan
response = requests.post("http://localhost:8000/api/scan", json={
    "target": "example.com",
    "task": "Perform comprehensive security test"
})

scan_id = response.json()["scan_id"]

# RAG CVE search
response = requests.post("http://localhost:8000/api/rag/search", json={
    "query": "SQL injection WordPress",
    "limit": 5,
    "severity": "CRITICAL"
})

cves = response.json()["results"]

# Generate report
response = requests.post("http://localhost:8000/api/generate-report", json={
    "target": "example.com",
    "scan_results": {"vulnerabilities": [...]},
    "cve_results": cves[:3]
})

report = response.json()
```

---

## 🔧 Technology Stack

### Backend
- **Framework:** FastAPI (async Python)
- **AI Model:** GPT OSS 120B (Groq API)
- **Vector Store:** Qdrant ([HuggingFace Space](https://huggingface.co/spaces/meryemarpaci/pentagent-qdrant))
- **Embeddings:** BGE-M3 (BAAI/bge-m3, 1024-dim)
- **Reranker:** mixedbread-ai/mxbai-rerank-base-v1
- **WebSocket:** Native FastAPI support with error handling
- **PDF Generation:** ReportLab
- **LLM Reports:** GPT OSS 120B for AI-enhanced markdown reports

### Frontend
- **Framework:** React 18
- **Build Tool:** Vite
- **Styling:** TailwindCSS + Custom CSS
- **State Management:** Context API
- **Routing:** React Router v6
- **Icons:** Lucide React
- **Deploy:** Firebase Hosting

### Database & ML
- **Vector DB:** Qdrant ([Deployed on HuggingFace](https://huggingface.co/spaces/meryemarpaci/pentagent-qdrant))
- **Embedding Model:** BAAI/bge-m3 (1024-dim, hybrid scoring)
- **Reranker Model:** mixedbread-ai/mxbai-rerank-base-v1 (10x boost + fallback)
- **LLM:** GPT OSS 120B 
- **CVE Data:** MITRE + NVD (95,000+ records)
- **Risk Scoring:** Dynamic tool-based calculation

---

## 📊 Performance Metrics

| Metric | Value | Description |
|--------|-------|-------------|
| RAG Response Time | <500ms | Average time including reranker |
| CVE Database | 95,000+ | MITRE and NVD sources |
| Embedding Size | 1024-dim | BGE-M3 vector dimension |
| Reranker Score Boost | 10x | Boost with mixedbread-ai model |
| Hybrid Scoring | 15/85 | Vector (15%) vs Reranker (85%) weight |
| Reranker Fallback | ✅ | Graceful degradation on API errors |
| Risk Score Accuracy | Dynamic | Tool output-based calculation |
| Tool Success Rate | ~85% | Average success rate |
| LLM Token Optimization | 60% | Prompt size reduction (3000→1500 words) |

---

## 🗂️ Project Structure

```
Pentagent/
├── agent_core/              # AI orchestration
│   ├── dynamic_orchestrator.py  # Main AI decision engine
│   ├── planner.py               # Strategy planner
│   ├── analyzer.py              # Result analyzer
│   ├── report_generator.py      # RAG-integrated reporting
│   └── state.py                 # State management
│
├── tools/                   # Security tools (30+)
│   ├── enum_*.py           # Discovery tools
│   ├── verify_*.py         # Validation tools
│   ├── recon_*.py          # Recon tools
│   └── vuln_*.py           # Vulnerability scanners
│
├── services/               # Services
│   └── rag_service.py      # RAG + Reranker system
│
├── mcp_server/            # Tool registry
│   ├── tool_registry.py    # Central tool registry
│   └── enhanced_mcp_tools.py
│
├── pentagent-frontend/    # React frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── chat/          # Chat interface
│   │   │   ├── reports/       # Report viewer
│   │   │   ├── layout/        # Layout components
│   │   │   └── common/        # Common components
│   │   ├── pages/
│   │   │   ├── ChatPage.jsx   # Main pentest page
│   │   │   ├── Reports.jsx    # Report page
│   │   │   └── RagSearch.jsx  # RAG search page
│   │   ├── services/
│   │   │   └── pentagentAPI.js # Backend API client
│   │   └── contexts/
│   │       └── AuthContext.jsx # Auth management
│   └── dist/              # Build output
│
├── reports/               # Generated reports
├── logs/                  # System logs
├── web_api.py            # FastAPI backend server
├── config.py             # Configuration
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

---

## 🔐 Security Notes

- ✅ Test your own systems
- ✅ Test systems with written permission
- ✅ Use in CTF and educational environments
- ❌ Do not use against unauthorized systems
- ❌ Do not abuse system resources

---

## 📈 Roadmap

### v2.0 (Current) ✅
- [x] RAG system integration (HuggingFace Space)
- [x] mixedbread-ai/mxbai-rerank-base-v1 optimization (10x boost)
- [x] GPT OSS 120B model integration
- [x] Dynamic risk score calculation (tool-based)
- [x] LLM-enhanced markdown reports
- [x] Automatic report generation (PDF/TXT/JSON/MD)
- [x] 30+ security tools
- [x] WebSocket real-time updates + error handling
- [x] Graceful fallback mechanisms (Reranker, LLM)
- [x] Token optimization (60% reduction)

### v2.1 (Planned) 🚧
- [ ] Multi-target scanning
- [ ] Custom wordlist management
- [ ] Export to Burp Suite
- [ ] Scheduled scans
- [ ] Email notifications

### v3.0 (Future) 🔮
- [ ] Machine learning CVE predictor
- [ ] Exploit generator
- [ ] API fuzzing
- [ ] Mobile app security
- [ ] Cloud security scanner

---

## 📄 License

This project is licensed under Apache License 2.0. See [LICENSE](LICENSE) file for details.

**Key Features:**
- ✅ Commercial use permission
- ✅ Modification permission
- ✅ Distribution permission
- ✅ Patent use permission
- ⚠️ Liability and warranty disclaimer

---

## Acknowledgments

- **GPT OSS 120B** - AI reasoning model 
- **Qdrant** - Vector database engine ([HuggingFace Space deployment](https://huggingface.co/spaces/meryemarpaci/pentagent-qdrant))
- **Docker** - Vector db storage
- **BAAI** - BGE-M3 embeddings
- **mixedbread-ai** - mxbai-rerank-base-v1 reranker model
- **HuggingFace** - Model hosting & inference API
- **NVD/MITRE** - CVE data source
- **FastAPI** - High-performance backend framework
- **React** - Modern frontend framework
- **Firebase** - Frontend hosting & authentication

---

Made by Pentagent

</div>
