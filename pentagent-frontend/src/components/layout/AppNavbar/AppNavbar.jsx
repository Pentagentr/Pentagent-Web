/**
 * Uygulama geneli sabit navbar
 * Tüm sayfalarda görünür
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { MessageSquare, Database, Shield } from 'lucide-react';

const AppNavbar = () => {
  const location = useLocation();
  
  const navItems = [
    { path: '/', label: 'Pentest', icon: MessageSquare },
    { path: '/rag-search', label: 'CVE Database', icon: Database }
  ];
  
  return (
    <nav className="w-full bg-obsidian-900 border-b border-obsidian-700 flex-shrink-0">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-platinum-500" />
          <span className="text-base font-semibold text-text-primary tracking-tight">
            PENTAGENT
          </span>
        </Link>
        
        {/* Navigation */}
        <div className="flex items-center gap-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-platinum-500/10 text-platinum-400 border border-platinum-500/30'
                    : 'text-text-secondary hover:text-text-primary hover:bg-obsidian-850'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
};

export default AppNavbar;

