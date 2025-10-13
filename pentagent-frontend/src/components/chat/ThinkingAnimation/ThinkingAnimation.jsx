import React from 'react';
import { Brain, Zap, Search, Shield } from 'lucide-react';

const ThinkingAnimation = () => {
  const thoughts = [
    "Analyzing target architecture...",
    "Planning optimal attack vectors...", 
    "Selecting appropriate tools...",
    "Preparing reconnaissance strategy..."
  ];

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
      
      <div className="space-y-3">
        {thoughts.map((thought, index) => (
          <div 
            key={index} 
            className="flex items-center gap-3 animate-fadeIn"
            style={{ animationDelay: `${index * 600}ms`, animationFillMode: 'both' }}
          >
            <div className="w-6 h-6 bg-obsidian-850 rounded-lg flex items-center justify-center">
              {index === 0 && <Search className="w-3 h-3 text-text-tertiary" />}
              {index === 1 && <Zap className="w-3 h-3 text-text-tertiary" />}
              {index === 2 && <Shield className="w-3 h-3 text-text-tertiary" />}
              {index === 3 && <Brain className="w-3 h-3 text-text-tertiary" />}
            </div>
            <span className="text-sm text-text-secondary">{thought}</span>
          </div>
        ))}
      </div>
      
      <div className="mt-4 p-3 bg-obsidian-850 rounded-lg">
        <div className="flex items-center justify-between text-xs text-text-tertiary">
          <span>Processing...</span>
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
