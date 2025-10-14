/**
 * Uygulama geneli sabit navbar
 * Tüm sayfalarda görünür
 */

import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { MessageSquare, Database, Shield, User, LogOut, ChevronDown } from 'lucide-react';
import { useAuth } from '../../../contexts/AuthContext';

const AppNavbar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { currentUser, userProfile, logout } = useAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);
  
  const navItems = [
    { path: '/chat', label: 'Pentest', icon: MessageSquare },
    { path: '/rag-search', label: 'CVE Database', icon: Database }
  ];
  
  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  return (
    <nav className="w-full bg-obsidian-900/90 backdrop-blur-md border-b border-platinum-500/10 flex-shrink-0 shadow-lg">
      <div className="max-w-7xl mx-auto px-4 h-11 flex items-center justify-between">
        {/* Logo - Sol */}
        <Link to={currentUser ? "/chat" : "/"} className="flex items-center gap-2 group flex-shrink-0">
          <Shield className="w-4 h-4 text-platinum-500 group-hover:text-purple-400 transition-colors duration-300" />
          <span className="text-sm font-bold bg-gradient-to-r from-platinum-400 to-purple-400 bg-clip-text text-transparent">
            PENTAGENT
          </span>
        </Link>
        
        {/* Nav Items - Orta */}
        <div className="absolute left-1/2 transform -translate-x-1/2 flex items-center gap-6">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`nav-item-underline flex items-center gap-1.5 py-1.5 text-xs font-medium transition-all duration-300 ${
                  isActive
                    ? 'text-platinum-400 active'
                    : 'text-platinum-600 hover:text-platinum-400'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>

        {/* User Menu - Sağ */}
        <div className="flex items-center">
          <div className="relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-xs font-medium text-platinum-600 hover:text-platinum-400 hover:bg-obsidian-850 transition-all duration-300"
            >
              <div className="w-6 h-6 rounded-full bg-purple-500/15 border border-purple-500/30 flex items-center justify-center">
                <User className="w-3.5 h-3.5 text-purple-400" />
              </div>
              <span className="max-w-[100px] truncate">
                {userProfile?.displayName || currentUser?.email?.split('@')[0] || 'User'}
              </span>
              <ChevronDown className={`w-3 h-3 transition-transform duration-300 ${showUserMenu ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown Menu */}
            {showUserMenu && (
              <div className="absolute right-0 mt-2 w-48 bg-obsidian-900/95 backdrop-blur-md border border-platinum-500/20 rounded-lg shadow-2xl z-50 overflow-hidden">
                <div className="p-3 border-b border-platinum-500/10 bg-obsidian-850/50">
                  <p className="text-xs font-medium text-platinum truncate">
                    {userProfile?.displayName || 'User'}
                  </p>
                  <p className="text-[10px] text-platinum-tertiary truncate mt-0.5">
                    {currentUser?.email}
                  </p>
                </div>
                <div className="p-1.5">
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2 px-2.5 py-2 rounded-lg text-xs text-rose-400 hover:bg-rose-500/10 hover:text-rose-300 transition-all duration-300"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Logout</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Click outside to close menu */}
      {showUserMenu && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowUserMenu(false)}
        />
      )}
    </nav>
  );
};

export default AppNavbar;

