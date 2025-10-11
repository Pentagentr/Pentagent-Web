import React from 'react';
import { AppLayout } from '../../layout';

const DashboardLayout = ({ children }) => {
  return (
    <AppLayout activeItem="/dashboard">
      <div className="space-y-8">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-text-primary mb-2">Security Dashboard</h1>
            <p className="text-text-secondary">
              Real-time security monitoring and AI-powered insights
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 px-3 py-2 bg-obsidian-900 border border-obsidian-700 rounded-lg">
              <div className="w-2 h-2 bg-success rounded-full animate-pulse" />
              <span className="text-sm text-text-secondary">All systems operational</span>
            </div>
          </div>
        </div>
        
        {children}
      </div>
    </AppLayout>
  );
};

export default DashboardLayout;
