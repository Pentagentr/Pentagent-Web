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
      CRITICAL: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
      HIGH: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
      MEDIUM: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20',
      LOW: 'text-blue-400 bg-blue-500/10 border-blue-500/20'
    };
    return colors[severity] || 'text-text-tertiary bg-obsidian-850 border-obsidian-700';
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
                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-obsidian-900 border border-obsidian-700 rounded-lg">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-text-secondary">Live</span>
                </div>
                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-obsidian-900 border border-obsidian-700 rounded-lg">
                  <Shield className="w-3.5 h-3.5 text-platinum-500" />
                  <span className="text-text-secondary">{stats.total_cves?.toLocaleString()} CVE</span>
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
                  className="w-full px-4 py-2.5 bg-obsidian-850 border border-obsidian-700 focus:border-platinum-500 rounded-lg text-text-primary placeholder:text-text-tertiary focus:outline-none transition-colors text-sm"
                  disabled={loading}
                />
              </div>
              
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="px-4 py-2.5 bg-obsidian-850 border border-obsidian-700 focus:border-platinum-500 rounded-lg text-text-secondary focus:outline-none transition-colors text-sm"
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
                className="flex items-center gap-2 px-6 py-2.5 bg-platinum-500 hover:bg-platinum-600 disabled:bg-obsidian-700 disabled:text-text-tertiary text-obsidian-950 font-medium rounded-lg transition-colors text-sm"
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
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-medium text-text-primary">
                {results.length} Results Found
              </h2>
              <span className="text-xs text-text-tertiary">
                Sorted by relevance
              </span>
            </div>

            {results.map((result, index) => (
              <div key={result.cve_id} className="bg-obsidian-900 border border-obsidian-700 hover:border-platinum-500/50 rounded-lg p-4 transition-all">
                <div className="space-y-3">
                  {/* CVE Header */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl font-bold text-white">
                        #{index + 1}
                      </span>
                      <div>
                      <h3 className="text-base font-semibold text-text-primary">
                        {result.cve_id}
                      </h3>
                      <div className="flex items-center gap-2 mt-1.5">
                        <span className={`px-2 py-0.5 text-xs font-medium rounded ${getSeverityColor(result.severity)}`}>
                          {result.severity || 'N/A'}
                        </span>
                        {result.base_score && (
                          <span className="px-2 py-0.5 text-xs font-medium bg-obsidian-850 text-text-tertiary rounded">
                            CVSS: {result.base_score}
                          </span>
                        )}
                        {result.attack_vector && (
                          <span className="px-2 py-0.5 text-xs font-medium bg-obsidian-850 text-text-tertiary rounded">
                            {result.attack_vector}
                          </span>
                        )}
                      </div>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <div className="text-xs font-medium text-platinum-400">
                        {(result.score * 100).toFixed(0)}%
                      </div>
                      {result.published_date && (
                        <div className="flex items-center gap-1 text-xs text-text-tertiary mt-1">
                          <Calendar className="w-3 h-3" />
                          <span>{result.published_date}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Description */}
                  <p className="text-text-secondary text-sm leading-relaxed">
                    {result.description}
                  </p>

                  {/* Actions */}
                  <div className="flex items-center gap-2 pt-2.5 border-t border-obsidian-700">
                    <a
                      href={`https://nvd.nist.gov/vuln/detail/${result.cve_id}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-xs text-platinum-400 hover:text-platinum-300 transition-colors"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      View on NVD
                    </a>
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
          <div className="text-center py-16 bg-obsidian-900 border border-obsidian-700 rounded-lg">
            <Search className="w-12 h-12 text-text-tertiary mx-auto mb-3" />
            <h3 className="text-base font-medium text-text-primary mb-2">
              Search CVE Database
            </h3>
            <p className="text-text-tertiary text-sm max-w-md mx-auto">
              Enter vulnerability type, technology name, or description to find relevant CVEs
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default RagSearch;

