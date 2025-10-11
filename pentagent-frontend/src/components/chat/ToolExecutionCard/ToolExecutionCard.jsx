import React, { useState } from 'react';
import { 
  ChevronDown, 
  ChevronUp, 
  Play, 
  Pause, 
  Square, 
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Copy,
  Download
} from 'lucide-react';
import Button from '../../common/Button';

const ToolExecutionCard = ({
  toolName,
  status,
  progress = 0,
  duration,
  results = [],
  timestamp,
  onStop,
  onView
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [showFullOutput, setShowFullOutput] = useState(false);
  const [animatedProgress, setAnimatedProgress] = useState(0);
  
  // Progress animasyonu
  React.useEffect(() => {
    if (status === 'running' && progress > 0) {
      const timer = setTimeout(() => {
        setAnimatedProgress(progress);
      }, 100);
      return () => clearTimeout(timer);
    } else if (status === 'completed') {
      setAnimatedProgress(100);
    }
  }, [progress, status]);

  const getStatusIcon = () => {
    switch (status) {
      case 'running':
        return <Play className="w-4 h-4 text-platinum-500 animate-pulse" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-success" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-rose-500" />;
      case 'stopped':
        return <Square className="w-4 h-4 text-text-tertiary" />;
      default:
        return <Clock className="w-4 h-4 text-text-tertiary" />;
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'running': return 'border-platinum-500/30 bg-platinum-500/5';
      case 'completed': return 'border-success/30 bg-success/5';
      case 'error': return 'border-rose-500/30 bg-rose-500/5';
      default: return 'border-obsidian-700 bg-obsidian-900/50';
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical': return 'text-rose-500 bg-rose-500/10';
      case 'high': return 'text-rose-500 bg-rose-500/10';
      case 'medium': return 'text-warning bg-warning/10';
      case 'low': return 'text-success bg-success/10';
      case 'info': return 'text-text-tertiary bg-obsidian-800';
      default: return 'text-text-tertiary bg-obsidian-800';
    }
  };

  const formatOutput = (results) => {
    return results.map((result, index) => (
      <div key={index} className="flex items-center justify-between py-2 border-b border-obsidian-700 last:border-b-0">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-text-tertiary" />
          <span className="text-text-secondary text-sm">
            {result.parameter && `${result.parameter}: `}
            {result.port && `Port ${result.port} (${result.service}): `}
            <span className="text-text-primary">{result.vector || result.status}</span>
          </span>
        </div>
        
        {result.severity && (
          <span className={`px-2 py-1 text-xs rounded-full ${getSeverityColor(result.severity)}`}>
            {result.severity}
          </span>
        )}
        
        {result.status && !result.severity && (
          <span className={`text-xs ${
            result.status === 'Open' || result.status === 'Vulnerable' 
              ? 'text-rose-400' 
              : result.status === 'Safe' || result.status === 'Closed'
              ? 'text-success'
              : 'text-platinum-400'
          }`}>
            {result.status}
          </span>
        )}
      </div>
    ));
  };

  return (
    <div className={`border rounded-xl overflow-hidden transition-all duration-300 ${getStatusColor()}`}>
      {/* Header */}
      <div className="p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {getStatusIcon()}
          <div>
            <h3 className="font-semibold text-text-primary">{toolName}</h3>
            <div className="flex items-center gap-3 text-sm text-text-tertiary">
              <span className="capitalize">{status}</span>
              {duration && (
                <>
                  <span>•</span>
                  <span>{duration}</span>
                </>
              )}
              {timestamp && (
                <>
                  <span>•</span>
                  <span>{timestamp}</span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {status === 'running' && onStop && (
            <Button variant="ghost" size="sm" onClick={onStop}>
              <Square className="w-4 h-4" />
            </Button>
          )}
          
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-2 text-text-tertiary hover:text-text-secondary hover:bg-obsidian-800 rounded-lg transition-all"
          >
            {isExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      {(status === 'running' || status === 'completed') && (
        <div className="px-4 pb-2">
          <div className="w-full h-2 bg-obsidian-700 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-500 ${
                status === 'running' 
                  ? 'bg-gradient-to-r from-platinum-500 to-platinum-600' 
                  : 'bg-gradient-to-r from-green-500 to-green-600'
              }`}
              style={{ width: `${animatedProgress}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-text-tertiary mt-1">
            <span>{status === 'running' ? 'Çalışıyor...' : 'Tamamlandı'}</span>
            <span>{animatedProgress}%</span>
          </div>
        </div>
      )}

      {/* Expandable Content */}
      {isExpanded && (
        <div className="border-t border-obsidian-700">
          {/* Results */}
          {results.length > 0 && (
            <div className="p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="font-medium text-text-primary">
                  Results ({results.length})
                </h4>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm" className="text-xs">
                    <Copy className="w-3 h-3 mr-1" />
                    Copy
                  </Button>
                  <Button variant="ghost" size="sm" className="text-xs">
                    <Download className="w-3 h-3 mr-1" />
                    Export
                  </Button>
                </div>
              </div>
              
              <div className="bg-obsidian-950 border border-obsidian-700 rounded-lg p-3">
                {showFullOutput ? (
                  <div className="space-y-1 max-h-64 overflow-y-auto">
                    {formatOutput(results)}
                  </div>
                ) : (
                  <div className="space-y-1">
                    {formatOutput(results.slice(0, 3))}
                    {results.length > 3 && (
                      <button
                        onClick={() => setShowFullOutput(true)}
                        className="w-full py-2 text-sm text-platinum-500 hover:text-platinum-400 transition-colors"
                      >
                        Show {results.length - 3} more results...
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Status-specific content */}
          {status === 'error' && (
            <div className="p-4 bg-rose-500/5">
              <div className="flex items-center gap-2 mb-2">
                <XCircle className="w-4 h-4 text-rose-500" />
                <span className="font-medium text-rose-400">Execution Error</span>
              </div>
              <p className="text-sm text-text-secondary">
                The tool encountered an error during execution. This might be due to network connectivity, 
                target unavailability, or configuration issues.
              </p>
              <div className="mt-3 flex gap-2">
                <Button variant="ghost" size="sm">Retry</Button>
                <Button variant="ghost" size="sm">View Logs</Button>
              </div>
            </div>
          )}

          {status === 'completed' && results.length === 0 && (
            <div className="p-4 text-center">
              <CheckCircle className="w-8 h-8 text-success mx-auto mb-2" />
              <p className="text-sm text-text-secondary">
                Tool completed successfully with no findings.
              </p>
            </div>
          )}

          {/* Action Buttons */}
          <div className="p-4 bg-obsidian-900/50 border-t border-obsidian-700">
            <div className="flex items-center justify-between">
              <div className="text-xs text-text-tertiary">
                {status === 'running' && 'Execution in progress...'}
                {status === 'completed' && 'Execution completed successfully'}
                {status === 'error' && 'Execution failed'}
              </div>
              
              <div className="flex gap-2">
                {status === 'completed' && onView && (
                  <Button variant="secondary" size="sm" onClick={onView}>
                    View Full Output
                  </Button>
                )}
                
                {(status === 'completed' || status === 'error') && (
                  <Button variant="ghost" size="sm">
                    Run Again
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ToolExecutionCard;
