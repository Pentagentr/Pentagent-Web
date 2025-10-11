import React, { useState, useEffect } from 'react';
import { Play, ArrowRight, Shield, Zap, Brain } from 'lucide-react';
import Button from '../../common/Button';
import Logo from '../../common/Logo';

const HeroSection = () => {
  const [typedText, setTypedText] = useState('');
  const fullText = 'Scan example.com for all OWASP Top 10 vulnerabilities';
  
  useEffect(() => {
    let index = 0;
    const timer = setInterval(() => {
      if (index <= fullText.length) {
        setTypedText(fullText.slice(0, index));
        index++;
      } else {
        clearInterval(timer);
      }
    }, 50);
    
    return () => clearInterval(timer);
  }, []);

  const FloatingElement = ({ children, className = '', delay = 0 }) => (
    <div 
      className={`animate-pulse ${className}`}
      style={{ 
        animationDelay: `${delay}s`,
        animationDuration: '3s'
      }}
    >
      {children}
    </div>
  );

  return (
    <div className="relative min-h-screen bg-obsidian-950 overflow-hidden">
      {/* Animated Grid Background */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-br from-obsidian-950 via-obsidian-900 to-obsidian-950" />
        <div 
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage: `
              linear-gradient(rgba(232,232,232,0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(232,232,232,0.1) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px'
          }}
        />
      </div>

      {/* Header */}
      <header className="relative z-10 flex items-center justify-between px-8 py-6">
        <Logo variant="full" size="md" />
        
        <nav className="hidden md:flex items-center gap-8">
          <a href="#features" className="text-text-secondary hover:text-platinum-500 transition-smooth">Features</a>
          <a href="#pricing" className="text-text-secondary hover:text-platinum-500 transition-smooth">Pricing</a>
          <a href="#docs" className="text-text-secondary hover:text-platinum-500 transition-smooth">Docs</a>
          <Button variant="ghost" size="sm">Sign In</Button>
          <Button variant="primary" size="sm">Get Started</Button>
        </nav>
      </header>

      {/* Hero Content */}
      <div className="relative z-10 px-8 py-16">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            
            {/* Left Column - Content */}
            <div className="space-y-8">
              {/* Badge */}
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-obsidian-900 border border-obsidian-700 rounded-full">
                <div className="w-2 h-2 bg-platinum-500 rounded-full animate-pulse" />
                <span className="text-sm text-text-secondary">AI-Powered Security Testing</span>
              </div>
              
              {/* Main Headline */}
              <div className="space-y-6">
                <h1 className="text-5xl lg:text-6xl font-bold text-text-primary leading-none tracking-tight">
                  Autonomous
                  <span className="block text-transparent bg-gradient-to-r from-platinum-400 to-platinum-600 bg-clip-text">
                    Penetration
                  </span>
                  Testing
                </h1>
                
                <p className="text-xl text-text-secondary leading-relaxed max-w-lg">
                  Deploy intelligent security assessments that think, adapt, and protect autonomously. 
                  No manual configuration required.
                </p>
              </div>
              
              {/* CTA Buttons */}
              <div className="flex flex-col sm:flex-row gap-4">
                <Button variant="primary" size="lg" className="group">
                  Start Free Trial
                  <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                </Button>
                
                <Button variant="secondary" size="lg" className="group">
                  <Play className="w-4 h-4 mr-2" />
                  Watch Demo
                </Button>
              </div>
              
              {/* Trust Indicators */}
              <div className="flex items-center gap-6 pt-8">
                <div className="flex items-center gap-2">
                  <Shield className="w-5 h-5 text-platinum-500" />
                  <span className="text-sm text-text-tertiary">SOC 2 Compliant</span>
                </div>
                <div className="flex items-center gap-2">
                  <Zap className="w-5 h-5 text-platinum-500" />
                  <span className="text-sm text-text-tertiary">10k+ Daily Scans</span>
                </div>
                <div className="flex items-center gap-2">
                  <Brain className="w-5 h-5 text-platinum-500" />
                  <span className="text-sm text-text-tertiary">AI-First Approach</span>
                </div>
              </div>
            </div>
            
            {/* Right Column - Interactive Demo */}
            <div className="relative">
              {/* Floating Elements */}
              <FloatingElement className="absolute -top-4 -left-4 w-20 h-20 bg-gradient-to-br from-platinum-500/20 to-platinum-600/20 rounded-full blur-xl" delay={0} />
              <FloatingElement className="absolute top-1/4 -right-8 w-32 h-32 bg-gradient-to-br from-purple-500/10 to-purple-600/10 rounded-full blur-2xl" delay={1} />
              <FloatingElement className="absolute bottom-1/4 -left-8 w-24 h-24 bg-gradient-to-br from-rose-400/10 to-rose-500/10 rounded-full blur-xl" delay={2} />
              
              {/* Main Demo Card */}
              <div className="relative bg-obsidian-900/50 backdrop-blur-xl border border-obsidian-700/50 rounded-2xl p-8 shadow-2xl">
                {/* Terminal Header */}
                <div className="flex items-center gap-2 mb-6">
                  <div className="flex gap-2">
                    <div className="w-3 h-3 bg-rose-500 rounded-full" />
                    <div className="w-3 h-3 bg-platinum-500 rounded-full" />
                    <div className="w-3 h-3 bg-green-500 rounded-full" />
                  </div>
                  <span className="text-sm text-text-tertiary ml-4">Pentagent AI Terminal</span>
                </div>
                
                {/* Command Input */}
                <div className="bg-obsidian-950 rounded-lg p-4 mb-4 border border-obsidian-700">
                  <div className="flex items-center gap-3">
                    <span className="text-platinum-500 font-mono text-sm">$</span>
                    <span className="text-text-primary font-mono text-sm">
                      {typedText}
                      <span className="animate-pulse">|</span>
                    </span>
                  </div>
                </div>
                
                {/* AI Response */}
                <div className="space-y-4">
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 bg-gradient-to-br from-platinum-500 to-platinum-600 rounded-full flex items-center justify-center flex-shrink-0">
                      <Brain className="w-3 h-3 text-obsidian-950" />
                    </div>
                    <div className="flex-1">
                      <p className="text-text-primary text-sm mb-3">
                        I'll perform a comprehensive security assessment. Here's my execution plan:
                      </p>
                      
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-platinum-500 rounded-full animate-pulse" />
                          <span className="text-text-secondary text-sm">Port scanning & service enumeration</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-obsidian-600 rounded-full" />
                          <span className="text-text-tertiary text-sm">Technology stack detection</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 bg-obsidian-600 rounded-full" />
                          <span className="text-text-tertiary text-sm">OWASP Top 10 vulnerability assessment</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Progress Card */}
                  <div className="bg-obsidian-850 rounded-lg p-4 border border-obsidian-700">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-text-primary text-sm font-medium">Port Scanner</span>
                      <span className="text-platinum-500 text-sm">Running</span>
                    </div>
                    <div className="w-full bg-obsidian-700 rounded-full h-2">
                      <div className="bg-gradient-to-r from-platinum-500 to-platinum-600 h-2 rounded-full w-3/4 animate-pulse" />
                    </div>
                    <p className="text-text-tertiary text-xs mt-2">Found 12 open ports</p>
                  </div>
                </div>
              </div>
              
              {/* Stats Cards */}
              <div className="grid grid-cols-2 gap-4 mt-6">
                <div className="bg-obsidian-900/30 backdrop-blur-xl border border-obsidian-700/50 rounded-xl p-4">
                  <div className="text-2xl font-bold text-text-primary">99.9%</div>
                  <div className="text-text-tertiary text-sm">Accuracy Rate</div>
                </div>
                <div className="bg-obsidian-900/30 backdrop-blur-xl border border-obsidian-700/50 rounded-xl p-4">
                  <div className="text-2xl font-bold text-text-primary">2.3s</div>
                  <div className="text-text-tertiary text-sm">Avg Response</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom CTA */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2">
        <div className="flex items-center gap-2 text-text-tertiary">
          <span className="text-sm">No credit card required</span>
          <span className="w-1 h-1 bg-text-tertiary rounded-full" />
          <span className="text-sm">14-day free trial</span>
          <span className="w-1 h-1 bg-text-tertiary rounded-full" />
          <span className="text-sm">Cancel anytime</span>
        </div>
      </div>
    </div>
  );
};

export default HeroSection;
