/**
 * RAG Arama Sayfası
 * CVE veritabanında direkt arama yapılabilir
 */

import { useState, useEffect } from 'react';
import { Search, AlertCircle, Shield, Calendar, ExternalLink } from 'lucide-react';
import Button from '../components/common/Button/Button';
import Card from '../components/common/Card/Card';
import Input from '../components/common/Input/Input';
import { pentagentAPI } from '../services/pentagentAPI';

const RagSearch = () => {
  const [query, setQuery] = useState('');
  const [severity, setSeverity] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [stats, setStats] = useState(null);

  // Sayfa yüklendiğinde stats al
  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const data = await pentagentAPI.getRagStats();
      setStats(data.stats);
    } catch (err) {
      console.error('Stats yüklenemedi:', err);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    
    if (!query.trim()) {
      setError('Lütfen bir arama terimi girin');
      return;
    }

    setLoading(true);
    setError('');
    setResults([]);

    try {
      const data = await pentagentAPI.searchCVE({
        query: query.trim(),
        limit: 10,
        severity: severity || undefined
      });

      setResults(data.results);
      
      if (data.results.length === 0) {
        setError('Sonuç bulunamadı. Farklı arama terimleri deneyin.');
      }
    } catch (err) {
      setError(err.message || 'Arama sırasında hata oluştu');
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity) => {
    const colors = {
      CRITICAL: 'text-red-600 bg-red-100 border-red-300',
      HIGH: 'text-orange-600 bg-orange-100 border-orange-300',
      MEDIUM: 'text-yellow-600 bg-yellow-100 border-yellow-300',
      LOW: 'text-blue-600 bg-blue-100 border-blue-300'
    };
    return colors[severity] || 'text-gray-600 bg-gray-100 border-gray-300';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-gray-900 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">
            CVE Arama Sistemi
          </h1>
          <p className="text-gray-300">
            95,000+ CVE veritabanında anlam tabanlı arama yapın
          </p>
          
          {/* Stats */}
          {stats?.available && (
            <div className="mt-4 flex items-center gap-4 text-sm text-gray-400">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-green-400" />
                <span>RAG Servisi Aktif</span>
              </div>
              <div className="flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-blue-400" />
                <span>{stats.total_cves?.toLocaleString()} CVE Yüklü</span>
              </div>
            </div>
          )}
        </div>

        {/* Search Form */}
        <Card className="mb-6">
          <form onSubmit={handleSearch} className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-1">
                <Input
                  type="text"
                  placeholder="Örn: SQL injection, remote code execution, buffer overflow..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full"
                  disabled={loading}
                />
              </div>
              
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="px-4 py-2 bg-gray-800 text-white border border-gray-700 rounded-lg focus:border-purple-500 focus:outline-none"
                disabled={loading}
              >
                <option value="">Tüm Severity</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>

              <Button
                type="submit"
                variant="primary"
                disabled={loading}
                className="flex items-center gap-2"
              >
                <Search className="w-5 h-5" />
                {loading ? 'Aranıyor...' : 'Ara'}
              </Button>
            </div>

            {error && (
              <div className="flex items-center gap-2 text-red-400 text-sm">
                <AlertCircle className="w-4 h-4" />
                <span>{error}</span>
              </div>
            )}
          </form>
        </Card>

        {/* Results */}
        {results.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-white">
                {results.length} Sonuç Bulundu
              </h2>
              <span className="text-sm text-gray-400">
                Alakalı sonuçlar önce gösterilir
              </span>
            </div>

            {results.map((result, index) => (
              <Card key={result.cve_id} className="hover:border-purple-500 transition-all">
                <div className="space-y-3">
                  {/* CVE Header */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl font-bold text-white">
                        #{index + 1}
                      </span>
                      <div>
                        <h3 className="text-lg font-semibold text-white">
                          {result.cve_id}
                        </h3>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={`px-2 py-1 text-xs font-medium rounded border ${getSeverityColor(result.severity)}`}>
                            {result.severity || 'N/A'}
                          </span>
                          {result.base_score && (
                            <span className="px-2 py-1 text-xs font-medium bg-gray-700 text-gray-300 rounded">
                              CVSS: {result.base_score}
                            </span>
                          )}
                          {result.attack_vector && (
                            <span className="px-2 py-1 text-xs font-medium bg-gray-700 text-gray-300 rounded">
                              {result.attack_vector}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <div className="text-sm font-medium text-purple-400">
                        Skor: {(result.score * 100).toFixed(1)}%
                      </div>
                      {result.published_date && (
                        <div className="flex items-center gap-1 text-xs text-gray-400 mt-1">
                          <Calendar className="w-3 h-3" />
                          <span>{result.published_date}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Description */}
                  <p className="text-gray-300 text-sm leading-relaxed">
                    {result.description}
                  </p>

                  {/* Actions */}
                  <div className="flex items-center gap-2 pt-2 border-t border-gray-700">
                    <a
                      href={`https://nvd.nist.gov/vuln/detail/${result.cve_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-sm text-purple-400 hover:text-purple-300 transition-colors"
                    >
                      <ExternalLink className="w-4 h-4" />
                      NVD'de Görüntüle
                    </a>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
          </div>
        )}

        {/* Empty State */}
        {!loading && results.length === 0 && !error && (
          <Card className="text-center py-12">
            <Search className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">
              CVE Araması Yapın
            </h3>
            <p className="text-gray-400">
              Zafiyet türü, teknoloji veya açıklama ile arama yapabilirsiniz.
              <br />
              Örnek: "SQL injection", "Apache vulnerability", "remote code execution"
            </p>
          </Card>
        )}

        {/* Info Box */}
        <Card className="mt-6 bg-gradient-to-r from-purple-900/20 to-blue-900/20 border-purple-500/30">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-purple-400 mt-1 flex-shrink-0" />
            <div className="text-sm text-gray-300 space-y-1">
              <p className="font-semibold text-white">Arama İpuçları:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Zafiyet türü ile arayın: "SQL injection", "XSS", "buffer overflow"</li>
                <li>Teknoloji adı ekleyin: "Apache Log4j", "WordPress plugin"</li>
                <li>Severity filtresi kullanarak kritik zafiyetleri bulun</li>
                <li>Semantik arama sayesinde benzer kavramları da bulur</li>
              </ul>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default RagSearch;

