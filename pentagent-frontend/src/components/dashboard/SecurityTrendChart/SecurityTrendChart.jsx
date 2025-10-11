import React, { useState } from 'react';
import { Calendar, TrendingUp } from 'lucide-react';
import Card from '../../common/Card';

const SecurityTrendChart = () => {
  const [timeRange, setTimeRange] = useState('7d');
  
  // Mock trend data
  const trendData = {
    '7d': [
      { date: 'Mon', scans: 12, vulns: 45, resolved: 38 },
      { date: 'Tue', scans: 15, vulns: 52, resolved: 43 },
      { date: 'Wed', scans: 8, vulns: 28, resolved: 31 },
      { date: 'Thu', scans: 18, vulns: 67, resolved: 54 },
      { date: 'Fri', scans: 22, vulns: 73, resolved: 68 },
      { date: 'Sat', scans: 6, vulns: 19, resolved: 22 },
      { date: 'Sun', scans: 11, vulns: 34, resolved: 29 }
    ],
    '30d': [
      { date: 'Week 1', scans: 89, vulns: 324, resolved: 298 },
      { date: 'Week 2', scans: 95, vulns: 356, resolved: 312 },
      { date: 'Week 3', scans: 78, vulns: 289, resolved: 267 },
      { date: 'Week 4', scans: 102, vulns: 378, resolved: 345 }
    ]
  };

  const data = trendData[timeRange];
  const maxValue = Math.max(...data.flatMap(d => [d.scans, d.vulns, d.resolved]));

  const LineChart = ({ data, color, label }) => {
    const points = data.map((item, index) => {
      const x = (index / (data.length - 1)) * 100;
      const y = 100 - (item / maxValue) * 100;
      return `${x},${y}`;
    }).join(' ');

    return (
      <div className="relative">
        <svg className="w-full h-32" viewBox="0 0 100 100" preserveAspectRatio="none">
          {/* Grid lines */}
          <defs>
            <pattern id={`grid-${label}`} x="0" y="0" width="20" height="25" patternUnits="userSpaceOnUse">
              <path d="M 20 0 L 0 0 0 25" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="0.5"/>
            </pattern>
          </defs>
          <rect width="100" height="100" fill={`url(#grid-${label})`} />
          
          {/* Area under curve */}
          <path
            d={`M 0,100 L ${points} L 100,100 Z`}
            fill={`url(#gradient-${label})`}
            opacity="0.3"
          />
          
          {/* Line */}
          <polyline
            points={points}
            fill="none"
            stroke={color}
            strokeWidth="2"
            vectorEffect="non-scaling-stroke"
          />
          
          {/* Gradient definition */}
          <defs>
            <linearGradient id={`gradient-${label}`} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor={color} stopOpacity="0.8"/>
              <stop offset="100%" stopColor={color} stopOpacity="0"/>
            </linearGradient>
          </defs>
        </svg>
      </div>
    );
  };

  const timeRanges = [
    { value: '7d', label: '7 days' },
    { value: '30d', label: '30 days' }
  ];

  return (
    <Card>
      <Card.Header>
        <Card.Title>Security Trends</Card.Title>
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-text-tertiary" />
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="bg-obsidian-850 border border-obsidian-700 rounded-lg px-3 py-1 text-sm text-text-primary focus:outline-none focus:border-platinum-500 transition-colors"
          >
            {timeRanges.map(range => (
              <option key={range.value} value={range.value}>
                {range.label}
              </option>
            ))}
          </select>
        </div>
      </Card.Header>
      
      <Card.Body>
        {/* Chart Legend */}
        <div className="flex items-center gap-6 mb-6">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-platinum-500 rounded-full" />
            <span className="text-sm text-text-secondary">Scans</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-rose-500 rounded-full" />
            <span className="text-sm text-text-secondary">Vulnerabilities</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-success rounded-full" />
            <span className="text-sm text-text-secondary">Resolved</span>
          </div>
        </div>

        {/* Chart Container */}
        <div className="relative mb-4">
          <div className="absolute inset-0">
            <LineChart 
              data={data.map(d => d.scans)} 
              color="#E5E7EB" 
              label="scans"
            />
          </div>
          <div className="absolute inset-0">
            <LineChart 
              data={data.map(d => d.vulns)} 
              color="#EF4444" 
              label="vulns"
            />
          </div>
          <div className="absolute inset-0">
            <LineChart 
              data={data.map(d => d.resolved)} 
              color="#10B981" 
              label="resolved"
            />
          </div>
        </div>

        {/* X-axis labels */}
        <div className="flex justify-between text-xs text-text-tertiary border-t border-obsidian-700 pt-2">
          {data.map((item, index) => (
            <span key={index}>{item.date}</span>
          ))}
        </div>
      </Card.Body>
      
      <Card.Footer>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-success" />
            <span className="text-sm text-success">Resolution rate up 23%</span>
          </div>
          <span className="text-xs text-text-tertiary">
            {timeRange === '7d' ? 'Last 7 days' : 'Last 30 days'}
          </span>
        </div>
      </Card.Footer>
    </Card>
  );
};

export default SecurityTrendChart;
