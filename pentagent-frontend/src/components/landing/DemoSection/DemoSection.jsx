import React, { useState } from 'react';
import { Play, Pause, RotateCcw, Maximize2, Volume2 } from 'lucide-react';
import Button from '../../common/Button';

const DemoSection = () => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [selectedDemo, setSelectedDemo] = useState('full-scan');

  const demoModes = [
    {
      id: 'full-scan',
      title: 'Complete Security Audit',
      duration: '2:34',
      description: 'Watch a full vulnerability assessment from start to finish'
    },
    {
      id: 'sql-injection',
      title: 'SQL Injection Detection',
      duration: '1:12',
      description: 'See how AI detects and validates SQL injection vulnerabilities'
    },
    {
      id: 'report-generation',
      title: 'Automated Reporting',
      duration: '0:45',
      description: 'Automated report generation for different stakeholders'
    }
  ];

  const timelineSteps = [
    { time: 0, label: 'Target Analysis', active: currentTime >= 0 },
    { time: 25, label: 'Port Scanning', active: currentTime >= 25 },
    { time: 50, label: 'Vulnerability Detection', active: currentTime >= 50 },
    { time: 75, label: 'Exploitation Validation', active: currentTime >= 75 },
    { time: 100, label: 'Report Generation', active: currentTime >= 100 },
  ];

  return (
    <section className="py-24 bg-obsidian-950">
      <div className="max-w-7xl mx-auto px-8">
        
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl lg:text-5xl font-bold text-text-primary mb-6">
            See Pentagent
            <span className="block text-transparent bg-gradient-to-r from-platinum-400 to-platinum-600 bg-clip-text">
              In Action
            </span>
          </h2>
          <p className="text-xl text-text-secondary max-w-3xl mx-auto">
            Watch real penetration tests unfold in minutes, not hours. 
            See how AI makes security testing accessible to everyone.
          </p>
        </div>

        {/* Demo Mode Selector */}
        <div className="flex flex-wrap gap-4 justify-center mb-12">
          {demoModes.map((mode) => (
            <button
              key={mode.id}
              onClick={() => setSelectedDemo(mode.id)}
              className={`
                p-4 rounded-xl border transition-all duration-300
                ${selectedDemo === mode.id 
                  ? 'bg-platinum-500/10 border-platinum-500/30 text-text-primary' 
                  : 'bg-obsidian-900 border-obsidian-700 text-text-secondary hover:border-obsidian-600'
                }
              `}
            >
              <div className="text-left">
                <div className="font-medium mb-1">{mode.title}</div>
                <div className="text-sm opacity-70">{mode.description}</div>
                <div className="text-xs mt-2 text-platinum-500">{mode.duration}</div>
              </div>
            </button>
          ))}
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          
          {/* Video Player */}
          <div className="lg:col-span-2">
            <div className="relative bg-obsidian-900 rounded-2xl border border-obsidian-700 overflow-hidden aspect-video">
              
              {/* Video Placeholder */}
              <div className="absolute inset-0 bg-gradient-to-br from-obsidian-800 to-obsidian-900 flex items-center justify-center">
                <div className="text-center">
                  <div className="w-20 h-20 bg-platinum-500/20 rounded-full flex items-center justify-center mb-4 mx-auto backdrop-blur-sm">
                    <Play className="w-8 h-8 text-platinum-500" />
                  </div>
                  <p className="text-text-secondary">Interactive Demo</p>
                  <p className="text-text-tertiary text-sm mt-1">Click to start simulation</p>
                </div>
                
                {/* Animated background elements */}
                <div className="absolute top-4 right-4 w-32 h-2 bg-obsidian-700 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-platinum-500 to-platinum-600 w-1/3 animate-pulse" />
                </div>
                
                <div className="absolute bottom-4 left-4 space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    <span className="text-xs text-text-tertiary">Live Simulation</span>
                  </div>
                </div>
              </div>
              
              {/* Video Controls */}
              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-obsidian-950/90 to-transparent p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <button 
                      onClick={() => setIsPlaying(!isPlaying)}
                      className="w-12 h-12 bg-platinum-500 hover:bg-platinum-600 rounded-full flex items-center justify-center transition-colors"
                    >
                      {isPlaying ? (
                        <Pause className="w-5 h-5 text-obsidian-950" />
                      ) : (
                        <Play className="w-5 h-5 text-obsidian-950 ml-0.5" />
                      )}
                    </button>
                    
                    <div className="text-sm text-text-secondary">
                      0:00 / {demoModes.find(m => m.id === selectedDemo)?.duration}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    <button className="p-2 text-text-secondary hover:text-text-primary transition-colors">
                      <Volume2 className="w-4 h-4" />
                    </button>
                    <button className="p-2 text-text-secondary hover:text-text-primary transition-colors">
                      <RotateCcw className="w-4 h-4" />
                    </button>
                    <button className="p-2 text-text-secondary hover:text-text-primary transition-colors">
                      <Maximize2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                
                {/* Progress Bar */}
                <div className="mt-4 w-full h-1 bg-obsidian-700 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-platinum-500 to-platinum-600 transition-all duration-300"
                    style={{ width: `${currentTime}%` }}
                  />
                </div>
              </div>
            </div>
            
            {/* Timeline */}
            <div className="mt-6 bg-obsidian-900 border border-obsidian-700 rounded-xl p-6">
              <h4 className="text-lg font-semibold text-text-primary mb-4">Demo Timeline</h4>
              <div className="space-y-3">
                {timelineSteps.map((step, index) => (
                  <div 
                    key={index}
                    className={`flex items-center gap-4 transition-all duration-300 ${
                      step.active ? 'text-text-primary' : 'text-text-tertiary'
                    }`}
                  >
                    <div className={`w-3 h-3 rounded-full transition-all duration-300 ${
                      step.active ? 'bg-platinum-500 shadow-lg shadow-platinum-500/30' : 'bg-obsidian-700'
                    }`} />
                    <span className="font-medium">{step.label}</span>
                    {step.active && (
                      <div className="ml-auto flex items-center gap-2">
                        <div className="w-2 h-2 bg-platinum-500 rounded-full animate-pulse" />
                        <span className="text-xs">Active</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
          
          {/* Live Stats */}
          <div className="space-y-6">
            <div className="bg-obsidian-900 border border-obsidian-700 rounded-xl p-6">
              <h4 className="text-lg font-semibold text-text-primary mb-4">Live Demo Stats</h4>
              
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-text-secondary">Scan Progress</span>
                    <span className="text-platinum-500 font-medium">{currentTime}%</span>
                  </div>
                  <div className="w-full h-2 bg-obsidian-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-platinum-500 to-platinum-600 transition-all duration-300"
                      style={{ width: `${currentTime}%` }}
                    />
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center p-3 bg-obsidian-850 rounded-lg">
                    <div className="text-2xl font-bold text-text-primary">23</div>
                    <div className="text-xs text-text-tertiary">Ports Scanned</div>
                  </div>
                  <div className="text-center p-3 bg-obsidian-850 rounded-lg">
                    <div className="text-2xl font-bold text-rose-500">5</div>
                    <div className="text-xs text-text-tertiary">Vulnerabilities</div>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-text-secondary">Tools Active</span>
                    <span className="text-text-primary">3</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-text-secondary">Time Elapsed</span>
                    <span className="text-text-primary">1m 23s</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-text-secondary">Est. Completion</span>
                    <span className="text-text-primary">2m 15s</span>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="bg-obsidian-900 border border-obsidian-700 rounded-xl p-6">
              <h4 className="text-lg font-semibold text-text-primary mb-4">Try It Yourself</h4>
              <p className="text-text-secondary text-sm mb-4">
                Ready to see Pentagent in action on your own targets?
              </p>
              <Button variant="primary" className="w-full">
                Start Free Trial
              </Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default DemoSection;
