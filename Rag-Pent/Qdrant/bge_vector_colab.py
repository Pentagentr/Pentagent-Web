"""
VEKTÖR ÜRETME SCRIPTI
Bu script, BAAI/bge-m3 modelini kullanarak JSON formatındaki metin verilerinden
yoğun (dense) ve seyrek (sparse) vektörler üretir ve bunları JSONL formatında kaydeder.

"""

import os
import torch
import numpy as np
import orjson  # Hızlı JSON işlemleri için standart kütüphane yerine kullanılır
import logging
from tqdm.auto import tqdm  # Otomatik ilerleme çubuğu seçimi
from FlagEmbedding import BGEM3FlagModel

# gereksiz ilerleme çubuklarını ve bilgi mesajlarını konsoldan gizliyoruz.
logging.getLogger("transformers").setLevel(logging.ERROR)


# --- AYARLAR VE SABITLER ---
# Veri setinizin bulunduğu dosya yolu.
DATA_FILE = "last_dataset.json"
# Oluşturulacak vektörlerin kaydedileceği dosya.
OUTPUT_FILE = "vectors.jsonl"
# Tek seferde işlenecek belge sayısı.
BATCH_SIZE = 256
# Kullanılacak embedding modeli.
BGE_MODEL_NAME = 'BAAI/bge-m3'

def main():
    """Ana fonksiyon: Modeli yükler, veriyi işler ve vektörleri dosyaya yazar."""

    print("="*50)
    print("BGE-M3 Vektör Üretme Scripti Başlatıldı")
    print("="*50)

    # --- GEREKLİ KONTROLLER ---
    if not os.path.exists(DATA_FILE):
        print(f"\n[HATA] Veri dosyası bulunamadı: '{DATA_FILE}'")
        print("Lütfen dosyanın doğru yolda olduğundan emin olun.")
        return # Dosya yoksa programı sonlandır

    # --- CİHAZ (GPU/CPU) AYARI ---
    device = "cuda" if torch.cuda.is_available() else "cpu"
    use_fp16 = True if device == "cuda" else False
    print(f"\n[BİLGİ] Cihaz tespiti tamamlandı. Kullanılan cihaz: {device.upper()}")
    if device == "cuda":
        print("[BİLGİ] FP16 (Yarı Hassasiyet) optimizasyonu AÇIK.")
    else:
        print("[BİLGİ] FP16 (Yarı Hassasiyet) optimizasyonu KAPALI (Sadece GPU'da geçerlidir).")

    # --- MODELİ YÜKLE ---
    try:
        print(f"\n[YÜKLENİYOR] '{BGE_MODEL_NAME}' modeli indiriliyor ve yükleniyor...")
        model = BGEM3FlagModel(BGE_MODEL_NAME, use_fp16=use_fp16)
        print("[BAŞARILI] Model başarıyla yüklendi.")
    except Exception as e:
        print(f"[HATA] Model yüklenirken bir sorun oluştu: {e}")
        return

    # --- VERİYİ YÜKLE ---
    try:
        print(f"\n[YÜKLENİYOR] '{DATA_FILE}' dosyasından veriler okunuyor...")
        with open(DATA_FILE, 'rb') as f: # orjson için binary modda okumak daha hızlı olabilir
            documents = orjson.loads(f.read())
        print(f"[BAŞARILI] Toplam {len(documents)} adet belge yüklendi.")
    except Exception as e:
        print(f"[HATA] Veri dosyası okunurken bir sorun oluştu: {e}")
        return

    # --- VEKTÖR OLUŞTURMA VE DOSYAYA YAZMA ---
    print(f"\n[İŞLEM] Vektör oluşturma işlemi başlatılıyor...")
    print(f"Batch boyutu: {BATCH_SIZE}")

    try:
        with open(OUTPUT_FILE, 'wb') as outfile:  # orjson byte yazdığı için 'wb' modunda açıyoruz
            # tqdm.auto ile temiz ilerleme çubuğu
            for i in tqdm(range(0, len(documents), BATCH_SIZE), desc="Vektörler oluşturuluyor"):
                batch_docs = documents[i:i + BATCH_SIZE]
                contents_to_embed = [doc["content"] for doc in batch_docs]

                # Model ile embeddingleri hesapla
                outputs = model.encode(
                    contents_to_embed,
                    batch_size=len(batch_docs), # Mevcut batch'in gerçek boyutunu ver
                    return_dense=True,
                    return_sparse=True,
                    return_colbert_vecs=False # İhtiyaç yoksa kapatmak hızı artırabilir
                )

                dense_vectors = outputs['dense_vecs']
                sparse_outputs = outputs['lexical_weights']

                # Batch içerisindeki her bir doküman için veriyi formatla ve yaz
                for j in range(len(batch_docs)):
                    doc_id = batch_docs[j]['id']

                    # JSON serileştirme hatalarını önlemek için veri tiplerini dönüştür
                    # dense_vectors zaten numpy array, .tolist() standart Python listesine çevirir.
                    dense_vec = dense_vectors[j].tolist()

                    # Seyrek vektör değerleri float16 olabilir, standart float'a çevirelim.
                    sparse_indices = list(sparse_outputs[j].keys())
                    sparse_values = [float(v) for v in sparse_outputs[j].values()]

                    point_data = {
                        "id": doc_id,
                        "payload": {
                            "content": batch_docs[j]["content"],
                            "metadata": batch_docs[j].get("metadata", {}), # metadata yoksa hata vermemesi için .get()
                            "cve_id": doc_id
                        },
                        "vector": {
                            "text-dense": dense_vec,
                            "text-sparse": {
                                "indices": sparse_indices,
                                "values": sparse_values
                            }
                        }
                    }
                    # orjson ile dosyaya yaz (daha hızlı)
                    outfile.write(orjson.dumps(point_data) + b'\n')

    except Exception as e:
        print(f"\n[HATA] Vektör oluşturma sırasında bir hata meydana geldi: {e}")
        return

    print("\n" + "="*50)
    print("✅ İŞLEM TAMAMLANDI ✅")
    print(f"Tüm vektörler başarıyla oluşturuldu ve '{OUTPUT_FILE}' dosyasına kaydedildi.")
    print("="*50)

if __name__ == '__main__':
    main()
