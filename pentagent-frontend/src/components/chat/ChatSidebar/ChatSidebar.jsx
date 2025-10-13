// Chat geçmişi sidebar - ChatGPT tarzı
import React, { useState, useEffect } from 'react';
import { Plus, MessageSquare, Trash2, Edit3, Check, X } from 'lucide-react';
import { useAuth } from '../../../contexts/AuthContext';
import { 
  collection, 
  query, 
  where, 
  orderBy, 
  onSnapshot,
  addDoc,
  deleteDoc,
  updateDoc,
  doc,
  serverTimestamp 
} from 'firebase/firestore';
import { db } from '../../../config/firebase';

const ChatSidebar = ({ currentConversationId, onConversationSelect, onNewChat }) => {
  const { currentUser } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [hoveredId, setHoveredId] = useState(null);

  // Firestore'dan konuşmaları dinle
  useEffect(() => {
    if (!currentUser) return;

    const q = query(
      collection(db, 'conversations'),
      where('userId', '==', currentUser.uid),
      orderBy('updatedAt', 'desc')
    );

    const unsubscribe = onSnapshot(q, (snapshot) => {
      const convs = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));
      setConversations(convs);
    });

    return () => unsubscribe();
  }, [currentUser]);

  // Yeni konuşma oluştur
  const handleNewChat = async () => {
    if (!currentUser) return;

    try {
      const newConv = await addDoc(collection(db, 'conversations'), {
        userId: currentUser.uid,
        title: 'New Chat',
        messages: [],
        createdAt: serverTimestamp(),
        updatedAt: serverTimestamp()
      });
      
      onNewChat(newConv.id);
    } catch (error) {
      console.error('Error creating conversation:', error);
    }
  };

  // Konuşmayı sil
  const handleDelete = async (e, convId) => {
    e.stopPropagation();
    if (!window.confirm('Bu konuşmayı silmek istediğinize emin misiniz?')) return;

    try {
      await deleteDoc(doc(db, 'conversations', convId));
      if (currentConversationId === convId) {
        onNewChat(null);
      }
    } catch (error) {
      console.error('Error deleting conversation:', error);
    }
  };

  // Konuşma başlığını düzenle
  const handleEdit = (e, conv) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitle(conv.title);
  };

  // Düzenlemeyi kaydet
  const handleSaveEdit = async (convId) => {
    if (!editTitle.trim()) return;

    try {
      await updateDoc(doc(db, 'conversations', convId), {
        title: editTitle.trim(),
        updatedAt: serverTimestamp()
      });
      setEditingId(null);
    } catch (error) {
      console.error('Error updating conversation:', error);
    }
  };

  // Düzenlemeyi iptal et
  const handleCancelEdit = () => {
    setEditingId(null);
    setEditTitle('');
  };

  return (
    <div className="w-64 h-full bg-obsidian-900/95 backdrop-blur-md border-r border-platinum-500/10 flex flex-col">
      {/* Header - Yeni Chat Butonu */}
      <div className="p-3 border-b border-platinum-500/10">
        <button
          onClick={handleNewChat}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/30 rounded-lg text-xs font-medium text-purple-400 transition-all duration-300"
        >
          <Plus size={14} />
          <span>New Chat</span>
        </button>
      </div>

      {/* Konuşma Listesi */}
      <div className="flex-1 overflow-y-auto py-2 px-2 space-y-1 scrollbar-thin scrollbar-thumb-purple-500/20 scrollbar-track-transparent">
        {conversations.length === 0 ? (
          <div className="text-center py-8 px-4">
            <MessageSquare size={32} className="mx-auto text-platinum-600 mb-2" />
            <p className="text-xs text-platinum-tertiary">No conversations yet</p>
          </div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => !editingId && onConversationSelect(conv.id)}
              onMouseEnter={() => setHoveredId(conv.id)}
              onMouseLeave={() => setHoveredId(null)}
              className={`group relative px-3 py-2 rounded-lg cursor-pointer transition-all duration-200 ${
                currentConversationId === conv.id
                  ? 'bg-purple-500/10 border border-purple-500/30'
                  : 'hover:bg-obsidian-850 border border-transparent'
              }`}
            >
              {editingId === conv.id ? (
                // Edit Mode
                <div className="flex items-center gap-1">
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleSaveEdit(conv.id);
                      if (e.key === 'Escape') handleCancelEdit();
                    }}
                    className="flex-1 bg-obsidian-950 border border-purple-500/30 rounded px-2 py-1 text-xs text-platinum focus:outline-none focus:border-purple-500/50"
                    autoFocus
                  />
                  <button
                    onClick={() => handleSaveEdit(conv.id)}
                    className="p-1 hover:bg-purple-500/20 rounded"
                  >
                    <Check size={12} className="text-purple-400" />
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    className="p-1 hover:bg-rose-500/20 rounded"
                  >
                    <X size={12} className="text-rose-400" />
                  </button>
                </div>
              ) : (
                // Normal Mode
                <>
                  <div className="flex items-start gap-2">
                    <MessageSquare size={14} className={`flex-shrink-0 mt-0.5 ${
                      currentConversationId === conv.id ? 'text-purple-400' : 'text-platinum-600'
                    }`} />
                    <p className={`flex-1 text-xs truncate ${
                      currentConversationId === conv.id ? 'text-platinum-400' : 'text-platinum-secondary'
                    }`}>
                      {conv.title}
                    </p>
                  </div>
                  
                  {/* Action Buttons - Hover'da görünür */}
                  {hoveredId === conv.id && !editingId && (
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1 bg-obsidian-900 px-1 rounded">
                      <button
                        onClick={(e) => handleEdit(e, conv)}
                        className="p-1 hover:bg-purple-500/20 rounded transition-colors"
                      >
                        <Edit3 size={12} className="text-platinum-600 hover:text-purple-400" />
                      </button>
                      <button
                        onClick={(e) => handleDelete(e, conv.id)}
                        className="p-1 hover:bg-rose-500/20 rounded transition-colors"
                      >
                        <Trash2 size={12} className="text-platinum-600 hover:text-rose-400" />
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          ))
        )}
      </div>

      {/* Footer - Info */}
      <div className="p-3 border-t border-platinum-500/10">
        <p className="text-[10px] text-platinum-tertiary text-center">
          {conversations.length} conversation{conversations.length !== 1 ? 's' : ''}
        </p>
      </div>
    </div>
  );
};

export default ChatSidebar;



