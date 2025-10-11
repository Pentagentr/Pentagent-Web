"""
Qdrant Cloud'a Vektör Yükleme Scripti
Local'deki vektörleri Qdrant Cloud'a yükler
"""

import os
import sys
from qdrant_client import QdrantClient
from qdrant_client.http import models
import orjson
from tqdm import tqdm
from uuid import uuid5, NAMESPACE_DNS

# ============= AYARLAR =============
# Qdrant Cloud credentials (buraya kendi bilgilerini gir)
QDRANT_CLOUD_URL = "https://xyz.cloud.qdrant.io"  # ⬅️ Senin cluster URL'in
QDRANT_API_KEY = "your-api-key-here"  # ⬅️ Senin API key'in

# Collection config
COLLECTION_NAME = "cve_collection_hybrid"
VECTORS_FILE = "vectors.jsonl"  # Local vektör dosyası
BATCH_SIZE = 100  # Cloud için daha küçük batch
# ===================================


def create_collection(client):
    """Collection oluştur veya kontrol et"""
    try:
        collection = client.get_collection(COLLECTION_NAME)
        print(f"✅ Collection '{COLLECTION_NAME}' zaten var")
        print(f"   Mevcut point sayısı: {collection.points_count}")
        
        # Devam etmek istiyor musun?
        response = input("\n⚠️  Mevcut collection'a devam edilsin mi? (y/n): ")
        if response.lower() != 'y':
            print("❌ İşlem iptal edildi")
            return False
            
        return True
        
    except Exception:
        print(f"📦 Collection '{COLLECTION_NAME}' oluşturuluyor...")
        
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "text-dense": models.VectorParams(
                    size=1024,
                    distance=models.Distance.COSINE
                )
            },
            sparse_vectors_config={
                "text-sparse": models.SparseVectorParams()
            }
        )
        
        print(f"✅ Collection '{COLLECTION_NAME}' oluşturuldu!")
        return True


def upload_vectors(client, vectors_file):
    """Vektörleri Qdrant Cloud'a yükle"""
    
    if not os.path.exists(vectors_file):
        print(f"❌ Vektör dosyası bulunamadı: {vectors_file}")
        print(f"   Aranılan dizin: {os.path.abspath(vectors_file)}")
        return False
    
    print(f"\n📂 Vektörler yükleniyor: {vectors_file}")
    
    # Dosya boyutunu kontrol et
    file_size_mb = os.path.getsize(vectors_file) / (1024 * 1024)
    print(f"   Dosya boyutu: {file_size_mb:.2f} MB")
    
    batch = []
    total = 0
    
    # Progress bar ile yükle
    with open(vectors_file, 'rb') as f:
        for line in tqdm(f, desc="Yükleniyor", unit=" vektör"):
            try:
                data = orjson.loads(line)
                
                # UUID oluştur (CVE ID'den deterministik)
                cve_id = data["payload"].get("cve_id", "")
                point_id = str(uuid5(NAMESPACE_DNS, cve_id)) if cve_id else data["id"]
                
                # Point oluştur
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
                
                # Batch dolu mu?
                if len(batch) >= BATCH_SIZE:
                    client.upsert(
                        collection_name=COLLECTION_NAME,
                        points=batch
                    )
                    total += len(batch)
                    batch = []
                    
            except Exception as e:
                print(f"\n⚠️  Satır parse hatası: {e}")
                continue
    
    # Son batch'i yükle
    if batch:
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=batch
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
                vector=[0.1] * 1024  # Dummy vector
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
    print("   QDRANT CLOUD VEKTÖR YÜKLEME ARACI")
    print("="*70)
    print()
    
    # Ayarları kontrol et
    if QDRANT_API_KEY == "your-api-key-here":
        print("❌ HATA: Qdrant Cloud API key ayarlanmamış!")
        print("   Lütfen script içinde QDRANT_API_KEY değişkenini güncelle")
        return
    
    if "xyz.cloud.qdrant.io" in QDRANT_CLOUD_URL:
        print("❌ HATA: Qdrant Cloud URL ayarlanmamış!")
        print("   Lütfen script içinde QDRANT_CLOUD_URL değişkenini güncelle")
        return
    
    print(f"🌐 Qdrant Cloud URL: {QDRANT_CLOUD_URL}")
    print(f"🔑 API Key: {QDRANT_API_KEY[:10]}...")
    print(f"📦 Collection: {COLLECTION_NAME}")
    print(f"📁 Vektör Dosyası: {VECTORS_FILE}")
    print()
    
    # Devam et?
    response = input("Devam etmek istiyor musun? (y/n): ")
    if response.lower() != 'y':
        print("❌ İşlem iptal edildi")
        return
    
    print()
    
    try:
        # Qdrant Cloud'a bağlan
        print("🔌 Qdrant Cloud'a bağlanılıyor...")
        client = QdrantClient(
            url=QDRANT_CLOUD_URL,
            api_key=QDRANT_API_KEY,
            timeout=120  # 2 dakika timeout
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
        print("   1. Backend environment variables'ları ayarla:")
        print(f"      QDRANT_HOST={QDRANT_CLOUD_URL}")
        print(f"      QDRANT_API_KEY={QDRANT_API_KEY[:10]}...")
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

