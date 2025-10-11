import React, { useState } from 'react';
import { 
  Plus, 
  Minus, 
  Search, 
  HelpCircle, 
  Shield, 
  Zap, 
  CreditCard,
  Settings 
} from 'lucide-react';
import Button from '../../common/Button';

const FAQSection = () => {
  const [activeCategory, setActiveCategory] = useState('general');
  const [openItems, setOpenItems] = useState(new Set(['general-0'])); // First item open by default
  const [searchTerm, setSearchTerm] = useState('');

  const categories = [
    { id: 'general', label: 'General', icon: HelpCircle },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'features', label: 'Features', icon: Zap },
    { id: 'pricing', label: 'Pricing', icon: CreditCard },
    { id: 'technical', label: 'Technical', icon: Settings },
  ];

  const faqs = {
    general: [
      {
        question: "What is Pentagent and how does it work?",
        answer: "Pentagent is an AI-powered autonomous penetration testing platform that simulates the thinking process of senior security professionals. It uses advanced machine learning algorithms to automatically discover, test, and validate security vulnerabilities in your applications and infrastructure without requiring manual configuration.",
        popular: true
      },
      {
        question: "Do I need security expertise to use Pentagent?",
        answer: "No! Pentagent is designed for users of all technical levels. You can simply describe what you want to test in plain English, and our AI will handle the complex technical details. However, having security knowledge helps you better understand and act on the results.",
        popular: true
      },
      {
        question: "How accurate are Pentagent's vulnerability findings?",
        answer: "Pentagent maintains a 99.2% accuracy rate with less than 1% false positives. Our AI validates each vulnerability finding through multiple verification methods and provides proof-of-concept demonstrations where applicable."
      },
      {
        question: "What types of applications can Pentagent test?",
        answer: "Pentagent can test web applications, APIs, mobile app backends, cloud infrastructure, and network services. It supports testing across various technologies including modern web frameworks, databases, and cloud platforms."
      }
    ],
    security: [
      {
        question: "Is my data safe with Pentagent?",
        answer: "Absolutely. Pentagent operates on a zero-knowledge architecture - we never store your application data, source code, or sensitive information. All scans are performed in isolated environments with enterprise-grade encryption. We are SOC 2 Type II certified and GDPR compliant.",
        popular: true
      },
      {
        question: "Can Pentagent damage my applications during testing?",
        answer: "No. Pentagent is designed to be completely non-destructive. It performs read-only reconnaissance and safe vulnerability validation techniques that won't impact your application's availability or data integrity."
      },
      {
        question: "How does Pentagent handle authentication and authorization?",
        answer: "Pentagent can work with various authentication methods including OAuth, JWT tokens, API keys, and session-based authentication. It can automatically maintain authentication state throughout the testing process and test both authenticated and unauthenticated attack vectors."
      },
      {
        question: "What compliance standards does Pentagent help with?",
        answer: "Pentagent helps organizations meet requirements for PCI DSS, OWASP Top 10, NIST Cybersecurity Framework, ISO 27001, and other major compliance standards. Our reports include compliance mapping and remediation guidance."
      }
    ],
    features: [
      {
        question: "What makes Pentagent's AI different from traditional scanners?",
        answer: "Unlike traditional scanners that follow predetermined patterns, Pentagent's AI dynamically adapts its testing strategy based on the target's characteristics. It can chain vulnerabilities, understand business logic, and make contextual decisions like a human pentester.",
        popular: true
      },
      {
        question: "Can I integrate Pentagent with my CI/CD pipeline?",
        answer: "Yes! Pentagent offers native integrations with popular CI/CD platforms like Jenkins, GitLab CI, GitHub Actions, and Azure DevOps. You can automatically trigger security tests on code commits, deployments, or scheduled intervals."
      },
      {
        question: "How does the natural language interface work?",
        answer: "Simply describe your testing goals in plain English, such as 'Test my login system for authentication bypasses' or 'Scan my API for injection vulnerabilities.' Our NLP engine translates these requests into comprehensive testing strategies."
      },
      {
        question: "What reporting formats are available?",
        answer: "Pentagent generates multiple report formats including executive summaries (PDF), detailed technical reports (JSON/XML), compliance reports, and interactive dashboards. Reports can be customized based on your audience and requirements."
      }
    ],
    pricing: [
      {
        question: "How does Pentagent pricing work?",
        answer: "Pentagent offers flexible pricing based on your testing needs. Our plans include a certain number of scan credits per month, with additional credits available as needed. We offer startup discounts and volume pricing for enterprises.",
        popular: true
      },
      {
        question: "Is there a free trial available?",
        answer: "Yes! We offer a 14-day free trial with full access to all features and 50 scan credits. No credit card required to start, and you can upgrade anytime during or after the trial period."
      },
      {
        question: "What's included in the scan credits?",
        answer: "Each scan credit covers a complete security assessment of one target (domain, subdomain, or API endpoint). Credits include unlimited vulnerability testing, report generation, and access to our AI chat interface for that target."
      },
      {
        question: "Do you offer custom pricing for enterprises?",
        answer: "Yes, we provide custom pricing for organizations with high-volume scanning needs, on-premise deployment requirements, or specific compliance requirements. Contact our sales team for a personalized quote."
      }
    ],
    technical: [
      {
        question: "What technologies and vulnerabilities does Pentagent detect?",
        answer: "Pentagent covers the OWASP Top 10, plus advanced vulnerability classes including business logic flaws, race conditions, authentication bypasses, and more. It supports testing of modern frameworks, APIs, SPAs, and cloud-native applications.",
        popular: true
      },
      {
        question: "How fast are Pentagent's scans?",
        answer: "Scan times vary based on target complexity, but most web application scans complete within 2-5 minutes. API scans typically finish in under 2 minutes, while comprehensive infrastructure scans may take 10-15 minutes."
      },
      {
        question: "Can I use Pentagent for internal/private applications?",
        answer: "Yes! Pentagent can test internal applications through our secure connector or VPN integration. We also offer on-premise deployment options for organizations with strict security requirements."
      },
      {
        question: "What are the API rate limits and scanning limits?",
        answer: "Pentagent intelligently manages scan rates to avoid overwhelming your applications. Default rates are 10 requests/second, but this can be adjusted based on your infrastructure capabilities and testing requirements."
      }
    ]
  };

  const toggleItem = (categoryId, index) => {
    const itemId = `${categoryId}-${index}`;
    const newOpenItems = new Set(openItems);
    
    if (newOpenItems.has(itemId)) {
      newOpenItems.delete(itemId);
    } else {
      newOpenItems.add(itemId);
    }
    
    setOpenItems(newOpenItems);
  };

  const filteredFAQs = searchTerm 
    ? Object.entries(faqs).reduce((acc, [category, questions]) => {
        const filtered = questions.filter(q => 
          q.question.toLowerCase().includes(searchTerm.toLowerCase()) ||
          q.answer.toLowerCase().includes(searchTerm.toLowerCase())
        );
        if (filtered.length > 0) {
          acc[category] = filtered;
        }
        return acc;
      }, {})
    : faqs;

  return (
    <section className="py-24 bg-gradient-to-b from-obsidian-900 to-obsidian-950">
      <div className="max-w-6xl mx-auto px-8">
        
        {/* Section Header */}
        <div className="text-center mb-16">
          <h2 className="text-4xl lg:text-5xl font-bold text-text-primary mb-6">
            Frequently Asked
            <span className="block text-transparent bg-gradient-to-r from-platinum-400 to-platinum-600 bg-clip-text">
              Questions
            </span>
          </h2>
          <p className="text-xl text-text-secondary max-w-3xl mx-auto mb-8">
            Everything you need to know about Pentagent's AI-powered security testing platform.
          </p>
          
          {/* Search */}
          <div className="relative max-w-md mx-auto">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-tertiary" />
            <input
              type="text"
              placeholder="Search FAQ..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full h-12 pl-12 pr-4 bg-obsidian-900 border border-obsidian-700 rounded-xl text-text-primary placeholder:text-text-tertiary focus:outline-none focus:border-platinum-500 focus:ring-2 focus:ring-platinum-500/10 transition-all"
            />
          </div>
        </div>

        {/* Category Tabs */}
        <div className="flex flex-wrap justify-center gap-2 mb-12">
          {categories.map((category) => {
            const Icon = category.icon;
            const hasResults = filteredFAQs[category.id]?.length > 0;
            
            return (
              <button
                key={category.id}
                onClick={() => setActiveCategory(category.id)}
                disabled={searchTerm && !hasResults}
                className={`
                  flex items-center gap-2 px-4 py-2 rounded-lg transition-all duration-300
                  ${activeCategory === category.id 
                    ? 'bg-platinum-500/10 text-platinum-500 border border-platinum-500/30' 
                    : hasResults || !searchTerm
                      ? 'bg-obsidian-850 text-text-secondary border border-obsidian-700 hover:border-obsidian-600 hover:text-text-primary'
                      : 'bg-obsidian-850 text-text-disabled border border-obsidian-700 opacity-50 cursor-not-allowed'
                  }
                `}
              >
                <Icon className="w-4 h-4" />
                <span className="font-medium">{category.label}</span>
                {filteredFAQs[category.id] && (
                  <span className="ml-1 px-2 py-0.5 bg-obsidian-700 text-xs rounded-full">
                    {filteredFAQs[category.id].length}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* FAQ Content */}
        <div className="space-y-4">
          {filteredFAQs[activeCategory]?.map((faq, index) => {
            const itemId = `${activeCategory}-${index}`;
            const isOpen = openItems.has(itemId);
            
            return (
              <div 
                key={index}
                className="bg-obsidian-900 border border-obsidian-700 rounded-xl overflow-hidden hover:border-obsidian-600 transition-all duration-300"
              >
                <button
                  onClick={() => toggleItem(activeCategory, index)}
                  className="w-full px-6 py-5 flex items-center justify-between text-left hover:bg-obsidian-850/50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    {faq.popular && (
                      <span className="px-2 py-1 bg-platinum-500/10 text-platinum-500 text-xs font-medium rounded-full border border-platinum-500/20">
                        Popular
                      </span>
                    )}
                    <h3 className="text-lg font-semibold text-text-primary pr-4">
                      {faq.question}
                    </h3>
                  </div>
                  
                  <div className="flex-shrink-0">
                    {isOpen ? (
                      <Minus className="w-5 h-5 text-platinum-500" />
                    ) : (
                      <Plus className="w-5 h-5 text-text-tertiary" />
                    )}
                  </div>
                </button>
                
                <div className={`overflow-hidden transition-all duration-300 ${isOpen ? 'max-h-96' : 'max-h-0'}`}>
                  <div className="px-6 pb-5">
                    <p className="text-text-secondary leading-relaxed">
                      {faq.answer}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* No Results */}
        {searchTerm && Object.keys(filteredFAQs).length === 0 && (
          <div className="text-center py-12">
            <HelpCircle className="w-16 h-16 text-text-tertiary mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-text-primary mb-2">No results found</h3>
            <p className="text-text-secondary mb-6">
              Try adjusting your search terms or browse by category above.
            </p>
            <Button variant="secondary" onClick={() => setSearchTerm('')}>
              Clear Search
            </Button>
          </div>
        )}

        {/* Contact Support */}
        <div className="mt-16 text-center">
          <div className="bg-obsidian-900 border border-obsidian-700 rounded-2xl p-8 max-w-2xl mx-auto">
            <HelpCircle className="w-12 h-12 text-platinum-500 mx-auto mb-4" />
            <h3 className="text-2xl font-bold text-text-primary mb-4">
              Still have questions?
            </h3>
            <p className="text-text-secondary mb-6">
              Our security experts are here to help you get the most out of Pentagent.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button variant="primary">Contact Support</Button>
              <Button variant="secondary">Schedule Demo</Button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default FAQSection;
