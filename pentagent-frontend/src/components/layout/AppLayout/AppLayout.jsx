import React, { useState } from 'react';
import Header from '../Header';
import Sidebar from '../Sidebar';

const AppLayout = ({ children, activeItem }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <div className="min-h-screen bg-obsidian-950">
      <Header 
        onMenuClick={() => setSidebarOpen(!sidebarOpen)}
        isAuthenticated={true}
        notifications={3}
      />
      
      <Sidebar 
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        activeItem={activeItem}
      />
      
      <main 
        className={`
          pt-16 transition-all duration-300
          ${sidebarOpen ? 'ml-60' : 'ml-16'}
        `}
      >
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  );
};

export default AppLayout;
