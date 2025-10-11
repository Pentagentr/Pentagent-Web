import React from 'react';
import { 
  Home, 
  MessageSquare, 
  Search, 
  FileText, 
  Shield,
  Settings,
  BookOpen,
  HelpCircle,
  ChevronLeft
} from 'lucide-react';

const menuItems = [
  { icon: Home, label: 'Dashboard', path: '/dashboard' },
  { icon: MessageSquare, label: 'Chat', path: '/chat', badge: 3 },
  { icon: Search, label: 'Scans', path: '/scans' },
  { icon: FileText, label: 'Reports', path: '/reports' },
  { icon: Shield, label: 'Vulnerabilities', path: '/vulnerabilities' },
];

const bottomItems = [
  { icon: Settings, label: 'Settings', path: '/settings' },
  { icon: BookOpen, label: 'Docs', path: '/docs' },
  { icon: HelpCircle, label: 'Help', path: '/help' },
];

const Sidebar = ({ isOpen = true, onToggle, activeItem = '/dashboard' }) => {
  return (
    <aside 
      className={`
        fixed left-0 top-16 h-[calc(100vh-4rem)] 
        bg-obsidian-900 border-r border-obsidian-700
        transition-all duration-300 z-40
        ${isOpen ? 'w-60' : 'w-16'}
      `}
    >
      <div className="flex flex-col h-full">
        {/* Toggle Button */}
        <button
          onClick={onToggle}
          className="absolute -right-3 top-6 w-6 h-6 bg-obsidian-800 border border-obsidian-700 rounded-full flex items-center justify-center text-text-tertiary hover:text-text-primary hover:border-platinum-500 transition-smooth"
        >
          <ChevronLeft 
            size={14} 
            className={`transition-transform ${!isOpen ? 'rotate-180' : ''}`}
          />
        </button>
        
        {/* Main Menu */}
        <nav className="flex-1 px-3 py-6 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeItem === item.path;
            
            return (
              <a
                key={item.path}
                href={item.path}
                className={`
                  group relative flex items-center h-10 px-3 rounded-lg transition-smooth
                  ${isActive 
                    ? 'bg-obsidian-850 text-text-primary border-l-3 border-platinum-500' 
                    : 'text-text-secondary hover:bg-obsidian-850 hover:text-text-primary'
                  }
                `}
              >
                <Icon size={18} className="flex-shrink-0" />
                
                {isOpen && (
                  <>
                    <span className="ml-3 font-medium">{item.label}</span>
                    {item.badge && (
                      <span className="ml-auto px-1.5 py-0.5 text-xs bg-rose-500 text-white rounded-full">
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
                
                {/* Tooltip for collapsed state */}
                {!isOpen && (
                  <div className="absolute left-14 px-2 py-1 bg-obsidian-800 border border-obsidian-700 rounded text-sm text-text-primary opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
                    {item.label}
                  </div>
                )}
              </a>
            );
          })}
        </nav>
        
        {/* Bottom Menu */}
        <div className="px-3 py-4 border-t border-obsidian-700 space-y-1">
          {bottomItems.map((item) => {
            const Icon = item.icon;
            
            return (
              <a
                key={item.path}
                href={item.path}
                className="group relative flex items-center h-10 px-3 rounded-lg text-text-secondary hover:bg-obsidian-850 hover:text-text-primary transition-smooth"
              >
                <Icon size={18} className="flex-shrink-0" />
                
                {isOpen && (
                  <span className="ml-3 font-medium">{item.label}</span>
                )}
                
                {!isOpen && (
                  <div className="absolute left-14 px-2 py-1 bg-obsidian-800 border border-obsidian-700 rounded text-sm text-text-primary opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
                    {item.label}
                  </div>
                )}
              </a>
            );
          })}
        </div>
        
        {/* User Section */}
        {isOpen && (
          <div className="p-4 border-t border-obsidian-700">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-obsidian-800 rounded-full flex items-center justify-center">
                <span className="text-sm font-medium text-text-primary">JD</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">John Doe</p>
                <p className="text-xs text-text-tertiary">Pro Plan</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
};

export default Sidebar;
