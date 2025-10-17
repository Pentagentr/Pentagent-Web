import React, { useState } from 'react';
import { 
  X, 
  Download, 
  ChevronLeft,
  ChevronRight,
  FileText,
  AlertTriangle,
  Shield,
  Target,
  Clock,
  CheckCircle,
  BookOpen,
  TrendingUp,
  Loader2,
  Database
} from 'lucide-react';

const ReportViewer = ({ report, isOpen, onClose }) => {
  const [currentSection, setCurrentSection] = useState('yonetici-ozeti');
  const [downloading, setDownloading] = useState(false);

  if (!isOpen || !report) return null;

  const sections = [
    { id: 'yonetici-ozeti', title: 'Yönetici Özeti', icon: FileText },
    { id: 'metodoloji', title: 'Metodoloji', icon: Shield },
    { id: 'detayli-bulgular', title: 'Detaylı Bulgular', icon: Target },
    { id: 'cve-detaylari', title: 'CVE Detayları', icon: Database },
    { id: 'tool-ciktilari', title: 'Tool Çıktıları', icon: Database },
    { id: 'oneriler', title: 'Öneriler', icon: CheckCircle }
  ];

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical': return 'text-rose-500 bg-rose-500/10';
      case 'high': return 'text-rose-400 bg-rose-400/10';
      case 'medium': return 'text-amber-500 bg-amber-500/10';
      case 'low': return 'text-emerald-500 bg-emerald-500/10';
      default: return 'text-platinum-500 bg-platinum-500/10';
    }
  };

  const getSeverityText = (severity) => {
    const map = {
      'critical': 'KRİTİK', 'high': 'YÜKSEK',
      'medium': 'ORTA', 'low': 'DÜŞÜK'
    };
    return map[severity?.toLowerCase()] || severity;
  };

  const getRiskColor = (score) => {
    if (score >= 70) return 'text-rose-500';
    if (score >= 40) return 'text-amber-500';
    return 'text-emerald-500';
  };

  const handleDownload = async (format = 'pdf') => {
    try {
      setDownloading(true);
      const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseURL}/api/reports/${report.report_id}/download?format=${format}`);
      
      if (!response.ok) throw new Error('Rapor indirilemedi');
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.report_id}.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Download error:', error);
      alert('Rapor indirilemedi');
    } finally {
      setDownloading(false);
    }
  };

  // 1. YÖNETİCİ ÖZETİ
  const renderYoneticiOzeti = () => {
    const data = report.structured_data?.executive_summary || {};
    
    return (
      <div className="space-y-6">
        <div className="prose prose-invert max-w-none">
          <p className="text-text-secondary leading-relaxed">{data.genel_degerlendirme}</p>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-obsidian-900/50 border border-platinum-500/10 rounded-lg p-5">
            <h4 className="text-sm font-medium text-text-primary mb-3">Risk Skoru</h4>
            <div className="flex items-baseline gap-3 mb-3">
              <div className={`text-4xl font-bold ${getRiskColor(data.risk_skoru)}`}>
                {data.risk_skoru}
              </div>
              <span className="text-text-tertiary text-sm">/100</span>
            </div>
            <div className="w-full bg-obsidian-950 rounded-full h-2 overflow-hidden">
              <div 
                className={`h-full transition-all ${
                  data.risk_skoru >= 70 ? 'bg-rose-500' : 
                  data.risk_skoru >= 40 ? 'bg-amber-500' : 'bg-emerald-500'
                }`}
                style={{ width: `${data.risk_skoru}%` }}
              />
            </div>
            <div className={`mt-2 text-sm font-medium ${getRiskColor(data.risk_skoru)}`}>
              {data.risk_seviyesi}
            </div>
          </div>
          
          <div className="bg-obsidian-900/50 border border-platinum-500/10 rounded-lg p-5">
            <h4 className="text-sm font-medium text-text-primary mb-3">Bulgular</h4>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(report.vulnerabilities || {}).map(([severity, count]) => (
                <div key={severity} className="text-center py-2 bg-obsidian-950/50 rounded">
                  <div className={`text-xl font-bold ${getSeverityColor(severity).split(' ')[0]}`}>
                    {count}
                  </div>
                  <div className="text-xs text-text-tertiary uppercase mt-0.5">
                    {getSeverityText(severity)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        {data.kritik_bulgular && data.kritik_bulgular.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-text-primary mb-3">Kritik Bulgular</h4>
            <div className="space-y-2">
              {data.kritik_bulgular.map((bulgu, index) => (
                <div key={index} className="bg-obsidian-900/50 border border-platinum-500/10 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-4 h-4 text-rose-500 flex-shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h5 className="text-sm font-medium text-text-primary truncate">{bulgu.baslik}</h5>
                        <span className={`px-2 py-0.5 rounded text-xs flex-shrink-0 ${getSeverityColor(bulgu.severity)}`}>
                          {getSeverityText(bulgu.severity)}
                        </span>
                      </div>
                      <p className="text-xs text-text-secondary line-clamp-2">{bulgu.is_etkisi}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  // 2. METODOLOJİ
  const renderMetodoloji = () => {
    const data = report.structured_data?.methodology || {};
    
    return (
      <div className="space-y-6">
        <div className="prose prose-invert max-w-none">
          <p className="text-text-secondary text-sm leading-relaxed">{data.aciklama}</p>
        </div>
        
        <div className="bg-obsidian-900/50 border border-platinum-500/10 rounded-lg p-5 space-y-4">
          <div className="flex items-center gap-3">
            <Target className="w-4 h-4 text-platinum-500" />
            <div className="flex-1 min-w-0">
              <div className="text-xs text-text-tertiary">Hedef</div>
              <div className="text-sm text-text-primary font-medium truncate">{data.kapsam}</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Clock className="w-4 h-4 text-platinum-500" />
            <div className="flex-1">
              <div className="text-xs text-text-tertiary">Tarih</div>
              <div className="text-sm text-text-primary font-medium">{data.test_baslangic}</div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Shield className="w-4 h-4 text-platinum-500" />
            <div className="flex-1">
              <div className="text-xs text-text-tertiary">Standartlar</div>
              <div className="text-sm text-text-primary font-medium">{data.standartlar}</div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // 3. DETAYLI BULGULAR (Risk Matrix ve Bulgular Özeti kaldırıldı)
  const renderDetayliBulgular = () => {
    const findings = report.structured_data?.detailed_findings || [];
    const cveReferences = report.structured_data?.cve_references || [];
    
    if (findings.length === 0) {
      return (
        <div className="text-center py-12">
          <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
          <p className="text-text-secondary text-sm">Teknik bulgu tespit edilmedi</p>
        </div>
      );
    }
    
    return (
      <div className="space-y-6">
        {/* Tool Bulguları */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-text-primary">Tespit Edilen Zafiyetler</h3>
          {findings.map((finding) => (
            <div key={finding.id} className="bg-obsidian-900/50 border border-platinum-500/10 rounded-lg p-5">
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="px-2 py-1 bg-obsidian-950 text-text-tertiary rounded text-xs font-mono">
                      #{finding.id}
                    </span>
                    <h4 className="text-sm font-semibold text-text-primary truncate">{finding.baslik}</h4>
                    <span className={`px-2 py-1 rounded text-xs flex-shrink-0 ${getSeverityColor(finding.severity)}`}>
                      {getSeverityText(finding.severity)}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-text-tertiary">
                    {finding.cvss_skoru !== 'N/A' && <span>CVSS: {finding.cvss_skoru}</span>}
                    {finding.cve_id && finding.cve_id !== 'N/A' && <span className="text-platinum-400">{finding.cve_id}</span>}
                    {finding.hedef && <span>Hedef: {finding.hedef}</span>}
                  </div>
                </div>
              </div>
              
              <div className="space-y-3 text-sm">
                <div>
                  <div className="text-xs text-text-tertiary mb-1">Açıklama</div>
                  <p className="text-text-secondary text-xs leading-relaxed">{finding.aciklama}</p>
                </div>
                
                {finding.kanit && finding.kanit !== 'Kanıt bulunamadı' && (
                  <div>
                    <div className="text-xs text-text-tertiary mb-1">Kanıt</div>
                    <pre className="bg-obsidian-950 p-3 rounded text-xs text-emerald-400 overflow-x-auto whitespace-pre-wrap">
                      {finding.kanit}
                    </pre>
                  </div>
                )}
                
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                  <div>
                    <div className="text-xs text-text-tertiary mb-1">İş Etkisi</div>
                    <p className="text-text-secondary text-xs">{finding.is_etkisi}</p>
                  </div>
                  <div>
                    <div className="text-xs text-text-tertiary mb-1">Çözüm</div>
                    <p className="text-text-secondary text-xs">{finding.cozum}</p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* CVE Referansları Tablosu */}
        {cveReferences.length > 0 && (
          <div className="space-y-3">
            <div className="border-t border-platinum-500/10 pt-6">
              <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
                <Database className="w-4 h-4 text-platinum-400" />
                İlişkili CVE Referansları
              </h3>
              <div className="bg-obsidian-900/50 border border-platinum-500/10 rounded-lg overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-obsidian-950 border-b border-platinum-500/10">
                      <tr>
                        <th className="text-left py-3 px-4 text-text-tertiary font-medium">CVE ID</th>
                        <th className="text-left py-3 px-4 text-text-tertiary font-medium">CVSS Skoru</th>
                        <th className="text-left py-3 px-4 text-text-tertiary font-medium">Severity</th>
                        <th className="text-left py-3 px-4 text-text-tertiary font-medium">Açıklama</th>
                        <th className="text-left py-3 px-4 text-text-tertiary font-medium">Etkilenen Sistem</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-platinum-500/10">
                      {cveReferences.map((cve, index) => (
                        <tr key={index} className="hover:bg-obsidian-800/30 transition-colors">
                          <td className="py-3 px-4 font-mono text-platinum-400">{cve.cve_id}</td>
                          <td className="py-3 px-4">
                            <span className="px-2 py-1 bg-obsidian-950 rounded text-text-primary font-medium">
                              {cve.cvss_skoru}
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            <span className={`px-2 py-1 rounded ${getSeverityColor(cve.severity)}`}>
                              {getSeverityText(cve.severity)}
                            </span>
                          </td>
                          <td className="py-3 px-4 text-text-secondary max-w-md">
                            <div className="line-clamp-2">{cve.aciklama}</div>
                          </td>
                          <td className="py-3 px-4 text-text-secondary">{cve.etkilenen_sistem}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <p className="text-xs text-text-tertiary mt-2">
                Toplam {cveReferences.length} ilişkili CVE referansı tespit edildi.
              </p>
            </div>
          </div>
        )}
      </div>
    );
  };

  // 6. ÖNERİLER
  const renderOneriler = () => {
    const data = report.structured_data?.recommendations || {};
    
    return (
      <div className="space-y-4">
        {data.acil_aksiyonlar && data.acil_aksiyonlar.length > 0 && (
          <div className="bg-rose-500/5 border border-rose-500/20 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-rose-400 mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              Acil Aksiyonlar (0-48 Saat)
            </h4>
            <div className="space-y-2">
              {data.acil_aksiyonlar.map((aksiyon, index) => (
                <div key={index} className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 bg-rose-500 rounded-full mt-1.5 flex-shrink-0" />
                  <div className="flex-1">
                    <div className="text-xs font-medium text-text-primary">{aksiyon.baslik}</div>
                    <div className="text-xs text-text-secondary mt-0.5">{aksiyon.oneri}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {data.kisa_vade_aksiyonlar && data.kisa_vade_aksiyonlar.length > 0 && (
          <div className="bg-amber-500/5 border border-amber-500/20 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Kısa Vade (1-7 Gün)
            </h4>
            <div className="space-y-2">
              {data.kisa_vade_aksiyonlar.map((aksiyon, index) => (
                <div key={index} className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 bg-amber-500 rounded-full mt-1.5 flex-shrink-0" />
                  <div className="flex-1">
                    <div className="text-xs font-medium text-text-primary">{aksiyon.baslik}</div>
                    <div className="text-xs text-text-secondary mt-0.5">{aksiyon.oneri}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {data.stratejik_iyilestirmeler && data.stratejik_iyilestirmeler.length > 0 && (
          <div className="bg-obsidian-900/50 border border-platinum-500/10 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-platinum-400 mb-3 flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Stratejik İyileştirmeler
            </h4>
            <div className="space-y-3">
              {data.stratejik_iyilestirmeler.map((iyilestirme, index) => (
                <div key={index}>
                  <div className="text-xs font-medium text-text-primary mb-1">{iyilestirme.alan}</div>
                  <div className="text-xs text-text-secondary pl-3 border-l-2 border-platinum-500/30">
                    {iyilestirme.oneri}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        
        {data.sonuc && (
          <div className="bg-obsidian-900/50 border border-platinum-500/10 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-text-primary mb-2 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-platinum-500" />
              Sonuç
            </h4>
            <p className="text-xs text-text-secondary leading-relaxed">{data.sonuc}</p>
          </div>
        )}
      </div>
    );
  };

  // 4. CVE DETAYLARI
  const renderCveDetaylari = () => {
    const cveReferences = report.structured_data?.cve_references || report.cve_results || [];
    
    if (cveReferences.length === 0) {
      return (
        <div className="text-center py-12">
          <Database className="w-12 h-12 text-platinum-500 mx-auto mb-3" />
          <p className="text-text-secondary text-sm">CVE referansı bulunamadı</p>
        </div>
      );
    }
    
    return (
      <div className="space-y-6">
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
            <Database className="w-4 h-4 text-platinum-400" />
            Tespit Edilen CVE Referansları ({cveReferences.length})
          </h3>
          
          <div className="grid gap-4">
            {cveReferences.map((cve, index) => (
              <div key={index} className="bg-obsidian-900/50 border border-platinum-500/10 rounded-lg p-5">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="px-2 py-1 bg-obsidian-950 text-text-tertiary rounded text-xs font-mono">
                        {cve.cve_id || `CVE-${index + 1}`}
                      </span>
                      <span className={`px-2 py-1 rounded text-xs flex-shrink-0 ${getSeverityColor(cve.severity)}`}>
                        {getSeverityText(cve.severity)}
                      </span>
                      {cve.base_score && (
                        <span className="px-2 py-1 bg-obsidian-950 rounded text-xs text-platinum-400">
                          CVSS: {cve.base_score}
                        </span>
                      )}
                    </div>
                    
                    {cve.product && (
                      <div className="text-xs text-text-tertiary mb-2">
                        Etkilenen Sistem: <span className="text-platinum-400">{cve.product}</span>
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="space-y-3 text-sm">
                  <div>
                    <div className="text-xs text-text-tertiary mb-1">Açıklama</div>
                    <p className="text-text-secondary text-xs leading-relaxed">
                      {cve.description || 'Açıklama mevcut değil'}
                    </p>
                  </div>
                  
                  {cve.cvss_vector && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">CVSS Vektör</div>
                      <code className="bg-obsidian-950 p-2 rounded text-xs text-emerald-400 block">
                        {cve.cvss_vector}
                      </code>
                    </div>
                  )}
                  
                  {cve.published_date && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                      <div>
                        <div className="text-xs text-text-tertiary mb-1">Yayın Tarihi</div>
                        <p className="text-text-secondary text-xs">{cve.published_date}</p>
                      </div>
                      {cve.modified_date && (
                        <div>
                          <div className="text-xs text-text-tertiary mb-1">Güncellenme Tarihi</div>
                          <p className="text-text-secondary text-xs">{cve.modified_date}</p>
                        </div>
                      )}
                    </div>
                  )}
                  
                  {cve.references && cve.references.length > 0 && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Referanslar</div>
                      <div className="space-y-1">
                        {cve.references.slice(0, 3).map((ref, refIndex) => (
                          <a
                            key={refIndex}
                            href={ref}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-platinum-400 hover:text-platinum-300 underline block truncate"
                          >
                            {ref}
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  // 5. TOOL ÇIKTILARI
  const renderToolCiktilari = () => {
    // Tool çıktılarını hem structured_data'dan hem de direkt report'tan al
    const toolOutputs = report.all_tool_outputs || report.structured_data?.all_tool_outputs || {};
    const toolKeys = Object.keys(toolOutputs);
    
    if (toolKeys.length === 0) {
      return (
        <div className="text-center py-12">
          <Database className="w-12 h-12 text-text-tertiary mx-auto mb-4" />
          <p className="text-text-secondary">Tool çıktısı bulunamadı</p>
        </div>
      );
    }
    
    return (
      <div className="space-y-6">
        <div className="prose prose-invert max-w-none">
          <p className="text-text-secondary leading-relaxed">
            Tarama sırasında çalıştırılan araçların detaylı çıktıları aşağıda listelenmiştir. 
            Bu çıktılar güvenlik bulgularının teknik detaylarını içerir.
          </p>
        </div>
        
        {toolKeys.map((toolName, index) => {
          const toolOutput = toolOutputs[toolName];
          const isSuccess = toolOutput?.success || toolOutput?.data;
          
          return (
            <div key={index} className="bg-obsidian-900/50 border border-platinum-500/10 rounded-lg p-5">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                    isSuccess ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'
                  }`}>
                    <Database className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-medium text-text-primary">{toolName}</h4>
                    <div className="flex items-center gap-2 text-xs">
                      <span className={`px-2 py-1 rounded ${
                        isSuccess ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'
                      }`}>
                        {isSuccess ? 'Başarılı' : 'Başarısız'}
                      </span>
                      {toolOutput?.timestamp && (
                        <span className="text-text-tertiary">
                          {new Date(toolOutput.timestamp).toLocaleString('tr-TR')}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              
              {toolOutput?.ai_summary && (
                <div className="mb-4 p-3 bg-obsidian-950/50 rounded border border-platinum-500/5">
                  <h5 className="text-sm font-medium text-text-primary mb-2">AI Özeti</h5>
                  <p className="text-text-secondary text-sm">{toolOutput.ai_summary}</p>
                </div>
              )}
              
              {toolOutput?.data && (
                <div className="space-y-3">
                  <h5 className="text-sm font-medium text-text-primary">Detaylı Çıktı</h5>
                  
                  {/* Teknoloji Bilgileri */}
                  {toolOutput.data.technologies && toolOutput.data.technologies.length > 0 && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Tespit Edilen Teknolojiler</div>
                      <div className="flex flex-wrap gap-1">
                        {toolOutput.data.technologies.slice(0, 10).map((tech, techIndex) => (
                          <span key={techIndex} className="px-2 py-1 bg-platinum-500/10 text-platinum-400 rounded text-xs">
                            {tech}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Zafiyetler */}
                  {toolOutput.data.vulnerabilities && toolOutput.data.vulnerabilities.length > 0 && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Tespit Edilen Zafiyetler</div>
                      <div className="space-y-2">
                        {toolOutput.data.vulnerabilities.slice(0, 5).map((vuln, vulnIndex) => (
                          <div key={vulnIndex} className="bg-obsidian-950 p-3 rounded">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs font-medium text-text-primary">
                                {vuln.type || vuln.title || 'Zafiyet'}
                              </span>
                              {vuln.severity && (
                                <span className={`px-2 py-1 rounded text-xs ${getSeverityColor(vuln.severity)}`}>
                                  {getSeverityText(vuln.severity)}
                                </span>
                              )}
                            </div>
                            {vuln.description && (
                              <p className="text-xs text-text-secondary">{vuln.description}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Açık Portlar */}
                  {toolOutput.data.open_ports && toolOutput.data.open_ports.length > 0 && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Açık Portlar</div>
                      <div className="flex flex-wrap gap-1">
                        {toolOutput.data.open_ports.slice(0, 10).map((port, portIndex) => (
                          <span key={portIndex} className="px-2 py-1 bg-amber-500/10 text-amber-400 rounded text-xs">
                            {port}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Eksik Güvenlik Başlıkları */}
                  {toolOutput.data.missing_security_headers && toolOutput.data.missing_security_headers.length > 0 && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Eksik Güvenlik Başlıkları</div>
                      <div className="flex flex-wrap gap-1">
                        {toolOutput.data.missing_security_headers.slice(0, 5).map((header, headerIndex) => (
                          <span key={headerIndex} className="px-2 py-1 bg-rose-500/10 text-rose-400 rounded text-xs">
                            {header}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Ham JSON Çıktı */}
                  <div className="bg-obsidian-950/50 rounded border border-platinum-500/5 p-3">
                    <div className="text-xs text-text-tertiary mb-1">Ham JSON Çıktı</div>
                    <pre className="text-xs text-text-secondary whitespace-pre-wrap overflow-x-auto">
                      {JSON.stringify(toolOutput.data, null, 2).substring(0, 2000)}
                      {JSON.stringify(toolOutput.data, null, 2).length > 2000 && '...'}
                    </pre>
                  </div>
                </div>
              )}
              
              {toolOutput?.error && (
                <div className="p-3 bg-rose-500/5 border border-rose-500/20 rounded">
                  <h5 className="text-sm font-medium text-rose-400 mb-1">Hata</h5>
                  <p className="text-rose-300 text-sm">{toolOutput.error}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  const renderCurrentSection = () => {
    switch (currentSection) {
      case 'yonetici-ozeti': return renderYoneticiOzeti();
      case 'metodoloji': return renderMetodoloji();
      case 'detayli-bulgular': return renderDetayliBulgular();
      case 'cve-detaylari': return renderCveDetaylari();
      case 'tool-ciktilari': return renderToolCiktilari();
      case 'oneriler': return renderOneriler();
      default: return <div className="text-center py-12 text-text-secondary">Yükleniyor...</div>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex bg-obsidian-950">
      {/* Sidebar */}
      <div className="w-64 bg-obsidian-900 border-r border-platinum-500/10 flex flex-col">
        <div className="p-4 border-b border-platinum-500/10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-text-primary">Rapor</h2>
            <button
              onClick={onClose}
              className="p-1.5 text-text-tertiary hover:text-text-primary hover:bg-obsidian-850 rounded transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          
          <div className="space-y-1.5 text-xs">
            <div className="flex items-center gap-2 text-text-secondary">
              <Target className="w-3 h-3" />
              <span className="truncate">{report.target}</span>
            </div>
            <div className="flex items-center gap-2 text-text-secondary">
              <Clock className="w-3 h-3" />
              <span>{new Date(report.createdAt).toLocaleDateString('tr-TR')}</span>
            </div>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-3">
          <nav className="space-y-1">
            {sections.map((section) => {
              const Icon = section.icon;
              return (
                <button
                  key={section.id}
                  onClick={() => setCurrentSection(section.id)}
                  className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition-colors ${
                    currentSection === section.id
                      ? 'bg-platinum-500/10 text-platinum-400 font-medium'
                      : 'text-text-secondary hover:text-text-primary hover:bg-obsidian-850'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5 flex-shrink-0" />
                  <span>{section.title}</span>
                </button>
              );
            })}
          </nav>
        </div>
        
        <div className="p-3 border-t border-platinum-500/10 space-y-2">
          <button 
            onClick={() => handleDownload('pdf')}
            disabled={downloading}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-platinum-500/10 hover:bg-platinum-500/20 text-platinum-400 rounded-lg transition-colors text-xs font-medium disabled:opacity-50"
          >
            {downloading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                İndiriliyor...
              </>
            ) : (
              <>
                <Download className="w-3.5 h-3.5" />
                PDF İndir
              </>
            )}
          </button>
          
          <button 
            onClick={() => handleDownload('md')}
            disabled={downloading}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 rounded-lg transition-colors text-xs font-medium disabled:opacity-50"
          >
            {downloading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                İndiriliyor...
              </>
            ) : (
              <>
                <FileText className="w-3.5 h-3.5" />
                Markdown İndir
              </>
            )}
          </button>
        </div>
      </div>
      
      {/* Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <div className="h-12 bg-obsidian-900 border-b border-platinum-500/10 flex items-center justify-between px-6">
          <h3 className="text-sm font-semibold text-text-primary">
            {sections.find(s => s.id === currentSection)?.title}
          </h3>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl mx-auto">
            {renderCurrentSection()}
          </div>
        </div>
        
        <div className="h-12 bg-obsidian-900 border-t border-platinum-500/10 flex items-center justify-between px-6">
          <button
            onClick={() => {
              const currentIndex = sections.findIndex(s => s.id === currentSection);
              if (currentIndex > 0) setCurrentSection(sections[currentIndex - 1].id);
            }}
            disabled={sections.findIndex(s => s.id === currentSection) === 0}
            className="flex items-center gap-1 text-xs text-text-secondary hover:text-text-primary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            Önceki
          </button>
          
          <span className="text-xs text-text-tertiary">
            {sections.findIndex(s => s.id === currentSection) + 1} / {sections.length}
          </span>
          
          <button
            onClick={() => {
              const currentIndex = sections.findIndex(s => s.id === currentSection);
              if (currentIndex < sections.length - 1) setCurrentSection(sections[currentIndex + 1].id);
            }}
            disabled={sections.findIndex(s => s.id === currentSection) === sections.length - 1}
            className="flex items-center gap-1 text-xs text-text-secondary hover:text-text-primary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Sonraki
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReportViewer;
