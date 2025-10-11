---
title: Pentagent Qdrant CVE Database
emoji: 🔍
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
app_port: 7860
---

# 🔍 Pentagent CVE RAG - Qdrant Vector Database

This HuggingFace Space hosts the Qdrant vector database for Pentagent security testing platform.

## 📊 Features

- **95,000+ CVE vectors** from NVD (2022-2024)
- **Hybrid search** (Dense 70% + Sparse 30%)
- **BGE-M3 embeddings** (1024 dimensions)
- **Open source** (Apache 2.0 License)

## 🔌 API Endpoints

**Base URL:** `https://YOUR_USERNAME-pentagent-qdrant.hf.space`

- `GET /health` - Health check
- `GET /collections` - List collections
- `POST /collections/{collection}/points/search` - Vector search

## 🚀 Usage

```python
from qdrant_client import QdrantClient

client = QdrantClient(
    url="https://YOUR_USERNAME-pentagent-qdrant.hf.space",
    timeout=30
)

# Search CVEs
results = client.search(
    collection_name="cve_collection_hybrid",
    query_vector=...,
    limit=10
)
```

## 📝 License

Apache 2.0 - Open Source & Licensable

## 🔗 Related

- [Pentagent Backend](https://github.com/YOUR_USERNAME/pentagent-backend)
- [Qdrant Documentation](https://qdrant.tech/documentation/)

