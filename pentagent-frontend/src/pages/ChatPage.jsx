import React from 'react';
import AppNavbar from '../components/layout/AppNavbar';
import ChatInterface from '../components/chat/ChatInterface';

const ChatPage = () => {
  return (
    <div className="h-screen bg-obsidian-950 flex flex-col">
      {/* Navbar */}
      <AppNavbar />
      
      {/* Chat Interface */}
      <div className="flex-1 pt-14">
        <ChatInterface />
      </div>
    </div>
  );
};

export default ChatPage;
