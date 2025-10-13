import React from 'react';
import { Play, CheckCircle } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Button from '../../common/Button';

const DemoSection = () => {
  const navigate = useNavigate();

  const steps = [
    {
      number: '01',
      title: 'Hedef Belirle',
      description: 'Test etmek istediğiniz URL, domain veya IP adresini girin.'
    },
    {
      number: '02',
      title: 'AI Analiz Eder',
      description: 'Otonom AI ajanımız hedefi analiz eder ve test stratejisini belirler.'
    },
    {
      number: '03',
      title: 'Sonuçları Al',
      description: 'Detaylı zafiyet raporu ve önerilerle güvenlik açıklarını kapatın.'
    }
  ];

  return (
    <section id="demo" className="py-20 bg-obsidian-900 relative overflow-hidden">
      {/* Background Gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-obsidian-950 via-obsidian-900 to-obsidian-950" />
      
      <div className="max-w-7xl mx-auto px-8 relative z-10">
        {/* Section Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-obsidian-950 border border-purple-900/30 rounded-full mb-6">
            <Play className="w-3 h-3 text-purple-500" />
            <span className="text-xs text-text-secondary">Nasıl Çalışır</span>
          </div>
          
          <h2 className="text-3xl lg:text-4xl font-bold text-text-primary mb-4">
            3 Adımda
            <span className="block text-transparent bg-gradient-to-r from-purple-400 to-purple-600 bg-clip-text">
              Güvenlik Testi
            </span>
          </h2>
          
          <p className="text-base text-text-secondary max-w-2xl mx-auto">
            Pentagent AI ile güvenlik testleri hiç bu kadar kolay olmamıştı.
          </p>
        </div>

        {/* Steps */}
        <div className="grid md:grid-cols-3 gap-8 mb-12">
          {steps.map((step, index) => (
            <div key={index} className="relative">
              {/* Connector Line */}
              {index < steps.length - 1 && (
                <div className="hidden md:block absolute top-12 left-1/2 w-full h-0.5 bg-gradient-to-r from-purple-500/50 to-transparent" />
              )}
              
              <div className="relative bg-obsidian-950/50 backdrop-blur-xl border border-purple-900/30 rounded-xl p-6 hover:border-purple-500/50 transition-all">
                {/* Step Number */}
                <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg flex items-center justify-center mb-4 font-bold text-white text-sm">
                  {step.number}
                </div>
                
                {/* Content */}
                <h3 className="text-base font-semibold text-text-primary mb-2">
                  {step.title}
                </h3>
                <p className="text-xs text-text-secondary leading-relaxed">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* CTA */}
        <div className="text-center">
          <Button
            variant="primary"
            size="lg"
            className="bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 text-sm"
            onClick={() => navigate('/register')}
          >
            <Play className="w-4 h-4 mr-2" />
            Hemen Başla
          </Button>
        </div>
      </div>
    </section>
  );
};

export default DemoSection;
