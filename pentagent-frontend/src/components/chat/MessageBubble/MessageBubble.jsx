import React, { useState } from 'react';
import { Copy, Check, ThumbsUp, ThumbsDown, RotateCcw, User, Brain } from 'lucide-react';

const MessageBubble = ({ 
  type, 
  content, 
  timestamp, 
  avatar, 
  thinking = false,
  onCopy,
  onRegenerate,
  onFeedback 
}) => {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      onCopy?.();
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  const handleFeedback = (type) => {
    setFeedback(type);
    onFeedback?.(type);
  };

  const isUser = type === 'user';
  const isAI = type === 'ai';

  return (
    <div className={`flex gap-4 group ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className="flex-shrink-0">
        {isUser ? (
          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center">
            {avatar ? (
              <span className="text-sm font-bold text-text-primary">{avatar}</span>
            ) : (
              <User className="w-5 h-5 text-text-primary" />
            )}
          </div>
        ) : (
          <div className="w-10 h-10 bg-gradient-to-br from-platinum-500 to-platinum-600 rounded-xl flex items-center justify-center">
            <Brain className="w-5 h-5 text-obsidian-950" />
          </div>
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 min-w-0 ${isUser ? 'flex flex-col items-end' : ''}`}>
        {/* Header */}
        <div className={`flex items-center gap-2 mb-2 ${isUser ? 'flex-row-reverse' : ''}`}>
          <span className="text-sm font-medium text-text-primary">
            {isUser ? 'You' : 'Pentagent AI'}
          </span>
          <span className="text-xs text-text-tertiary">{timestamp}</span>
        </div>

        {/* Message Bubble */}
        <div className={`
          relative max-w-2xl rounded-2xl px-4 py-3 transition-all duration-200 group-hover:shadow-lg
          ${isUser 
            ? 'bg-gradient-to-br from-purple-500 to-purple-600 text-text-primary ml-auto' 
            : 'bg-obsidian-900 border border-obsidian-700 text-text-primary'
          }
          ${isUser ? 'rounded-br-md' : 'rounded-bl-md'}
        `}>
          {/* Content */}
          <div className="prose prose-invert max-w-none">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {content}
            </p>
          </div>

          {/* Thinking Indicator */}
          {thinking && (
            <div className="flex items-center gap-2 mt-3 pt-3 border-t border-obsidian-700">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-platinum-500 rounded-full animate-pulse" />
                <span className="text-xs text-text-tertiary">AI is thinking...</span>
              </div>
            </div>
          )}

          {/* Actions */}
          {isAI && (
            <div className="absolute -right-12 top-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex flex-col gap-1">
              <button
                onClick={handleCopy}
                className="p-2 bg-obsidian-800 border border-obsidian-700 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-obsidian-700 transition-all"
                title="Copy message"
              >
                {copied ? (
                  <Check className="w-3 h-3 text-success" />
                ) : (
                  <Copy className="w-3 h-3" />
                )}
              </button>
              
              <button
                onClick={() => onRegenerate?.()}
                className="p-2 bg-obsidian-800 border border-obsidian-700 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-obsidian-700 transition-all"
                title="Regenerate response"
              >
                <RotateCcw className="w-3 h-3" />
              </button>
            </div>
          )}
        </div>

        {/* Feedback */}
        {isAI && (
          <div className="flex items-center gap-2 mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
            <button
              onClick={() => handleFeedback('positive')}
              className={`p-1 rounded transition-all ${
                feedback === 'positive' 
                  ? 'text-success bg-success/10' 
                  : 'text-text-tertiary hover:text-success hover:bg-success/5'
              }`}
              title="Good response"
            >
              <ThumbsUp className="w-3 h-3" />
            </button>
            
            <button
              onClick={() => handleFeedback('negative')}
              className={`p-1 rounded transition-all ${
                feedback === 'negative' 
                  ? 'text-rose-500 bg-rose-500/10' 
                  : 'text-text-tertiary hover:text-rose-500 hover:bg-rose-500/5'
              }`}
              title="Poor response"
            >
              <ThumbsDown className="w-3 h-3" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
