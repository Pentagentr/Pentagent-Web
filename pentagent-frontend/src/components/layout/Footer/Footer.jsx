import React, { useState } from 'react';
import { 
  ArrowUp, 
  Mail, 
  Github, 
  Twitter, 
  Linkedin, 
  Youtube,
  Shield,
  Zap,
  Book,
  MessageSquare
} from 'lucide-react';
import Logo from '../../common/Logo';
import Button from '../../common/Button';
import Input from '../../common/Input';

const Footer = () => {
  const [email, setEmail] = useState('');
  const [subscribed, setSubscribed] = useState(false);

  const handleNewsletterSubmit = (e) => {
    e.preventDefault();
    if (email) {
      setSubscribed(true);
      setEmail('');
      setTimeout(() => setSubscribed(false), 3000);
    }
  };

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const footerLinks = {
    product: {
      title: 'Product',
      links: [
        { label: 'Features', href: '#features' },
        { label: 'Pricing', href: '#pricing' },
        { label: 'Security', href: '/security' },
        { label: 'Integrations', href: '/integrations' },
        { label: 'API Documentation', href: '/docs/api' },
        { label: 'Changelog', href: '/changelog' }
      ]
    },
    resources: {
      title: 'Resources',
      links: [
        { label: 'Documentation', href: '/docs' },
        { label: 'Tutorials', href: '/tutorials' },
        { label: 'Blog', href: '/blog' },
        { label: 'Case Studies', href: '/case-studies' },
        { label: 'Webinars', href: '/webinars' },
        { label: 'Security Research', href: '/research' }
      ]
    },
    support: {
      title: 'Support',
      links: [
        { label: 'Help Center', href: '/help' },
        { label: 'Contact Support', href: '/support' },
        { label: 'Community Forum', href: '/community' },
        { label: 'Status Page', href: '/status' },
        { label: 'Bug Reports', href: '/bugs' },
        { label: 'Feature Requests', href: '/features' }
      ]
    },
    company: {
      title: 'Company',
      links: [
        { label: 'About Us', href: '/about' },
        { label: 'Careers', href: '/careers' },
        { label: 'Press Kit', href: '/press' },
        { label: 'Partners', href: '/partners' },
        { label: 'Contact', href: '/contact' },
        { label: 'News', href: '/news' }
      ]
    }
  };

  const socialLinks = [
    { icon: Github, href: 'https://github.com/pentagent', label: 'GitHub' },
    { icon: Twitter, href: 'https://twitter.com/pentagent', label: 'Twitter' },
    { icon: Linkedin, href: 'https://linkedin.com/company/pentagent', label: 'LinkedIn' },
    { icon: Youtube, href: 'https://youtube.com/@pentagent', label: 'YouTube' }
  ];

  const legalLinks = [
    { label: 'Privacy Policy', href: '/privacy' },
    { label: 'Terms of Service', href: '/terms' },
    { label: 'Cookie Policy', href: '/cookies' },
    { label: 'DPA', href: '/dpa' },
    { label: 'Security', href: '/security' }
  ];

  return (
    <footer className="relative bg-obsidian-950 border-t border-obsidian-700">
      {/* Back to top button */}
      <button
        onClick={scrollToTop}
        className="absolute -top-6 left-1/2 -translate-x-1/2 w-12 h-12 bg-platinum-500 hover:bg-platinum-600 rounded-full flex items-center justify-center text-obsidian-950 transition-all duration-300 hover:scale-110 hover:shadow-lg hover:shadow-platinum-500/25"
      >
        <ArrowUp className="w-5 h-5" />
      </button>

      <div className="max-w-7xl mx-auto px-8 pt-16 pb-8">
        {/* Main Footer Content */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mb-12">
          
          {/* Company Info & Newsletter */}
          <div className="lg:col-span-4 space-y-8">
            <div>
              <Logo variant="full" size="lg" className="mb-4" />
              <p className="text-text-secondary leading-relaxed max-w-sm">
                Autonomous AI-powered penetration testing platform that thinks, adapts, 
                and protects your applications 24/7.
              </p>
            </div>

            {/* Newsletter Signup */}
            <div>
              <h4 className="text-lg font-semibold text-text-primary mb-4">
                Stay Updated
              </h4>
              <p className="text-text-secondary text-sm mb-4">
                Get the latest security insights, product updates, and industry news.
              </p>
              
              {subscribed ? (
                <div className="flex items-center gap-3 p-4 bg-success/10 border border-success/30 rounded-lg">
                  <div className="w-6 h-6 bg-success rounded-full flex items-center justify-center">
                    <span className="text-xs text-obsidian-950">✓</span>
                  </div>
                  <span className="text-success font-medium">
                    Thanks for subscribing!
                  </span>
                </div>
              ) : (
                <form onSubmit={handleNewsletterSubmit} className="flex gap-2">
                  <Input
                    type="email"
                    placeholder="Enter your email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    icon={Mail}
                    className="flex-1"
                  />
                  <Button variant="primary" type="submit">
                    Subscribe
                  </Button>
                </form>
              )}
            </div>

            {/* Trust Badges */}
            <div className="flex items-center gap-4 pt-4">
              <div className="flex items-center gap-2 px-3 py-2 bg-obsidian-900 border border-obsidian-700 rounded-lg">
                <Shield className="w-4 h-4 text-platinum-500" />
                <span className="text-xs text-text-secondary">SOC 2 Type II</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-2 bg-obsidian-900 border border-obsidian-700 rounded-lg">
                <Zap className="w-4 h-4 text-platinum-500" />
                <span className="text-xs text-text-secondary">99.9% Uptime</span>
              </div>
            </div>
          </div>

          {/* Links Columns */}
          <div className="lg:col-span-8 grid grid-cols-2 lg:grid-cols-4 gap-8">
            {Object.entries(footerLinks).map(([key, section]) => (
              <div key={key}>
                <h4 className="text-lg font-semibold text-text-primary mb-4">
                  {section.title}
                </h4>
                <ul className="space-y-3">
                  {section.links.map((link, index) => (
                    <li key={index}>
                      <a
                        href={link.href}
                        className="text-text-secondary hover:text-platinum-500 transition-colors text-sm"
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

        {/* Social Links & Contact */}
        <div className="flex flex-col lg:flex-row items-center justify-between py-8 border-t border-obsidian-700">
          <div className="flex items-center gap-6 mb-6 lg:mb-0">
            <span className="text-text-secondary font-medium">Follow us:</span>
            {socialLinks.map((social, index) => {
              const Icon = social.icon;
              return (
                <a
                  key={index}
                  href={social.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-10 h-10 bg-obsidian-900 border border-obsidian-700 rounded-lg flex items-center justify-center text-text-secondary hover:text-platinum-500 hover:border-platinum-500/30 hover:bg-platinum-500/5 transition-all duration-300"
                  aria-label={social.label}
                >
                  <Icon className="w-4 h-4" />
                </a>
              );
            })}
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-success rounded-full animate-pulse" />
              <span className="text-text-tertiary text-sm">All systems operational</span>
            </div>
            <a 
              href="/status" 
              className="text-platinum-500 hover:text-platinum-400 text-sm transition-colors"
            >
              Status →
            </a>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="flex flex-col lg:flex-row items-center justify-between py-6 border-t border-obsidian-700">
          <div className="flex flex-wrap items-center gap-6 mb-4 lg:mb-0">
            <span className="text-text-tertiary text-sm">
              © 2025 Pentagent. All rights reserved.
            </span>
            <div className="flex items-center gap-4">
              {legalLinks.map((link, index) => (
                <a
                  key={index}
                  href={link.href}
                  className="text-text-tertiary hover:text-text-secondary text-sm transition-colors"
                >
                  {link.label}
                </a>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-4 text-sm text-text-tertiary">
            <span>Made with ❤️ for security teams worldwide</span>
          </div>
        </div>

        {/* Additional Info Bar */}
        <div className="mt-6 p-4 bg-obsidian-900 border border-obsidian-700 rounded-lg">
          <div className="flex flex-col lg:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <Book className="w-4 h-4 text-platinum-500" />
                <span className="text-sm text-text-secondary">
                  Read our latest security research
                </span>
              </div>
              <div className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4 text-platinum-500" />
                <span className="text-sm text-text-secondary">
                  Join 10k+ security professionals
                </span>
              </div>
            </div>
            
            <div className="flex gap-3">
              <Button variant="ghost" size="sm">
                Community
              </Button>
              <Button variant="secondary" size="sm">
                Get Started
              </Button>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
