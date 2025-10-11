import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Bell, User, Menu, Database, MessageSquare } from 'lucide-react';
import Button from '../../common/Button';

const Header = ({ 
  onMenuClick,
  isAuthenticated = false,
  notifications = 0 
}) => {
  const location = useLocation();
  
  const navLinks = [
    { path: '/', label: 'Pentest Chat', icon: MessageSquare },
    { path: '/rag-search', label: 'CVE Search', icon: Database }
  ];
  
  return (
    <header className="sticky top-0 z-50 w-full h-16 bg-obsidian-950/80 backdrop-blur-lg border-b border-obsidian-700">
      <div className="h-full px-6 flex items-center justify-between">
        {/* Left: Logo */}
        <div className="flex items-center gap-6">
          <button 
            onClick={onMenuClick}
            className="lg:hidden p-2 text-text-secondary hover:text-text-primary transition-smooth"
          >
            <Menu size={20} />
          </button>
          
          <Link to="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-platinum-500 to-platinum-600 rounded-lg" />
            <span className="text-lg font-semibold text-text-primary tracking-tight">
              PENTAGENT
            </span>
          </Link>
          
          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-2">
            {navLinks.map((link) => {
              const Icon = link.icon;
              const isActive = location.pathname === link.path;
              return (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                    isActive
                      ? 'bg-platinum-500/10 text-platinum-400 border border-platinum-500/30'
                      : 'text-text-secondary hover:text-text-primary hover:bg-obsidian-850'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>
        
        {/* Center: CVE Search Button */}
        <div className="flex-1 flex justify-center">
          <Link
            to="/rag-search"
            className="flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-white font-semibold rounded-lg shadow-lg hover:shadow-xl transition-all transform hover:scale-105"
          >
            <Database className="w-5 h-5" />
            <span>CVE Ara</span>
          </Link>
        </div>
        
        {/* Right: Actions */}
        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <>
              <button className="relative p-2 text-text-secondary hover:text-text-primary transition-smooth">
                <Bell size={20} />
                {notifications > 0 && (
                  <span className="absolute top-1 right-1 w-2 h-2 bg-rose-500 rounded-full" />
                )}
              </button>
              
              <button className="flex items-center gap-2 p-2 hover:bg-obsidian-850 rounded-lg transition-smooth">
                <div className="w-8 h-8 bg-obsidian-800 rounded-full flex items-center justify-center">
                  <User size={16} className="text-text-secondary" />
                </div>
              </button>
            </>
          ) : (
            <>
              <Button variant="ghost" size="sm">Sign In</Button>
              <Button variant="primary" size="sm">Get Started</Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
