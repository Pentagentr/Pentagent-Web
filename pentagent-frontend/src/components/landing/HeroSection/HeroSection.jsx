import React, { useState, useEffect } from 'react';
import { Play, ArrowRight, Shield, Zap, Brain } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Button from '../../common/Button';
import Logo from '../../common/Logo';

const HeroSection = () => {
  const navigate = useNavigate();
  const [typedText, setTypedText] = useState('');
  const fullText = 'example.com için tüm OWASP Top 10 zafiyetlerini tara';
  
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
          <a href="#features" className="text-sm text-text-secondary hover:text-purple-400 transition-smooth">Özellikler</a>
          <a href="#demo" className="text-sm text-text-secondary hover:text-purple-400 transition-smooth">Demo</a>
          <a href="#faq" className="text-sm text-text-secondary hover:text-purple-400 transition-smooth">SSS</a>
          <Button 
            variant="ghost" 
            size="sm"
            onClick={() => navigate('/login')}
            className="text-sm"
          >
            Giriş Yap
          </Button>
          <Button 
            variant="primary" 
            size="sm"
            onClick={() => navigate('/register')}
            className="text-sm bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800"
          >
            Başla
          </Button>
        </nav>
      </header>

      {/* Hero Content */}
      <div className="relative z-10 px-8 py-16">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            
            {/* Left Column - Content */}
            <div className="space-y-8">
              {/* Badge */}
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-obsidian-900 border border-purple-900/30 rounded-full">
                <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
                <span className="text-xs text-text-secondary">AI Destekli Güvenlik Testi</span>
              </div>
              
              {/* Main Headline */}
              <div className="space-y-6">
                <h1 className="text-4xl lg:text-5xl font-bold text-text-primary leading-tight tracking-tight">
                  Otonom
                  <span className="block text-transparent bg-gradient-to-r from-purple-400 to-purple-600 bg-clip-text">
                    Penetrasyon
                  </span>
                  Testi
                </h1>
                
                <p className="text-base text-text-secondary leading-relaxed max-w-lg">
                  Düşünen, adapte olan ve otonom şekilde koruyan akıllı güvenlik değerlendirmeleri yapın. 
                  Manuel konfigürasyon gerektirmez.
                </p>
              </div>
              
              {/* CTA Buttons */}
              <div className="flex flex-col sm:flex-row gap-4">
                <Button 
                  variant="primary" 
                  size="lg" 
                  className="group bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-sm"
                  onClick={() => navigate('/register')}
                >
                  Ücretsiz Başla
                  <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                </Button>
                
                <Button 
                  variant="secondary" 
                  size="lg" 
                  className="group text-sm"
                  onClick={() => document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth' })}
                >
                  <Play className="w-4 h-4 mr-2" />
                  Demo İzle
                </Button>
              </div>
              
              {/* Trust Indicators */}
              <div className="flex items-center gap-6 pt-8">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-purple-500" />
                  <span className="text-xs text-text-tertiary">SOC 2 Uyumlu</span>
                </div>
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-purple-500" />
                  <span className="text-xs text-text-tertiary">10k+ Günlük Tarama</span>
                </div>
                <div className="flex items-center gap-2">
                  <Brain className="w-4 h-4 text-purple-500" />
                  <span className="text-xs text-text-tertiary">AI Öncelikli</span>
                </div>
              </div>
            </div>
            
            {/* Right Column - Interactive Demo */}
            <div className="relative">
              {/* Floating Elements */}
              <FloatingElement className="absolute -top-4 -left-4 w-20 h-20 bg-gradient-to-br from-purple-500/20 to-purple-600/20 rounded-full blur-xl" delay={0} />
              <FloatingElement className="absolute top-1/4 -right-8 w-32 h-32 bg-gradient-to-br from-purple-500/10 to-purple-600/10 rounded-full blur-2xl" delay={1} />
              <FloatingElement className="absolute bottom-1/4 -left-8 w-24 h-24 bg-gradient-to-br from-purple-400/10 to-purple-500/10 rounded-full blur-xl" delay={2} />
              
              {/* Main Demo Card */}
              <div className="relative bg-obsidian-900/50 backdrop-blur-xl border border-purple-900/30 rounded-2xl p-6 shadow-2xl">
                {/* Terminal Header */}
                <div className="flex items-center gap-2 mb-4">
                  <div className="flex gap-2">
                    <div className="w-2.5 h-2.5 bg-rose-500 rounded-full" />
                    <div className="w-2.5 h-2.5 bg-purple-500 rounded-full" />
                    <div className="w-2.5 h-2.5 bg-green-500 rounded-full" />
                  </div>
                  <span className="text-xs text-text-tertiary ml-4">Pentagent AI Terminal</span>
                </div>
                
                {/* Command Input */}
                <div className="bg-obsidian-950 rounded-lg p-3 mb-3 border border-purple-900/30">
                  <div className="flex items-center gap-3">
                    <span className="text-purple-500 font-mono text-xs">$</span>
                    <span className="text-text-primary font-mono text-xs">
                      {typedText}
                      <span className="animate-pulse">|</span>
                    </span>
                  </div>
                </div>
                
                {/* AI Response */}
                <div className="space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="w-5 h-5 bg-gradient-to-br from-purple-500 to-purple-600 rounded-full flex items-center justify-center flex-shrink-0">
                      <Brain className="w-3 h-3 text-white" />
                    </div>
                    <div className="flex-1">
                      <p className="text-text-primary text-xs mb-2">
                        Kapsamlı güvenlik değerlendirmesi yapacağım. İşte yürütme planım:
                      </p>
                      
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-pulse" />
                          <span className="text-text-secondary text-xs">Port tarama & servis numaralandırma</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 bg-obsidian-600 rounded-full" />
                          <span className="text-text-tertiary text-xs">Teknoloji yığını tespiti</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 bg-obsidian-600 rounded-full" />
                          <span className="text-text-tertiary text-xs">OWASP Top 10 zafiyet değerlendirmesi</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Progress Card */}
                  <div className="bg-obsidian-850 rounded-lg p-3 border border-purple-900/30">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-text-primary text-xs font-medium">Port Tarayıcı</span>
                      <span className="text-purple-500 text-xs">Çalışıyor</span>
                    </div>
                    <div className="w-full bg-obsidian-700 rounded-full h-1.5">
                      <div className="bg-gradient-to-r from-purple-500 to-purple-600 h-1.5 rounded-full w-3/4 animate-pulse" />
                    </div>
                    <p className="text-text-tertiary text-xs mt-1.5">12 açık port bulundu</p>
                  </div>
                </div>
              </div>
              
              {/* Stats Cards */}
              <div className="grid grid-cols-2 gap-3 mt-4">
                <div className="bg-obsidian-900/30 backdrop-blur-xl border border-purple-900/30 rounded-xl p-3">
                  <div className="text-xl font-bold text-text-primary">99.9%</div>
                  <div className="text-text-tertiary text-xs">Doğruluk Oranı</div>
                </div>
                <div className="bg-obsidian-900/30 backdrop-blur-xl border border-purple-900/30 rounded-xl p-3">
                  <div className="text-xl font-bold text-text-primary">2.3s</div>
                  <div className="text-text-tertiary text-xs">Ort. Yanıt</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom CTA */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2">
        <div className="flex items-center gap-2 text-text-tertiary">
          <span className="text-xs">Kredi kartı gerektirmez</span>
          <span className="w-1 h-1 bg-text-tertiary rounded-full" />
          <span className="text-xs">14 günlük ücretsiz deneme</span>
          <span className="w-1 h-1 bg-text-tertiary rounded-full" />
          <span className="text-xs">İstediğiniz zaman iptal edin</span>
        </div>
      </div>
    </div>
  );
};

export default HeroSection;
