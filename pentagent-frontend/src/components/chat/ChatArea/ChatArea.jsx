import React, { useState, useRef, useEffect } from 'react';
import { Brain, User, Copy, ThumbsUp, ThumbsDown, RotateCcw } from 'lucide-react';
import MessageBubble from '../MessageBubble';
import ToolExecutionCard from '../ToolExecutionCard';
import ThinkingAnimation from '../ThinkingAnimation';

const ChatArea = ({ conversationId, isTyping, messages = [], currentScan }) => {
  const messagesEndRef = useRef(null);
  const listRef = useRef(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [showNewMsgHint, setShowNewMsgHint] = useState(false);
  
  // Props'tan gelen messages'i kullan
  const displayMessages = messages.length > 0 ? messages : [
    {
      id: 'welcome',
      type: 'system',
      content: 'Welcome to Pentagent! Start by describing what you want to test.'
    }
  ];

  // Scroll behavior: only autoscroll if user near bottom
  useEffect(() => {
    if (!listRef.current) return;
    const el = listRef.current;
    const threshold = 120; // px from bottom
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < threshold;
    if (nearBottom || autoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      setShowNewMsgHint(false);
    } else {
      setShowNewMsgHint(true);
    }
  }, [messages, isTyping]);

  const handleScroll = () => {
    if (!listRef.current) return;
    const el = listRef.current;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 4;
    setAutoScroll(atBottom);
    if (atBottom) setShowNewMsgHint(false);
  };

  const SystemMessage = ({ children }) => (
    <div className="flex justify-center my-4">
      <div className="px-4 py-2 bg-obsidian-850 border border-obsidian-700 rounded-full">
        <span className="text-xs text-text-tertiary">{children}</span>
      </div>
    </div>
  );

  return (
    <div ref={listRef} onScroll={handleScroll} className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-3 py-4 space-y-4">
        
        {/* Welcome Message - show when no messages */}
        {displayMessages.length === 0 && (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-gradient-to-br from-platinum-500 to-platinum-600 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Brain className="w-8 h-8 text-obsidian-950" />
            </div>
            <h2 className="text-xl font-bold text-text-primary mb-3">
              Ready for Security Testing
            </h2>
            <p className="text-text-secondary text-sm mb-6 max-w-xl mx-auto">
              AI güvenlik uzmanınız. Test etmek istediğinizi doğal dilde açıklayın.
            </p>
            <div className="flex flex-wrap gap-2 justify-center">
              <div className="px-3 py-1 bg-obsidian-850 border border-obsidian-700 rounded-lg text-xs text-text-tertiary">
                💡 "renicames.com için güvenlik testi yap"
              </div>
              <div className="px-3 py-1 bg-obsidian-850 border border-obsidian-700 rounded-lg text-xs text-text-tertiary">
                🔍 "SQL injection ve XSS testi"
              </div>
            </div>
          </div>
        )}

        {/* Messages */}
        {displayMessages.map((message, idx) => {
          switch (message.type) {
            case 'user':
              return (
                <MessageBubble
                  key={message.id}
                  type="user"
                  content={message.content}
                  timestamp={message.timestamp}
                  avatar={message.avatar}
                  className="animate-slideUp stagger-1"
                />
              );
              
            case 'ai':
              return (
                <MessageBubble
                  key={message.id}
                  type="ai"
                  content={message.content}
                  timestamp={message.timestamp}
                  thinking={message.thinking}
                  className="animate-fadeIn"
                />
              );
              
            case 'ai_thinking':
              return (
                <div key={message.id} className="flex items-start gap-3 animate-fadeIn">
                  <div className="w-8 h-8 bg-gradient-to-br from-platinum-500 to-platinum-600 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Brain className="w-4 h-4 text-obsidian-950 animate-pulse" />
                  </div>
                  <div className="flex-1">
                    <div className="bg-obsidian-850 border border-platinum-500/30 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-1.5 h-1.5 bg-platinum-500 rounded-full animate-pulse" />
                        <span className="text-xs text-platinum-400 font-medium">AI Düşünüyor</span>
                        <span className="text-xs text-text-tertiary">{message.timestamp}</span>
                      </div>
                      <p className="text-text-primary text-xs">{message.content}</p>
                    </div>
                  </div>
                </div>
              );
              
            case 'ai_reasoning':
              return (
                <div key={message.id} className="flex items-start gap-3 animate-fadeIn">
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
                    <Brain className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <div className="bg-obsidian-850 border border-blue-500/30 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                        <span className="text-xs text-blue-400 font-medium">
                          {message.content.includes('AI Analizi:') ? '📊 Tool Sonuçları' : 'AI Analizi'}
                        </span>
                        <span className="text-xs text-text-tertiary">{message.timestamp}</span>
                      </div>
                      <p className="text-text-primary text-xs whitespace-pre-wrap leading-relaxed">{message.content}</p>
                    </div>
                  </div>
                </div>
              );
              
            case 'tool':
              return (
                <ToolExecutionCard
                  key={message.id}
                  toolName={message.toolName}
                  status={message.status}
                  progress={message.progress}
                  duration={message.duration}
                  results={message.results}
                  timestamp={message.timestamp}
                />
              );
              
            case 'system':
              return (
                <SystemMessage key={message.id}>
                  {message.content}
                </SystemMessage>
              );
              
            default:
              return null;
          }
        })}

        {/* Typing Indicator */}
        {isTyping && (
          <div className="flex items-start gap-4 animate-fadeIn">
            <div className="w-10 h-10 bg-gradient-to-br from-platinum-500 to-platinum-600 rounded-xl flex items-center justify-center flex-shrink-0">
              <Brain className="w-5 h-5 text-obsidian-950" />
            </div>
            <div className="flex-1">
              <ThinkingAnimation />
            </div>
          </div>
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
        {showNewMsgHint && (
          <div className="sticky bottom-4 w-full flex justify-end pr-6">
            <button
              onClick={() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); setAutoScroll(true); setShowNewMsgHint(false); }}
              className="px-3 py-2 bg-obsidian-850/90 border border-obsidian-700 rounded-full text-xs text-text-secondary hover:text-text-primary hover:border-platinum-500/40 transition-all shadow-lg"
            >
              Yeni mesajlar ↓
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatArea;
