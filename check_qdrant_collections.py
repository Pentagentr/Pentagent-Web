"""Check Qdrant collections"""
from qdrant_client import QdrantClient

# Try local
try:
    print("Checking localhost:6333...")
    client = QdrantClient(host="localhost", port=6333)
    collections = client.get_collections()
    print(f"Found {len(collections.collections)} collections:")
    for col in collections.collections:
        print(f"  - {col.name}")
except Exception as e:
    print(f"Local failed: {e}")





















