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
  Loader2
} from 'lucide-react';
import Button from '../../common/Button';
import Card from '../../common/Card';
import { pentagentAPI } from '../../../services/pentagentAPI';

const ContextPanel = ({ isOpen, conversationId, onToggle, scanResults }) => {
  const [activeTab, setActiveTab] = useState('cve');
  const [cveResults, setCveResults] = useState([]);
  const [cveLoading, setCveLoading] = useState(false);
  const [cveError, setCveError] = useState('');

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
      fetchCVESuggestions();
    }
  }, [scanResults, activeTab]);

  const fetchCVESuggestions = async () => {
    if (!scanResults) return;

    setCveLoading(true);
    setCveError('');
    
    try {
      const data = await pentagentAPI.analyzeScanResults(scanResults, 5);
      setCveResults(data.results || []);
      
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

  if (!isOpen) return null;

  return (
    <div className="w-80 bg-obsidian-900 border-l border-obsidian-700 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-obsidian-700 flex items-center justify-between">
        <h3 className="font-semibold text-text-primary">Scan Context</h3>
        <button
          onClick={onToggle}
          className="p-2 text-text-tertiary hover:text-text-secondary hover:bg-obsidian-850 rounded-lg transition-all"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-obsidian-700">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm font-medium transition-all ${
                activeTab === tab.id
                  ? 'text-platinum-500 border-b-2 border-platinum-500 bg-platinum-500/5'
                  : 'text-text-secondary hover:text-text-primary hover:bg-obsidian-850'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        
        {activeTab === 'cve' && (
          <>
            {/* CVE Suggestions */}
            {cveLoading ? (
              <div className="flex flex-col items-center justify-center py-12 space-y-3">
                <Loader2 className="w-8 h-8 text-platinum-500 animate-spin" />
                <p className="text-sm text-text-tertiary">CVE analizi yapılıyor...</p>
              </div>
            ) : cveError ? (
              <Card variant="default" className="p-4 text-center">
                <AlertTriangle className="w-8 h-8 text-warning mx-auto mb-2" />
                <p className="text-sm text-text-tertiary">{cveError}</p>
                <Button 
                  variant="secondary" 
                  size="sm" 
                  className="mt-3"
                  onClick={fetchCVESuggestions}
                >
                  Tekrar Dene
                </Button>
              </Card>
            ) : cveResults.length > 0 ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-medium text-text-primary">
                    İlgili CVE'ler ({cveResults.length})
                  </h4>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={fetchCVESuggestions}
                    className="text-xs"
                  >
                    Yenile
                  </Button>
                </div>
                {cveResults.map((cve, index) => (
                  <Card key={cve.cve_id} variant="default" className="p-3 hover:border-platinum-500/50 transition-all">
                    <div className="space-y-2">
                      {/* CVE Header */}
                      <div className="flex items-start justify-between">
                        <div>
                          <h5 className="text-sm font-semibold text-text-primary">{cve.cve_id}</h5>
                          <div className="flex items-center gap-2 mt-1">
                            {cve.severity && (
                              <span className={`w-2 h-2 rounded-full ${getSeverityColor(cve.severity)}`} />
                            )}
                            <span className="text-xs text-text-tertiary">{cve.severity || 'N/A'}</span>
                            {cve.base_score && (
                              <span className="text-xs text-text-tertiary">
                                • CVSS: {cve.base_score}
                              </span>
                            )}
                          </div>
                        </div>
                        <div className="text-xs text-platinum-400 font-medium">
                          {(cve.score * 100).toFixed(0)}%
                        </div>
                      </div>

                      {/* Description */}
                      <p className="text-xs text-text-secondary leading-relaxed line-clamp-3">
                        {cve.description}
                      </p>

                      {/* Link */}
                      <a
                        href={`https://nvd.nist.gov/vuln/detail/${cve.cve_id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-xs text-platinum-400 hover:text-platinum-300 transition-colors"
                      >
                        <ExternalLink className="w-3 h-3" />
                        <span>NVD'de Aç</span>
                      </a>
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <Card variant="default" className="p-6 text-center">
                <Database className="w-10 h-10 text-text-tertiary mx-auto mb-3" />
                <p className="text-sm text-text-tertiary mb-2">CVE önerisi yok</p>
                <p className="text-xs text-text-tertiary">
                  Tarama tamamlandığında ilgili CVE'ler burada görünecek
                </p>
              </Card>
            )}
          </>
        )}
      </div>

      {/* Actions */}
      <div className="p-4 border-t border-obsidian-700 space-y-3">
        <Button variant="primary" className="w-full">
          <Download className="w-4 h-4 mr-2" />
          Generate Report
        </Button>
        <Button variant="secondary" className="w-full">
          <Share2 className="w-4 h-4 mr-2" />
          Export Results
        </Button>
      </div>
    </div>
  );
};

export default ContextPanel;
