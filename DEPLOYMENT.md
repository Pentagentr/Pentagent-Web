# 🚀 Pentagent Deployment Guide

## 📊 System Architecture

```
┌─────────────────────────────────────────────────┐
│           PENTAGENT ARCHITECTURE                │
└─────────────────────────────────────────────────┘

Frontend (Firebase Hosting)
    ↓ HTTPS / WebSocket
Backend API (Render.com)
    ↓ REST API
RAG Vector Database (HuggingFace Space)
    └─ Qdrant (95K+ CVE vectors)
```

---

## 🎯 Deployment Stack

| Component | Platform | Type | Cost |
|-----------|----------|------|------|
| **Frontend** | Firebase Hosting | Static SPA | Free |
| **Backend** | Render.com | Python/FastAPI | Free |
| **Vector DB** | HuggingFace Space | Docker/Qdrant | Free |

---

## 🚀 Deployment Steps

### 1. Vector Database (Qdrant on HuggingFace)

**Setup:**
1. Create HuggingFace account
2. Create new Space (Docker SDK)
3. Upload Qdrant Docker image with pre-loaded vectors
4. Set Space visibility (public/private)
5. Get Space URL and access token (if private)

**Configuration:**
- Port: 7860 (HuggingFace default)
- Storage: Persistent volume
- Vectors: 95K+ CVE embeddings (BGE-M3)

---

### 2. Backend API (Render.com)

**Setup:**
1. Connect GitHub repository
2. Create new Web Service
3. Configure build settings

**Build Configuration:**
```yaml
Language: Python 3
Build Command: pip install -r requirements.txt
Start Command: uvicorn web_api:app --host 0.0.0.0 --port $PORT
Instance Type: Free
```

**Environment Variables Required:**
```env
GEMINI_API_KEY=<your_gemini_api_key>
ALLOWED_ORIGINS=<your_frontend_url>
QDRANT_HOST=<your_huggingface_space_url>
QDRANT_PORT=443
HUGGINGFACE_TOKEN=<your_hf_token>  # If Space is private
```

**Health Check:**
- Path: `/health`
- Expected Response: 
  ```json
  {
    "status": "healthy",
    "rag_available": true,
    "rag_cves": 95237
  }
  ```

---

### 3. Frontend (Firebase Hosting)

**Setup:**
1. Build production bundle with backend URL
2. Deploy to Firebase Hosting

**Build Commands:**
```bash
cd pentagent-frontend

# Set backend URL
echo VITE_API_URL=<your_backend_url> > .env.production

# Build
npm run build

# Deploy
firebase deploy --only hosting
```

---

## 🔌 API Endpoints

### Core Endpoints
- `GET /health` - System health check
- `POST /api/scan` - Start security scan
- `WebSocket /ws` - Real-time scan updates

### RAG Endpoints
- `POST /api/rag/search` - Search CVE database
- `GET /api/rag/cve/{id}` - Get CVE details
- `POST /api/rag/analyze-scan` - Analyze scan results for CVEs
- `GET /api/rag/stats` - RAG system statistics

---

## 🔒 Security Considerations

### Environment Variables
- Store all secrets in platform environment variables
- Never commit API keys or tokens to repository
- Use `.env.production` for frontend (gitignored)

### CORS Configuration
- Backend validates allowed origins
- Frontend URL must be whitelisted
- WebSocket connections authenticated

### Vector Database Access
- Private HuggingFace Space requires authentication token
- Token passed via HTTP headers
- Read-only access recommended for backend

---

## 🧪 Testing

### 1. Backend Health
```bash
curl https://<backend-url>/health
```

### 2. RAG System
```bash
curl -X POST "https://<backend-url>/api/rag/search" \
  -H "Content-Type: application/json" \
  -d '{"query":"SQL injection","limit":5}'
```

### 3. Frontend
- Navigate to deployed URL
- Test pentest functionality
- Test CVE search page (`/rag-search`)
- Verify ContextPanel CVE suggestions

---

## 📈 Performance & Limits

### Free Tier Limitations

**Render.com:**
- 750 hours/month
- 512MB RAM
- Spins down after 15min inactivity
- Cold start: 30-60 seconds

**HuggingFace Space:**
- CPU-basic (free tier)
- Persistent storage included
- Always-on (no sleep)

**Firebase Hosting:**
- 10GB storage
- 360MB/day transfer
- CDN included

---

## 🛠️ Maintenance

### Update Deployment

**Backend:**
- Push to GitHub → Auto-deploy on Render
- Monitor logs in Render Dashboard

**Frontend:**
- Build and deploy: `firebase deploy --only hosting`

**Vector Database:**
- Update via HuggingFace Space interface
- Re-upload Docker image if needed

### Monitoring
- **Backend:** Render Dashboard → Logs
- **Frontend:** Firebase Console → Hosting
- **Qdrant:** HuggingFace Space → Logs

---

## 📚 Documentation

- `README.md` - Main project documentation
- `RAG_INTEGRATION_README.md` - RAG system usage
- `HUGGINGFACE_QDRANT_DEPLOYMENT.md` - Qdrant deployment details
- `PRIVATE_SPACE_SOLUTION.md` - Private Space authentication

---

## 🆘 Troubleshooting

### Backend Build Fails
- Check `requirements.txt` dependencies
- Verify Python version compatibility
- Review build logs in Render

### RAG Not Available
- Verify HuggingFace Space is running
- Check authentication token
- Confirm Qdrant collection exists

### Frontend Can't Connect
- Verify backend URL in `.env.production`
- Check CORS settings (ALLOWED_ORIGINS)
- Inspect browser console for errors

---

## 📞 Support

For issues and questions:
- Check logs in respective platforms
- Review API documentation
- Verify environment variables

---

**License:** Apache 2.0 - Open Source & Licensable
