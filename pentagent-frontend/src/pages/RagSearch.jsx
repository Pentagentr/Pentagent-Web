/**
 * RAG Arama Sayfası
 * CVE veritabanında direkt arama yapılabilir
 */

import { useState, useEffect } from 'react';
import { Search, AlertCircle, Shield, Calendar, ExternalLink } from 'lucide-react';
import AppNavbar from '../components/layout/AppNavbar';
import Button from '../components/common/Button/Button';
import Card from '../components/common/Card/Card';
import Input from '../components/common/Input/Input';
import CVEModal from '../components/chat/CVEModal';
import { pentagentAPI } from '../services/pentagentAPI';

const RagSearch = () => {
  const [query, setQuery] = useState('');
  const [severity, setSeverity] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [stats, setStats] = useState(null);
  const [selectedCve, setSelectedCve] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [optimizedQuery, setOptimizedQuery] = useState(null);

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
    setOptimizedQuery(null);

    try {
      const data = await pentagentAPI.searchCVE({
        query: query.trim(),
        limit: 10,
        severity: severity || undefined
      });

      setResults(data.results);
      
      // AI ile optimize edilmiş query'yi kaydet
      if (data.optimized_query && data.optimized_query !== query.trim()) {
        setOptimizedQuery(data.optimized_query);
      }
      
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
      CRITICAL: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
      HIGH: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
      MEDIUM: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
      LOW: 'text-blue-400 bg-blue-500/10 border-blue-500/20'
    };
    return colors[severity] || 'text-text-tertiary bg-obsidian-850 border-obsidian-700';
  };

  const handleCveClick = (cve) => {
    setSelectedCve(cve);
    setModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-obsidian-950">
      {/* Navbar */}
      <AppNavbar />
      
      <div className="max-w-5xl mx-auto p-6 pt-20">
        {/* Header */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-semibold text-text-primary mb-1">
                CVE Intelligence Database
              </h1>
              <p className="text-text-tertiary text-sm">
                Search 95,000+ vulnerability records with semantic AI
              </p>
            </div>
            
            {/* Stats */}
            {stats?.available && (
              <div className="flex items-center gap-3 text-xs">
                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-green-500/10 border border-green-500/20 rounded-lg">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                  <span className="text-green-400">Live</span>
                </div>
                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-500/10 border border-purple-500/20 rounded-lg">
                  <Shield className="w-3.5 h-3.5 text-purple-400" />
                  <span className="text-purple-300">{stats.total_cves?.toLocaleString()} CVE</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Search Form */}
        <div className="bg-obsidian-900 border border-obsidian-700 rounded-lg p-4 mb-6">
          <form onSubmit={handleSearch}>
            <div className="flex gap-3">
              <div className="flex-1">
                <input
                  type="text"
                  placeholder="Search vulnerabilities... (e.g., SQL injection, Apache Log4j)"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full px-4 py-2.5 bg-obsidian-850 border border-obsidian-700 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 rounded-lg text-text-primary placeholder:text-text-tertiary focus:outline-none transition-all duration-300 text-sm"
                  disabled={loading}
                />
              </div>
              
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="px-4 py-2.5 bg-obsidian-850 border border-obsidian-700 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 rounded-lg text-text-secondary focus:outline-none transition-all duration-300 text-sm"
                disabled={loading}
              >
                <option value="">All Severity</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>

              <button
                type="submit"
                disabled={loading}
                className="flex items-center gap-2 px-6 py-2.5 bg-purple-500 hover:bg-purple-600 disabled:bg-obsidian-700 disabled:text-text-tertiary text-white font-medium rounded-lg transition-all duration-300 hover:shadow-lg hover:shadow-purple-500/20 text-sm"
              >
                <Search className="w-4 h-4" />
                {loading ? 'Searching...' : 'Search'}
              </button>
            </div>

            {error && (
              <div className="flex items-center gap-2 text-rose-400 text-sm mt-3">
                <AlertCircle className="w-4 h-4" />
                <span>{error}</span>
              </div>
            )}
          </form>
        </div>

        {/* Results */}
        {results.length > 0 && (
          <div className="space-y-3">
            {/* AI Optimization Notice */}
            {optimizedQuery && (
              <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-3 mb-3">
                <div className="flex items-start gap-2">
                  <div className="flex-shrink-0 mt-0.5">
                    <div className="w-5 h-5 rounded-full bg-purple-500/20 flex items-center justify-center">
                      <span className="text-purple-400 text-xs">✨</span>
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[10px] font-medium text-purple-300 mb-1">
                      AI Optimized Search
                    </p>
                    <p className="text-xs text-text-secondary">
                      Your query was optimized: <span className="text-purple-400 font-mono">{optimizedQuery}</span>
                    </p>
                  </div>
                </div>
              </div>
            )}

            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-text-primary">
                {results.length} Results Found
              </h2>
              <span className="text-xs text-text-tertiary">
                Sorted by relevance
              </span>
            </div>

            {results.map((result, index) => (
              <div 
                key={result.cve_id} 
                onClick={() => handleCveClick(result)}
                className="bg-obsidian-900 border border-purple-500/20 hover:border-purple-500/40 rounded-lg p-4 transition-all duration-300 cursor-pointer group"
              >
                <div className="space-y-3">
                  {/* CVE Header */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-lg font-bold text-purple-400/50 group-hover:text-purple-400 transition-colors">
                        #{index + 1}
                      </span>
                      <div>
                        <div className="flex items-center gap-2">
                          <Shield size={14} className="text-purple-400" />
                          <h3 className="text-sm font-semibold text-platinum group-hover:text-purple-300 transition-colors">
                            {result.cve_id}
                          </h3>
                        </div>
                        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                          <span className={`px-2 py-0.5 text-[10px] font-medium rounded border ${getSeverityColor(result.severity)}`}>
                            {result.severity || 'N/A'}
                          </span>
                          {result.base_score && (
                            <span className="px-2 py-0.5 text-[10px] font-medium bg-purple-500/10 border border-purple-500/20 text-purple-400 rounded">
                              CVSS: {result.base_score}
                            </span>
                          )}
                          {result.attack_vector && (
                            <span className="px-2 py-0.5 text-[10px] font-medium bg-obsidian-850 border border-obsidian-700 text-text-tertiary rounded">
                              {result.attack_vector}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      {result.published_date && (
                        <div className="flex items-center gap-1 text-[10px] text-text-tertiary mt-1">
                          <Calendar className="w-3 h-3" />
                          <span>{result.published_date}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Description */}
                  <p className="text-text-secondary text-xs leading-relaxed line-clamp-2">
                    {result.description}
                  </p>

                  {/* Actions */}
                  <div className="flex items-center justify-between pt-2 border-t border-purple-500/10">
                    <a
                      href={`https://nvd.nist.gov/vuln/detail/${result.cve_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="flex items-center gap-1 text-[10px] text-purple-400 hover:text-purple-300 transition-colors"
                    >
                      <ExternalLink className="w-3 h-3" />
                      NVD
                    </a>
                    
                    <span className="text-[10px] text-text-tertiary opacity-0 group-hover:opacity-100 transition-opacity">
                      Click for full details →
                    </span>
                  </div>
                </div>
              </div>
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
          <div className="text-center py-16 bg-obsidian-900 border border-purple-500/20 rounded-lg">
            <Search className="w-12 h-12 text-purple-400/50 mx-auto mb-3" />
            <h3 className="text-base font-medium text-platinum mb-2">
              Search CVE Database
            </h3>
            <p className="text-text-tertiary text-sm max-w-md mx-auto">
              Enter vulnerability type, technology name, CVE ID, or version to find relevant CVEs
            </p>
            <p className="text-purple-400 text-xs mt-2">
              💡 Example: "Apache 2.4.49", "CVE-2021-44228", "SQL injection"
            </p>
          </div>
        )}
      </div>

      {/* CVE Modal */}
      {modalOpen && selectedCve && (
        <CVEModal 
          cve={selectedCve}
          onClose={() => {
            setModalOpen(false);
            setSelectedCve(null);
          }}
        />
      )}
    </div>
  );
};

export default RagSearch;

