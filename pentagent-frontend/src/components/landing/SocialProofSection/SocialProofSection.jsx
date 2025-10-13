import React from 'react';
import { TrendingUp, Users, Shield, Zap } from 'lucide-react';

const SocialProofSection = () => {
  const stats = [
    {
      icon: Users,
      number: '2,500+',
      label: 'Güvenlik Ekibi',
      sublabel: 'Pentagent\'e güveniyor'
    },
    {
      icon: Shield,
      number: '500K+',
      label: 'Zafiyet',
      sublabel: 'tespit edildi ve düzeltildi'
    },
    {
      icon: TrendingUp,
      number: '99.9%',
      label: 'Çalışma Süresi',
      sublabel: 'garantili SLA'
    },
    {
      icon: Zap,
      number: '< 2dk',
      label: 'Ortalama Tarama',
      sublabel: 'tamamlanma süresi'
    }
  ];

  return (
    <section className="py-16 bg-obsidian-900 relative overflow-hidden">
      {/* Background Gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-obsidian-950 via-obsidian-900 to-obsidian-950" />
      
      <div className="max-w-7xl mx-auto px-8 relative z-10">
        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat, index) => {
            const Icon = stat.icon;
            return (
              <div
                key={index}
                className="bg-obsidian-950/50 backdrop-blur-xl border border-purple-900/30 rounded-xl p-6 hover:border-purple-500/50 transition-all group"
              >
                <Icon className="w-6 h-6 text-purple-500 mb-3 group-hover:scale-110 transition-transform" />
                <div className="text-2xl font-bold text-text-primary mb-1">
                  {stat.number}
                </div>
                <div className="text-xs font-medium text-text-secondary mb-1">
                  {stat.label}
                </div>
                <div className="text-xs text-text-tertiary">
                  {stat.sublabel}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default SocialProofSection;
