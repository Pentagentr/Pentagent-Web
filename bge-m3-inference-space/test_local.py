"""
Local test script - Deploy etmeden önce test et
"""

import requests
import json

# Test endpoint (local veya deployed)
ENDPOINT = "http://localhost:7860"  # Local test
# ENDPOINT = "https://YOUR_USERNAME-bge-m3-inference.hf.space"  # Deployed

print("="*80)
print("BGE-M3 Custom Inference API Test")
print("="*80)
print(f"\nEndpoint: {ENDPOINT}\n")

# Test 1: Health check
print("[1] Health Check:")
print("-" * 80)
try:
    response = requests.get(f"{ENDPOINT}/health", timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Encoding (dense + sparse)
print("\n[2] Encoding Test (Dense + Sparse):")
print("-" * 80)

test_query = "SQL injection vulnerability in Apache 2.4.49"
print(f"Query: '{test_query}'")

try:
    response = requests.post(
        f"{ENDPOINT}/encode",
        json={
            "inputs": test_query,
            "return_dense": True,
            "return_sparse": True,
            "return_colbert_vecs": False
        },
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        
        # Dense
        if data.get("dense_vecs"):
            dense = data["dense_vecs"]
            print(f"\n✅ Dense Vector:")
            print(f"   Dimension: {len(dense)}")
            print(f"   First 5: {dense[:5]}")
        
        # Sparse
        if data.get("lexical_weights"):
            sparse = data["lexical_weights"]
            print(f"\n✅ Sparse Vector (Lexical Weights):")
            print(f"   Token count: {len(sparse)}")
            print(f"   Sample (first 5):")
            for token_id, weight in list(sparse.items())[:5]:
                print(f"     Token {token_id}: {weight:.4f}")
        
        print(f"\n✅ SUCCESS! Native sparse vectors working!")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")

# Test 3: CVE query
print("\n[3] CVE Query Test:")
print("-" * 80)

cve_query = "CVE-2024-3400 Palo Alto Networks command injection"
print(f"Query: '{cve_query}'")

try:
    response = requests.post(
        f"{ENDPOINT}/encode",
        json={
            "inputs": cve_query,
            "return_dense": True,
            "return_sparse": True
        },
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Dense: {len(data.get('dense_vecs', []))} dims")
        print(f"✅ Sparse: {len(data.get('lexical_weights', {}))} tokens")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*80)
print("Test Complete!")
print("="*80)


