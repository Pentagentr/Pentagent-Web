"""
Basit RAG Test - Docker Qdrant
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'Rag-Pent'))

from Qdrant.cve_search import CVESearchEngine, SearchConfig

print("="*70)
print("RAG SEARCH TEST - Docker Qdrant")
print("="*70)

# Config
config = SearchConfig(
    collection_name="cve_collection_hybrid",
    qdrant_host="localhost",
    qdrant_port=6333
)

print("[*] Connecting to Docker Qdrant (localhost:6333)...")

try:
    engine = CVESearchEngine(config)
    print("[+] Connected!\n")
except Exception as e:
    print(f"[-] Failed: {e}")
    sys.exit(1)

# Test queries
tests = [
    ("SQL injection", "Semantic - Dense"),
    ("CVE-2021-44228", "CVE Direct"),
    ("Apache 2.4.49", "Version - Sparse"),
    ("XSS vulnerability", "Semantic"),
    ("remote code execution", "Semantic"),
]

passed = 0
for query, test_type in tests:
    print(f"[{test_type}] '{query}'")
    try:
        results = engine.search(query, limit=3)
        if results:
            print(f"  [+] {len(results)} results")
            print(f"      #{1}: {results[0].cve_id} ({results[0].score:.2f})")
            passed += 1
        else:
            print(f"  [-] No results")
    except Exception as e:
        print(f"  [-] Error: {str(e)[:50]}")

print(f"\n{'='*70}")
print(f"PASSED: {passed}/{len(tests)}")
print("="*70)

