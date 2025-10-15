import React, { useState, useEffect } from 'react';
import { FileText, Download, AlertCircle, Loader2, Shield, Clock, Target } from 'lucide-react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import AppNavbar from '../components/layout/AppNavbar';
import { ReportViewer } from '../components/reports';
import { pentagentAPI } from '../services/pentagentAPI';
import { reportService } from '../services/reportService';
import { useAuth } from '../contexts/AuthContext';

const Reports = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { currentUser } = useAuth();
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [viewerOpen, setViewerOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const action = searchParams.get('action');
    if (action === 'generate') {
      handleGenerateNewReport();
    } else {
      loadReports();
    }
  }, [searchParams, currentUser]);

  const loadReports = async () => {
    if (!currentUser) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const userReports = await reportService.getUserReports(currentUser.uid);
      setReports(userReports);
    } catch (err) {
      console.error('Raporlar yüklenemedi:', err);
      setError('Raporlar yüklenemedi');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateNewReport = async () => {
    setGenerating(true);
    setError(null);

    try {
      const pendingReportStr = localStorage.getItem('pendingReport');
      if (!pendingReportStr) {
        throw new Error('Rapor verileri bulunamadı');
      }

      const pendingReport = JSON.parse(pendingReportStr);

      // Backend'e rapor oluşturma isteği
      const response = await fetch(`${pentagentAPI.baseURL}/api/generate-report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target: pendingReport.target,
          scan_results: pendingReport.scanResults,
          cve_results: pendingReport.cveResults,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Rapor oluşturulamadı');
      }

      const reportData = await response.json();

      // Firestore'a kaydet
      const savedReport = await reportService.saveReport(currentUser.uid, {
        report_id: reportData.report_id,
        target: pendingReport.target,
        risk_score: reportData.risk_score,
        vulnerabilities: reportData.vulnerabilities,
        pages: reportData.pages,
        structured_data: reportData.structured_data,
        files: reportData.files,
        download_url: reportData.download_url,
        createdAt: reportData.createdAt
      });

      // localStorage'ı temizle
      localStorage.removeItem('pendingReport');

      // Raporu göster
      setSelectedReport(savedReport);
      setViewerOpen(true);

      // Listeyi yenile
      await loadReports();
    } catch (err) {
      console.error('Rapor oluşturma hatası:', err);
      setError(err.message);
    } finally {
      setGenerating(false);
      navigate('/reports', { replace: true });
    }
  };

  const handleViewReport = (report) => {
    setSelectedReport(report);
    setViewerOpen(true);
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'text-rose-500';
      case 'high': return 'text-rose-400';
      case 'medium': return 'text-amber-500';
      case 'low': return 'text-emerald-500';
      default: return 'text-platinum-500';
    }
  };

  const getRiskColor = (score) => {
    if (score >= 70) return 'text-rose-500';
    if (score >= 40) return 'text-amber-500';
    return 'text-emerald-500';
  };

  if (generating) {
    return (
      <div className="min-h-screen bg-obsidian-950 flex flex-col">
        <AppNavbar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-12 h-12 text-platinum-500 animate-spin mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-text-primary mb-2">Rapor Oluşturuluyor</h2>
            <p className="text-text-secondary">Lütfen bekleyin...</p>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-obsidian-950 flex flex-col">
        <AppNavbar />
        <div className="flex-1 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-platinum-500 animate-spin" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-obsidian-950 flex flex-col">
        <AppNavbar />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md">
            <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-text-primary mb-2">Hata Oluştu</h2>
            <p className="text-text-secondary mb-4">{error}</p>
            <button
              onClick={() => navigate('/chat')}
              className="px-4 py-2 bg-platinum-500/10 hover:bg-platinum-500/20 text-platinum-400 rounded-lg transition-colors"
            >
              Tarama Sayfasına Dön
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-obsidian-950 flex flex-col">
      <AppNavbar />
      
      <div className="flex-1 p-6">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <Shield className="w-6 h-6 text-platinum-500" />
              <h1 className="text-2xl font-bold text-text-primary">Güvenlik Raporları</h1>
            </div>
            <p className="text-text-secondary text-sm">
              Geçmiş penetrasyon testi raporlarınızı görüntüleyin ve indirin
            </p>
          </div>

          {/* Reports List */}
          {reports.length === 0 ? (
            <div className="text-center py-16">
              <FileText className="w-16 h-16 text-text-tertiary mx-auto mb-4 opacity-50" />
              <h3 className="text-lg font-medium text-text-primary mb-2">Henüz Rapor Yok</h3>
              <p className="text-text-secondary mb-6">
                Pentest sayfasından tarama yapın ve rapor oluşturun
              </p>
              <button
                onClick={() => navigate('/chat')}
                className="px-6 py-2 bg-platinum-500/10 hover:bg-platinum-500/20 text-platinum-400 rounded-lg transition-all duration-300"
              >
                Tarama Yap
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {reports.map((report) => (
                <div
                  key={report.id}
                  className="bg-obsidian-900/50 border border-platinum-500/10 rounded-lg p-5 hover:border-platinum-500/30 transition-all duration-300 cursor-pointer group"
                  onClick={() => handleViewReport(report)}
                >
                  {/* Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <div className="w-10 h-10 rounded-lg bg-platinum-500/10 flex items-center justify-center group-hover:bg-platinum-500/20 transition-colors">
                        <FileText className="w-5 h-5 text-platinum-500" />
                      </div>
                      <div>
                        <h3 className="text-sm font-semibold text-text-primary group-hover:text-platinum-400 transition-colors">
                          {report.target}
                        </h3>
                        <p className="text-xs text-text-tertiary flex items-center gap-1 mt-0.5">
                          <Clock className="w-3 h-3" />
                          {new Date(report.createdAt).toLocaleDateString('tr-TR')}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Risk Score */}
                  <div className="mb-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-text-tertiary">Risk Skoru</span>
                      <span className={`text-lg font-bold ${getRiskColor(report.risk_score)}`}>
                        {report.risk_score}/100
                      </span>
                    </div>
                    <div className="w-full bg-obsidian-950 rounded-full h-1.5 overflow-hidden">
                      <div 
                        className={`h-full transition-all ${
                          report.risk_score >= 70 ? 'bg-rose-500' : 
                          report.risk_score >= 40 ? 'bg-amber-500' : 'bg-emerald-500'
                        }`}
                        style={{ width: `${report.risk_score}%` }}
                      />
                    </div>
                  </div>

                  {/* Vulnerabilities */}
                  <div className="grid grid-cols-4 gap-2">
                    {Object.entries(report.vulnerabilities || {}).map(([severity, count]) => (
                      <div key={severity} className="text-center">
                        <div className={`text-lg font-bold ${getSeverityColor(severity)}`}>
                          {count}
                        </div>
                        <div className="text-[10px] text-text-tertiary uppercase">
                          {severity === 'critical' ? 'Kritik' : 
                           severity === 'high' ? 'Yüksek' : 
                           severity === 'medium' ? 'Orta' : 'Düşük'}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Footer */}
                  <div className="mt-4 pt-4 border-t border-platinum-500/10 flex items-center justify-between">
                    <span className="text-xs text-text-tertiary">{report.pages} sayfa</span>
                    <Download className="w-4 h-4 text-platinum-500 group-hover:text-platinum-400 transition-colors" />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Report Viewer */}
      {selectedReport && (
        <ReportViewer
          report={selectedReport}
          isOpen={viewerOpen}
          onClose={() => {
            setViewerOpen(false);
            setSelectedReport(null);
          }}
        />
      )}
    </div>
  );
};

export default Reports;
