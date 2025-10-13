import React from 'react';
import { Brain } from 'lucide-react';

const ThinkingAnimation = () => {
  return (
    <div className="bg-obsidian-900 border border-obsidian-700 rounded-2xl rounded-bl-sm p-4">
      <div className="flex items-center gap-2 mb-3">
        <Brain className="w-4 h-4 text-platinum-500" />
        <span className="text-xs font-medium text-platinum-500 uppercase tracking-wide">AI Assistant</span>
        <div className="flex gap-1 ml-2">
          <div className="w-1.5 h-1.5 bg-platinum-500 rounded-full animate-pulse" style={{ animationDelay: '0ms' }} />
          <div className="w-1.5 h-1.5 bg-platinum-500 rounded-full animate-pulse" style={{ animationDelay: '200ms' }} />
          <div className="w-1.5 h-1.5 bg-platinum-500 rounded-full animate-pulse" style={{ animationDelay: '400ms' }} />
        </div>
      </div>
      
      <div className="mt-2 p-3 bg-obsidian-850 rounded-lg">
        <div className="flex items-center justify-between text-xs text-text-tertiary">
          <span>Thinking...</span>
          <div className="flex items-center gap-2">
            <div className="w-12 h-1 bg-obsidian-700 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-platinum-500 to-platinum-600 rounded-full animate-pulse w-3/4" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ThinkingAnimation;
