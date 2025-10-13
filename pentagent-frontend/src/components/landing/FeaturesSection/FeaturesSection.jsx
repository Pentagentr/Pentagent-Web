import React from 'react';
import { Brain, Zap, Shield, BarChart3, MessageSquare, Eye } from 'lucide-react';

const FeaturesSection = () => {
  const features = [
    {
      icon: Brain,
      title: 'Otonom Güvenlik Testi',
      description: 'AI ajanımız kıdemli bir pentester gibi düşünür, hedef keşfine göre yaklaşımını adapte eder.'
    },
    {
      icon: MessageSquare,
      title: 'Doğal Dil Komutları',
      description: 'Test etmek istediğinizi basitçe Türkçe olarak tanımlayın. Karmaşık konfigürasyon gerekmez.'
    },
    {
      icon: Zap,
      title: 'Gerçek Zamanlı İstihbarat',
      description: 'Güvenlik testlerinizi canlı ilerleme güncellemeleri ve anlık zafiyet uyarılarıyla izleyin.'
    },
    {
      icon: BarChart3,
      title: 'Akıllı Raporlar',
      description: 'Otomatik oluşturulan, kapsamlı güvenlik raporları ile bulgularınızı detaylı inceleyin.'
    },
    {
      icon: Shield,
      title: 'OWASP Top 10',
      description: 'Tüm OWASP Top 10 zafiyetlerini otomatik olarak tespit edin ve raporlayın.'
    },
    {
      icon: Eye,
      title: 'Sürekli İzleme',
      description: 'Hedeflerinizi 7/24 izleyin, yeni zafiyetler ortaya çıktığında anında haberdar olun.'
    }
  ];

  return (
    <section id="features" className="py-20 bg-obsidian-950 relative overflow-hidden">
      {/* Background Grid */}
      <div 
        className="absolute inset-0 opacity-10"
        style={{
          backgroundImage: `
            linear-gradient(rgba(147,51,234,0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(147,51,234,0.1) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }}
      />

      <div className="max-w-7xl mx-auto px-8 relative z-10">
        {/* Section Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-obsidian-900 border border-purple-900/30 rounded-full mb-6">
            <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse" />
            <span className="text-xs text-text-secondary">Özellikler</span>
          </div>
          
          <h2 className="text-3xl lg:text-4xl font-bold text-text-primary mb-4">
            Güvenlik Testlerini
            <span className="block text-transparent bg-gradient-to-r from-purple-400 to-purple-600 bg-clip-text">
              Yeniden Tanımlıyoruz
            </span>
          </h2>
          
          <p className="text-base text-text-secondary max-w-2xl mx-auto">
            AI destekli otonom penetrasyon testi ile güvenlik açıklarını daha hızlı ve etkili bir şekilde tespit edin.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <div
                key={index}
                className="group relative bg-obsidian-900/50 backdrop-blur-xl border border-purple-900/30 rounded-xl p-6 hover:border-purple-500/50 transition-all duration-300"
              >
                {/* Icon */}
                <div className="w-10 h-10 bg-gradient-to-br from-purple-500/20 to-purple-600/20 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                  <Icon className="w-5 h-5 text-purple-500" />
                </div>

                {/* Content */}
                <h3 className="text-base font-semibold text-text-primary mb-2">
                  {feature.title}
                </h3>
                <p className="text-xs text-text-secondary leading-relaxed">
                  {feature.description}
                </p>

                {/* Hover Effect */}
                <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity rounded-xl" />
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default FeaturesSection;
