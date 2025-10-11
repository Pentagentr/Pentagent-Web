import React, { useState } from 'react';
import { 
  Brain, 
  Zap, 
  Shield, 
  BarChart3, 
  MessageSquare, 
  GitBranch,
  Eye,
  Cpu,
  ArrowRight
} from 'lucide-react';
import Button from '../../common/Button';

const FeaturesSection = () => {
  const [activeFeature, setActiveFeature] = useState(0);

  const features = [
    {
      id: 'autonomous',
      icon: Brain,
      badge: 'AI-Powered',
      title: 'Autonomous Security Testing',
      description: 'Our AI agent thinks like a senior pentester, adapting its approach based on target reconnaissance and continuously learning from each scan.',
      codeExample: `// AI automatically adapts testing strategy
const scanResult = await pentagent.scan({
  target: "example.com",
  mode: "autonomous",
  depth: "comprehensive"
});

// AI decides optimal tool sequence
scanResult.strategy = [
  "port_enumeration",
  "web_technology_detection", 
  "vulnerability_assessment",
  "exploitation_validation"
];`,
      highlights: [
        'Zero configuration required',
        'Self-adapting test strategies',
        'Continuous learning from scans',
        'Human-like decision making'
      ],
      visual: 'brain-network'
    },
    {
      id: 'natural-language',
      icon: MessageSquare,
      badge: 'NLP Interface',
      title: 'Natural Language Commands',
      description: 'Simply describe what you want to test in plain English. No complex configurations or technical syntax required.',
      codeExample: `User: "Test example.com for SQL injection vulnerabilities"

AI: I'll perform SQL injection testing on example.com.
    Starting with parameter discovery...
    
🔍 Found 23 input parameters
⚡ Testing injection vectors
✅ Detected 3 potential SQLi vulnerabilities
📊 Generating detailed report...`,
      highlights: [
        'Plain English commands',
        'Context-aware responses', 
        'Interactive conversations',
        'No technical expertise needed'
      ],
      visual: 'chat-interface'
    },
    {
      id: 'real-time',
      icon: Zap,
      badge: 'Live Updates',
      title: 'Real-Time Intelligence',
      description: 'Watch your security tests unfold in real-time with live progress updates, instant vulnerability alerts, and dynamic threat intelligence.',
      codeExample: `// Live scan updates via WebSocket
pentagent.onScanUpdate((update) => {
  console.log(\`\${update.tool}: \${update.status}\`);
  
  if (update.vulnerability) {
    alert(\`🚨 \${update.severity} vulnerability found!\`);
  }
});

// Real-time CVE intelligence
pentagent.onCveMatch((cve) => {
  dashboard.addThreat(cve.id, cve.severity);
});`,
      highlights: [
        'Live progress tracking',
        'Instant vulnerability alerts',
        'Real-time CVE matching',
        'Dynamic threat intelligence'
      ],
      visual: 'real-time-dashboard'
    },
    {
      id: 'reporting',
      icon: BarChart3,
      badge: 'Smart Reports',
      title: 'Executive & Technical Reports',
      description: 'Automatically generated reports tailored for different audiences - from executive summaries to detailed technical findings.',
      codeExample: `// Multi-format report generation
const reports = await pentagent.generateReports({
  executive: {
    format: "pdf",
    sections: ["summary", "risk_matrix", "recommendations"]
  },
  technical: {
    format: "json",
    sections: ["detailed_findings", "proof_of_concept", "remediation"]
  }
});`,
      highlights: [
        'Executive summaries',
        'Technical deep-dives',
        'Multiple export formats',
        'Compliance ready'
      ],
      visual: 'report-preview'
    }
  ];

  const FeatureVisual = ({ feature }) => {
    switch (feature.visual) {
      case 'brain-network':
        return (
          <div className="relative">
            <div className="w-full h-80 bg-obsidian-900 rounded-2xl border border-obsidian-700 p-8 flex items-center justify-center">
              <div className="relative">
                {/* Central brain node */}
                <div className="w-20 h-20 bg-gradient-to-br from-platinum-500 to-platinum-600 rounded-full flex items-center justify-center">
                  <Brain className="w-10 h-10 text-obsidian-950" />
                </div>
                
                {/* Surrounding nodes */}
                {[0, 1, 2, 3, 4, 5].map((i) => {
                  const angle = (i * 60) * Math.PI / 180;
                  const radius = 80;
                  const x = Math.cos(angle) * radius;
                  const y = Math.sin(angle) * radius;
                  
                  return (
                    <div
                      key={i}
                      className="absolute w-8 h-8 bg-obsidian-800 border-2 border-platinum-500/30 rounded-full animate-pulse"
                      style={{
                        left: `calc(50% + ${x}px - 16px)`,
                        top: `calc(50% + ${y}px - 16px)`,
                        animationDelay: `${i * 0.2}s`
                      }}
                    />
                  );
                })}
                
                {/* Connection lines */}
                <svg className="absolute inset-0 w-full h-full pointer-events-none">
                  {[0, 1, 2, 3, 4, 5].map((i) => {
                    const angle = (i * 60) * Math.PI / 180;
                    const radius = 80;
                    const x = Math.cos(angle) * radius;
                    const y = Math.sin(angle) * radius;
                    
                    return (
                      <line
                        key={i}
                        x1="50%"
                        y1="50%"
                        x2={`calc(50% + ${x}px)`}
                        y2={`calc(50% + ${y}px)`}
                        stroke="rgba(232,232,232,0.3)"
                        strokeWidth="2"
                        className="animate-pulse"
                        style={{ animationDelay: `${i * 0.3}s` }}
                      />
                    );
                  })}
                </svg>
              </div>
            </div>
          </div>
        );
        
      case 'chat-interface':
        return (
          <div className="w-full h-80 bg-obsidian-900 rounded-2xl border border-obsidian-700 p-6">
            <div className="space-y-4">
              <div className="flex justify-end">
                <div className="bg-platinum-500 text-obsidian-950 px-4 py-2 rounded-2xl rounded-br-sm max-w-xs">
                  <p className="text-sm font-medium">Test example.com for SQL injection</p>
                </div>
              </div>
              
              <div className="flex justify-start">
                <div className="bg-obsidian-850 border border-obsidian-700 px-4 py-3 rounded-2xl rounded-bl-sm max-w-sm">
                  <div className="flex items-center gap-2 mb-2">
                    <Brain className="w-4 h-4 text-platinum-500" />
                    <span className="text-xs text-text-tertiary">AI Agent</span>
                  </div>
                  <p className="text-sm text-text-primary mb-2">I'll test for SQL injection vulnerabilities:</p>
                  <div className="space-y-1 text-xs">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-platinum-500 rounded-full animate-pulse" />
                      <span className="text-text-secondary">Analyzing parameters...</span>
                    </div>
                    <div className="flex items-center gap-2 opacity-50">
                      <div className="w-2 h-2 bg-obsidian-600 rounded-full" />
                      <span className="text-text-tertiary">Testing injection vectors</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
        
      default:
        return (
          <div className="w-full h-80 bg-obsidian-900 rounded-2xl border border-obsidian-700 flex items-center justify-center">
            <div className="text-center text-text-tertiary">
              <feature.icon className="w-16 h-16 mx-auto mb-4 text-platinum-500" />
              <p>Interactive Demo</p>
            </div>
          </div>
        );
    }
  };

  return (
    <section className="py-24 bg-gradient-to-b from-obsidian-950 to-obsidian-900">
      <div className="max-w-7xl mx-auto px-8">
        
        {/* Section Header */}
        <div className="text-center mb-20">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-obsidian-850 border border-obsidian-700 rounded-full mb-6">
            <Cpu className="w-4 h-4 text-platinum-500" />
            <span className="text-sm text-text-secondary">Powered by Advanced AI</span>
          </div>
          
          <h2 className="text-4xl lg:text-5xl font-bold text-text-primary mb-6">
            Security Testing
            <span className="block text-transparent bg-gradient-to-r from-platinum-400 to-platinum-600 bg-clip-text">
              Reimagined
            </span>
          </h2>
          
          <p className="text-xl text-text-secondary max-w-3xl mx-auto">
            Experience the future of penetration testing with AI that thinks, adapts, and evolves 
            with every scan. No configuration, no complexity, just results.
          </p>
        </div>

        {/* Features List */}
        <div className="space-y-24">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            const isEven = index % 2 === 0;
            
            return (
              <div 
                key={feature.id}
                className={`grid lg:grid-cols-2 gap-12 items-center ${!isEven ? 'lg:grid-flow-col-dense' : ''}`}
              >
                {/* Content */}
                <div className={`space-y-6 ${!isEven ? 'lg:col-start-2' : ''}`}>
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 bg-obsidian-850 border border-obsidian-700 rounded-xl flex items-center justify-center">
                      <Icon className="w-6 h-6 text-platinum-500" />
                    </div>
                    <span className="px-3 py-1 bg-platinum-500/10 text-platinum-500 text-sm font-medium rounded-full border border-platinum-500/20">
                      {feature.badge}
                    </span>
                  </div>
                  
                  <div className="space-y-4">
                    <h3 className="text-3xl font-bold text-text-primary">
                      {feature.title}
                    </h3>
                    <p className="text-lg text-text-secondary leading-relaxed">
                      {feature.description}
                    </p>
                  </div>
                  
                  {/* Highlights */}
                  <div className="space-y-3">
                    {feature.highlights.map((highlight, idx) => (
                      <div key={idx} className="flex items-center gap-3">
                        <div className="w-1.5 h-1.5 bg-platinum-500 rounded-full" />
                        <span className="text-text-secondary">{highlight}</span>
                      </div>
                    ))}
                  </div>
                  
                  {/* Code Example */}
                  <div className="bg-obsidian-950 border border-obsidian-700 rounded-lg p-4 overflow-hidden">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="flex gap-1.5">
                        <div className="w-2.5 h-2.5 bg-rose-500 rounded-full" />
                        <div className="w-2.5 h-2.5 bg-platinum-500 rounded-full" />
                        <div className="w-2.5 h-2.5 bg-green-500 rounded-full" />
                      </div>
                      <span className="text-xs text-text-tertiary ml-2">example.js</span>
                    </div>
                    <pre className="text-sm text-text-primary overflow-x-auto">
                      <code>{feature.codeExample}</code>
                    </pre>
                  </div>
                  
                  <Button variant="secondary" className="group">
                    Learn More
                    <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                  </Button>
                </div>
                
                {/* Visual */}
                <div className={!isEven ? 'lg:col-start-1' : ''}>
                  <FeatureVisual feature={feature} />
                </div>
              </div>
            );
          })}
        </div>
        
        {/* Bottom CTA */}
        <div className="mt-20 text-center">
          <div className="bg-obsidian-900 border border-obsidian-700 rounded-2xl p-8 max-w-2xl mx-auto">
            <h3 className="text-2xl font-bold text-text-primary mb-4">
              Ready to Transform Your Security Testing?
            </h3>
            <p className="text-text-secondary mb-6">
              Join thousands of security teams already using AI-powered penetration testing.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button variant="primary" size="lg">Start Free Trial</Button>
              <Button variant="ghost" size="lg">Schedule Demo</Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default FeaturesSection;
