import React from 'react';
import { 
  Shield, 
  Zap, 
  AlertTriangle, 
  TrendingUp,
  Clock,
  CheckCircle
} from 'lucide-react';
import {
  DashboardLayout,
  StatsCard,
  ActiveScansTable,
  VulnerabilityChart, 
  SecurityTrendChart,
  AIRecommendations
} from '../components/dashboard';
import Button from '../components/common/Button';

const Dashboard = () => {
  // Mock data - would come from API/context in real implementation
  const statsData = [
    {
      title: 'Active Scans',
      value: 12,
      subtitle: '3 completing soon',
      icon: Zap,
      trend: 'up',
      trendValue: '+25%',
      color: 'amber'
    },
    {
      title: 'Vulnerabilities Found',
      value: 247,
      subtitle: 'Last 7 days',
      icon: AlertTriangle,
      trend: 'down',
      trendValue: '-12%',
      color: 'red'
    },
    {
      title: 'Security Score',
      value: '8.4/10',
      subtitle: 'Excellent rating',
      icon: Shield,
      trend: 'up',
      trendValue: '+0.3',
      color: 'green'
    },
    {
      title: 'Resolution Rate',
      value: '94%',
      subtitle: 'This month',
      icon: CheckCircle,
      trend: 'up',
      trendValue: '+8%',
      color: 'blue'
    }
  ];

  const handleViewScan = (scanId) => {
    console.log('Viewing scan:', scanId);
    // Navigate to scan details
  };

  const handleControlScan = (scanId, action) => {
    console.log('Scan control:', scanId, action);
    // Handle scan control actions
  };

  const handleStartNewScan = () => {
    console.log('Starting new scan');
    // Navigate to chat interface or scan setup
  };

  return (
    <DashboardLayout>
      {/* Stats Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statsData.map((stat, index) => (
          <StatsCard
            key={index}
            title={stat.title}
            value={stat.value}
            subtitle={stat.subtitle}
            icon={stat.icon}
            trend={stat.trend}
            trendValue={stat.trendValue}
            color={stat.color}
            onClick={() => console.log(`Clicked ${stat.title}`)}
          />
        ))}
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column - Active Scans */}
        <div className="lg:col-span-2 space-y-8">
          <ActiveScansTable 
            onViewScan={handleViewScan}
            onControlScan={handleControlScan}
          />
          
          {/* Charts Row */}
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <VulnerabilityChart />
            <SecurityTrendChart />
          </div>
        </div>
        
        {/* Right Column - AI Recommendations */}
        <div className="lg:col-span-1">
          <AIRecommendations />
        </div>
      </div>

      {/* Quick Actions Bar */}
      <div className="bg-obsidian-900 border border-obsidian-700 rounded-xl p-6">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-br from-platinum-500 to-platinum-600 rounded-xl flex items-center justify-center">
              <Zap className="w-6 h-6 text-obsidian-950" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-text-primary">Ready to start scanning?</h3>
              <p className="text-text-secondary">Launch AI-powered security assessments with natural language commands.</p>
            </div>
          </div>
          
          <div className="flex gap-3">
            <Button variant="secondary" size="lg">
              <Clock className="w-4 h-4 mr-2" />
              Schedule Scan
            </Button>
            <Button variant="primary" size="lg" onClick={handleStartNewScan}>
              <Zap className="w-4 h-4 mr-2" />
              Start New Scan
            </Button>
          </div>
        </div>
      </div>

      {/* Recent Activity Summary */}
      <div className="bg-obsidian-900 border border-obsidian-700 rounded-xl p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-semibold text-text-primary">Recent Activity</h3>
          <Button variant="ghost" size="sm">View All →</Button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-platinum-500 mb-2">156</div>
            <div className="text-text-secondary">Scans completed</div>
            <div className="text-text-tertiary text-sm">This month</div>
          </div>
          
          <div className="text-center">
            <div className="text-3xl font-bold text-rose-500 mb-2">1,247</div>
            <div className="text-text-secondary">Vulnerabilities detected</div>
            <div className="text-text-tertiary text-sm">Across all targets</div>
          </div>
          
          <div className="text-center">
            <div className="text-3xl font-bold text-success mb-2">1,168</div>
            <div className="text-text-secondary">Issues resolved</div>
            <div className="text-text-tertiary text-sm">94% resolution rate</div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Dashboard;
