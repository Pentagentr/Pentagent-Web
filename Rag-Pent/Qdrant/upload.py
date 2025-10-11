import orjson # Hızlı JSON işlemleri için
from qdrant_client import QdrantClient, models
from tqdm.auto import tqdm # İlerleme çubuğu
import time
import os
import sys
import uuid  # UUID oluşturmak için

# --- AYARLAR ---
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "cve_collection_hybrid" # Yeni ve temiz bir koleksiyon adı
VECTORS_FILE = "../ChromaDB/vectors.jsonl"  # Vektörlerinin bulunduğu dosya (düzeltildi)
BATCH_SIZE = 256 # Tek seferde yüklenecek vektör sayısı

# Qdrant bağlantısını test et
def test_qdrant_connection():
    """Qdrant bağlantısını test eder"""
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        # Basit bir health check
        collections = client.get_collections()
        print("✅ Qdrant bağlantısı başarılı!")
        return True
    except Exception as e:
        print(f"❌ Qdrant bağlantı hatası: {e}")
        print("💡 Çözüm: Docker ile Qdrant'ı başlatın: ./setup_qdrant.sh")
        return False

def main():
    print("="*50)
    print("Hazır Vektörleri Qdrant'a Yükleme Scripti")
    print("="*50)

    # Bağlantı testi
    if not test_qdrant_connection():
        return

    # Vektör dosyasının varlığını kontrol et
    if not os.path.exists(VECTORS_FILE):
        print(f"❌ HATA: '{VECTORS_FILE}' dosyası bulunamadı!")
        print("💡 Çözüm: Önce BGE-M3 ile vektörleri oluşturun: python Qdrant/bge_vector_colab.py")
        return

    # --- QDRANT İSTEMCİSİNİ BAŞLAT ---
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

    # --- KOLEKSİYONU OLUŞTUR ---
    # Bu koleksiyon hem dense (yoğun) hem de sparse (seyrek) vektörleri destekleyecek şekilde ayarlanacak.
    print(f"\n[İŞLEM] '{COLLECTION_NAME}' koleksiyonu oluşturuluyor...")
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        # İsimlendirilmiş vektörler kullanacağız
        vectors_config={
            # Yoğun vektör için ayarlar
            "text-dense": models.VectorParams(
                size=1024,  # BGE-M3 modelinin dense vektör boyutu
                distance=models.Distance.COSINE
            ),
        },
        # Seyrek vektör için ayarlar
        sparse_vectors_config={
            "text-sparse": models.SparseVectorParams(
                index=models.SparseIndexParams(on_disk=False)
            )
        }
    )
    print("[BAŞARILI] Koleksiyon oluşturuldu.")

    # --- VEKTÖRLERİ DOSYADAN OKU VE YÜKLE ---
    print(f"\n[İŞLEM] '{VECTORS_FILE}' dosyasından vektörler okunuyor ve yükleniyor...")
    start_time = time.time()
    points_uploaded = 0
    points_batch = []

    with open(VECTORS_FILE, 'rb') as f:
        # Dosyayı satır satır oku (JSONL formatı için)
        for line in tqdm(f, desc="Vektörler yükleniyor"):
            # Her satırı JSON olarak parse et
            data = orjson.loads(line)

            # CVE ID'sinden deterministik UUID oluştur (aynı CVE her zaman aynı UUID'yi alır)
            cve_id_str = data["id"]
            # UUID5 kullanarak string'den UUID oluştur
            point_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, cve_id_str))

            # Qdrant'ın sparse vektör formatına çevir
            sparse_qdrant_vector = models.SparseVector(
                indices=data["vector"]["text-sparse"]["indices"],
                values=data["vector"]["text-sparse"]["values"]
            )

            # Payload'a CVE ID'sini ekle
            payload = data["payload"]
            payload["cve_id"] = cve_id_str  # Orijinal CVE ID'sini payload'da sakla

            # Yüklenecek Point'i oluştur
            point = models.PointStruct(
                id=point_uuid,  # UUID kullan
                payload=payload,
                # İsimlendirilmiş vektörleri ata
                vector={
                    "text-dense": data["vector"]["text-dense"],
                    "text-sparse": sparse_qdrant_vector
                }
            )
            points_batch.append(point)

            # Batch boyutu dolduğunda Qdrant'a yükle
            if len(points_batch) >= BATCH_SIZE:
                client.upload_points(
                    collection_name=COLLECTION_NAME,
                    points=points_batch,
                    wait=True,
                    parallel=2
                )
                points_uploaded += len(points_batch)
                points_batch = [] # Batch'i temizle

    # Döngü bittikten sonra kalan point'leri yükle
    if points_batch:
        client.upload_points(
            collection_name=COLLECTION_NAME,
            points=points_batch,
            wait=True
        )
        points_uploaded += len(points_batch)

    end_time = time.time()

    print("\n" + "="*50)
    print("✅ İŞLEM TAMAMLANDI ✅")
    print(f"Toplam {points_uploaded} adet vektör yüklendi.")
    print(f"İşlem süresi: {end_time - start_time:.2f} saniye.")
    print(f"Doğrulama için: http://localhost:6333/dashboard")
    print("="*50)

if __name__ == "__main__":
    main()