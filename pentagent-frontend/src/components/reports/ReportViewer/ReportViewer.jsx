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
  const [expandedCve, setExpandedCve] = useState(null);

  if (!isOpen || !report) return null;

  const sections = [
    { id: 'yonetici-ozeti', title: 'Yönetici Özeti', icon: FileText },
    { id: 'metodoloji', title: 'Metodoloji', icon: Shield },
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
    // Veriyi hem structured_data'dan hem de direkt report'tan al
    const executiveData = report.structured_data?.executive_summary || {};
    const riskScore = report.risk_score || executiveData.risk_skoru || 0;
    
    // Debug: Vulnerabilities objesini kontrol et
    console.log('🔍 Report vulnerabilities:', report.vulnerabilities);
    console.log('🔍 Report structured_data:', report.structured_data);
    
    // Vulnerabilities objesini oluştur
    let vulnerabilities = report.vulnerabilities || {};
    
    // Eğer vulnerabilities yoksa, structured_data'dan oluştur
    if (!vulnerabilities || Object.keys(vulnerabilities).length === 0) {
      const findings = report.structured_data?.detailed_findings || report.structured_data?.findings || [];
      vulnerabilities = {
        'critical': findings.filter(f => f.severity === 'critical').length,
        'high': findings.filter(f => f.severity === 'high').length,
        'medium': findings.filter(f => f.severity === 'medium').length,
        'low': findings.filter(f => f.severity === 'low').length,
        'info': findings.filter(f => f.severity === 'info').length
      };
      console.log('🔧 Vulnerabilities objesi oluşturuldu:', vulnerabilities);
    }
    
    // Genel değerlendirme metni
    const genelDegerlendirme = executiveData.genel_degerlendirme || 
      `Bu rapor, ${report.target || 'hedef sistem'} sistemine yönelik gerçekleştirilen penetrasyon testinin sonuçlarını özetlemektedir. ` +
      `Testler, sistemin genel güvenlik duruşunu ve potansiyel risklerini değerlendirmek amacıyla yapılmıştır. ` +
      `Değerlendirme sonucunda, sistemin güvenlik seviyesi '${riskScore >= 70 ? 'HIGH' : riskScore >= 40 ? 'MEDIUM' : 'LOW'}' olarak belirlenmiştir.`;
    
    return (
      <div className="space-y-6">
        <div className="prose prose-invert max-w-none">
          <p className="text-text-secondary leading-relaxed">{genelDegerlendirme}</p>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="bg-obsidian-900/50 border border-platinum-500/10 rounded-lg p-5">
            <h4 className="text-sm font-medium text-text-primary mb-3">Risk Skoru</h4>
            <div className="flex items-baseline gap-3 mb-3">
              <div className={`text-4xl font-bold ${getRiskColor(riskScore)}`}>
                {riskScore}
              </div>
              <span className="text-text-tertiary text-sm">/100</span>
            </div>
            <div className="w-full bg-obsidian-950 rounded-full h-2 overflow-hidden">
              <div 
                className={`h-full transition-all ${
                  riskScore >= 70 ? 'bg-rose-500' : 
                  riskScore >= 40 ? 'bg-amber-500' : 'bg-emerald-500'
                }`}
                style={{ width: `${Math.min(riskScore, 100)}%` }}
              />
            </div>
            <div className={`mt-2 text-sm font-medium ${getRiskColor(riskScore)}`}>
              {riskScore >= 70 ? 'HIGH' : riskScore >= 40 ? 'MEDIUM' : 'LOW'}
            </div>
          </div>
          
          <div className="bg-obsidian-900/50 border border-platinum-500/10 rounded-lg p-5">
            <h4 className="text-sm font-medium text-text-primary mb-3">Bulgular</h4>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(vulnerabilities).length > 0 ? (
                Object.entries(vulnerabilities).map(([severity, count]) => (
                  <div key={severity} className="text-center py-2 bg-obsidian-950/50 rounded">
                    <div className={`text-xl font-bold ${getSeverityColor(severity).split(' ')[0]}`}>
                      {count}
                    </div>
                    <div className="text-xs text-text-tertiary uppercase mt-0.5">
                      {getSeverityText(severity)}
                    </div>
                  </div>
                ))
              ) : (
                <div className="col-span-2 text-center py-4">
                  <div className="text-text-tertiary text-sm">Bulgular yükleniyor...</div>
                </div>
              )}
            </div>
          </div>
        </div>
        
        {executiveData.kritik_bulgular && executiveData.kritik_bulgular.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-text-primary mb-3">Kritik Bulgular</h4>
            <div className="space-y-2">
              {executiveData.kritik_bulgular.map((bulgu, index) => (
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
    // Bulguları hem structured_data'dan hem de direkt report'tan al
    const findings = report.structured_data?.detailed_findings || report.structured_data?.findings || [];
    const cveReferences = report.structured_data?.cve_references || report.cve_results || [];
    
    if (findings.length === 0) {
      return (
        <div className="text-center py-12">
          <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
          <p className="text-text-secondary text-sm">Teknik bulgu tespit edilmedi</p>
          <p className="text-text-tertiary text-xs mt-2">
            Tarama verileri henüz yüklenmemiş olabilir. Lütfen tarama tamamlandıktan sonra tekrar deneyin.
          </p>
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
        
        {data?.sonuc && (
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
    // CVE'leri farklı yerlerden al
    const cveReferences = report.structured_data?.cve_references || [];
    const cveResults = report.structured_data?.cve_results || report.cve_results || [];
    
    // CVE'leri birleştir ve benzersiz yap
    const allCves = [...cveReferences, ...cveResults];
    const uniqueCves = allCves.filter((cve, index, self) => 
      index === self.findIndex(c => c.cve_id === cve.cve_id)
    );
    
    console.log('🔍 CVE References:', cveReferences); // Debug
    console.log('🔍 CVE Results:', cveResults); // Debug
    console.log('🔍 All CVE:', uniqueCves); // Debug
    console.log('🔍 Report:', report); // Debug
    
    if (uniqueCves.length === 0) {
      return (
        <div className="text-center py-12">
          <Database className="w-12 h-12 text-platinum-500 mx-auto mb-3" />
          <p className="text-text-secondary text-sm">CVE referansı bulunamadı</p>
          <p className="text-text-tertiary text-xs mt-2">
            RAG servisi henüz CVE verilerini yüklememiş olabilir. Lütfen tarama tamamlandıktan sonra tekrar deneyin.
          </p>
          <div className="mt-4 bg-obsidian-950/50 rounded border border-platinum-500/5 p-3">
            <div className="text-xs text-text-tertiary mb-1">Debug: Report Data</div>
            <pre className="text-xs text-text-secondary whitespace-pre-wrap overflow-x-auto">
              {JSON.stringify(report, null, 2).substring(0, 1000)}...
            </pre>
          </div>
        </div>
      );
    }
    
    return (
      <div className="space-y-6">
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-text-primary flex items-center gap-2">
            <Database className="w-4 h-4 text-platinum-400" />
            Tespit Edilen CVE Referansları ({uniqueCves.length})
          </h3>
          
          <div className="grid gap-4">
            {uniqueCves.map((cve, index) => (
              <div 
                key={index} 
                className="bg-obsidian-900/50 border border-platinum-500/10 rounded-lg p-5 cursor-pointer hover:border-platinum-500/30 transition-all duration-200"
                onClick={() => setExpandedCve(expandedCve === index ? null : index)}
              >
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
                  
                  {/* CVE Meta Bilgileri */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
                    {cve.published_date && (
                      <div>
                        <div className="text-xs text-text-tertiary mb-1">Yayın Tarihi</div>
                        <p className="text-text-secondary text-xs">{cve.published_date}</p>
                      </div>
                    )}
                    {cve.modified_date && (
                      <div>
                        <div className="text-xs text-text-tertiary mb-1">Güncellenme Tarihi</div>
                        <p className="text-text-secondary text-xs">{cve.modified_date}</p>
                      </div>
                    )}
                    {cve.last_modified_date && (
                      <div>
                        <div className="text-xs text-text-tertiary mb-1">Son Güncelleme</div>
                        <p className="text-text-secondary text-xs">{cve.last_modified_date}</p>
                      </div>
                    )}
                    {cve.source && (
                      <div>
                        <div className="text-xs text-text-tertiary mb-1">Kaynak</div>
                        <p className="text-text-secondary text-xs">{cve.source}</p>
                      </div>
                    )}
                  </div>
                  
                  {/* CVE Context ve Detaylar */}
                  {cve.context && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Context</div>
                      <p className="text-text-secondary text-xs leading-relaxed">{cve.context}</p>
                    </div>
                  )}
                  
                  {cve.summary && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Özet</div>
                      <p className="text-text-secondary text-xs leading-relaxed">{cve.summary}</p>
                    </div>
                  )}
                  
                  {/* CVE Kategorileri */}
                  {cve.categories && cve.categories.length > 0 && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Kategoriler</div>
                      <div className="flex flex-wrap gap-1">
                        {cve.categories.map((category, catIndex) => (
                          <span key={catIndex} className="px-2 py-1 bg-platinum-500/10 text-platinum-400 rounded text-xs">
                            {category}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* CVE Etiketleri */}
                  {cve.tags && cve.tags.length > 0 && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Etiketler</div>
                      <div className="flex flex-wrap gap-1">
                        {cve.tags.map((tag, tagIndex) => (
                          <span key={tagIndex} className="px-2 py-1 bg-amber-500/10 text-amber-400 rounded text-xs">
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* CVE Skor Detayları */}
                  {cve.score && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Detaylı Skor</div>
                      <div className="bg-obsidian-950 p-2 rounded text-xs">
                        <div className="grid grid-cols-2 gap-2">
                          {Object.entries(cve.score).map(([key, value]) => (
                            <div key={key} className="flex justify-between">
                              <span className="text-text-tertiary">{key}:</span>
                              <span className="text-text-primary">{value}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {cve.references && cve.references.length > 0 && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Referanslar ({cve.references.length})</div>
                      <div className="space-y-1">
                        {cve.references.slice(0, 10).map((ref, refIndex) => (
                          <a
                            key={refIndex}
                            href={ref}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-platinum-400 hover:text-platinum-300 underline block truncate"
                            title={ref}
                          >
                            {ref}
                          </a>
                        ))}
                        {cve.references.length > 10 && (
                          <div className="text-xs text-text-tertiary">
                            ... ve {cve.references.length - 10} referans daha
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* CVE Exploitability */}
                  {cve.exploitability && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Exploitability</div>
                      <div className="bg-obsidian-950 p-2 rounded text-xs">
                        <div className="grid grid-cols-2 gap-2">
                          {Object.entries(cve.exploitability).map(([key, value]) => (
                            <div key={key} className="flex justify-between">
                              <span className="text-text-tertiary">{key}:</span>
                              <span className="text-text-primary">{value}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {/* CVE Impact */}
                  {cve.impact && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Impact</div>
                      <div className="bg-obsidian-950 p-2 rounded text-xs">
                        <div className="grid grid-cols-2 gap-2">
                          {Object.entries(cve.impact).map(([key, value]) => (
                            <div key={key} className="flex justify-between">
                              <span className="text-text-tertiary">{key}:</span>
                              <span className="text-text-primary">{value}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                  
                  {/* CVE Versions */}
                  {cve.versions && cve.versions.length > 0 && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Etkilenen Versiyonlar</div>
                      <div className="space-y-1">
                        {cve.versions.map((version, verIndex) => (
                          <div key={verIndex} className="text-xs text-text-secondary bg-obsidian-950 p-2 rounded">
                            {version}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* CVE Solutions */}
                  {cve.solutions && cve.solutions.length > 0 && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Çözüm Önerileri</div>
                      <div className="space-y-2">
                        {cve.solutions.map((solution, solIndex) => (
                          <div key={solIndex} className="text-xs text-text-secondary bg-emerald-500/5 border border-emerald-500/20 p-2 rounded">
                            {solution}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Ham CVE Verisi - Debug için */}
                  <div className="mt-4 bg-obsidian-950/50 rounded border border-platinum-500/5 p-3">
                    <div className="text-xs text-text-tertiary mb-1">Ham CVE Verisi</div>
                    <pre className="text-xs text-text-secondary whitespace-pre-wrap overflow-x-auto">
                      {JSON.stringify(cve, null, 2)}
                    </pre>
                  </div>
                </div>
                
                {/* Genişletilmiş Detaylar */}
                {expandedCve === index && (
                  <div className="mt-4 pt-4 border-t border-platinum-500/10">
                    <div className="space-y-4">
                      {/* Exploitability Detayları */}
                      {cve.exploitability && (
                        <div>
                          <div className="text-xs text-text-tertiary mb-2">Exploitability</div>
                          <div className="bg-obsidian-950/50 p-3 rounded text-xs">
                            <div className="grid grid-cols-2 gap-2">
                              {Object.entries(cve.exploitability).map(([key, value]) => (
                                <div key={key} className="flex justify-between">
                                  <span className="text-text-tertiary">{key}:</span>
                                  <span className="text-text-primary">{value}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {/* Impact Detayları */}
                      {cve.impact && (
                        <div>
                          <div className="text-xs text-text-tertiary mb-2">Impact</div>
                          <div className="bg-obsidian-950/50 p-3 rounded text-xs">
                            <div className="grid grid-cols-2 gap-2">
                              {Object.entries(cve.impact).map(([key, value]) => (
                                <div key={key} className="flex justify-between">
                                  <span className="text-text-tertiary">{key}:</span>
                                  <span className="text-text-primary">{value}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        </div>
                      )}
                      
                      {/* Versions Detayları */}
                      {cve.versions && cve.versions.length > 0 && (
                        <div>
                          <div className="text-xs text-text-tertiary mb-2">Etkilenen Versiyonlar</div>
                          <div className="bg-obsidian-950/50 p-3 rounded text-xs">
                            {cve.versions.map((version, vIndex) => (
                              <div key={vIndex} className="text-text-primary mb-1">
                                {version}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* Solutions */}
                      {cve.solutions && cve.solutions.length > 0 && (
                        <div>
                          <div className="text-xs text-text-tertiary mb-2">Çözüm Önerileri</div>
                          <div className="bg-obsidian-950/50 p-3 rounded text-xs">
                            {cve.solutions.map((solution, sIndex) => (
                              <div key={sIndex} className="text-text-primary mb-2 p-2 bg-emerald-500/10 rounded border border-emerald-500/20">
                                {solution}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      
                      {/* Tüm Referanslar */}
                      {cve.references && cve.references.length > 10 && (
                        <div>
                          <div className="text-xs text-text-tertiary mb-2">Tüm Referanslar ({cve.references.length})</div>
                          <div className="bg-obsidian-950/50 p-3 rounded text-xs max-h-40 overflow-y-auto">
                            {cve.references.map((ref, refIndex) => (
                              <a
                                key={refIndex}
                                href={ref}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-platinum-400 hover:text-platinum-300 underline block mb-1 truncate"
                                title={ref}
                              >
                                {ref}
                              </a>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
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
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center bg-platinum-500/10">
                    <Database className="w-4 h-4 text-platinum-500" />
                  </div>
                  <div>
                    <h4 className="font-medium text-text-primary">{toolName}</h4>
                    {toolOutput?.timestamp && (
                      <div className="flex items-center gap-2 text-xs">
                        <span className="text-text-tertiary">
                          {new Date(toolOutput.timestamp).toLocaleString('tr-TR')}
                        </span>
                      </div>
                    )}
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
                            {typeof tech === 'object' ? (tech.name || tech.technology || JSON.stringify(tech)) : tech}
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
                      <div className="grid grid-cols-2 gap-2">
                        {toolOutput.data.open_ports.slice(0, 10).map((port, portIndex) => {
                          // Port obje ise detaylı göster
                          if (typeof port === 'object' && port !== null) {
                            return (
                              <div key={portIndex} className="bg-obsidian-950 p-2 rounded">
                                <div className="text-xs font-medium text-amber-400">
                                  Port: {port.port || 'N/A'}
                                </div>
                                {port.service && (
                                  <div className="text-xs text-text-tertiary">Service: {port.service}</div>
                                )}
                                {port.product && (
                                  <div className="text-xs text-text-tertiary">Product: {port.product}</div>
                                )}
                                {port.version && (
                                  <div className="text-xs text-text-tertiary">Version: {port.version}</div>
                                )}
                              </div>
                            );
                          }
                          // Port string/number ise basit göster
                          return (
                            <span key={portIndex} className="px-2 py-1 bg-amber-500/10 text-amber-400 rounded text-xs">
                              {port}
                            </span>
                          );
                        })}
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
                  
                  {/* Subdomain Bilgileri */}
                  {toolOutput.data.subdomains && toolOutput.data.subdomains.length > 0 && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Tespit Edilen Subdomainler</div>
                      <div className="space-y-2">
                        {toolOutput.data.subdomains.slice(0, 5).map((subdomain, subIndex) => (
                          <div key={subIndex} className="bg-obsidian-950 p-3 rounded">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs font-medium text-text-primary">
                                {subdomain.subdomain || subdomain}
                              </span>
                              {subdomain.status_code && (
                                <span className="px-2 py-1 bg-emerald-500/10 text-emerald-400 rounded text-xs">
                                  HTTP {subdomain.status_code}
                                </span>
                              )}
                            </div>
                            {subdomain.url && (
                              <p className="text-xs text-text-secondary">{subdomain.url}</p>
                            )}
                            {subdomain.ip && (
                              <p className="text-xs text-text-tertiary">IP: {subdomain.ip}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* XSS Test Sonuçları */}
                  {toolOutput.data.vulnerabilities && toolOutput.data.vulnerabilities.length > 0 && toolName.includes('xss') && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">XSS Test Sonuçları</div>
                      <div className="space-y-2">
                        {toolOutput.data.vulnerabilities.map((vuln, vulnIndex) => (
                          <div key={vulnIndex} className="bg-obsidian-950 p-3 rounded">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs font-medium text-text-primary">
                                {vuln.type || vuln.title || 'XSS Zafiyeti'}
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
                            {vuln.payload && (
                              <p className="text-xs text-text-tertiary">Payload: {vuln.payload}</p>
                            )}
                            {vuln.evidence && (
                              <p className="text-xs text-text-tertiary">Evidence: {vuln.evidence}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Directory Bruteforce Sonuçları */}
                  {toolOutput.data.directories && toolOutput.data.directories.length > 0 && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Tespit Edilen Dizinler</div>
                      <div className="flex flex-wrap gap-1">
                        {toolOutput.data.directories.slice(0, 10).map((dir, dirIndex) => (
                          <span key={dirIndex} className="px-2 py-1 bg-blue-500/10 text-blue-400 rounded text-xs">
                            {dir.path || dir}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Web Crawling Sonuçları */}
                  {toolOutput.data.pages && toolOutput.data.pages.length > 0 && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Tespit Edilen Sayfalar</div>
                      <div className="space-y-1">
                        {toolOutput.data.pages.slice(0, 5).map((page, pageIndex) => (
                          <div key={pageIndex} className="bg-obsidian-950 p-2 rounded">
                            <div className="text-xs text-text-primary">{page.url || page}</div>
                            {page.title && (
                              <div className="text-xs text-text-secondary">{page.title}</div>
                            )}
                            {page.status_code && (
                              <span className="px-1 py-0.5 bg-emerald-500/10 text-emerald-400 rounded text-xs">
                                {page.status_code}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Firewall Tespiti */}
                  {toolOutput.data.firewall_detected !== undefined && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Firewall Tespiti</div>
                      <div className={`px-3 py-2 rounded ${
                        toolOutput.data.firewall_detected 
                          ? 'bg-amber-500/10 text-amber-400' 
                          : 'bg-emerald-500/10 text-emerald-400'
                      }`}>
                        {toolOutput.data.firewall_detected ? 'Firewall Tespit Edildi' : 'Firewall Tespit Edilmedi'}
                      </div>
                      {toolOutput.data.firewall_type && (
                        <div className="text-xs text-text-secondary mt-1">
                          Tip: {toolOutput.data.firewall_type}
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* Genel Sonuçlar */}
                  {toolOutput.data.results && toolOutput.data.results.length > 0 && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">Sonuçlar</div>
                      <div className="space-y-2">
                        {toolOutput.data.results.slice(0, 5).map((result, resultIndex) => (
                          <div key={resultIndex} className="bg-obsidian-950 p-3 rounded">
                            <div className="text-xs text-text-primary">
                              {result.title || result.name || result.type || 'Sonuç'}
                            </div>
                            {result.description && (
                              <div className="text-xs text-text-secondary mt-1">{result.description}</div>
                            )}
                            {result.severity && (
                              <span className={`px-2 py-1 rounded text-xs mt-1 inline-block ${getSeverityColor(result.severity)}`}>
                                {getSeverityText(result.severity)}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* İstatistikler */}
                  {toolOutput.data.stats && (
                    <div>
                      <div className="text-xs text-text-tertiary mb-1">İstatistikler</div>
                      <div className="grid grid-cols-2 gap-2">
                        {Object.entries(toolOutput.data.stats).map(([key, value]) => (
                          <div key={key} className="bg-obsidian-950 p-2 rounded text-center">
                            <div className="text-sm font-medium text-text-primary">{value}</div>
                            <div className="text-xs text-text-tertiary">{key}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Ham JSON Çıktı - Production'da da göster */}
                    <div className="bg-obsidian-950/50 rounded border border-platinum-500/5 p-3">
                    <div className="text-xs text-text-tertiary mb-1">Ham Çıktı</div>
                    <pre className="text-xs text-text-secondary whitespace-pre-wrap overflow-x-auto max-h-40">
                      {JSON.stringify(toolOutput.data, null, 2)}
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
      case 'cve-detaylari': return renderCveDetaylari();
      case 'tool-ciktilari': return renderToolCiktilari();
      case 'oneriler': return renderOneriler();
      default: return <div className="text-center py-12 text-text-secondary">Yükleniyor...</div>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex bg-obsidian-950">
      {/* Sidebar */}
      <div className="w-64 bg-obsidian-900 border-r border-platinum-500/10 flex flex-col flex-shrink-0">
        <div className="p-4 border-b border-platinum-500/10 flex-shrink-0">
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
      <div className="flex-1 flex flex-col min-w-0">
        <div className="h-12 bg-obsidian-900 border-b border-platinum-500/10 flex items-center justify-between px-6 flex-shrink-0">
          <h3 className="text-sm font-semibold text-text-primary">
            {sections.find(s => s.id === currentSection)?.title}
          </h3>
        </div>
        
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-6">
          <div className="max-w-4xl mx-auto">
            {renderCurrentSection()}
          </div>
        </div>
        
        <div className="h-12 bg-obsidian-900 border-t border-platinum-500/10 flex items-center justify-between px-6 flex-shrink-0">
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
