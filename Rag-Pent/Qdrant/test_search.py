"""
CVE Search - Hızlı Test Scripti
Bu script yeni search sistemini test eder.
"""

import sys
from cve_search import CVESearchEngine, SearchConfig

def test_basic_search():
    """Temel arama testi"""
    print("\n" + "="*60)
    print("🔍 TEST 1: Temel Arama")
    print("="*60)
    
    engine = CVESearchEngine()
    
    query = "SQL injection vulnerability"
    print(f"\nSorgu: '{query}'")
    print("-" * 60)
    
    results = engine.search(query, limit=5)
    
    if not results:
        print("❌ Sonuç bulunamadı!")
        return False
    
    print(f"✅ {len(results)} sonuç bulundu\n")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. CVE ID: {result.cve_id}")
        print(f"   Hybrid Score: {result.score:.4f}")
        print(f"   Dense Score:  {result.dense_score:.4f}")
        print(f"   Sparse Score: {result.sparse_score:.4f}")
        print(f"   Severity: {result.severity or 'N/A'}")
        print(f"   Base Score: {result.base_score or 'N/A'}")
        print(f"   Description: {result.description[:100]}...")
        print()
    
    return True


def test_severity_search():
    """Severity filtrelemeli arama testi"""
    print("\n" + "="*60)
    print("🔍 TEST 2: Severity Filtrelemeli Arama")
    print("="*60)
    
    engine = CVESearchEngine()
    
    query = "remote code execution"
    severity = "CRITICAL"
    print(f"\nSorgu: '{query}' (Severity: {severity})")
    print("-" * 60)
    
    results = engine.search_by_severity(query, severity=severity, limit=5)
    
    if not results:
        print("❌ Sonuç bulunamadı!")
        return False
    
    print(f"✅ {len(results)} {severity} sonuç bulundu\n")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.cve_id} - Severity: {result.severity}")
        print(f"   Score: {result.score:.4f}")
        print()
    
    return True


def test_weight_comparison():
    """Farklı ağırlıklarla arama karşılaştırması"""
    print("\n" + "="*60)
    print("🔍 TEST 3: Ağırlık Karşılaştırması")
    print("="*60)
    
    engine = CVESearchEngine()
    query = "buffer overflow"
    
    # Dense ağırlıklı (default)
    print(f"\nSorgu: '{query}'")
    print("\n📊 Dense Ağırlıklı (Dense:70%, Sparse:30%) - DEFAULT (Semantik öncelikli)")
    print("-" * 60)
    results_dense_default = engine.search(query, limit=3, dense_weight=0.7, sparse_weight=0.3)
    
    for i, r in enumerate(results_dense_default, 1):
        print(f"{i}. {r.cve_id} - Score: {r.score:.4f} (D:{r.dense_score:.3f}, S:{r.sparse_score:.3f})")
    
    # Sparse ağırlıklı (karşılaştırma için)
    print("\n📊 Sparse Ağırlıklı (Dense:30%, Sparse:70%) - Keyword öncelikli")
    print("-" * 60)
    results_sparse = engine.search(query, limit=3, dense_weight=0.3, sparse_weight=0.7)
    
    for i, r in enumerate(results_sparse, 1):
        print(f"{i}. {r.cve_id} - Score: {r.score:.4f} (D:{r.dense_score:.3f}, S:{r.sparse_score:.3f})")
    
    return True


def test_health_and_stats():
    """Sistem sağlığı ve istatistik testi"""
    print("\n" + "="*60)
    print("🔍 TEST 4: Sistem Sağlığı ve İstatistikler")
    print("="*60)
    
    engine = CVESearchEngine()
    
    # Health check
    print("\n🏥 Health Check:")
    healthy = engine.health_check()
    print(f"   Durum: {'✅ Sağlıklı' if healthy else '❌ Sağlıksız'}")
    
    # Stats
    print("\n📊 İstatistikler:")
    stats = engine.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    return healthy


def main():
    """Ana test fonksiyonu"""
    print("\n" + "="*70)
    print("🚀 CVE SEARCH ENGINE - KAPSAMLI TEST")
    print("="*70)
    
    try:
        # Test 1: Temel arama
        success_1 = test_basic_search()
        
        # Test 2: Severity filtrelemeli arama
        success_2 = test_severity_search()
        
        # Test 3: Ağırlık karşılaştırması
        success_3 = test_weight_comparison()
        
        # Test 4: Health check ve stats
        success_4 = test_health_and_stats()
        
        # Özet
        print("\n" + "="*70)
        print("📋 TEST SONUÇLARI")
        print("="*70)
        print(f"Test 1 (Temel Arama):           {'✅ BAŞARILI' if success_1 else '❌ BAŞARISIZ'}")
        print(f"Test 2 (Severity Filtreleme):   {'✅ BAŞARILI' if success_2 else '❌ BAŞARISIZ'}")
        print(f"Test 3 (Ağırlık Karşılaştırma): {'✅ BAŞARILI' if success_3 else '❌ BAŞARISIZ'}")
        print(f"Test 4 (Health Check):          {'✅ BAŞARILI' if success_4 else '❌ BAŞARISIZ'}")
        print("="*70)
        
        if all([success_1, success_2, success_3, success_4]):
            print("\n🎉 TÜM TESTLER BAŞARILI!")
            print("✅ Sistem production'a hazır.")
            return 0
        else:
            print("\n⚠️  BAZI TESTLER BAŞARISIZ!")
            print("💡 Lütfen hataları kontrol edin.")
            return 1
            
    except Exception as e:
        print(f"\n❌ HATA: {e}")
        print("\n💡 Kontrol Listesi:")
        print("   1. Qdrant çalışıyor mu? (docker-compose up -d)")
        print("   2. Vektörler yüklendi mi? (python Qdrant/upload.py)")
        print("   3. Collection adı doğru mu? (cve_collection_hybrid)")
        return 1


if __name__ == "__main__":
    sys.exit(main())

