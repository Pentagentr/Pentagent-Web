import React from 'react';
import { ArrowUp, Github, Twitter, Linkedin, Shield } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Logo from '../../common/Logo';

const Footer = () => {
  const navigate = useNavigate();

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const footerLinks = {
    product: {
      title: 'Ürün',
      links: [
        { label: 'Özellikler', href: '#features' },
        { label: 'Demo', href: '#demo' },
        { label: 'Güvenlik', href: '#' }
      ]
    },
    support: {
      title: 'Destek',
      links: [
        { label: 'Yardım Merkezi', href: '#' },
        { label: 'İletişim', href: '#' },
        { label: 'SSS', href: '#faq' }
      ]
    },
    legal: {
      title: 'Yasal',
      links: [
        { label: 'Gizlilik Politikası', href: '#' },
        { label: 'Kullanım Şartları', href: '#' },
        { label: 'Çerez Politikası', href: '#' }
      ]
    }
  };

  const socialLinks = [
    { icon: Github, href: 'https://github.com/pentagent', label: 'GitHub' },
    { icon: Twitter, href: 'https://twitter.com/pentagent', label: 'Twitter' },
    { icon: Linkedin, href: 'https://linkedin.com/company/pentagent', label: 'LinkedIn' }
  ];

  return (
    <footer className="relative bg-obsidian-950 border-t border-purple-900/30">
      {/* Back to top button */}
      <button
        onClick={scrollToTop}
        className="absolute -top-6 left-1/2 -translate-x-1/2 w-12 h-12 bg-gradient-to-r from-purple-600 to-purple-700 hover:from-purple-700 hover:to-purple-800 rounded-full flex items-center justify-center text-white transition-all duration-300 hover:scale-110 shadow-lg shadow-purple-500/25"
      >
        <ArrowUp className="w-5 h-5" />
      </button>

      <div className="max-w-7xl mx-auto px-8 pt-16 pb-8">
        {/* Main Footer Content */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mb-12">
          
          {/* Company Info */}
          <div className="lg:col-span-5 space-y-6">
            <div>
              <Logo variant="full" size="md" className="mb-4" />
              <p className="text-xs text-text-secondary leading-relaxed max-w-sm">
                Yapay zeka destekli otonom penetrasyon testi platformu. 
                Uygulamalarınızı 7/24 düşünen, adapte olan ve koruyan güvenlik çözümü.
              </p>
            </div>

            {/* Trust Badge */}
            <div className="flex items-center gap-2 px-3 py-2 bg-obsidian-900 border border-purple-900/30 rounded-lg w-fit">
              <Shield className="w-4 h-4 text-purple-500" />
              <span className="text-xs text-text-secondary">SOC 2 Uyumlu</span>
            </div>
          </div>

          {/* Links Columns */}
          <div className="lg:col-span-7 grid grid-cols-3 gap-8">
            {Object.entries(footerLinks).map(([key, section]) => (
              <div key={key}>
                <h4 className="text-sm font-semibold text-text-primary mb-4">
                  {section.title}
                </h4>
                <ul className="space-y-2">
                  {section.links.map((link, index) => (
                    <li key={index}>
                      <a
                        href={link.href}
                        className="text-xs text-text-secondary hover:text-purple-400 transition-colors"
                      >
                        {link.label}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* Social Links */}
        <div className="flex flex-col lg:flex-row items-center justify-between py-6 border-t border-purple-900/30">
          <div className="flex items-center gap-4 mb-6 lg:mb-0">
            <span className="text-xs text-text-secondary">Bizi takip edin:</span>
            {socialLinks.map((social, index) => {
              const Icon = social.icon;
              return (
                <a
                  key={index}
                  href={social.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-9 h-9 bg-obsidian-900 border border-purple-900/30 rounded-lg flex items-center justify-center text-text-secondary hover:text-purple-400 hover:border-purple-500/50 transition-all duration-300"
                  aria-label={social.label}
                >
                  <Icon className="w-4 h-4" />
                </a>
              );
            })}
          </div>

          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-xs text-text-tertiary">Tüm sistemler çalışıyor</span>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="flex flex-col lg:flex-row items-center justify-between py-6 border-t border-purple-900/30">
          <span className="text-xs text-text-tertiary mb-4 lg:mb-0">
            © 2025 Pentagent. Tüm hakları saklıdır.
          </span>

          <span className="text-xs text-text-tertiary">
            Dünya çapındaki güvenlik ekipleri için ❤️ ile yapıldı
          </span>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
