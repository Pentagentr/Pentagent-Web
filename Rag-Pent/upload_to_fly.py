"""
Fly.io Qdrant'a Vektör Yükleme Scripti
Docker container'a vektörleri yükler
"""

import os
from qdrant_client import QdrantClient
from qdrant_client.http import models
import orjson
from tqdm import tqdm
from uuid import uuid5, NAMESPACE_DNS

# ============= AYARLAR =============
QDRANT_URL = "https://pentagent-qdrant.fly.dev"  # ⬅️ Deploy sonrası Fly.io URL'in
COLLECTION_NAME = "cve_collection_hybrid"
VECTORS_FILE = "vectors.jsonl"
BATCH_SIZE = 100
# ===================================


def create_collection(client):
    """Collection oluştur veya kontrol et"""
    try:
        collection = client.get_collection(COLLECTION_NAME)
        print(f"✅ Collection '{COLLECTION_NAME}' zaten var")
        print(f"   Mevcut point sayısı: {collection.points_count}")
        
        response = input("\n⚠️  Mevcut collection'a devam edilsin mi? (y/n): ")
        if response.lower() != 'y':
            print("❌ İşlem iptal edildi")
            return False
            
        return True
        
    except Exception:
        print(f"📦 Collection '{COLLECTION_NAME}' oluşturuluyor...")
        
        # On-disk indexing ile RAM tasarrufu
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "text-dense": models.VectorParams(
                    size=1024,
                    distance=models.Distance.COSINE,
                    on_disk=True  # RAM tasarrufu için disk kullan
                )
            },
            sparse_vectors_config={
                "text-sparse": models.SparseVectorParams(
                    index={"on_disk": True}
                )
            },
            optimizers_config=models.OptimizersConfigDiff(
                indexing_threshold=0  # Hemen indexleme başlat
            )
        )
        
        print(f"✅ Collection '{COLLECTION_NAME}' oluşturuldu!")
        return True


def upload_vectors(client, vectors_file):
    """Vektörleri Fly.io Qdrant'a yükle"""
    
    if not os.path.exists(vectors_file):
        print(f"❌ Vektör dosyası bulunamadı: {vectors_file}")
        print(f"   Aranılan dizin: {os.path.abspath(vectors_file)}")
        return False
    
    print(f"\n📂 Vektörler yükleniyor: {vectors_file}")
    
    # Dosya boyutu
    file_size_mb = os.path.getsize(vectors_file) / (1024 * 1024)
    print(f"   Dosya boyutu: {file_size_mb:.2f} MB")
    
    batch = []
    total = 0
    
    with open(vectors_file, 'rb') as f:
        for line in tqdm(f, desc="Yükleniyor", unit=" vektör"):
            try:
                data = orjson.loads(line)
                
                # UUID oluştur (CVE ID'den deterministik)
                cve_id = data["payload"].get("cve_id", "")
                point_id = str(uuid5(NAMESPACE_DNS, cve_id)) if cve_id else data["id"]
                
                point = models.PointStruct(
                    id=point_id,
                    payload=data["payload"],
                    vector={
                        "text-dense": data["vector"]["text-dense"],
                        "text-sparse": models.SparseVector(
                            indices=data["vector"]["text-sparse"]["indices"],
                            values=data["vector"]["text-sparse"]["values"]
                        )
                    }
                )
                
                batch.append(point)
                
                if len(batch) >= BATCH_SIZE:
                    # Async upload (wait=False) - daha hızlı
                    client.upsert(
                        collection_name=COLLECTION_NAME,
                        points=batch,
                        wait=False
                    )
                    total += len(batch)
                    batch = []
                    
            except Exception as e:
                print(f"\n⚠️  Satır parse hatası: {e}")
                continue
    
    # Son batch (wait=True - bitene kadar bekle)
    if batch:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=batch,
            wait=True
        )
        total += len(batch)
    
    print(f"\n✅ {total:,} vektör başarıyla yüklendi!")
    return True


def verify_upload(client):
    """Yükleme sonrası doğrulama"""
    try:
        collection_info = client.get_collection(COLLECTION_NAME)
        
        print("\n" + "="*50)
        print("📊 YÜKLEME DOĞRULAMA")
        print("="*50)
        print(f"Collection Name: {collection_info.name}")
        print(f"Total Points: {collection_info.points_count:,}")
        print(f"Vectors Count: {collection_info.vectors_count}")
        print(f"Status: {collection_info.status}")
        print("="*50)
        
        # Test search
        print("\n🔍 Test arama yapılıyor...")
        test_results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=models.NamedVector(
                name="text-dense",
                vector=[0.1] * 1024
            ),
            limit=1
        )
        
        if test_results:
            print(f"✅ Test arama başarılı! İlk sonuç: {test_results[0].payload.get('cve_id', 'N/A')}")
        else:
            print("⚠️  Test arama sonuç döndürmedi")
        
        return True
        
    except Exception as e:
        print(f"❌ Doğrulama hatası: {e}")
        return False


def main():
    """Ana fonksiyon"""
    print("="*70)
    print("   FLY.IO QDRANT VEKTÖR YÜKLEME ARACI")
    print("="*70)
    print()
    
    # URL kontrolü
    if "pentagent-qdrant.fly.dev" not in QDRANT_URL:
        print("⚠️  UYARI: QDRANT_URL değişkenini Fly.io deploy sonrası URL ile güncelle!")
        print(f"   Şu anki URL: {QDRANT_URL}")
        response = input("\nDevam etmek istiyor musun? (y/n): ")
        if response.lower() != 'y':
            return
    
    print(f"🌐 Qdrant URL: {QDRANT_URL}")
    print(f"📦 Collection: {COLLECTION_NAME}")
    print(f"📁 Vektör Dosyası: {VECTORS_FILE}")
    print()
    
    response = input("Devam etmek istiyor musun? (y/n): ")
    if response.lower() != 'y':
        print("❌ İşlem iptal edildi")
        return
    
    print()
    
    try:
        # Fly.io Qdrant'a bağlan (public, auth yok)
        print("🔌 Fly.io Qdrant'a bağlanılıyor...")
        client = QdrantClient(
            url=QDRANT_URL,
            timeout=120,
            https=True
        )
        print("✅ Bağlantı başarılı!")
        
        # Collection oluştur/kontrol et
        if not create_collection(client):
            return
        
        # Vektörleri yükle
        if not upload_vectors(client, VECTORS_FILE):
            return
        
        # Doğrula
        verify_upload(client)
        
        print("\n" + "="*70)
        print("✅ YÜKLEME TAMAMLANDI!")
        print("="*70)
        print()
        print("🎯 Sonraki adımlar:")
        print("   1. Backend environment variables'ı güncelle:")
        print(f"      QDRANT_HOST={QDRANT_URL}")
        print("      QDRANT_PORT=443")
        print()
        print("   2. Backend'i Render.com'a deploy et")
        print("   3. Frontend'i Firebase'e deploy et")
        print()
        
    except Exception as e:
        print(f"\n❌ HATA: {e}")
        import traceback
        print(traceback.format_exc())


if __name__ == "__main__":
    main()

