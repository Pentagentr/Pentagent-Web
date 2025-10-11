import React from 'react';
import AppNavbar from '../components/layout/AppNavbar';
import ChatInterface from '../components/chat/ChatInterface';

const ChatPage = () => {
  return (
    <div className="h-screen bg-obsidian-950 flex flex-col overflow-hidden">
      {/* Navbar - Sabit */}
      <AppNavbar />
      
      {/* Chat Interface - Kalan alan */}
      <div className="flex-1 overflow-hidden">
        <ChatInterface />
      </div>
    </div>
  );
};

export default ChatPage;
