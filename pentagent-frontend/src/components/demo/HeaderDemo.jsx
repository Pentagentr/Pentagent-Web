import React, { useState } from 'react';
import Header from '../layout/Header';

export const HeaderDemo = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [notifications, setNotifications] = useState(3);

  const handleMenuClick = () => {
    alert('Menu clicked!');
  };

  const toggleAuth = () => {
    setIsAuthenticated(!isAuthenticated);
  };

  const toggleNotifications = () => {
    setNotifications(notifications > 0 ? 0 : 5);
  };

  return (
    <div className="space-y-6">
      <h3 className="text-xl font-semibold text-text-primary">Header Component</h3>
      
      <div className="space-y-8">
        {/* Controls */}
        <div className="flex gap-4 flex-wrap">
          <button 
            onClick={toggleAuth}
            className="px-4 py-2 bg-obsidian-800 border border-obsidian-700 rounded-lg text-text-primary hover:bg-obsidian-700 transition-smooth"
          >
            {isAuthenticated ? 'Logout' : 'Login'}
          </button>
          <button 
            onClick={toggleNotifications}
            className="px-4 py-2 bg-obsidian-800 border border-obsidian-700 rounded-lg text-text-primary hover:bg-obsidian-700 transition-smooth"
          >
            {notifications > 0 ? 'Clear Notifications' : 'Add Notifications'}
          </button>
        </div>

        {/* Header Demo */}
        <div className="border border-obsidian-700 rounded-lg overflow-hidden">
          <div className="bg-obsidian-800 px-4 py-2 border-b border-obsidian-700">
            <h4 className="text-sm font-medium text-text-secondary">
              Header Preview (Sticky positioning disabled for demo)
            </h4>
          </div>
          
          {/* Simulated Header */}
          <div className="relative">
            <Header 
              onMenuClick={handleMenuClick}
              isAuthenticated={isAuthenticated}
              notifications={notifications}
            />
            
            {/* Demo Content */}
            <div className="p-6 bg-obsidian-900">
              <h4 className="text-lg font-semibold text-text-primary mb-4">Demo Content</h4>
              <p className="text-text-secondary mb-4">
                This demonstrates how the header looks with content below it. 
                In a real application, the header would be sticky and stay at the top.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-obsidian-800 rounded-lg p-4">
                  <h5 className="text-sm font-medium text-text-primary mb-2">Feature 1</h5>
                  <p className="text-xs text-text-tertiary">Description of feature</p>
                </div>
                <div className="bg-obsidian-800 rounded-lg p-4">
                  <h5 className="text-sm font-medium text-text-primary mb-2">Feature 2</h5>
                  <p className="text-xs text-text-tertiary">Description of feature</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Header States */}
        <div>
          <h4 className="text-lg font-medium text-text-secondary mb-4">Header States</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="border border-obsidian-700 rounded-lg overflow-hidden">
              <div className="bg-obsidian-800 px-4 py-2 border-b border-obsidian-700">
                <h5 className="text-sm font-medium text-text-secondary">Guest State</h5>
              </div>
              <div className="p-4">
                <div className="h-16 bg-obsidian-950 border-b border-obsidian-700 flex items-center justify-between px-6">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-gradient-to-br from-amber-500 to-amber-600 rounded-lg" />
                    <span className="text-lg font-semibold text-text-primary tracking-tight">
                      PENTAGENT
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <button className="px-3 py-1 text-sm text-amber-500 hover:bg-obsidian-850 rounded-lg transition-smooth">
                      Sign In
                    </button>
                    <button className="px-3 py-1 text-sm bg-gradient-to-r from-amber-500 to-amber-600 text-obsidian-950 rounded-lg font-medium">
                      Get Started
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div className="border border-obsidian-700 rounded-lg overflow-hidden">
              <div className="bg-obsidian-800 px-4 py-2 border-b border-obsidian-700">
                <h5 className="text-sm font-medium text-text-secondary">Authenticated State</h5>
              </div>
              <div className="p-4">
                <div className="h-16 bg-obsidian-950 border-b border-obsidian-700 flex items-center justify-between px-6">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 bg-gradient-to-br from-amber-500 to-amber-600 rounded-lg" />
                    <span className="text-lg font-semibold text-text-primary tracking-tight">
                      PENTAGENT
                    </span>
                  </div>
                  <div className="hidden md:block flex-1 max-w-md mx-8">
                    <input 
                      type="text"
                      placeholder="Search..."
                      className="w-full h-9 px-4 bg-obsidian-900 border border-obsidian-700 rounded-lg text-sm text-text-primary placeholder:text-text-tertiary"
                    />
                  </div>
                  <div className="flex items-center gap-3">
                    <button className="relative p-2 text-text-secondary hover:text-text-primary transition-smooth">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
                        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
                      </svg>
                      <span className="absolute top-1 right-1 w-2 h-2 bg-coral-500 rounded-full" />
                    </button>
                    <button className="flex items-center gap-2 p-2 hover:bg-obsidian-850 rounded-lg transition-smooth">
                      <div className="w-8 h-8 bg-obsidian-800 rounded-full flex items-center justify-center">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                          <circle cx="12" cy="7" r="4" />
                        </svg>
                      </div>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
