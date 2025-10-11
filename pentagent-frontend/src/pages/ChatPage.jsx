import React from 'react';
import { Link } from 'react-router-dom';
import { Database } from 'lucide-react';
import ChatInterface from '../components/chat/ChatInterface';

const ChatPage = () => {
  return (
    <div className="h-screen bg-obsidian-950 flex flex-col">
      {/* CVE Database - Profesyonel buton */}
      <div className="absolute top-4 right-6 z-50">
        <Link
          to="/rag-search"
          className="flex items-center gap-2 px-4 py-2 bg-obsidian-900/90 backdrop-blur-sm border border-obsidian-700 hover:border-platinum-500/50 text-text-secondary hover:text-platinum-400 rounded-lg transition-all text-sm font-medium"
        >
          <Database className="w-4 h-4" />
          <span>CVE Database</span>
        </Link>
      </div>
      
      {/* Chat Interface */}
      <div className="flex-1">
        <ChatInterface />
      </div>
    </div>
  );
};

export default ChatPage;
