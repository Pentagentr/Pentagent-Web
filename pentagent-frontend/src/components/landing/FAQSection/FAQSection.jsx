import React, { useState } from 'react';
import { ChevronDown, HelpCircle } from 'lucide-react';

const FAQSection = () => {
  const [openIndex, setOpenIndex] = useState(null);

  const faqs = [
    {
      question: 'Pentagent AI nedir?',
      answer: 'Pentagent AI, yapay zeka destekli otonom penetrasyon testi platformudur. Hedeflerinizi otomatik olarak analiz eder, zafiyetleri tespit eder ve detaylı raporlar sunar.'
    },
    {
      question: 'Hangi zafiyetleri tespit edebilir?',
      answer: 'OWASP Top 10 dahil SQL Injection, XSS, CSRF, güvensiz yapılandırmalar, hassas veri sızıntıları ve daha fazlasını tespit edebilir.'
    },
    {
      question: 'Ücretsiz deneme süresi var mı?',
      answer: 'Evet! 14 günlük ücretsiz deneme süresi sunuyoruz. Kredi kartı bilgisi gerektirmez, istediğiniz zaman iptal edebilirsiniz.'
    },
    {
      question: 'Teknik bilgi gerekli mi?',
      answer: 'Hayır! Doğal dil komutları ile sistemi kullanabilirsiniz. Sadece test etmek istediğiniz hedefi belirtin, gerisini AI halleder.'
    },
    {
      question: 'Sonuçlar ne kadar sürede gelir?',
      answer: 'Hedefin büyüklüğüne göre değişir. Ortalama bir web sitesi için 2-5 dakika içinde ilk sonuçları alırsınız.'
    },
    {
      question: 'Verilerim güvende mi?',
      answer: 'Evet! Tüm verileriniz şifreli olarak saklanır ve SOC 2 uyumlu altyapımızda güvende tutulur. Verilerinizi asla üçüncü taraflarla paylaşmayız.'
    }
  ];

  return (
    <section id="faq" className="py-20 bg-obsidian-950 relative overflow-hidden">
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

      <div className="max-w-4xl mx-auto px-8 relative z-10">
        {/* Section Header */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-obsidian-900 border border-purple-900/30 rounded-full mb-6">
            <HelpCircle className="w-3 h-3 text-purple-500" />
            <span className="text-xs text-text-secondary">Sık Sorulan Sorular</span>
          </div>
          
          <h2 className="text-3xl lg:text-4xl font-bold text-text-primary mb-4">
            Merak Ettikleriniz
          </h2>
          
          <p className="text-base text-text-secondary">
            Pentagent AI hakkında en çok sorulan sorular ve cevapları.
          </p>
        </div>

        {/* FAQ Items */}
        <div className="space-y-4">
          {faqs.map((faq, index) => (
              <div 
                key={index}
              className="bg-obsidian-900/50 backdrop-blur-xl border border-purple-900/30 rounded-xl overflow-hidden hover:border-purple-500/50 transition-all"
              >
                <button
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
                className="w-full flex items-center justify-between p-6 text-left"
              >
                <span className="text-sm font-semibold text-text-primary pr-4">
                  {faq.question}
                      </span>
                <ChevronDown
                  className={`w-5 h-5 text-purple-500 flex-shrink-0 transition-transform ${
                    openIndex === index ? 'rotate-180' : ''
                  }`}
                />
                </button>
                
              {openIndex === index && (
                <div className="px-6 pb-6">
                  <p className="text-xs text-text-secondary leading-relaxed">
                      {faq.answer}
                    </p>
          </div>
        )}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default FAQSection;
