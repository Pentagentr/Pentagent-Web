import React, { useState } from 'react';
import AppNavbar from '../components/layout/AppNavbar';
import ChatInterface from '../components/chat/ChatInterface';
import ChatSidebar from '../components/chat/ChatSidebar';

const ChatPage = () => {
  const [currentConversationId, setCurrentConversationId] = useState(null);

  const handleConversationSelect = (convId) => {
    setCurrentConversationId(convId);
  };

  const handleNewChat = (newConvId) => {
    setCurrentConversationId(newConvId);
  };

  const handleScanSelect = (scan) => {
    // Tarama seçildiğinde reports sayfasına yönlendir
    window.location.href = `/reports?scanId=${scan.id}`;
  };

  return (
    <div className="h-screen bg-obsidian-950 flex flex-col overflow-hidden">
      {/* Navbar - Sabit */}
      <AppNavbar />
      
      {/* Main Content - Sidebar + Chat */}
      <div className="flex-1 overflow-hidden flex">
        {/* Chat Sidebar - Sol */}
        <ChatSidebar 
          currentConversationId={currentConversationId}
          onConversationSelect={handleConversationSelect}
          onNewChat={handleNewChat}
          onScanSelect={handleScanSelect}
        />
        
        {/* Chat Interface - Sağ */}
        <div className="flex-1 overflow-hidden">
          <ChatInterface conversationId={currentConversationId} />
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
