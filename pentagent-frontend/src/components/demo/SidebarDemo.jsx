import React, { useState } from 'react';
import Sidebar from '../layout/Sidebar';
import Header from '../layout/Header';

export const SidebarDemo = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [activeItem, setActiveItem] = useState('/dashboard');

  const handleSidebarToggle = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  const handleMenuClick = () => {
    alert('Mobile menu clicked!');
  };

  return (
    <div className="space-y-6">
      <h3 className="text-xl font-semibold text-text-primary">Sidebar Navigation</h3>
      
      <div className="space-y-8">
        {/* Controls */}
        <div className="flex gap-4 flex-wrap">
          <button 
            onClick={handleSidebarToggle}
            className="px-4 py-2 bg-obsidian-800 border border-obsidian-700 rounded-lg text-text-primary hover:bg-obsidian-700 transition-smooth"
          >
            {isSidebarOpen ? 'Collapse Sidebar' : 'Expand Sidebar'}
          </button>
          <button 
            onClick={() => setActiveItem('/chat')}
            className="px-4 py-2 bg-obsidian-800 border border-obsidian-700 rounded-lg text-text-primary hover:bg-obsidian-700 transition-smooth"
          >
            Set Active: Chat
          </button>
          <button 
            onClick={() => setActiveItem('/scans')}
            className="px-4 py-2 bg-obsidian-800 border border-obsidian-700 rounded-lg text-text-primary hover:bg-obsidian-700 transition-smooth"
          >
            Set Active: Scans
          </button>
        </div>

        {/* Layout Demo */}
        <div className="border border-obsidian-700 rounded-lg overflow-hidden">
          <div className="bg-obsidian-800 px-4 py-2 border-b border-obsidian-700">
            <h4 className="text-sm font-medium text-text-secondary">
              Layout Preview (Header + Sidebar + Content)
            </h4>
          </div>
          
          {/* Simulated Layout */}
          <div className="relative h-96 bg-obsidian-950">
            {/* Header */}
            <Header 
              onMenuClick={handleMenuClick}
              isAuthenticated={true}
              notifications={3}
            />
            
            {/* Sidebar */}
            <Sidebar 
              isOpen={isSidebarOpen}
              onToggle={handleSidebarToggle}
              activeItem={activeItem}
            />
            
            {/* Main Content */}
            <main 
              className={`
                pt-16 transition-all duration-300
                ${isSidebarOpen ? 'pl-60' : 'pl-16'}
              `}
            >
              <div className="p-6">
                <h4 className="text-lg font-semibold text-text-primary mb-4">
                  Main Content Area
                </h4>
                <p className="text-text-secondary mb-4">
                  This demonstrates how the sidebar affects the main content layout. 
                  The content area adjusts its padding based on sidebar state.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="bg-obsidian-800 rounded-lg p-4">
                    <h5 className="text-sm font-medium text-text-primary mb-2">Content Block 1</h5>
                    <p className="text-xs text-text-tertiary">Sidebar is {isSidebarOpen ? 'expanded' : 'collapsed'}</p>
                  </div>
                  <div className="bg-obsidian-800 rounded-lg p-4">
                    <h5 className="text-sm font-medium text-text-primary mb-2">Content Block 2</h5>
                    <p className="text-xs text-text-tertiary">Active item: {activeItem}</p>
                  </div>
                </div>
              </div>
            </main>
          </div>
        </div>

        {/* Sidebar States */}
        <div>
          <h4 className="text-lg font-medium text-text-secondary mb-4">Sidebar States</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="border border-obsidian-700 rounded-lg overflow-hidden">
              <div className="bg-obsidian-800 px-4 py-2 border-b border-obsidian-700">
                <h5 className="text-sm font-medium text-text-secondary">Expanded State</h5>
              </div>
              <div className="p-4">
                <div className="relative h-64 bg-obsidian-900 border border-obsidian-700 rounded">
                  <div className="absolute left-0 top-0 w-60 h-full bg-obsidian-900 border-r border-obsidian-700">
                    <div className="p-3 space-y-1">
                      <div className="flex items-center h-10 px-3 bg-obsidian-850 text-text-primary rounded-lg">
                        <div className="w-4 h-4 bg-amber-500 rounded mr-3"></div>
                        <span className="text-sm font-medium">Dashboard</span>
                      </div>
                      <div className="flex items-center h-10 px-3 text-text-secondary rounded-lg">
                        <div className="w-4 h-4 bg-text-tertiary rounded mr-3"></div>
                        <span className="text-sm">Chat</span>
                        <span className="ml-auto px-1.5 py-0.5 text-xs bg-coral-500 text-white rounded-full">3</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="border border-obsidian-700 rounded-lg overflow-hidden">
              <div className="bg-obsidian-800 px-4 py-2 border-b border-obsidian-700">
                <h5 className="text-sm font-medium text-text-secondary">Collapsed State</h5>
              </div>
              <div className="p-4">
                <div className="relative h-64 bg-obsidian-900 border border-obsidian-700 rounded">
                  <div className="absolute left-0 top-0 w-16 h-full bg-obsidian-900 border-r border-obsidian-700">
                    <div className="p-3 space-y-1">
                      <div className="flex items-center justify-center h-10 bg-obsidian-850 text-text-primary rounded-lg">
                        <div className="w-4 h-4 bg-amber-500 rounded"></div>
                      </div>
                      <div className="flex items-center justify-center h-10 text-text-secondary rounded-lg">
                        <div className="w-4 h-4 bg-text-tertiary rounded"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Features */}
        <div>
          <h4 className="text-lg font-medium text-text-secondary mb-4">Sidebar Features</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-obsidian-800 rounded-lg p-4">
              <h5 className="text-sm font-medium text-text-primary mb-2">Toggle Animation</h5>
              <p className="text-xs text-text-tertiary">Smooth expand/collapse with 300ms transition</p>
            </div>
            <div className="bg-obsidian-800 rounded-lg p-4">
              <h5 className="text-sm font-medium text-text-primary mb-2">Tooltips</h5>
              <p className="text-xs text-text-tertiary">Hover tooltips when collapsed</p>
            </div>
            <div className="bg-obsidian-800 rounded-lg p-4">
              <h5 className="text-sm font-medium text-text-primary mb-2">Badge Support</h5>
              <p className="text-xs text-text-tertiary">Notification badges on menu items</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
