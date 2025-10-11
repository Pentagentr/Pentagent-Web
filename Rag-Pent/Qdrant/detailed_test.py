"""
Detaylı Hybrid Arama Testi - Siber Güvenlik Senaryoları
Dense (semantik) ve Sparse (keyword) skorları ayrı ayrı gösterir
"""
from qdrant_client import QdrantClient, models
from FlagEmbedding import BGEM3FlagModel
import torch

class DetailedSearcher:
    def __init__(self):
        print("🔧 BGE-M3 modeli yükleniyor...")
        self.model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=False)
        self.client = QdrantClient(host="localhost", port=6333)
        self.collection_name = "cve_collection_hybrid"
        print("✅ Model ve Qdrant bağlantısı hazır!\n")
    
    def detailed_search(self, query: str, limit: int = 5):
        """Hem dense hem sparse sonuçları detaylı gösterir"""
        print("="*80)
        print(f"🔍 SORGU: '{query}'")
        print("="*80)
        
        # Dense arama
        print("\n📊 DENSE (Semantik) Arama Sonuçları:")
        print("-" * 80)
        dense_vec = self.model.encode([query], return_dense=True)['dense_vecs'][0]
        dense_results = self.client.query_points(
            collection_name=self.collection_name,
            query=dense_vec.tolist(),
            using="text-dense",
            limit=limit,
            with_payload=True
        )
        
        for i, point in enumerate(dense_results.points, 1):
            cve_id = point.payload.get("cve_id", point.id)
            metadata = point.payload.get("metadata", {})
            print(f"\n{i}. {cve_id} [Dense Score: {point.score:.4f}]")
            print(f"   Severity: {metadata.get('severity', 'N/A'):8} | Base Score: {metadata.get('base_score', 'N/A')}")
            print(f"   Attack: {metadata.get('attack_vector', 'N/A')}")
            print(f"   📝 {point.payload.get('content', '')[:150]}...")
        
        # Sparse arama
        print("\n\n🔑 SPARSE (Keyword) Arama Sonuçları:")
        print("-" * 80)
        sparse_output = self.model.encode([query], return_sparse=True)['lexical_weights'][0]
        print(f"Tespit edilen keyword'ler: {len(sparse_output)} token")
        
        sparse_vec = models.SparseVector(
            indices=list(sparse_output.keys()),
            values=list(sparse_output.values())
        )
        
        sparse_results = self.client.query_points(
            collection_name=self.collection_name,
            query=sparse_vec,
            using="text-sparse",
            limit=limit,
            with_payload=True
        )
        
        for i, point in enumerate(sparse_results.points, 1):
            cve_id = point.payload.get("cve_id", point.id)
            metadata = point.payload.get("metadata", {})
            print(f"\n{i}. {cve_id} [Sparse Score: {point.score:.4f}]")
            print(f"   Severity: {metadata.get('severity', 'N/A'):8} | Base Score: {metadata.get('base_score', 'N/A')}")
            print(f"   Attack: {metadata.get('attack_vector', 'N/A')}")
            print(f"   📝 {point.payload.get('content', '')[:150]}...")
        
        # Hybrid (birleştirilmiş) sonuçlar
        print("\n\n🎯 HYBRID (Dense 70% + Sparse 30%) Sonuçları:")
        print("-" * 80)
        
        # Sonuçları birleştir
        combined = {}
        for point in dense_results.points:
            cve_id = point.payload.get("cve_id", point.id)
            combined[cve_id] = {
                "dense": point.score,
                "sparse": 0.0,
                "payload": point.payload
            }
        
        for point in sparse_results.points:
            cve_id = point.payload.get("cve_id", point.id)
            if cve_id not in combined:
                combined[cve_id] = {
                    "dense": 0.0,
                    "sparse": point.score,
                    "payload": point.payload
                }
            else:
                combined[cve_id]["sparse"] = point.score
        
        # Hybrid skoru hesapla ve sırala
        hybrid_results = []
        for cve_id, data in combined.items():
            hybrid_score = (0.7 * data["dense"]) + (0.3 * data["sparse"])
            hybrid_results.append({
                "cve_id": cve_id,
                "hybrid": hybrid_score,
                "dense": data["dense"],
                "sparse": data["sparse"],
                "payload": data["payload"]
            })
        
        hybrid_results.sort(key=lambda x: x["hybrid"], reverse=True)
        
        for i, result in enumerate(hybrid_results[:limit], 1):
            metadata = result["payload"].get("metadata", {})
            print(f"\n{i}. {result['cve_id']}")
            print(f"   🎯 Hybrid: {result['hybrid']:.4f} = Dense({result['dense']:.4f}) × 0.7 + Sparse({result['sparse']:.4f}) × 0.3")
            print(f"   Severity: {metadata.get('severity', 'N/A'):8} | Base Score: {metadata.get('base_score', 'N/A')}")
            print(f"   📝 {result['payload'].get('content', '')[:150]}...")
        
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    searcher = DetailedSearcher()
    
    # Siber güvenlik test senaryoları
    test_queries = [
        "Windows privilege escalation vulnerability in kernel driver",
        "Apache web server remote code execution",
        "zero-day authentication bypass in VPN",
    ]
    
    for query in test_queries:
        searcher.detailed_search(query, limit=5)
        print("\n")

