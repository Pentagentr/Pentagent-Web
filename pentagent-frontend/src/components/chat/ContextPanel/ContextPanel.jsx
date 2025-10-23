import React, { useState, useEffect } from 'react';
import { 
  X, 
  Target, 
  Clock, 
  Shield, 
  AlertTriangle, 
  CheckCircle,
  BarChart3,
  Download,
  Share2,
  Settings,
  Database,
  ExternalLink,
  Loader2,
  RefreshCw,
  FileText,
  Brain
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Button from '../../common/Button';
import Card from '../../common/Card';
import { pentagentAPI } from '../../../services/pentagentAPI';

const ContextPanel = ({ isOpen, conversationId, onToggle, scanResults }) => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('cve');
  const [cveResults, setCveResults] = useState([]);
  const [cveLoading, setCveLoading] = useState(false);
  const [cveError, setCveError] = useState('');
  const [reportGenerating, setReportGenerating] = useState(false);

  // Mock data - would come from props/context in real implementation
  const scanContext = {
    target: 'example.com',
    startTime: '2:30 PM',
    duration: '5m 32s',
    status: 'completed',
    toolsUsed: [
      { name: 'Port Scanner', status: 'completed', icon: '🔍' },
      { name: 'Web Crawler', status: 'completed', icon: '🕷️' },
      { name: 'SQL Injection Tester', status: 'running', icon: '💉' },
      { name: 'XSS Detector', status: 'queued', icon: '⚡' }
    ],
    findings: {
      critical: 2,
      high: 8,
      medium: 15,
      low: 17,
      info: 23
    },
    riskScore: 7.8
  };

  const tabs = [
    { id: 'cve', label: 'CVE Suggestions', icon: Database }
  ];

  // Scan sonuçları değiştiğinde CVE analizi yap
  useEffect(() => {
    if (scanResults && activeTab === 'cve') {
      // Her taramada yeni analiz yap
      setCveResults([]); // Önce önceki sonuçları temizle
      fetchCVESuggestions();
    }
  }, [JSON.stringify(scanResults), activeTab, conversationId]); // JSON.stringify ile deep comparison

  const [llmQuery, setLlmQuery] = useState('');
  const [scanSummary, setScanSummary] = useState('');

  const fetchCVESuggestions = async () => {
    if (!scanResults) return;

    setCveLoading(true);
    setCveError('');
    
    try {
      const data = await pentagentAPI.analyzeScanResults(scanResults, 5);
      console.log('🔍 RAG API Response:', data); // DEBUG
      console.log('📝 LLM Query:', data.llm_query); // DEBUG
      console.log('📊 Scan Summary:', data.scan_summary); // DEBUG
      
      setCveResults(data.results || []);
      setLlmQuery(data.llm_query || '');
      setScanSummary(data.scan_summary || '');
      
      if (data.results.length === 0) {
        setCveError('İlgili CVE bulunamadı');
      }
    } catch (error) {
      console.error('CVE analizi hatası:', error);
      setCveError(error.message || 'CVE analizi yapılamadı');
    } finally {
      setCveLoading(false);
    }
  };

  const getSeverityColor = (severity) => {
    const colors = {
      CRITICAL: 'bg-rose-500',
      HIGH: 'bg-rose-500',
      MEDIUM: 'bg-warning',
      LOW: 'bg-success'
    };
    return colors[severity] || 'bg-text-tertiary';
  };

  // Rapor oluşturma handler
  const handleGenerateReport = async () => {
    console.log('📄 RAPOR OLUŞTURULUYOR'); // DEBUG
    console.log('📊 scanResults:', scanResults); // DEBUG
    console.log('🛡️ cveResults:', cveResults); // DEBUG
    
    if (!scanResults || !cveResults || cveResults.length === 0) {
      alert('Rapor oluşturmak için önce tarama yapın ve CVE sonuçlarını bekleyin.');
      return;
    }

    setReportGenerating(true);
    
    try {
      // En yakın 3 CVE'yi seç
      const topCVEs = cveResults.slice(0, 3);
      
      // Rapor verilerini localStorage'a kaydet
      const reportData = {
        timestamp: Date.now(),
        scanResults: scanResults,
        cveResults: topCVEs,
        target: scanResults.target || 'Unknown Target',
        generatedAt: new Date().toISOString(),
        llmQuery: llmQuery, // LLM'in oluşturduğu query
        scanSummary: scanSummary // Tarama özeti (LLM'e gönderilecek)
      };
      
      console.log('💾 reportData:', reportData); // DEBUG
      
      localStorage.setItem('pendingReport', JSON.stringify(reportData));
      
      // Rapor sayfasına yönlendir
      navigate('/reports?action=generate');
    } catch (error) {
      console.error('Rapor oluşturma hatası:', error);
      alert('Rapor oluşturulurken bir hata oluştu: ' + error.message);
    } finally {
      setReportGenerating(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="w-full bg-obsidian-900 border-l border-obsidian-700 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-purple-500/10 flex items-center justify-between bg-obsidian-900/50">
        <h3 className="text-sm font-semibold text-platinum">Scan Context</h3>
        <button
          onClick={onToggle}
          className="p-1.5 text-text-tertiary hover:text-purple-400 hover:bg-purple-500/10 rounded-lg transition-all duration-300"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-purple-500/10">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 text-xs font-medium transition-all duration-300 ${
                activeTab === tab.id
                  ? 'text-purple-400 border-b-2 border-purple-500 bg-purple-500/5'
                  : 'text-text-secondary hover:text-purple-300 hover:bg-purple-500/5'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin scrollbar-thumb-purple-500/20 scrollbar-track-transparent">
        
        {/* LLM Query - TÜM TAB'LARDA GÖSTER (Scan sonuçlarının üstünde) */}
        {(llmQuery || cveLoading) && activeTab === 'cve' && (
          <div className="bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30 rounded-lg p-3 mb-3">
            <div className="flex items-center gap-2 mb-2">
              <Brain className="w-4 h-4 text-purple-400" />
              <span className="text-xs font-semibold text-purple-300">🤖 AI Tarama Sorgusu</span>
            </div>
            {cveLoading ? (
              <div className="flex items-center gap-2 text-xs text-text-tertiary">
                <Loader2 className="w-3 h-3 animate-spin" />
                <span>LLM tarama sonuçlarını analiz ediyor...</span>
              </div>
            ) : llmQuery ? (
              <div className="bg-obsidian-950/70 p-3 rounded-lg border border-purple-500/20">
                <p className="text-xs text-purple-200 font-mono leading-relaxed">
                  "{llmQuery}"
                </p>
              </div>
            ) : null}
          </div>
        )}
        
        {activeTab === 'cve' && (
          <>
            {/* CVE Suggestions */}
            {(llmQuery || cveLoading) && false && (
              <div className="bg-obsidian-900/30 border border-purple-500/10 rounded-lg p-3 mb-3">
                <div className="flex items-center gap-2 mb-2">
                  <Brain className="w-3 h-3 text-purple-400" />
                  <span className="text-xs font-medium text-purple-400">AI Query</span>
                </div>
                {cveLoading ? (
                  <div className="flex items-center gap-2 text-xs text-text-tertiary">
                    <Loader2 className="w-3 h-3 animate-spin" />
                    <span>Query oluşturuluyor...</span>
                  </div>
                ) : llmQuery ? (
                  <>
                    <p className="text-xs text-text-secondary font-mono bg-obsidian-950/50 p-2 rounded border border-purple-500/10 mb-2">
                      "{llmQuery}"
                    </p>
                    {scanSummary && (
                      <div className="pt-2 border-t border-purple-500/10">
                        <div className="flex items-center gap-2 mb-1">
                          <FileText className="w-3 h-3 text-platinum-400" />
                          <span className="text-[10px] font-medium text-platinum-400">Tarama Özeti</span>
                        </div>
                        <p className="text-[10px] text-text-tertiary line-clamp-2">
                          {scanSummary}
                        </p>
                      </div>
                    )}
                  </>
                ) : null}
              </div>
            )}

            {cveLoading ? (
              <div className="flex flex-col items-center justify-center py-8 space-y-3">
                <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
                <p className="text-xs text-text-tertiary">CVE araması yapılıyor...</p>
              </div>
            ) : cveError ? (
              <div className="bg-obsidian-900/50 border border-purple-500/20 rounded-lg p-4 text-center">
                <AlertTriangle className="w-6 h-6 text-warning mx-auto mb-2" />
                <p className="text-xs text-text-tertiary">{cveError}</p>
                <button
                  onClick={fetchCVESuggestions}
                  className="mt-3 px-3 py-1.5 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 rounded-lg text-xs font-medium text-purple-400 transition-all duration-300"
                >
                  Tekrar Dene
                </button>
              </div>
            ) : cveResults.length > 0 ? (
              <div className="space-y-2.5">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-xs font-medium text-platinum">
                    İlgili CVE'ler ({cveResults.length})
                  </h4>
                  <button
                    onClick={fetchCVESuggestions}
                    className="px-2 py-1 text-[10px] text-purple-400 hover:text-purple-300 hover:bg-purple-500/10 rounded transition-all"
                  >
                    Yenile
                  </button>
                </div>
                {cveResults.map((cve) => (
                  <div key={cve.cve_id} className="bg-obsidian-900/50 border border-purple-500/20 hover:border-purple-500/40 rounded-lg p-3 transition-all duration-300">
                    <div className="space-y-2">
                      {/* CVE Header */}
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-1.5 mb-1">
                            <Shield size={12} className="text-purple-400" />
                            <h5 className="text-xs font-semibold text-platinum">{cve.cve_id}</h5>
                          </div>
                          <div className="flex items-center gap-2 flex-wrap text-[10px]">
                            {cve.severity && (
                              <div className="flex items-center gap-1">
                                <span className={`w-1.5 h-1.5 rounded-full ${getSeverityColor(cve.severity)}`} />
                                <span className="text-text-tertiary">{cve.severity}</span>
                              </div>
                            )}
                            {cve.base_score && (
                              <span className="text-purple-400">CVSS: {cve.base_score}</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Description */}
                      <p className="text-xs text-text-secondary leading-relaxed line-clamp-3">
                        {cve.description}
                      </p>

                      {/* Link */}
                      <div className="pt-2 border-t border-purple-500/10">
                        <a
                          href={`https://nvd.nist.gov/vuln/detail/${cve.cve_id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-1.5 text-[10px] text-purple-400 hover:text-purple-300 transition-colors"
                        >
                          <ExternalLink className="w-3 h-3" />
                          <span>View on NVD</span>
                        </a>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-obsidian-900/50 border border-purple-500/20 rounded-lg p-6 text-center">
                <Database className="w-8 h-8 text-purple-400/50 mx-auto mb-3" />
                <p className="text-xs text-text-tertiary mb-1">CVE önerisi yok</p>
                <p className="text-[10px] text-text-tertiary">
                  Tarama tamamlandığında ilgili CVE'ler burada görünecek
                </p>
              </div>
            )}
          </>
        )}
      </div>

      {/* Actions */}
      <div className="p-3 border-t border-purple-500/10 space-y-2 bg-obsidian-900/50">
        <button 
          onClick={handleGenerateReport}
          disabled={reportGenerating || !cveResults || cveResults.length === 0}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 rounded-lg text-xs font-medium text-purple-400 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {reportGenerating ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              Oluşturuluyor...
            </>
          ) : (
            <>
              <Download className="w-3.5 h-3.5" />
              Generate Report
            </>
          )}
        </button>
        <button className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-obsidian-850 hover:bg-obsidian-800 border border-purple-500/20 rounded-lg text-xs font-medium text-text-secondary hover:text-purple-400 transition-all duration-300">
          <Share2 className="w-3.5 h-3.5" />
          Export Results
        </button>
      </div>
    </div>
  );
};

export default ContextPanel;
