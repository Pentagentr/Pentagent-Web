// CVE Modal - Glassmorphism, detaylı bilgi
import React, { useEffect } from 'react';
import { X, Shield, AlertCircle, ExternalLink, Calendar, Info } from 'lucide-react';

const CVEModal = ({ cve, onClose }) => {
  // ESC key ile kapatma
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);
  // CVE severity color
  const getSeverityColor = (severity) => {
    const colors = {
      CRITICAL: 'text-rose-400 bg-rose-500/10 border-rose-500/30',
      HIGH: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
      MEDIUM: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30',
      LOW: 'text-blue-400 bg-blue-500/10 border-blue-500/30'
    };
    return colors[severity] || 'text-text-tertiary bg-obsidian-850 border-obsidian-700';
  };

  // Parse CVE data - TÜM ALANLAR
  const cveId = typeof cve === 'string' ? cve : cve.cve_id || cve.id;
  const description = cve.description || cve.summary || 'No description available';
  const severity = cve.severity || 'UNKNOWN';
  const baseScore = cve.base_score || cve.cvss_score || null;
  const references = cve.references || cve.refs || cve.metadata?.references || [];
  const publishedDate = cve.published || cve.published_date || cve.metadata?.published_date || null;
  const modifiedDate = cve.modified || cve.modified_date || cve.metadata?.modified_date || null;
  const cweId = cve.cwe_id || cve.cwe || cve.metadata?.cwe_id || null;
  const vendor = cve.vendor || cve.metadata?.vendor || null;
  const product = cve.product || cve.metadata?.product || null;
  const cvssVector = cve.cvss_vector || cve.metadata?.cvss_vector || null;
  const exploitabilityScore = cve.exploitability_score || cve.metadata?.exploitability_score || null;
  const impactScore = cve.impact_score || cve.metadata?.impact_score || null;
  const attackVector = cve.attack_vector || cve.metadata?.attack_vector || null;
  const accessComplexity = cve.access_complexity || cve.metadata?.access_complexity || null;
  const authentication = cve.authentication || cve.metadata?.authentication || null;
  const confidentialityImpact = cve.confidentiality_impact || cve.metadata?.confidentiality_impact || null;
  const integrityImpact = cve.integrity_impact || cve.metadata?.integrity_impact || null;
  const availabilityImpact = cve.availability_impact || cve.metadata?.availability_impact || null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-obsidian-950/80 backdrop-blur-sm"
      onClick={onClose}
    >
      {/* Modal Container - Glassmorphism */}
      <div 
        onClick={(e) => e.stopPropagation()}
        className="relative w-full max-w-3xl max-h-[90vh] overflow-hidden bg-obsidian-900/70 backdrop-blur-xl border border-purple-500/20 rounded-2xl shadow-2xl"
        style={{
          boxShadow: '0 0 60px rgba(139, 92, 246, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.05)'
        }}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 bg-obsidian-900/90 backdrop-blur-md border-b border-purple-500/20 p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Shield size={18} className="text-purple-400" />
                <h2 className="text-lg font-bold text-platinum">{cveId}</h2>
              </div>
              
              {/* Severity & Scores */}
              <div className="flex items-center gap-2 flex-wrap">
                <div className={`px-2.5 py-1 rounded text-xs font-medium border ${getSeverityColor(severity)}`}>
                  {severity}
                </div>
                {baseScore && (
                  <div className="flex items-center gap-1.5 px-2.5 py-1 bg-purple-500/10 border border-purple-500/20 rounded">
                    <AlertCircle size={12} className="text-purple-400" />
                    <span className="text-xs text-purple-400 font-medium">
                      CVSS: {baseScore}
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Close Button */}
            <button
              onClick={onClose}
              className="p-2 hover:bg-obsidian-850 rounded-lg text-text-tertiary hover:text-text-primary transition-all"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-120px)] p-6 space-y-6 scrollbar-thin scrollbar-thumb-purple-500/20 scrollbar-track-transparent">
          {/* Description */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <Info size={14} className="text-purple-400" />
              <h3 className="text-sm font-semibold text-platinum">Description</h3>
            </div>
            <div className="bg-obsidian-950/50 border border-purple-500/10 rounded-lg p-4">
              <p className="text-xs text-text-secondary leading-relaxed">
                {description}
              </p>
            </div>
          </section>

          {/* CVSS Details */}
          {(exploitabilityScore || impactScore || attackVector || accessComplexity || authentication) && (
            <section>
              <div className="flex items-center gap-2 mb-3">
                <AlertCircle size={14} className="text-purple-400" />
                <h3 className="text-sm font-semibold text-platinum">CVSS Metrics</h3>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {attackVector && (
                  <div className="bg-obsidian-950/50 border border-purple-500/10 rounded-lg p-3">
                    <span className="text-[10px] text-text-tertiary uppercase tracking-wide block mb-1">Attack Vector</span>
                    <p className="text-xs text-platinum font-medium">{attackVector}</p>
                  </div>
                )}
                {accessComplexity && (
                  <div className="bg-obsidian-950/50 border border-purple-500/10 rounded-lg p-3">
                    <span className="text-[10px] text-text-tertiary uppercase tracking-wide block mb-1">Complexity</span>
                    <p className="text-xs text-platinum font-medium">{accessComplexity}</p>
                  </div>
                )}
                {authentication && (
                  <div className="bg-obsidian-950/50 border border-purple-500/10 rounded-lg p-3">
                    <span className="text-[10px] text-text-tertiary uppercase tracking-wide block mb-1">Auth Required</span>
                    <p className="text-xs text-platinum font-medium">{authentication}</p>
                  </div>
                )}
                {exploitabilityScore && (
                  <div className="bg-obsidian-950/50 border border-purple-500/10 rounded-lg p-3">
                    <span className="text-[10px] text-text-tertiary uppercase tracking-wide block mb-1">Exploitability</span>
                    <p className="text-xs text-purple-400 font-medium">{exploitabilityScore.toFixed(1)}</p>
                  </div>
                )}
                {impactScore && (
                  <div className="bg-obsidian-950/50 border border-purple-500/10 rounded-lg p-3">
                    <span className="text-[10px] text-text-tertiary uppercase tracking-wide block mb-1">Impact Score</span>
                    <p className="text-xs text-rose-400 font-medium">{impactScore.toFixed(1)}</p>
                  </div>
                )}
                {confidentialityImpact && (
                  <div className="bg-obsidian-950/50 border border-purple-500/10 rounded-lg p-3">
                    <span className="text-[10px] text-text-tertiary uppercase tracking-wide block mb-1">Confidentiality</span>
                    <p className="text-xs text-platinum font-medium">{confidentialityImpact}</p>
                  </div>
                )}
                {integrityImpact && (
                  <div className="bg-obsidian-950/50 border border-purple-500/10 rounded-lg p-3">
                    <span className="text-[10px] text-text-tertiary uppercase tracking-wide block mb-1">Integrity</span>
                    <p className="text-xs text-platinum font-medium">{integrityImpact}</p>
                  </div>
                )}
                {availabilityImpact && (
                  <div className="bg-obsidian-950/50 border border-purple-500/10 rounded-lg p-3">
                    <span className="text-[10px] text-text-tertiary uppercase tracking-wide block mb-1">Availability</span>
                    <p className="text-xs text-platinum font-medium">{availabilityImpact}</p>
                  </div>
                )}
              </div>
              {cvssVector && (
                <div className="mt-3 bg-obsidian-950/50 border border-purple-500/10 rounded-lg p-3">
                  <span className="text-[10px] text-text-tertiary uppercase tracking-wide block mb-1">CVSS Vector</span>
                  <code className="text-[10px] text-purple-300 font-mono">{cvssVector}</code>
                </div>
              )}
            </section>
          )}

          {/* Metadata */}
          {(publishedDate || modifiedDate || cweId || vendor || product) && (
            <section>
              <h3 className="text-sm font-semibold text-platinum mb-3">Metadata</h3>
              <div className="grid grid-cols-2 gap-3">
                {publishedDate && (
                  <div className="bg-obsidian-950/50 border border-purple-500/10 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Calendar size={12} className="text-purple-400" />
                      <span className="text-[10px] text-text-tertiary uppercase tracking-wide">Published</span>
                    </div>
                    <p className="text-xs text-platinum">{new Date(publishedDate).toLocaleDateString()}</p>
                  </div>
                )}
                
                {modifiedDate && (
                  <div className="bg-obsidian-950/50 border border-purple-500/10 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Calendar size={12} className="text-purple-400" />
                      <span className="text-[10px] text-text-tertiary uppercase tracking-wide">Modified</span>
                    </div>
                    <p className="text-xs text-platinum">{new Date(modifiedDate).toLocaleDateString()}</p>
                  </div>
                )}
                
                {cweId && (
                  <div className="bg-obsidian-950/50 border border-purple-500/10 rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <Shield size={12} className="text-purple-400" />
                      <span className="text-[10px] text-text-tertiary uppercase tracking-wide">CWE ID</span>
                    </div>
                    <p className="text-xs text-platinum">{cweId}</p>
                  </div>
                )}
                
                {vendor && (
                  <div className="bg-obsidian-950/50 border border-purple-500/10 rounded-lg p-3">
                    <span className="text-[10px] text-text-tertiary uppercase tracking-wide block mb-1">Vendor</span>
                    <p className="text-xs text-platinum">{vendor}</p>
                  </div>
                )}
                
                {product && (
                  <div className="bg-obsidian-950/50 border border-purple-500/10 rounded-lg p-3">
                    <span className="text-[10px] text-text-tertiary uppercase tracking-wide block mb-1">Product</span>
                    <p className="text-xs text-platinum">{product}</p>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* References */}
          {references && references.length > 0 && (
            <section>
              <div className="flex items-center gap-2 mb-3">
                <ExternalLink size={14} className="text-purple-400" />
                <h3 className="text-sm font-semibold text-platinum">
                  References ({references.length})
                </h3>
              </div>
              <div className="space-y-2">
                {references.map((ref, index) => {
                  const url = typeof ref === 'string' ? ref : ref.url || ref.link;
                  const name = typeof ref === 'object' ? ref.name || ref.source : null;
                  
                  return (
                    <a
                      key={index}
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 bg-obsidian-950/50 border border-purple-500/10 hover:border-purple-500/30 rounded-lg p-3 transition-all duration-300 group"
                    >
                      <ExternalLink size={12} className="text-purple-400 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        {name && (
                          <p className="text-xs text-platinum font-medium mb-0.5">{name}</p>
                        )}
                        <p className="text-[10px] text-text-tertiary truncate group-hover:text-purple-400 transition-colors">
                          {url}
                        </p>
                      </div>
                      <ChevronRight size={12} className="text-text-tertiary group-hover:text-purple-400 transition-colors flex-shrink-0" />
                    </a>
                  );
                })}
              </div>
            </section>
          )}

          {/* Full RAG Output (eğer varsa) */}
          {cve.full_text && (
            <section>
              <h3 className="text-sm font-semibold text-platinum mb-3">Full Details</h3>
              <div className="bg-obsidian-950/50 border border-purple-500/10 rounded-lg p-4">
                <pre className="text-xs text-text-secondary leading-relaxed whitespace-pre-wrap font-mono">
                  {cve.full_text}
                </pre>
              </div>
            </section>
          )}
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-obsidian-900/90 backdrop-blur-md border-t border-purple-500/20 p-4">
          <div className="flex items-center justify-between">
            <p className="text-[10px] text-text-tertiary">
              Click outside or press ESC to close
            </p>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 rounded-lg text-xs font-medium text-purple-400 transition-all duration-300"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ESC key ile kapatma
const ChevronRight = ({ size, className }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" className={className}>
    <path d="M9 18l6-6-6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
);

export default CVEModal;

