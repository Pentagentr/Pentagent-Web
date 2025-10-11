import React from 'react';
import { Link } from 'react-router-dom';
import { Database } from 'lucide-react';
import ChatInterface from '../components/chat/ChatInterface';

const ChatPage = () => {
  return (
    <div className="h-screen bg-obsidian-950 flex flex-col">
      {/* CVE Ara Butonu - Sabit üstte */}
      <div className="absolute top-4 right-4 z-50">
        <Link
          to="/rag-search"
          className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white font-semibold rounded-lg shadow-lg hover:shadow-emerald-500/50 transition-all transform hover:scale-105 animate-pulse hover:animate-none"
        >
          <Database className="w-5 h-5" />
          <span>CVE Ara</span>
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
