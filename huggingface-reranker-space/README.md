---
title: Pentagent Reranker
emoji: 🔄
colorFrom: purple
colorTo: blue
sdk: docker
pinned: false
license: apache-2.0
---

# Pentagent Reranker API

Reranking service using **mixedbread-ai/mxbai-rerank-xsmall-v1** model for the Pentagent security testing platform.

## Features

- ⚡ Fast reranking with CrossEncoder
- 🎯 Optimized for CVE search relevance
- 🔒 Production-ready API
- 📊 Health check endpoints

## API Endpoints

### POST /rerank

Rerank documents based on query relevance.

**Request:**
```json
{
  "query": "SQL injection vulnerability",
  "documents": [
    "CVE-2021-1234: SQL injection in WordPress",
    "CVE-2021-5678: XSS vulnerability in React"
  ],
  "top_k": 5
}
```

**Response:**
```json
{
  "scores": [0.95, 0.23],
  "top_k_indices": [0, 1]
}
```

### GET /health

Health check endpoint.

## Usage

```python
import requests

response = requests.post(
    "https://YOUR-SPACE.hf.space/rerank",
    json={
        "query": "SQL injection",
        "documents": ["doc1", "doc2"],
        "top_k": 5
    }
)

result = response.json()
print(result["scores"])
```

## Model

- **Model**: mixedbread-ai/mxbai-rerank-xsmall-v1
- **Type**: CrossEncoder
- **Max Length**: 512 tokens
- **License**: Apache 2.0

