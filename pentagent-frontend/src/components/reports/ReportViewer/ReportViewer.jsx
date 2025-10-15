import React, { useState } from 'react';
import { 
  X, 
  Download, 
  Share2, 
  Printer,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Maximize2,
  FileText,
  AlertTriangle,
  Shield,
  Target,
  Clock,
  CheckCircle
} from 'lucide-react';
import Button from '../../common/Button';
import Card from '../../common/Card';

const ReportViewer = ({ report, isOpen, onClose }) => {
  const [currentSection, setCurrentSection] = useState('executive-summary');
  const [zoom, setZoom] = useState(100);

  if (!isOpen || !report) return null;

  const sections = [
    { id: 'executive-summary', title: 'Executive Summary', icon: FileText },
    { id: 'methodology', title: 'Methodology', icon: Shield },
    { id: 'findings', title: 'Security Findings', icon: AlertTriangle },
    { id: 'vulnerabilities', title: 'Vulnerability Details', icon: Target },
    { id: 'recommendations', title: 'Recommendations', icon: CheckCircle },
    { id: 'appendix', title: 'Technical Appendix', icon: FileText }
  ];

  const mockReportData = {
    executiveSummary: {
      overview: "This comprehensive security assessment of example.com identified 47 vulnerabilities across multiple categories. The assessment revealed critical security gaps that require immediate attention to prevent potential data breaches and service disruptions.",
      keyFindings: [
        "3 Critical SQL injection vulnerabilities in user authentication system",
        "15 High-severity XSS vulnerabilities in user-generated content areas", 
        "12 Medium-severity configuration issues in web server setup",
        "17 Low-severity information disclosure vulnerabilities"
      ],
      riskAssessment: "The overall security posture presents a HIGH risk level (8.2/10) due to the presence of multiple critical vulnerabilities that could lead to complete system compromise.",
      businessImpact: "Successful exploitation could result in unauthorized access to customer data, financial losses, and significant reputational damage."
    },
    findings: [
      {
        id: 'sql-001',
        title: 'SQL Injection in Login Form',
        severity: 'Critical',
        cvss: 9.8,
        cve: 'CVE-2023-1234',
        description: 'The login form is vulnerable to SQL injection attacks through the username parameter.',
        location: '/login.php',
        parameter: 'username',
        payload: "' OR '1'='1' --",
        impact: 'Complete database access, user account takeover',
        remediation: 'Implement parameterized queries and input validation'
      },
      {
        id: 'xss-001', 
        title: 'Stored XSS in Comment System',
        severity: 'High',
        cvss: 7.2,
        description: 'User comments are not properly sanitized, allowing stored XSS attacks.',
        location: '/comments.php',
        parameter: 'comment_text',
        payload: '<script>alert("XSS")</script>',
        impact: 'Session hijacking, credential theft',
        remediation: 'Implement proper output encoding and CSP headers'
      },
      {
        id: 'info-001',
        title: 'Server Information Disclosure',
        severity: 'Low', 
        cvss: 3.1,
        description: 'Server headers reveal detailed version information.',
        location: 'HTTP Headers',
        impact: 'Information gathering for targeted attacks',
        remediation: 'Configure server to hide version information'
      }
    ]
  };

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical': return 'text-rose-500 bg-rose-500/10';
      case 'high': return 'text-rose-500 bg-rose-500/10';
      case 'medium': return 'text-warning bg-warning/10';
      case 'low': return 'text-success bg-success/10';
      default: return 'text-text-tertiary bg-obsidian-800';
    }
  };

  const renderExecutiveSummary = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-xl font-semibold text-text-primary mb-4">Assessment Overview</h3>
        <p className="text-text-secondary leading-relaxed">{mockReportData.executiveSummary.overview}</p>
      </div>
      
      <div>
        <h4 className="text-lg font-semibold text-text-primary mb-3">Key Findings</h4>
        <ul className="space-y-2">
          {mockReportData.executiveSummary.keyFindings.map((finding, index) => (
            <li key={index} className="flex items-start gap-3">
              <div className="w-2 h-2 bg-platinum-500 rounded-full mt-2 flex-shrink-0" />
              <span className="text-text-secondary">{finding}</span>
            </li>
          ))}
        </ul>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-4">
          <h4 className="font-semibold text-text-primary mb-2">Risk Assessment</h4>
          <p className="text-text-secondary text-sm mb-3">{mockReportData.executiveSummary.riskAssessment}</p>
          <div className="flex items-center gap-2">
            <div className="text-2xl font-bold text-rose-500">8.2/10</div>
            <span className="text-rose-400 text-sm">HIGH RISK</span>
          </div>
        </Card>
        
        <Card className="p-4">
          <h4 className="font-semibold text-text-primary mb-2">Business Impact</h4>
          <p className="text-text-secondary text-sm">{mockReportData.executiveSummary.businessImpact}</p>
        </Card>
      </div>
    </div>
  );

  const renderFindings = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {Object.entries(report.vulnerabilities).map(([severity, count]) => (
          <div key={severity} className={`p-4 rounded-lg border ${getSeverityColor(severity)}`}>
            <div className="text-2xl font-bold mb-1">{count}</div>
            <div className="text-sm capitalize">{severity}</div>
          </div>
        ))}
      </div>
      
      <div className="space-y-4">
        {mockReportData.findings.map((finding) => (
          <Card key={finding.id} className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h4 className="text-lg font-semibold text-text-primary">{finding.title}</h4>
                  <span className={`px-3 py-1 rounded-full text-sm ${getSeverityColor(finding.severity)}`}>
                    {finding.severity}
                  </span>
                </div>
                <div className="flex items-center gap-4 text-sm text-text-tertiary">
                  <span>CVSS: {finding.cvss}</span>
                  {finding.cve && <span>{finding.cve}</span>}
                  <span>ID: {finding.id}</span>
                </div>
              </div>
            </div>
            
            <div className="space-y-4">
              <div>
                <h5 className="font-medium text-text-primary mb-2">Description</h5>
                <p className="text-text-secondary">{finding.description}</p>
              </div>
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div>
                  <h5 className="font-medium text-text-primary mb-2">Location</h5>
                  <code className="bg-obsidian-950 px-3 py-2 rounded text-sm text-platinum-400 block">
                    {finding.location}
                  </code>
                </div>
                
                {finding.parameter && (
                  <div>
                    <h5 className="font-medium text-text-primary mb-2">Parameter</h5>
                    <code className="bg-obsidian-950 px-3 py-2 rounded text-sm text-platinum-400 block">
                      {finding.parameter}
                    </code>
                  </div>
                )}
              </div>
              
              {finding.payload && (
                <div>
                  <h5 className="font-medium text-text-primary mb-2">Proof of Concept</h5>
                  <pre className="bg-obsidian-950 p-4 rounded text-sm text-success overflow-x-auto">
                    {finding.payload}
                  </pre>
                </div>
              )}
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div>
                  <h5 className="font-medium text-text-primary mb-2">Impact</h5>
                  <p className="text-text-secondary text-sm">{finding.impact}</p>
                </div>
                
                <div>
                  <h5 className="font-medium text-text-primary mb-2">Remediation</h5>
                  <p className="text-text-secondary text-sm">{finding.remediation}</p>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );

  const renderCurrentSection = () => {
    switch (currentSection) {
      case 'executive-summary': return renderExecutiveSummary();
      case 'findings': return renderFindings();
      case 'vulnerabilities': return renderFindings();
      default: 
        return (
          <div className="text-center py-12">
            <FileText className="w-16 h-16 text-text-tertiary mx-auto mb-4" />
            <h3 className="text-text-primary font-medium mb-2">Section Coming Soon</h3>
            <p className="text-text-secondary">This section is being generated...</p>
          </div>
        );
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative w-full bg-obsidian-950 flex">
        
        {/* Sidebar Navigation */}
        <div className="w-80 bg-obsidian-900 border-r border-obsidian-700 flex flex-col">
          <div className="p-6 border-b border-obsidian-700">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-text-primary">Report Viewer</h2>
              <button
                onClick={onClose}
                className="p-2 text-text-tertiary hover:text-text-primary hover:bg-obsidian-850 rounded-lg transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2 text-text-secondary">
                <Target className="w-4 h-4" />
                <span>{report.target}</span>
              </div>
              <div className="flex items-center gap-2 text-text-secondary">
                <Clock className="w-4 h-4" />
                <span>{new Date(report.createdAt).toLocaleDateString()}</span>
              </div>
              <div className="flex items-center gap-2 text-text-secondary">
                <FileText className="w-4 h-4" />
                <span>{report.pages} pages</span>
              </div>
            </div>
          </div>
          
          {/* Section Navigation */}
          <div className="flex-1 overflow-y-auto p-4">
            <nav className="space-y-1">
              {sections.map((section) => {
                const Icon = section.icon;
                return (
                  <button
                    key={section.id}
                    onClick={() => setCurrentSection(section.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left transition-colors ${
                      currentSection === section.id
                        ? 'bg-platinum-500/10 text-platinum-500 border border-platinum-500/20'
                        : 'text-text-secondary hover:text-text-primary hover:bg-obsidian-850'
                    }`}
                  >
                    <Icon className="w-4 h-4 flex-shrink-0" />
                    <span className="text-sm">{section.title}</span>
                  </button>
                );
              })}
            </nav>
          </div>
          
          {/* Actions */}
          <div className="p-4 border-t border-obsidian-700 space-y-3">
            <Button variant="primary" className="w-full">
              <Download className="w-4 h-4 mr-2" />
              Download PDF
            </Button>
            <div className="grid grid-cols-2 gap-2">
              <Button variant="secondary" size="sm">
                <Share2 className="w-4 h-4 mr-2" />
                Share
              </Button>
              <Button variant="secondary" size="sm">
                <Printer className="w-4 h-4 mr-2" />
                Print
              </Button>
            </div>
          </div>
        </div>
        
        {/* Main Content */}
        <div className="flex-1 flex flex-col">
          
          {/* Toolbar */}
          <div className="h-16 bg-obsidian-900 border-b border-obsidian-700 flex items-center justify-between px-6">
            <div className="flex items-center gap-4">
              <h3 className="text-lg font-semibold text-text-primary">
                {sections.find(s => s.id === currentSection)?.title}
              </h3>
            </div>
            
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setZoom(Math.max(50, zoom - 25))}
                  className="p-2 text-text-tertiary hover:text-text-primary hover:bg-obsidian-850 rounded-lg transition-all"
                >
                  <ZoomOut className="w-4 h-4" />
                </button>
                <span className="text-sm text-text-secondary min-w-[4rem] text-center">
                  {zoom}%
                </span>
                <button
                  onClick={() => setZoom(Math.min(200, zoom + 25))}
                  className="p-2 text-text-tertiary hover:text-text-primary hover:bg-obsidian-850 rounded-lg transition-all"
                >
                  <ZoomIn className="w-4 h-4" />
                </button>
              </div>
              
              <button className="p-2 text-text-tertiary hover:text-text-primary hover:bg-obsidian-850 rounded-lg transition-all">
                <Maximize2 className="w-4 h-4" />
              </button>
            </div>
          </div>
          
          {/* Report Content */}
          <div className="flex-1 overflow-y-auto p-8" style={{ fontSize: `${zoom}%` }}>
            <div className="max-w-4xl mx-auto">
              {renderCurrentSection()}
            </div>
          </div>
          
          {/* Navigation Footer */}
          <div className="h-16 bg-obsidian-900 border-t border-obsidian-700 flex items-center justify-between px-6">
            <button
              onClick={() => {
                const currentIndex = sections.findIndex(s => s.id === currentSection);
                if (currentIndex > 0) {
                  setCurrentSection(sections[currentIndex - 1].id);
                }
              }}
              disabled={sections.findIndex(s => s.id === currentSection) === 0}
              className="flex items-center gap-2 px-4 py-2 text-text-secondary hover:text-text-primary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Previous</span>
            </button>
            
            <div className="text-sm text-text-tertiary">
              {sections.findIndex(s => s.id === currentSection) + 1} of {sections.length}
            </div>
            
            <button
              onClick={() => {
                const currentIndex = sections.findIndex(s => s.id === currentSection);
                if (currentIndex < sections.length - 1) {
                  setCurrentSection(sections[currentIndex + 1].id);
                }
              }}
              disabled={sections.findIndex(s => s.id === currentSection) === sections.length - 1}
              className="flex items-center gap-2 px-4 py-2 text-text-secondary hover:text-text-primary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <span>Next</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportViewer;
