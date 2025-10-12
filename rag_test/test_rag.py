"""
RAG Test - Basit ve Çalışan
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Rag-Pent'))

from Qdrant.cve_search import CVESearchEngine, SearchConfig

# Test queries (farklı kategorilerde)
test_data = [
    # Semantic (Dense)
    ("SQL injection vulnerability", "semantic"),
    ("XSS cross-site scripting", "semantic"),
    ("remote code execution RCE", "semantic"),
    
    # Version (Sparse)  
    ("Apache 2.4.49", "version"),
    ("Log4j 2.14.1", "version"),
    
    # CVE Direct
    ("CVE-2021-44228", "cve_direct"),
    ("CVE-2021-41773", "cve_direct"),
    
    # Hybrid
    ("CVE-2021-44228 Log4j", "hybrid"),
    ("Apache 2.4.49 path traversal", "hybrid"),
]

print("="*70)
print(" "*25 + "RAG SEARCH TEST")
print("="*70)

# Config - localhost Qdrant
config = SearchConfig(
    collection_name="cve_collection",  # Not cve_collection_hybrid!
    qdrant_host="localhost",
    qdrant_port=6333
)

try:
    engine = CVESearchEngine(config)
    print("[+] RAG Engine initialized\n")
except Exception as e:
    print(f"[-] RAG init failed: {e}")
    sys.exit(1)

# Test
results = {"passed": 0, "failed": 0, "by_category": {}}

for i, (query, category) in enumerate(test_data, 1):
    if category not in results["by_category"]:
        results["by_category"][category] = {"passed": 0, "failed": 0}
    
    print(f"[{i}/{len(test_data)}] {category.upper()}: '{query}'")
    
    try:
        search_results = engine.search(query, limit=5)
        
        if search_results and len(search_results) > 0:
            top = search_results[0]
            print(f"    [+] {len(search_results)} results - Top: {top.cve_id} ({top.score:.2f})")
            results["passed"] += 1
            results["by_category"][category]["passed"] += 1
        else:
            print(f"    [-] No results")
            results["failed"] += 1
            results["by_category"][category]["failed"] += 1
            
    except Exception as e:
        print(f"    [-] Error: {str(e)[:60]}")
        results["failed"] += 1
        results["by_category"][category]["failed"] += 1

print("\n" + "="*70)
print(" "*28 + "RESULTS")
print("="*70)

total = results["passed"] + results["failed"]
rate = (results["passed"] / total * 100) if total > 0 else 0

print(f"Passed: {results['passed']}/{total} ({rate:.0f}%)\n")

print("By Category:")
for cat, stats in results["by_category"].items():
    cat_total = stats["passed"] + stats["failed"]
    cat_rate = (stats["passed"] / cat_total * 100) if cat_total > 0 else 0
    print(f"  {cat:<15}: {stats['passed']}/{cat_total} ({cat_rate:.0f}%)")

print("="*70)

# Save results
with open("test_results.md", "w", encoding="utf-8") as f:
    f.write(f"# RAG Test Results\n\n")
    f.write(f"**Total:** {results['passed']}/{total} ({rate:.0f}%)\n\n")
    f.write(f"## By Category\n\n")
    for cat, stats in results["by_category"].items():
        cat_total = stats["passed"] + stats["failed"]
        cat_rate = (stats["passed"] / cat_total * 100) if cat_total > 0 else 0
        f.write(f"- **{cat}**: {stats['passed']}/{cat_total} ({cat_rate:.0f}%)\n")

print("\n[+] Results saved to test_results.md")

sys.exit(0 if results["failed"] == 0 else 1)
