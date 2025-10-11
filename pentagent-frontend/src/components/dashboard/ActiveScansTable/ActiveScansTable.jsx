import React, { useState } from 'react';
import { 
  Play, 
  Pause, 
  Square, 
  Eye, 
  MoreVertical,
  Clock,
  CheckCircle,
  AlertTriangle,
  Zap
} from 'lucide-react';
import Button from '../../common/Button';
import Card from '../../common/Card';

const ActiveScansTable = ({ scans = [], onViewScan, onControlScan }) => {
  const [sortField, setSortField] = useState('startTime');
  const [sortDirection, setSortDirection] = useState('desc');

  const mockScans = [
    {
      id: '1',
      target: 'example.com',
      scanType: 'Full Security Audit',
      status: 'running',
      progress: 75,
      startTime: '2:30 PM',
      duration: '5m 32s',
      vulnerabilities: 12,
      currentTool: 'SQL Injection Tester',
      estimatedTime: '2m 15s'
    },
    {
      id: '2',
      target: 'api.testsite.io',
      scanType: 'API Security Check',
      status: 'queued',
      progress: 0,
      startTime: '2:45 PM',
      duration: '0m 00s',
      vulnerabilities: 0,
      currentTool: null,
      estimatedTime: '3m 00s'
    },
    {
      id: '3',
      target: 'app.demo.co',
      scanType: 'OWASP Top 10',
      status: 'completed',
      progress: 100,
      startTime: '2:15 PM',
      duration: '8m 47s',
      vulnerabilities: 23,
      currentTool: null,
      estimatedTime: null
    },
    {
      id: '4',
      target: 'staging.myapp.com',
      scanType: 'Quick Vulnerability Scan',
      status: 'error',
      progress: 35,
      startTime: '2:20 PM',
      duration: '2m 12s',
      vulnerabilities: 0,
      currentTool: 'Port Scanner',
      estimatedTime: null,
      error: 'Connection timeout'
    }
  ];

  const data = scans.length > 0 ? scans : mockScans;

  const getStatusIcon = (status) => {
    switch (status) {
      case 'running':
        return <Zap className="w-4 h-4 text-platinum-500 animate-pulse" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-success" />;
      case 'queued':
        return <Clock className="w-4 h-4 text-text-tertiary" />;
      case 'error':
        return <AlertTriangle className="w-4 h-4 text-rose-500" />;
      default:
        return <Clock className="w-4 h-4 text-text-tertiary" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'running': return 'text-platinum-500 bg-platinum-500/10';
      case 'completed': return 'text-success bg-success/10';
      case 'queued': return 'text-text-tertiary bg-obsidian-800';
      case 'error': return 'text-rose-500 bg-rose-500/10';
      default: return 'text-text-tertiary bg-obsidian-800';
    }
  };

  const getVulnerabilityColor = (count) => {
    if (count >= 20) return 'text-rose-500';
    if (count >= 10) return 'text-rose-500';  
    if (count > 0) return 'text-warning';
    return 'text-success';
  };

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortedData = [...data].sort((a, b) => {
    let aVal = a[sortField];
    let bVal = b[sortField];
    
    if (sortDirection === 'asc') {
      return aVal > bVal ? 1 : -1;
    } else {
      return aVal < bVal ? 1 : -1;
    }
  });

  return (
    <Card>
      <Card.Header>
        <Card.Title>Active Scans</Card.Title>
        <Button variant="primary" size="sm">
          + New Scan
        </Button>
      </Card.Header>
      
      <Card.Body className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-obsidian-700">
                <th className="text-left py-3 px-6 font-medium text-text-secondary">
                  <button 
                    onClick={() => handleSort('target')}
                    className="hover:text-text-primary transition-colors"
                  >
                    Target
                  </button>
                </th>
                <th className="text-left py-3 px-6 font-medium text-text-secondary">
                  <button 
                    onClick={() => handleSort('scanType')}
                    className="hover:text-text-primary transition-colors"
                  >
                    Scan Type
                  </button>
                </th>
                <th className="text-left py-3 px-6 font-medium text-text-secondary">
                  <button 
                    onClick={() => handleSort('status')}
                    className="hover:text-text-primary transition-colors"
                  >
                    Status
                  </button>
                </th>
                <th className="text-left py-3 px-6 font-medium text-text-secondary">Progress</th>
                <th className="text-left py-3 px-6 font-medium text-text-secondary">Duration</th>
                <th className="text-left py-3 px-6 font-medium text-text-secondary">Findings</th>
                <th className="text-left py-3 px-6 font-medium text-text-secondary">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sortedData.map((scan) => (
                <tr 
                  key={scan.id} 
                  className="border-b border-obsidian-700 hover:bg-obsidian-850/50 transition-colors"
                >
                  {/* Target */}
                  <td className="py-4 px-6">
                    <div>
                      <div className="font-medium text-text-primary">{scan.target}</div>
                      {scan.currentTool && (
                        <div className="text-sm text-text-tertiary">
                          Running: {scan.currentTool}
                        </div>
                      )}
                      {scan.error && (
                        <div className="text-sm text-rose-400">
                          Error: {scan.error}
                        </div>
                      )}
                    </div>
                  </td>
                  
                  {/* Scan Type */}
                  <td className="py-4 px-6">
                    <span className="text-text-secondary">{scan.scanType}</span>
                  </td>
                  
                  {/* Status */}
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(scan.status)}
                      <span className={`px-2 py-1 text-xs rounded-full capitalize ${getStatusColor(scan.status)}`}>
                        {scan.status}
                      </span>
                    </div>
                  </td>
                  
                  {/* Progress */}
                  <td className="py-4 px-6">
                    <div className="w-full">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-text-secondary">{scan.progress}%</span>
                        {scan.estimatedTime && (
                          <span className="text-xs text-text-tertiary">{scan.estimatedTime} left</span>
                        )}
                      </div>
                      <div className="w-24 h-2 bg-obsidian-700 rounded-full overflow-hidden">
                        <div 
                          className={`h-full transition-all duration-300 ${
                            scan.status === 'error' 
                              ? 'bg-rose-500' 
                              : scan.status === 'completed'
                              ? 'bg-success'
                              : 'bg-gradient-to-r from-platinum-500 to-platinum-600'
                          }`}
                          style={{ width: `${scan.progress}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  
                  {/* Duration */}
                  <td className="py-4 px-6">
                    <div className="text-sm">
                      <div className="text-text-secondary">{scan.duration}</div>
                      <div className="text-text-tertiary">{scan.startTime}</div>
                    </div>
                  </td>
                  
                  {/* Findings */}
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-2">
                      <span className={`font-medium ${getVulnerabilityColor(scan.vulnerabilities)}`}>
                        {scan.vulnerabilities}
                      </span>
                      <span className="text-text-tertiary text-sm">
                        {scan.vulnerabilities === 1 ? 'vuln' : 'vulns'}
                      </span>
                    </div>
                  </td>
                  
                  {/* Actions */}
                  <td className="py-4 px-6">
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onViewScan?.(scan.id)}
                      >
                        <Eye className="w-4 h-4" />
                      </Button>
                      
                      {scan.status === 'running' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onControlScan?.(scan.id, 'pause')}
                        >
                          <Pause className="w-4 h-4" />
                        </Button>
                      )}
                      
                      {scan.status === 'queued' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onControlScan?.(scan.id, 'start')}
                        >
                          <Play className="w-4 h-4" />
                        </Button>
                      )}
                      
                      {(scan.status === 'running' || scan.status === 'queued') && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => onControlScan?.(scan.id, 'stop')}
                        >
                          <Square className="w-4 h-4" />
                        </Button>
                      )}
                      
                      <Button variant="ghost" size="sm">
                        <MoreVertical className="w-4 h-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {data.length === 0 && (
          <div className="text-center py-12">
            <div className="w-16 h-16 bg-obsidian-850 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Zap className="w-8 h-8 text-text-tertiary" />
            </div>
            <h3 className="text-text-primary font-medium mb-2">No active scans</h3>
            <p className="text-text-tertiary text-sm mb-4">
              Start your first security assessment to see scan progress here.
            </p>
            <Button variant="primary">
              Start New Scan
            </Button>
          </div>
        )}
      </Card.Body>
      
      {data.length > 0 && (
        <Card.Footer>
          <div className="flex items-center justify-between">
            <span className="text-sm text-text-tertiary">
              Showing {data.length} active scans
            </span>
            <Button variant="secondary" size="sm">
              View All Scans →
            </Button>
          </div>
        </Card.Footer>
      )}
    </Card>
  );
};

export default ActiveScansTable;
