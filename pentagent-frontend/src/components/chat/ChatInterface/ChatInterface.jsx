import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Paperclip, 
  Mic, 
  Plus, 
  MoreVertical,
  Brain,
  Zap,
  Shield,
  Search,
  Wifi,
  WifiOff
} from 'lucide-react';
import Button from '../../common/Button';
import ConversationSidebar from '../ConversationSidebar';
import ChatArea from '../ChatArea';
import ContextPanel from '../ContextPanel';
import PentagentAPI from '../../../services/pentagentAPI';

const ChatInterface = () => {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [contextOpen, setContextOpen] = useState(true);
  const [message, setMessage] = useState('');
  const [conversations, setConversations] = useState([]);
  const [activeConversation, setActiveConversation] = useState(null);
  const [isTyping, setIsTyping] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [currentScan, setCurrentScan] = useState(null);
  const [messages, setMessages] = useState([]);
  const [scanResults, setScanResults] = useState(null);
  
  const apiRef = useRef(new PentagentAPI());

  // WebSocket mesaj handler
  const handleWebSocketMessage = (data) => {
    console.log('WebSocket mesajı:', data);
    
    switch (data.type) {
      case 'connection_status':
        console.log('Bağlantı durumu:', data.status);
        if (data.status === 'connected') {
          setConnectionStatus('connected');
        }
        break;
        
      case 'scan_status':
        if (data.status_type === 'ai_thinking') {
          addMessage({
            type: 'ai_thinking',
            content: data.message,
            timestamp: data.timestamp,
            status: data.status_type
          });
        } else if (data.status_type === 'ai_reasoning') {
          addMessage({
            type: 'ai_reasoning',
            content: data.message,
            timestamp: data.timestamp,
            status: data.status_type
          });
        } else if (data.status_type === 'tool_start') {
          addMessage({
            type: 'tool',
            toolName: data.message.replace('🔧 ', '').replace(' başlatılıyor...', ''),
            status: 'running',
            progress: 0,
            timestamp: data.timestamp,
            results: []
          });
        } else if (data.status_type === 'tool_complete') {
          // Son tool mesajını güncelle
          setMessages(prev => {
            const updated = [...prev];
            const lastToolIndex = updated.findLastIndex(msg => msg.type === 'tool');
            if (lastToolIndex !== -1) {
              updated[lastToolIndex] = {
                ...updated[lastToolIndex],
                status: 'completed',
                progress: 100
              };
            }
            return updated;
          });
        } else {
          addMessage({
            type: 'system',
            content: data.message,
            timestamp: data.timestamp,
            status: data.status_type
          });
        }
        break;
        
      case 'scan_completed':
        addMessage({
          type: 'ai',
          content: `✅ Tarama tamamlandı! ${data.scan_id}`,
          timestamp: data.timestamp
        });
        setIsTyping(false);
        setCurrentScan(null);
        
        // Scan sonuçlarını kaydet (CVE analizi için)
        if (data.result) {
          console.log('Scan sonuçları alındı:', data.result);
          setScanResults(data.result);
        }
        break;
        
      case 'scan_started':
        setCurrentScan({
          id: data.scan_id,
          target: data.target,
          task: data.task,
          status: 'running'
        });
        addMessage({
          type: 'system',
          content: `🚀 Tarama başlatıldı: ${data.target}`,
          timestamp: data.timestamp
        });
        break;
        
      case 'pong':
        console.log('Pong alındı');
        break;
        
      default:
        console.log('Bilinmeyen mesaj tipi:', data.type);
    }
  };

  // Mesaj ekle
  const addMessage = (message) => {
    const newMessage = {
      id: Date.now().toString(),
      ...message
    };
    setMessages(prev => [...prev, newMessage]);
  };

  // Component mount olduğunda WebSocket bağlantısı kur
  useEffect(() => {
    console.log('ChatInterface mount edildi, WebSocket bağlantısı kuruluyor...');
    
    // Bağlantı durumunu başlangıçta connecting olarak ayarla
    setConnectionStatus('connecting');
    
    // WebSocket bağlantısını aktif et
    apiRef.current.connectWebSocket(handleWebSocketMessage, (status) => {
      console.log('Bağlantı durumu değişti:', status);
      setConnectionStatus(status);
    });
    
    // Cleanup - React Strict Mode için optimize edildi
    return () => {
      console.log('ChatInterface cleanup çağrıldı');
      // React Strict Mode'da çift mount olur, gerçek unmount'u tespit et
      // Hiçbir şey yapma - WebSocket bağlantısı açık kalsın
      // Sadece gerçek sayfa kapanışında disconnect olacak
    };
  }, []); // Boş dependency array - sadece mount/unmount'ta çalışsın

  const handleSendMessage = (e) => {
    e.preventDefault();
    
    if (!message.trim()) {
      return;
    }
    
    console.log('Mesaj gönderiliyor:', message);
    console.log('Bağlantı durumu:', connectionStatus);
    
    // User mesajını ekle
    addMessage({
      type: 'user',
      content: message,
      timestamp: new Date().toLocaleTimeString(),
      avatar: 'U'
    });
    
    // AI typing başlat
    setIsTyping(true);
    
    // Gerçek güvenlik testi başlat
    if (connectionStatus === 'connected') {
      console.log('WebSocket ile scan başlatılıyor...');
      // WebSocket ile gönder
      apiRef.current.startScan(message, 'Kapsamlı güvenlik testi yap');
    } else {
      console.log('REST API ile scan başlatılıyor...');
      // REST API fallback
      apiRef.current.startScanREST(message, 'Kapsamlı güvenlik testi yap')
        .then(result => {
          console.log('REST API scan started:', result);
          addMessage({
            type: 'system',
            content: `✅ Scan başlatıldı (REST API): ${result.scan_id || 'Unknown'}`,
            timestamp: new Date().toLocaleTimeString()
          });
          
          // REST API ile başlatılan scan için WebSocket'i dinlemeye başla
          // Çünkü scan sonuçları WebSocket üzerinden gelecek
        })
        .catch(error => {
          console.error('REST API scan failed:', error);
          addMessage({
            type: 'system',
            content: `❌ Scan başlatılamadı: ${error?.message || 'Unknown error'}`,
            timestamp: new Date().toLocaleTimeString()
          });
          setIsTyping(false);
        });
    }
    
    setMessage('');
  };

  const suggestedPrompts = [
    {
      icon: Shield,
      text: "Scan example.com for OWASP Top 10 vulnerabilities",
      category: "security"
    },
    {
      icon: Search,
      text: "Enumerate subdomains for target.com", 
      category: "reconnaissance"
    },
    {
      icon: Zap,
      text: "Test API endpoints for injection flaws",
      category: "testing"
    },
    {
      icon: Brain,
      text: "Generate security report for last scan",
      category: "reporting"
    }
  ];

  return (
    <div className="h-full bg-obsidian-950 flex overflow-hidden">
      {/* Conversation Sidebar */}
      <ConversationSidebar 
        isOpen={sidebarOpen}
        conversations={conversations}
        activeConversation={activeConversation}
        onSelectConversation={setActiveConversation}
        onToggle={() => setSidebarOpen(!sidebarOpen)}
      />

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 max-w-full overflow-hidden">
        {/* Connection Status Bar (Minimal) */}
        <div className="h-10 bg-obsidian-900/50 border-b border-obsidian-700 flex items-center justify-end px-6">
          <div className="flex items-center gap-3">
            {/* Connection Status */}
            <div className="flex items-center gap-1.5">
              {connectionStatus === 'connected' ? (
                <>
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  <span className="text-xs text-text-tertiary">Live</span>
                </>
              ) : connectionStatus === 'connecting' ? (
                <>
                  <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"></div>
                  <span className="text-xs text-text-tertiary">Connecting</span>
                </>
              ) : (
                <>
                  <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
                  <span className="text-xs text-text-tertiary">Offline</span>
                </>
              )}
            </div>
            
            {/* Context Panel Toggle */}
            <button
              onClick={() => setContextOpen(!contextOpen)}
              className="p-1.5 text-text-secondary hover:text-text-primary hover:bg-obsidian-850 rounded transition-all"
            >
              <MoreVertical className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Chat Messages Area */}
        <ChatArea 
          conversationId={activeConversation}
          isTyping={isTyping}
          messages={messages}
          currentScan={currentScan}
        />

        {/* Input Area */}
        <div className="border-t border-obsidian-700 bg-obsidian-900 p-4">
          {/* Suggested Prompts (show when no active conversation or empty) */}
          <div className="mb-4">
            <div className="flex gap-2 flex-wrap">
              {suggestedPrompts.map((prompt, index) => {
                const Icon = prompt.icon;
                return (
                  <button
                    key={index}
                    onClick={() => setMessage(prompt.text)}
                    className="flex items-center gap-2 px-3 py-2 bg-obsidian-850 hover:bg-obsidian-800 border border-obsidian-700 hover:border-platinum-500/30 rounded-lg text-sm text-text-secondary hover:text-text-primary transition-all group"
                  >
                    <Icon className="w-4 h-4 group-hover:text-platinum-500" />
                    <span className="truncate max-w-48">{prompt.text}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Message Input */}
          <form onSubmit={handleSendMessage} className="flex gap-3">
            <div className="flex-1 relative">
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Describe what you want to test..."
                rows={1}
                className="w-full min-h-[44px] max-h-32 px-4 py-3 pr-24 bg-obsidian-850 border border-obsidian-700 rounded-xl text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-platinum-500 focus:ring-2 focus:ring-platinum-500/10 resize-none transition-all"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage(e);
                  }
                }}
              />
              
              {/* Input Actions */}
              <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-2">
                <button
                  type="button"
                  className="p-2 text-text-tertiary hover:text-text-secondary hover:bg-obsidian-700 rounded-lg transition-all"
                >
                  <Paperclip className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  className="p-2 text-text-tertiary hover:text-text-secondary hover:bg-obsidian-700 rounded-lg transition-all"
                >
                  <Mic className="w-4 h-4" />
                </button>
              </div>
            </div>
            
            <Button 
              type="submit" 
              variant="primary" 
              disabled={!message.trim() || isTyping}
              className="h-11 px-4"
            >
              <Send className="w-4 h-4" />
            </Button>
          </form>

          {/* Input Help */}
          <div className="flex items-center justify-between mt-2 text-xs text-text-tertiary">
            <span>Use natural language to describe security tests</span>
            <span>Press Enter to send, Shift+Enter for new line</span>
          </div>
          
        </div>
      </div>

      {/* Context Panel */}
      <ContextPanel 
        isOpen={contextOpen}
        conversationId={activeConversation}
        onToggle={() => setContextOpen(!contextOpen)}
        scanResults={scanResults}
      />
    </div>
  );
};

export default ChatInterface;
