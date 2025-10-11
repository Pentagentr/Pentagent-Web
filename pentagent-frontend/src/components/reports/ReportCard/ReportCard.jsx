import React, { useState } from 'react';
import { 
  Eye, 
  Download, 
  Share2, 
  Calendar,
  Target,
  AlertTriangle,
  CheckCircle,
  Clock,
  MoreVertical,
  FileText,
  Trash2,
  Archive
} from 'lucide-react';
import Button from '../../common/Button';

const ReportCard = ({ 
  report, 
  onView, 
  onDownload, 
  onShare, 
  onDelete,
  onArchive 
}) => {
  const [showDropdown, setShowDropdown] = useState(false);

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical': return 'text-rose-500 bg-rose-500/10 border-rose-500/20';
      case 'high': return 'text-rose-500 bg-rose-500/10 border-rose-500/20';
      case 'medium': return 'text-warning bg-warning/10 border-warning/20';
      case 'low': return 'text-success bg-success/10 border-success/20';
      default: return 'text-text-tertiary bg-obsidian-800 border-obsidian-700';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-4 h-4 text-success" />;
      case 'processing': return <Clock className="w-4 h-4 text-platinum-500" />;
      case 'failed': return <AlertTriangle className="w-4 h-4 text-rose-500" />;
      default: return <FileText className="w-4 h-4 text-text-tertiary" />;
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  };

  return (
    <div className="bg-obsidian-900 border border-obsidian-700 rounded-xl overflow-hidden hover:border-obsidian-600 transition-all duration-300 hover-lift group">
      {/* Report Preview Thumbnail */}
      <div className="relative h-48 bg-gradient-to-br from-obsidian-800 to-obsidian-850 border-b border-obsidian-700">
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <FileText className="w-16 h-16 text-text-tertiary mx-auto mb-2" />
            <span className="text-sm text-text-tertiary">{report.format?.toUpperCase()} Report</span>
          </div>
        </div>
        
        {/* Status Badge */}
        <div className="absolute top-4 left-4 flex items-center gap-2 px-3 py-1.5 bg-obsidian-950/80 backdrop-blur-sm border border-obsidian-700 rounded-full">
          {getStatusIcon(report.status)}
          <span className="text-xs font-medium text-text-primary capitalize">{report.status}</span>
        </div>
        
        {/* Actions Dropdown */}
        <div className="absolute top-4 right-4">
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="p-2 bg-obsidian-950/80 backdrop-blur-sm border border-obsidian-700 rounded-lg text-text-tertiary hover:text-text-primary transition-colors opacity-0 group-hover:opacity-100"
          >
            <MoreVertical className="w-4 h-4" />
          </button>
          
          {showDropdown && (
            <div className="absolute right-0 top-12 bg-obsidian-900 border border-obsidian-700 rounded-lg shadow-xl z-10 py-1 min-w-[140px]">
              <button 
                onClick={() => { onView?.(report); setShowDropdown(false); }}
                className="w-full px-3 py-2 text-left text-sm text-text-secondary hover:bg-obsidian-850 hover:text-text-primary flex items-center gap-2"
              >
                <Eye className="w-3 h-3" />
                View Report
              </button>
              <button 
                onClick={() => { onShare?.(report); setShowDropdown(false); }}
                className="w-full px-3 py-2 text-left text-sm text-text-secondary hover:bg-obsidian-850 hover:text-text-primary flex items-center gap-2"
              >
                <Share2 className="w-3 h-3" />
                Share
              </button>
              <button 
                onClick={() => { onArchive?.(report); setShowDropdown(false); }}
                className="w-full px-3 py-2 text-left text-sm text-text-secondary hover:bg-obsidian-850 hover:text-text-primary flex items-center gap-2"
              >
                <Archive className="w-3 h-3" />
                Archive
              </button>
              <button 
                onClick={() => { onDelete?.(report); setShowDropdown(false); }}
                className="w-full px-3 py-2 text-left text-sm text-rose-400 hover:bg-rose-500/10 flex items-center gap-2"
              >
                <Trash2 className="w-3 h-3" />
                Delete
              </button>
            </div>
          )}
        </div>
        
        {/* Quick Preview on Hover */}
        <div className="absolute inset-0 bg-obsidian-950/90 backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
          <Button variant="primary" size="sm" onClick={() => onView?.(report)}>
            <Eye className="w-4 h-4 mr-2" />
            Quick View
          </Button>
        </div>
      </div>
      
      {/* Report Info */}
      <div className="p-6">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold text-text-primary mb-1 truncate">
              {report.title}
            </h3>
            <div className="flex items-center gap-2 text-sm text-text-tertiary">
              <Target className="w-3 h-3" />
              <span>{report.target}</span>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-2 text-sm text-text-tertiary mb-4">
          <Calendar className="w-3 h-3" />
          <span>{formatDate(report.createdAt)}</span>
          <span>•</span>
          <span>{report.pages} pages</span>
        </div>
        
        {/* Vulnerability Summary */}
        <div className="mb-4">
          <div className="text-sm text-text-secondary mb-2">Findings:</div>
          <div className="flex items-center gap-3 text-sm">
            {Object.entries(report.vulnerabilities).map(([severity, count]) => (
              <div key={severity} className="flex items-center gap-1">
                <div className={`w-3 h-3 rounded-full ${
                  severity === 'critical' ? 'bg-rose-500' :
                  severity === 'high' ? 'bg-rose-500' :
                  severity === 'medium' ? 'bg-warning' :
                  severity === 'low' ? 'bg-success' : 'bg-text-tertiary'
                }`} />
                <span className="text-text-tertiary capitalize">{severity}:</span>
                <span className="font-medium text-text-primary">{count}</span>
              </div>
            ))}
          </div>
        </div>
        
        {/* Risk Score */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-text-secondary">Risk Score</span>
            <span className="text-lg font-bold text-rose-500">{report.riskScore}/10</span>
          </div>
          <div className="w-full h-2 bg-obsidian-700 rounded-full overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-rose-500 to-rose-600 rounded-full transition-all duration-300"
              style={{ width: `${(report.riskScore / 10) * 100}%` }}
            />
          </div>
        </div>
        
        {/* Action Buttons */}
        <div className="flex gap-3">
          <Button 
            variant="primary" 
            className="flex-1"
            onClick={() => onView?.(report)}
          >
            <Eye className="w-4 h-4 mr-2" />
            View
          </Button>
          <Button 
            variant="secondary"
            onClick={() => onDownload?.(report)}
          >
            <Download className="w-4 h-4" />
          </Button>
          <Button 
            variant="ghost"
            onClick={() => onShare?.(report)}
          >
            <Share2 className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ReportCard;
