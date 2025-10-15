import React, { useState, useEffect } from 'react';
import { Plus, FileText, Download, Archive, AlertCircle, Loader2, Shield } from 'lucide-react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { AppLayout } from '../components/layout';
import { ReportCard, ReportFilters, ReportViewer } from '../components/reports';
import Button from '../components/common/Button';
import { pentagentAPI } from '../services/pentagentAPI';

const Reports = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [reports, setReports] = useState([]);
  const [filteredReports, setFilteredReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [viewerOpen, setViewerOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generationError, setGenerationError] = useState(null);

  // Mock reports data
  const mockReports = [
    {
      id: '1',
      title: 'Comprehensive Security Assessment',
      target: 'example.com',
      status: 'completed',
      createdAt: '2024-01-15T10:30:00Z',
      format: 'PDF',
      pages: 156,
      riskScore: 8.2,
      vulnerabilities: {
        critical: 3,
        high: 15,
        medium: 28,
        low: 41
      }
    },
    {
      id: '2',
      title: 'API Security Audit',
      target: 'api.testsite.io',
      status: 'completed',
      createdAt: '2024-01-14T15:45:00Z',
      format: 'JSON',
      pages: 89,
      riskScore: 6.5,
      vulnerabilities: {
        critical: 1,
        high: 8,
        medium: 15,
        low: 23
      }
    },
    {
      id: '3',
      title: 'Web Application Penetration Test',
      target: 'app.demo.co',
      status: 'completed',
      createdAt: '2024-01-13T09:15:00Z',
      format: 'HTML',
      pages: 234,
      riskScore: 9.1,
      vulnerabilities: {
        critical: 7,
        high: 22,
        medium: 45,
        low: 67
      }
    },
    {
      id: '4',
      title: 'Quick Vulnerability Scan',
      target: 'staging.myapp.com',
      status: 'processing',
      createdAt: '2024-01-15T14:20:00Z',
      format: 'PDF',
      pages: 0,
      riskScore: 0,
      vulnerabilities: {
        critical: 0,
        high: 0,
        medium: 0,
        low: 0
      }
    },
    {
      id: '5',
      title: 'E-commerce Security Review',
      target: 'shop.example.com',
      status: 'completed',
      createdAt: '2024-01-12T11:30:00Z',
      format: 'PDF',
      pages: 178,
      riskScore: 7.3,
      vulnerabilities: {
        critical: 2,
        high: 12,
        medium: 31,
        low: 48
      }
    },
    {
      id: '6',
      title: 'Infrastructure Assessment',
      target: '192.168.1.0/24',
      status: 'failed',
      createdAt: '2024-01-11T16:00:00Z',
      format: 'PDF',
      pages: 12,
      riskScore: 0,
      vulnerabilities: {
        critical: 0,
        high: 0,
        medium: 0,
        low: 0
      }
    }
  ];

  useEffect(() => {
    // Rapor oluşturma isteği var mı kontrol et
    const action = searchParams.get('action');
    if (action === 'generate') {
      handleGenerateNewReport();
    } else {
      // Normal sayfa yüklemesi - mock reports göster
      setTimeout(() => {
        setReports(mockReports);
        setFilteredReports(mockReports);
        setLoading(false);
      }, 1000);
    }
  }, [searchParams]);

  const handleGenerateNewReport = async () => {
    setGenerating(true);
    setGenerationError(null);

    try {
      // localStorage'dan pending report verilerini al
      const pendingReportStr = localStorage.getItem('pendingReport');
      if (!pendingReportStr) {
        throw new Error('Rapor verileri bulunamadı');
      }

      const pendingReport = JSON.parse(pendingReportStr);
      console.log('Rapor oluşturuluyor:', pendingReport);

      // Backend'e rapor oluşturma isteği gönder
      const response = await fetch(`${pentagentAPI.baseURL}/api/generate-report`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
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
      console.log('Rapor oluşturuldu:', reportData);

      // Yeni raporu listeye ekle
      const newReport = {
        id: reportData.report_id || Date.now().toString(),
        title: `Security Assessment - ${pendingReport.target}`,
        target: pendingReport.target,
        status: 'completed',
        createdAt: new Date().toISOString(),
        format: 'PDF',
        pages: reportData.pages || 0,
        riskScore: reportData.risk_score || 0,
        vulnerabilities: reportData.vulnerabilities || {
          critical: pendingReport.cveResults.filter(c => c.severity === 'CRITICAL').length,
          high: pendingReport.cveResults.filter(c => c.severity === 'HIGH').length,
          medium: pendingReport.cveResults.filter(c => c.severity === 'MEDIUM').length,
          low: pendingReport.cveResults.filter(c => c.severity === 'LOW').length,
        },
        downloadUrl: reportData.download_url,
        reportContent: reportData.report_content,
      };

      setReports(prev => [newReport, ...prev]);
      setFilteredReports(prev => [newReport, ...prev]);

      // localStorage'ı temizle
      localStorage.removeItem('pendingReport');

      // Raporu göster
      setSelectedReport(newReport);
      setViewerOpen(true);
    } catch (error) {
      console.error('Rapor oluşturma hatası:', error);
      setGenerationError(error.message);
    } finally {
      setGenerating(false);
      setLoading(false);
      // URL'den action parametresini temizle
      navigate('/reports', { replace: true });
    }
  };

  const handleFilterChange = (filters) => {
    let filtered = [...reports];

    // Status filter
    if (filters.status.length > 0) {
      filtered = filtered.filter(report => filters.status.includes(report.status));
    }

    // Severity filter (based on vulnerabilities)
    if (filters.severity.length > 0) {
      filtered = filtered.filter(report => {
        return filters.severity.some(severity => {
          return report.vulnerabilities[severity] > 0;
        });
      });
    }

    // Target filter
    if (filters.target) {
      filtered = filtered.filter(report => 
        report.target.toLowerCase().includes(filters.target.toLowerCase())
      );
    }

    // Date range filter
    if (filters.dateRange !== 'all') {
      const now = new Date();
      const filterDate = new Date();
      
      switch (filters.dateRange) {
        case 'today':
          filterDate.setDate(now.getDate());
          break;
        case 'week':
          filterDate.setDate(now.getDate() - 7);
          break;
        case 'month':
          filterDate.setMonth(now.getMonth() - 1);
          break;
        case 'quarter':
          filterDate.setMonth(now.getMonth() - 3);
          break;
      }
      
      filtered = filtered.filter(report => 
        new Date(report.createdAt) >= filterDate
      );
    }

    setFilteredReports(filtered);
  };

  const handleSearch = (searchTerm) => {
    if (!searchTerm) {
      setFilteredReports(reports);
      return;
    }

    const filtered = reports.filter(report =>
      report.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      report.target.toLowerCase().includes(searchTerm.toLowerCase())
    );

    setFilteredReports(filtered);
  };

  const handleSort = ({ field, order }) => {
    const sorted = [...filteredReports].sort((a, b) => {
      let aVal = a[field];
      let bVal = b[field];

      if (field === 'vulnerabilities') {
        aVal = Object.values(a.vulnerabilities).reduce((sum, count) => sum + count, 0);
        bVal = Object.values(b.vulnerabilities).reduce((sum, count) => sum + count, 0);
      }

      if (field === 'createdAt') {
        aVal = new Date(aVal);
        bVal = new Date(bVal);
      }

      if (order === 'asc') {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    setFilteredReports(sorted);
  };

  const handleViewReport = (report) => {
    setSelectedReport(report);
    setViewerOpen(true);
  };

  const handleDownloadReport = (report) => {
    console.log('Downloading report:', report.id);
    // Implement download logic
  };

  const handleShareReport = (report) => {
    console.log('Sharing report:', report.id);
    // Implement share logic
  };

  const handleDeleteReport = (report) => {
    if (window.confirm('Are you sure you want to delete this report?')) {
      setReports(prev => prev.filter(r => r.id !== report.id));
      setFilteredReports(prev => prev.filter(r => r.id !== report.id));
    }
  };

  const handleArchiveReport = (report) => {
    console.log('Archiving report:', report.id);
    // Implement archive logic
  };

  const handleBulkAction = (action, selectedIds) => {
    console.log('Bulk action:', action, selectedIds);
    // Implement bulk actions
  };

  if (loading || generating) {
    return (
      <AppLayout activeItem="/reports">
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <div className="flex items-center gap-3">
            <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
            <span className="text-text-primary font-medium">
              {generating ? 'Rapor oluşturuluyor...' : 'Loading reports...'}
            </span>
          </div>
          {generating && (
            <div className="bg-obsidian-900 border border-purple-500/20 rounded-xl p-6 max-w-md">
              <div className="flex items-center gap-3 mb-4">
                <Shield className="w-6 h-6 text-purple-400" />
                <h3 className="text-lg font-semibold text-text-primary">Rapor Hazırlanıyor</h3>
              </div>
              <div className="space-y-2 text-sm text-text-secondary">
                <p>✓ Tarama sonuçları analiz ediliyor</p>
                <p>✓ RAG CVE veritabanı sorgulanıyor</p>
                <p>✓ En alakalı CVE'ler seçiliyor</p>
                <p className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                  PDF raporu oluşturuluyor
                </p>
              </div>
            </div>
          )}
        </div>
      </AppLayout>
    );
  }

  if (generationError) {
    return (
      <AppLayout activeItem="/reports">
        <div className="flex flex-col items-center justify-center h-64 space-y-4">
          <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-6 max-w-md">
            <div className="flex items-center gap-3 mb-4">
              <AlertCircle className="w-6 h-6 text-rose-500" />
              <h3 className="text-lg font-semibold text-text-primary">Rapor Oluşturulamadı</h3>
            </div>
            <p className="text-sm text-text-secondary mb-4">{generationError}</p>
            <Button variant="secondary" onClick={() => navigate('/chat')}>
              Tarama Sayfasına Dön
            </Button>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout activeItem="/reports">
      <div className="space-y-8">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-text-primary mb-2">Security Reports</h1>
            <p className="text-text-secondary">
              Comprehensive vulnerability assessments and security findings
            </p>
          </div>
          
          <div className="flex gap-3">
            <Button variant="secondary">
              <Archive className="w-4 h-4 mr-2" />
              View Archived
            </Button>
            <Button variant="primary">
              <Plus className="w-4 h-4 mr-2" />
              Generate Report
            </Button>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-obsidian-900 border border-obsidian-700 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-platinum-500/10 rounded-xl flex items-center justify-center">
                <FileText className="w-6 h-6 text-platinum-500" />
              </div>
              <span className="text-sm text-success">+12%</span>
            </div>
            <div className="text-3xl font-bold text-text-primary mb-2">
              {reports.length}
            </div>
            <div className="text-text-secondary">Total Reports</div>
          </div>

          <div className="bg-obsidian-900 border border-obsidian-700 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-rose-500/10 rounded-xl flex items-center justify-center">
                <AlertCircle className="w-6 h-6 text-rose-500" />
              </div>
              <span className="text-sm text-rose-400">-8%</span>
            </div>
            <div className="text-3xl font-bold text-text-primary mb-2">
              {reports.reduce((sum, r) => sum + (r.vulnerabilities.critical || 0), 0)}
            </div>
            <div className="text-text-secondary">Critical Issues</div>
          </div>

          <div className="bg-obsidian-900 border border-obsidian-700 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-success/10 rounded-xl flex items-center justify-center">
                <Download className="w-6 h-6 text-success" />
              </div>
              <span className="text-sm text-success">+23%</span>
            </div>
            <div className="text-3xl font-bold text-text-primary mb-2">
              {reports.filter(r => r.status === 'completed').length}
            </div>
            <div className="text-text-secondary">Completed</div>
          </div>

          <div className="bg-obsidian-900 border border-obsidian-700 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-purple-500/10 rounded-xl flex items-center justify-center">
                <FileText className="w-6 h-6 text-purple-500" />
              </div>
              <span className="text-sm text-text-tertiary">--</span>
            </div>
            <div className="text-3xl font-bold text-text-primary mb-2">
              {(reports.reduce((sum, r) => sum + r.riskScore, 0) / reports.filter(r => r.riskScore > 0).length).toFixed(1)}
            </div>
            <div className="text-text-secondary">Avg Risk Score</div>
          </div>
        </div>

        {/* Filters */}
        <ReportFilters
          onFilterChange={handleFilterChange}
          onSearch={handleSearch}
          onSort={handleSort}
          totalReports={reports.length}
          filteredCount={filteredReports.length}
          onBulkAction={handleBulkAction}
        />

        {/* Reports Grid */}
        {filteredReports.length > 0 ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
            {filteredReports.map(report => (
              <ReportCard
                key={report.id}
                report={report}
                onView={handleViewReport}
                onDownload={handleDownloadReport}
                onShare={handleShareReport}
                onDelete={handleDeleteReport}
                onArchive={handleArchiveReport}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-16">
            <div className="w-24 h-24 bg-obsidian-900 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <FileText className="w-12 h-12 text-text-tertiary" />
            </div>
            <h3 className="text-xl font-semibold text-text-primary mb-4">No reports found</h3>
            <p className="text-text-secondary mb-8 max-w-md mx-auto">
              No reports match your current filters. Try adjusting your search criteria or generate a new report.
            </p>
            <div className="flex gap-3 justify-center">
              <Button variant="secondary">Clear Filters</Button>
              <Button variant="primary">Generate New Report</Button>
            </div>
          </div>
        )}

        {/* Pagination - if needed for large datasets */}
        {filteredReports.length > 12 && (
          <div className="flex items-center justify-center">
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm">Previous</Button>
              <span className="px-4 py-2 text-sm text-text-secondary">1 of 1</span>
              <Button variant="ghost" size="sm">Next</Button>
            </div>
          </div>
        )}
      </div>

      {/* Report Viewer Modal */}
      <ReportViewer
        report={selectedReport}
        isOpen={viewerOpen}
        onClose={() => {
          setViewerOpen(false);
          setSelectedReport(null);
        }}
      />
    </AppLayout>
  );
};

export default Reports;
