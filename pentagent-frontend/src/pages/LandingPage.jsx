import React from 'react';
import HeroSection from '../components/landing/HeroSection';
import SocialProofSection from '../components/landing/SocialProofSection';
import FeaturesSection from '../components/landing/FeaturesSection';
import DemoSection from '../components/landing/DemoSection';
import FAQSection from '../components/landing/FAQSection';
import Footer from '../components/layout/Footer';

const LandingPage = () => {
  return (
    <div className="min-h-screen bg-obsidian-950">
      <HeroSection />
      <SocialProofSection />
      <FeaturesSection />
      <DemoSection />
      <FAQSection />
      <Footer />
    </div>
  );
};

export default LandingPage;
