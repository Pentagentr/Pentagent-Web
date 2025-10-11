import React, { useState } from 'react';
import { 
  Plus, 
  Search, 
  MoreHorizontal, 
  Trash2, 
  Edit3, 
  Archive,
  Clock,
  Shield,
  AlertTriangle,
  CheckCircle,
  Zap
} from 'lucide-react';
import Button from '../../common/Button';

const ConversationSidebar = ({ 
  isOpen, 
  conversations, 
  activeConversation, 
  onSelectConversation,
  onToggle 
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [showDropdown, setShowDropdown] = useState(null);

  const filteredConversations = conversations.filter(conv => 
    conv.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const groupedConversations = {
    today: filteredConversations.filter(conv => conv.timestamp.includes('min ago') || conv.timestamp.includes('hour ago')),
    yesterday: filteredConversations.filter(conv => conv.timestamp === 'Yesterday'),
    thisWeek: filteredConversations.filter(conv => conv.timestamp.includes('day ago')),
    older: filteredConversations.filter(conv => conv.timestamp.includes('week ago') || conv.timestamp.includes('month ago'))
  };

  const getStatusIcon = (status, progress) => {
    switch (status) {
      case 'active':
        return <Zap className="w-4 h-4 text-platinum-500 animate-pulse" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-success" />;
      case 'error':
        return <AlertTriangle className="w-4 h-4 text-rose-500" />;
      default:
        return <Clock className="w-4 h-4 text-text-tertiary" />;
    }
  };

  const getVulnerabilityColor = (count) => {
    if (count >= 10) return 'text-rose-500';
    if (count >= 5) return 'text-warning';
    if (count > 0) return 'text-warning';
    return 'text-success';
  };

  const ConversationItem = ({ conversation }) => {
    const isActive = activeConversation === conversation.id;
    
    return (
      <div 
        className={`
          group relative p-3 rounded-lg cursor-pointer transition-all duration-200
          ${isActive 
            ? 'bg-platinum-500/10 border-l-3 border-platinum-500' 
            : 'hover:bg-obsidian-850 border-l-3 border-transparent'
          }
        `}
        onClick={() => onSelectConversation(conversation.id)}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              {getStatusIcon(conversation.status)}
              <h3 className={`font-medium truncate ${isActive ? 'text-text-primary' : 'text-text-secondary'}`}>
                {conversation.title}
              </h3>
            </div>
            
            <p className="text-sm text-text-tertiary truncate mb-2">
              {conversation.lastMessage}
            </p>
            
            <div className="flex items-center justify-between text-xs">
              <span className="text-text-tertiary">{conversation.timestamp}</span>
              
              {conversation.vulnerabilities !== undefined && (
                <div className="flex items-center gap-1">
                  <Shield className="w-3 h-3" />
                  <span className={getVulnerabilityColor(conversation.vulnerabilities)}>
                    {conversation.vulnerabilities} vulns
                  </span>
                </div>
              )}
              
              {conversation.progress !== undefined && (
                <div className="flex items-center gap-2">
                  <div className="w-12 h-1 bg-obsidian-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-platinum-500 to-platinum-600 transition-all duration-300"
                      style={{ width: `${conversation.progress}%` }}
                    />
                  </div>
                  <span className="text-platinum-500">{conversation.progress}%</span>
                </div>
              )}
            </div>
          </div>
          
          {/* Options Menu */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowDropdown(showDropdown === conversation.id ? null : conversation.id);
            }}
            className="opacity-0 group-hover:opacity-100 p-1 text-text-tertiary hover:text-text-secondary transition-all ml-2"
          >
            <MoreHorizontal className="w-4 h-4" />
          </button>
          
          {/* Dropdown Menu */}
          {showDropdown === conversation.id && (
            <div className="absolute right-2 top-8 bg-obsidian-900 border border-obsidian-700 rounded-lg shadow-xl z-10 py-1 min-w-[120px]">
              <button className="w-full px-3 py-2 text-left text-sm text-text-secondary hover:bg-obsidian-850 hover:text-text-primary flex items-center gap-2">
                <Edit3 className="w-3 h-3" />
                Rename
              </button>
              <button className="w-full px-3 py-2 text-left text-sm text-text-secondary hover:bg-obsidian-850 hover:text-text-primary flex items-center gap-2">
                <Archive className="w-3 h-3" />
                Archive
              </button>
              <button className="w-full px-3 py-2 text-left text-sm text-rose-400 hover:bg-rose-500/10 flex items-center gap-2">
                <Trash2 className="w-3 h-3" />
                Delete
              </button>
            </div>
          )}
        </div>
      </div>
    );
  };

  const ConversationGroup = ({ title, conversations }) => {
    if (conversations.length === 0) return null;
    
    return (
      <div className="mb-6">
        <h4 className="text-xs font-medium text-text-tertiary uppercase tracking-wider mb-2 px-3">
          {title}
        </h4>
        <div className="space-y-1">
          {conversations.map(conv => (
            <ConversationItem key={conv.id} conversation={conv} />
          ))}
        </div>
      </div>
    );
  };

  if (!isOpen) {
    return (
      <div className="w-16 bg-obsidian-900 border-r border-obsidian-700 p-3">
        <button
          onClick={() => {/* New conversation */}}
          className="w-10 h-10 bg-platinum-500 hover:bg-platinum-600 rounded-lg flex items-center justify-center text-obsidian-950 transition-colors mb-4"
        >
          <Plus className="w-5 h-5" />
        </button>
        
        <div className="space-y-2">
          {conversations.slice(0, 4).map((conv) => (
            <button
              key={conv.id}
              onClick={() => onSelectConversation(conv.id)}
              className={`
                w-10 h-10 rounded-lg border-2 transition-all flex items-center justify-center
                ${activeConversation === conv.id
                  ? 'border-platinum-500 bg-platinum-500/10'
                  : 'border-obsidian-700 hover:border-obsidian-600'
                }
              `}
            >
              {getStatusIcon(conv.status)}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="w-80 bg-obsidian-900 border-r border-obsidian-700 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-obsidian-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text-primary">Conversations</h2>
          <button
            onClick={() => {/* New conversation */}}
            className="w-8 h-8 bg-platinum-500 hover:bg-platinum-600 rounded-lg flex items-center justify-center text-obsidian-950 transition-colors"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>
        
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-tertiary" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full h-9 pl-10 pr-4 bg-obsidian-850 border border-obsidian-700 rounded-lg text-sm text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-platinum-500 focus:ring-1 focus:ring-platinum-500/20 transition-all"
          />
        </div>
      </div>

      {/* Conversations List */}
      <div className="flex-1 overflow-y-auto p-4">
        <ConversationGroup title="Today" conversations={groupedConversations.today} />
        <ConversationGroup title="Yesterday" conversations={groupedConversations.yesterday} />
        <ConversationGroup title="This Week" conversations={groupedConversations.thisWeek} />
        <ConversationGroup title="Older" conversations={groupedConversations.older} />
        
        {filteredConversations.length === 0 && (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-obsidian-850 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Shield className="w-8 h-8 text-text-tertiary" />
            </div>
            <h3 className="text-text-primary font-medium mb-2">No conversations found</h3>
            <p className="text-text-tertiary text-sm mb-4">
              {searchTerm ? 'Try adjusting your search terms' : 'Start your first security assessment'}
            </p>
            <Button variant="primary" size="sm">
              New Scan
            </Button>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-obsidian-700">
        <div className="flex items-center gap-3 text-xs text-text-tertiary">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-success rounded-full animate-pulse" />
            <span>AI Online</span>
          </div>
          <span>•</span>
          <span>32 scans today</span>
        </div>
      </div>
    </div>
  );
};

export default ConversationSidebar;
