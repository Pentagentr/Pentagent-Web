import React from 'react';
import { TrendingUp, Users, Shield, Zap } from 'lucide-react';

const SocialProofSection = () => {
  // Simulated company logos (you can replace with real logos later)
  const companies = [
    { name: 'TechCorp', logo: 'TC' },
    { name: 'SecureBank', logo: 'SB' },
    { name: 'DataFlow', logo: 'DF' },
    { name: 'CyberGuard', logo: 'CG' },
    { name: 'CloudSecure', logo: 'CS' },
    { name: 'NetShield', logo: 'NS' },
    { name: 'InfoSafe', logo: 'IS' },
    { name: 'TechGuard', logo: 'TG' },
  ];

  const stats = [
    {
      icon: Users,
      number: '2,500+',
      label: 'Security Teams',
      sublabel: 'trust Pentagent daily'
    },
    {
      icon: Shield,
      number: '500K+',
      label: 'Vulnerabilities',
      sublabel: 'detected and fixed'
    },
    {
      icon: TrendingUp,
      number: '99.9%',
      label: 'Uptime',
      sublabel: 'guaranteed SLA'
    },
    {
      icon: Zap,
      number: '< 2min',
      label: 'Average Scan',
      sublabel: 'completion time'
    },
  ];

  const CompanyLogo = ({ company }) => (
    <div className="flex-shrink-0 flex items-center justify-center w-24 h-16 bg-obsidian-850/50 border border-obsidian-700/30 rounded-lg group hover:border-platinum-500/30 transition-all duration-300">
      <div className="text-center">
        <div className="w-8 h-8 bg-gradient-to-br from-platinum-500/20 to-platinum-600/20 rounded-full flex items-center justify-center mx-auto mb-1">
          <span className="text-xs font-bold text-platinum-500">{company.logo}</span>
        </div>
        <span className="text-xs text-text-tertiary group-hover:text-text-secondary transition-colors">
          {company.name}
        </span>
      </div>
    </div>
  );

  return (
    <section className="relative py-24 bg-obsidian-950">
      <div className="max-w-7xl mx-auto px-8">
        
        {/* Section Header */}
        <div className="text-center mb-16">
          <p className="text-text-secondary text-lg mb-4">
            Trusted by security teams at leading organizations
          </p>
        </div>

        {/* Company Logos - Animated Marquee */}
        <div className="relative mb-20 overflow-hidden">
          <div className="flex animate-marquee gap-8 py-4">
            {[...companies, ...companies].map((company, index) => (
              <CompanyLogo key={`${company.name}-${index}`} company={company} />
            ))}
          </div>
          
          {/* Fade edges */}
          <div className="absolute left-0 top-0 w-20 h-full bg-gradient-to-r from-obsidian-950 to-transparent pointer-events-none" />
          <div className="absolute right-0 top-0 w-20 h-full bg-gradient-to-l from-obsidian-950 to-transparent pointer-events-none" />
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
          {stats.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <div 
                key={index} 
                className="text-center group"
              >
                <div className="inline-flex items-center justify-center w-16 h-16 bg-obsidian-900 border border-obsidian-700 rounded-2xl mb-4 group-hover:border-platinum-500/30 transition-all duration-300">
                  <Icon className="w-7 h-7 text-platinum-500" />
                </div>
                
                <div className="space-y-1">
                  <div className="text-3xl font-bold text-text-primary">
                    {stat.number}
                  </div>
                  <div className="text-lg font-medium text-text-secondary">
                    {stat.label}
                  </div>
                  <div className="text-sm text-text-tertiary">
                    {stat.sublabel}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Bottom Quote */}
        <div className="mt-20 text-center">
          <blockquote className="text-xl text-text-primary italic max-w-3xl mx-auto">
            "Pentagent reduced our security testing time by 75% while increasing vulnerability detection accuracy. 
            It's like having a senior pentester working 24/7."
          </blockquote>
          <div className="mt-6 flex items-center justify-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-br from-platinum-500 to-platinum-600 rounded-full flex items-center justify-center">
              <span className="text-sm font-bold text-obsidian-950">MJ</span>
            </div>
            <div className="text-left">
              <div className="font-semibold text-text-primary">Michael Johnson</div>
              <div className="text-text-tertiary text-sm">CISO, TechCorp</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default SocialProofSection;
