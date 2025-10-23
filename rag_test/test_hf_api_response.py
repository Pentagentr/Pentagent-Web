"""
HuggingFace Inference API Response Test
BGE-M3 sparse vector üretiyor mu kontrol edelim
"""

import sys
import io
import requests
import json
import os

# UTF-8 encoding fix
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# HF API URL
HF_API_URL = "https://router.huggingface.co/hf-inference/models/BAAI/bge-m3"

# Test query
test_query = "SQL injection vulnerability"

print("="*80)
print("HuggingFace Inference API Response Test")
print("="*80)
print(f"\nModel: BAAI/bge-m3")
print(f"Query: '{test_query}'")
print("\n" + "="*80)

# Token yoksa anonymous (rate-limited)
hf_token = os.getenv("HUGGINGFACE_TOKEN")
if hf_token:
    print("✅ HF Token bulundu")
else:
    print("⚠️  HF Token yok (anonymous request)")

headers = {}
if hf_token:
    headers["Authorization"] = f"Bearer {hf_token}"

# Standard request (feature extraction)
print("\n[1] Standard Feature Extraction Request:")
print("-" * 80)

payload1 = {
    "inputs": test_query,
    "options": {"wait_for_model": True}
}

try:
    response1 = requests.post(HF_API_URL, headers=headers, json=payload1, timeout=30)
    print(f"Status: {response1.status_code}")
    
    if response1.status_code == 200:
        data1 = response1.json()
        print(f"Response type: {type(data1)}")
        
        if isinstance(data1, list):
            print(f"Vector dimension: {len(data1)}")
            print(f"First 5 values: {data1[:5]}")
            print(f"\n❌ SADECE DENSE VECTOR - Sparse yok!")
        elif isinstance(data1, dict):
            print(f"Response keys: {list(data1.keys())}")
            print(f"Response: {json.dumps(data1, indent=2)[:500]}")
    else:
        print(f"Error: {response1.text}")
except Exception as e:
    print(f"Exception: {e}")

# Alternative: parameters ile deneyelim
print("\n[2] Parameters ile Dense + Sparse Request Denemesi:")
print("-" * 80)

payload2 = {
    "inputs": test_query,
    "parameters": {
        "return_dense": True,
        "return_sparse": True,
        "return_colbert_vecs": False
    },
    "options": {"wait_for_model": True}
}

try:
    response2 = requests.post(HF_API_URL, headers=headers, json=payload2, timeout=30)
    print(f"Status: {response2.status_code}")
    
    if response2.status_code == 200:
        data2 = response2.json()
        print(f"Response type: {type(data2)}")
        
        if isinstance(data2, dict):
            print(f"Response keys: {list(data2.keys())}")
            
            if 'dense_vecs' in data2:
                print(f"✅ Dense vectors bulundu: {len(data2['dense_vecs'])}")
            
            if 'lexical_weights' in data2:
                print(f"✅ Sparse vectors (lexical_weights) bulundu!")
                print(f"   Sample: {str(data2['lexical_weights'])[:200]}")
            else:
                print(f"❌ Sparse vectors (lexical_weights) YOK!")
                
            print(f"\nFull response: {json.dumps(data2, indent=2)[:500]}")
        else:
            print(f"Response: {data2}")
    else:
        print(f"Error: {response2.text}")
except Exception as e:
    print(f"Exception: {e}")

# Sonuç
print("\n" + "="*80)
print("SONUÇ:")
print("="*80)
print("""
HuggingFace Inference API'nin standard 'feature-extraction' endpoint'i:
- ✅ Dense embeddings üretir (1024 boyut)
- ❌ Sparse vectors (lexical weights) ÜRETEMİYOR
- ❌ ColBERT multi-vectors ÜRETEMİYOR

BGE-M3'ün sparse özelliğini kullanmak için:
- Model'i local çalıştırmak gerekir (FlagEmbedding kütüphanesi)
- Veya custom inference endpoint gerekir (HF Space'te deploy)

Canlı sistemde manuel sparse approximation kullanmalıyız.
""")
print("="*80)

