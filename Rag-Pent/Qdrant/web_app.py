"""
CVE RAG Projesi - Web Arayüzü
Flask ile basit web arayüzü - hem dense hem sparse arama
"""

from flask import Flask, render_template, request, jsonify
import json
from hybrid_search import CVEHybridSearcher
import os

app = Flask(__name__)

# Global searcher instance
searcher = None

def init_searcher():
    """Searcher'ı başlat"""
    global searcher
    try:
        searcher = CVEHybridSearcher()
        return True
    except Exception as e:
        print(f"Searcher başlatma hatası: {e}")
        return False

@app.route('/')
def index():
    """Ana sayfa"""
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    """Arama API endpoint'i"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        search_type = data.get('type', 'hybrid')  # hybrid, dense, sparse
        limit = min(int(data.get('limit', 10)), 50)  # Max 50 sonuç
        
        if not query:
            return jsonify({'error': 'Sorgu boş olamaz'}), 400
        
        if not searcher:
            return jsonify({'error': 'Arama sistemi hazır değil'}), 500
        
        # Arama türüne göre sonuçları al
        if search_type == 'dense':
            results = searcher.search_dense(query, limit)
        elif search_type == 'sparse':
            results = searcher.search_sparse(query, limit)
        else:  # hybrid
            results = searcher.hybrid_search(query, limit)
        
        # Sonuçları formatla
        formatted_results = []
        for result in results:
            payload = result.get('payload', {})
            metadata = payload.get('metadata', {})
            
            formatted_results.append({
                'id': result['id'],
                'score': result.get('hybrid_score', result.get('score', 0)),
                'content': payload.get('content', '')[:500] + '...' if len(payload.get('content', '')) > 500 else payload.get('content', ''),
                'severity': metadata.get('severity', 'N/A'),
                'attack_vector': metadata.get('attack_vector', 'N/A'),
                'base_score': metadata.get('base_score', 'N/A'),
                'source_url': metadata.get('source_url', 'N/A')
            })
        
        return jsonify({
            'results': formatted_results,
            'total': len(formatted_results),
            'query': query,
            'type': search_type
        })
        
    except Exception as e:
        return jsonify({'error': f'Arama hatası: {str(e)}'}), 500

@app.route('/cve/<cve_id>')
def get_cve_details(cve_id):
    """CVE detaylarını getir"""
    try:
        if not searcher:
            return jsonify({'error': 'Arama sistemi hazır değil'}), 500
        
        details = searcher.get_cve_details(cve_id)
        if not details:
            return jsonify({'error': 'CVE bulunamadı'}), 404
        
        return jsonify(details)
        
    except Exception as e:
        return jsonify({'error': f'Detay getirme hatası: {str(e)}'}), 500

@app.route('/health')
def health():
    """Sistem sağlık kontrolü"""
    try:
        if searcher:
            # Basit bir test sorgusu
            test_results = searcher.search_dense("test", 1)
            return jsonify({
                'status': 'healthy',
                'searcher': 'ready',
                'qdrant': 'connected'
            })
        else:
            return jsonify({
                'status': 'unhealthy',
                'searcher': 'not_ready'
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Templates klasörünü oluştur
    os.makedirs('templates', exist_ok=True)
    
    # Searcher'ı başlat
    print("🚀 CVE RAG Web Arayüzü başlatılıyor...")
    if init_searcher():
        print("✅ Searcher başarıyla başlatıldı")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("❌ Searcher başlatılamadı. Qdrant'ın çalıştığından emin olun.")

