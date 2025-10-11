import React, { useState } from 'react';
import { 
  Search, 
  Filter, 
  Calendar,
  Target,
  AlertTriangle,
  SortDesc,
  X,
  Download,
  Archive
} from 'lucide-react';
import Button from '../../common/Button';
import Input from '../../common/Input';

const ReportFilters = ({ 
  onFilterChange, 
  onSearch, 
  onSort,
  totalReports,
  filteredCount,
  onBulkAction
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [activeFilters, setActiveFilters] = useState({
    status: [],
    severity: [],
    dateRange: 'all',
    target: '',
    riskScore: 'all'
  });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [sortBy, setSortBy] = useState('createdAt');
  const [sortOrder, setSortOrder] = useState('desc');

  const statusOptions = [
    { value: 'completed', label: 'Completed', count: 45 },
    { value: 'processing', label: 'Processing', count: 3 },
    { value: 'failed', label: 'Failed', count: 2 }
  ];

  const severityOptions = [
    { value: 'critical', label: 'Critical', color: 'rose' },
    { value: 'high', label: 'High', color: 'rose' },
    { value: 'medium', label: 'Medium', color: 'warning' },
    { value: 'low', label: 'Low', color: 'success' }
  ];

  const dateRangeOptions = [
    { value: 'all', label: 'All Time' },
    { value: 'today', label: 'Today' },
    { value: 'week', label: 'This Week' },
    { value: 'month', label: 'This Month' },
    { value: 'quarter', label: 'This Quarter' },
    { value: 'custom', label: 'Custom Range' }
  ];

  const sortOptions = [
    { value: 'createdAt', label: 'Date Created' },
    { value: 'title', label: 'Report Title' },
    { value: 'target', label: 'Target' },
    { value: 'riskScore', label: 'Risk Score' },
    { value: 'vulnerabilities', label: 'Total Vulnerabilities' }
  ];

  const handleSearch = (value) => {
    setSearchTerm(value);
    onSearch?.(value);
  };

  const handleFilterChange = (filterType, value) => {
    const newFilters = { ...activeFilters };
    
    if (filterType === 'status' || filterType === 'severity') {
      if (newFilters[filterType].includes(value)) {
        newFilters[filterType] = newFilters[filterType].filter(v => v !== value);
      } else {
        newFilters[filterType] = [...newFilters[filterType], value];
      }
    } else {
      newFilters[filterType] = value;
    }
    
    setActiveFilters(newFilters);
    onFilterChange?.(newFilters);
  };

  const clearAllFilters = () => {
    const clearedFilters = {
      status: [],
      severity: [],
      dateRange: 'all',
      target: '',
      riskScore: 'all'
    };
    setActiveFilters(clearedFilters);
    setSearchTerm('');
    onFilterChange?.(clearedFilters);
    onSearch?.('');
  };

  const handleSort = (field) => {
    const newOrder = sortBy === field && sortOrder === 'desc' ? 'asc' : 'desc';
    setSortBy(field);
    setSortOrder(newOrder);
    onSort?.({ field, order: newOrder });
  };

  const getActiveFilterCount = () => {
    return activeFilters.status.length + 
           activeFilters.severity.length + 
           (activeFilters.dateRange !== 'all' ? 1 : 0) +
           (activeFilters.target ? 1 : 0) +
           (activeFilters.riskScore !== 'all' ? 1 : 0);
  };

  const FilterChip = ({ label, onRemove, color = 'default' }) => {
    const colorClasses = {
      default: 'bg-obsidian-800 text-text-secondary',
      rose: 'bg-rose-500/10 text-rose-400 border-rose-500/20',
      warning: 'bg-warning/10 text-warning border-warning/20',
      success: 'bg-success/10 text-success border-success/20'
    };

    return (
      <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm border ${colorClasses[color]}`}>
        <span>{label}</span>
        <button
          onClick={onRemove}
          className="hover:text-text-primary transition-colors"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
    );
  };

  return (
    <div className="bg-obsidian-900 border border-obsidian-700 rounded-xl p-6">
      {/* Search & Quick Actions */}
      <div className="flex flex-col lg:flex-row gap-4 mb-6">
        <div className="flex-1">
          <Input
            placeholder="Search reports by title, target, or findings..."
            value={searchTerm}
            onChange={(e) => handleSearch(e.target.value)}
            icon={Search}
          />
        </div>
        
        <div className="flex gap-3">
          <Button
            variant={showAdvanced ? 'primary' : 'secondary'}
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            <Filter className="w-4 h-4 mr-2" />
            Filters
            {getActiveFilterCount() > 0 && (
              <span className="ml-2 px-2 py-0.5 bg-platinum-500 text-obsidian-950 rounded-full text-xs">
                {getActiveFilterCount()}
              </span>
            )}
          </Button>
          
          <Button variant="ghost">
            <Download className="w-4 h-4 mr-2" />
            Export All
          </Button>
        </div>
      </div>

      {/* Results Summary */}
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-text-secondary">
          Showing <span className="font-medium text-text-primary">{filteredCount}</span> of{' '}
          <span className="font-medium">{totalReports}</span> reports
        </div>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <SortDesc className="w-4 h-4 text-text-tertiary" />
            <select
              value={`${sortBy}-${sortOrder}`}
              onChange={(e) => {
                const [field, order] = e.target.value.split('-');
                setSortBy(field);
                setSortOrder(order);
                onSort?.({ field, order });
              }}
              className="bg-obsidian-850 border border-obsidian-700 rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-platinum-500 transition-colors"
            >
              {sortOptions.map(option => (
                <React.Fragment key={option.value}>
                  <option value={`${option.value}-desc`}>{option.label} (Newest)</option>
                  <option value={`${option.value}-asc`}>{option.label} (Oldest)</option>
                </React.Fragment>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Active Filter Chips */}
      {(getActiveFilterCount() > 0 || searchTerm) && (
        <div className="flex flex-wrap gap-2 mb-6">
          {searchTerm && (
            <FilterChip 
              label={`Search: "${searchTerm}"`} 
              onRemove={() => handleSearch('')}
            />
          )}
          
          {activeFilters.status.map(status => (
            <FilterChip
              key={`status-${status}`}
              label={`Status: ${status}`}
              onRemove={() => handleFilterChange('status', status)}
            />
          ))}
          
          {activeFilters.severity.map(severity => (
            <FilterChip
              key={`severity-${severity}`}
              label={`Severity: ${severity}`}
              onRemove={() => handleFilterChange('severity', severity)}
              color={severity === 'critical' || severity === 'high' ? 'rose' : severity === 'medium' ? 'warning' : 'success'}
            />
          ))}
          
          {activeFilters.dateRange !== 'all' && (
            <FilterChip
              label={`Date: ${dateRangeOptions.find(o => o.value === activeFilters.dateRange)?.label}`}
              onRemove={() => handleFilterChange('dateRange', 'all')}
            />
          )}
          
          {activeFilters.target && (
            <FilterChip
              label={`Target: ${activeFilters.target}`}
              onRemove={() => handleFilterChange('target', '')}
            />
          )}
          
          <Button variant="ghost" size="sm" onClick={clearAllFilters}>
            Clear All
          </Button>
        </div>
      )}

      {/* Advanced Filters */}
      {showAdvanced && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 p-6 bg-obsidian-850 rounded-lg">
          
          {/* Status Filter */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-3">Status</label>
            <div className="space-y-2">
              {statusOptions.map(option => (
                <label key={option.value} className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={activeFilters.status.includes(option.value)}
                    onChange={() => handleFilterChange('status', option.value)}
                    className="w-4 h-4 text-platinum-500 bg-obsidian-900 border-obsidian-600 rounded focus:ring-platinum-500 focus:ring-2"
                  />
                  <span className="text-sm text-text-secondary">
                    {option.label} ({option.count})
                  </span>
                </label>
              ))}
            </div>
          </div>

          {/* Severity Filter */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-3">Severity</label>
            <div className="space-y-2">
              {severityOptions.map(option => (
                <label key={option.value} className="flex items-center gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={activeFilters.severity.includes(option.value)}
                    onChange={() => handleFilterChange('severity', option.value)}
                    className="w-4 h-4 text-platinum-500 bg-obsidian-900 border-obsidian-600 rounded focus:ring-platinum-500 focus:ring-2"
                  />
                  <div className="flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${
                      option.color === 'rose' ? 'bg-rose-500' :
                      option.color === 'warning' ? 'bg-warning' :
                      option.color === 'success' ? 'bg-success' : 'bg-text-tertiary'
                    }`} />
                    <span className="text-sm text-text-secondary capitalize">
                      {option.label}
                    </span>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Date Range Filter */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-3">Date Range</label>
            <select
              value={activeFilters.dateRange}
              onChange={(e) => handleFilterChange('dateRange', e.target.value)}
              className="w-full bg-obsidian-900 border border-obsidian-700 rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-platinum-500 transition-colors"
            >
              {dateRangeOptions.map(option => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Target Filter */}
          <div>
            <label className="block text-sm font-medium text-text-secondary mb-3">Target</label>
            <Input
              placeholder="Filter by target..."
              value={activeFilters.target}
              onChange={(e) => handleFilterChange('target', e.target.value)}
              icon={Target}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportFilters;
