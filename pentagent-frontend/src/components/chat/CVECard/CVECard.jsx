// CVE Card - Minimalist, küçük yazı, özet bilgi
import React, { useState } from 'react';
import { Shield, ExternalLink, AlertCircle, ChevronRight } from 'lucide-react';
import CVEModal from '../CVEModal';

const CVECard = ({ cve }) => {
  const [modalOpen, setModalOpen] = useState(false);

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

  // Açıklamayı kısalt (ilk 150 karakter)
  const getTruncatedDescription = (desc) => {
    if (!desc) return 'No description available';
    if (desc.length <= 150) return desc;
    return desc.substring(0, 150) + '...';
  };

  // CVE ID parse (eğer string ise)
  const cveId = typeof cve === 'string' ? cve : cve.cve_id || cve.id;
  const description = cve.description || cve.summary || '';
  const severity = cve.severity || 'UNKNOWN';
  const score = cve.score || cve.cvss_score || 'N/A';
  const references = cve.references || cve.refs || [];

  return (
    <>
      <div 
        onClick={() => setModalOpen(true)}
        className="bg-obsidian-900/50 border border-purple-500/20 rounded-lg p-3 hover:bg-obsidian-900 hover:border-purple-500/40 transition-all duration-300 cursor-pointer group"
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <Shield size={14} className="text-purple-400 flex-shrink-0" />
            <span className="text-xs font-semibold text-platinum">{cveId}</span>
          </div>
          
          {/* Severity Badge */}
          <div className={`px-2 py-0.5 rounded text-[10px] font-medium border ${getSeverityColor(severity)}`}>
            {severity}
          </div>
        </div>

        {/* Description - Truncated */}
        <p className="text-xs text-text-secondary leading-relaxed mb-2 line-clamp-2">
          {getTruncatedDescription(description)}
        </p>

        {/* Footer - Score & References */}
        <div className="flex items-center justify-between gap-2 pt-2 border-t border-obsidian-700">
          {/* CVSS Score */}
          {score && score !== 'N/A' && (
            <div className="flex items-center gap-1.5">
              <AlertCircle size={12} className="text-purple-400" />
              <span className="text-[10px] text-text-tertiary">
                CVSS: <span className="text-purple-400 font-medium">{score}</span>
              </span>
            </div>
          )}

          {/* References Count */}
          {references && references.length > 0 && (
            <div className="flex items-center gap-1.5">
              <ExternalLink size={12} className="text-text-tertiary" />
              <span className="text-[10px] text-text-tertiary">
                {references.length} {references.length === 1 ? 'ref' : 'refs'}
              </span>
            </div>
          )}

          {/* View Details */}
          <div className="flex items-center gap-1 text-purple-400 opacity-0 group-hover:opacity-100 transition-opacity ml-auto">
            <span className="text-[10px] font-medium">Details</span>
            <ChevronRight size={12} />
          </div>
        </div>
      </div>

      {/* Modal */}
      {modalOpen && (
        <CVEModal 
          cve={cve}
          onClose={() => setModalOpen(false)}
        />
      )}
    </>
  );
};

export default CVECard;












