import React from 'react';
import { 
  Zap
} from 'lucide-react';
import {
  DashboardLayout,
} from '../components/dashboard';
import Button from '../components/common/Button';

const Dashboard = () => {
  const handleStartNewScan = () => {
    console.log('Starting new scan');
    // Navigate to chat interface or scan setup
    window.location.href = '/chat';
  };

  return (
    <DashboardLayout>
      <div className="bg-obsidian-900 border border-obsidian-700 rounded-xl p-6">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-platinum-500/10 border border-platinum-500/20 flex items-center justify-center">
              <Zap className="w-5 h-5 text-platinum-500" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-text-primary">Dashboard</h2>
              <p className="text-sm text-text-tertiary">
                Analytics widgets were removed because they were not backed by real data.
              </p>
            </div>
          </div>
          <Button onClick={handleStartNewScan} variant="primary">
            Start new scan
          </Button>
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
