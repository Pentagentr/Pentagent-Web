import React from 'react';
import { Star, Heart, Share2, TrendingUp, Users, DollarSign, Activity } from 'lucide-react';
import Card from '../common/Card';
import Button from '../common/Button';

export const CardDemo = () => {
  return (
    <div className="space-y-6">
      <h3 className="text-xl font-semibold text-text-primary">Card Component System</h3>
      
      <div className="space-y-8">
        {/* Basic Variants */}
        <div>
          <h4 className="text-lg font-medium text-text-secondary mb-4">Card Variants</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card variant="default">
              <Card.Header>
                <Card.Title>Default Card</Card.Title>
              </Card.Header>
              <Card.Body>
                <p className="text-text-secondary text-sm">Basic card with subtle border</p>
              </Card.Body>
            </Card>

            <Card variant="elevated">
              <Card.Header>
                <Card.Title>Elevated Card</Card.Title>
              </Card.Header>
              <Card.Body>
                <p className="text-text-secondary text-sm">Card with shadow for emphasis</p>
              </Card.Body>
            </Card>

            <Card variant="interactive">
              <Card.Header>
                <Card.Title>Interactive Card</Card.Title>
              </Card.Header>
              <Card.Body>
                <p className="text-text-secondary text-sm">Hover for effects</p>
              </Card.Body>
            </Card>
          </div>
        </div>

        {/* Card Structure */}
        <div>
          <h4 className="text-lg font-medium text-text-secondary mb-4">Card Structure</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card variant="default">
              <Card.Header>
                <Card.Title>Header Section</Card.Title>
                <Button size="sm" variant="secondary">Action</Button>
              </Card.Header>
              <Card.Body>
                <p className="text-text-secondary text-sm mb-4">This is the main content area of the card.</p>
                <div className="bg-obsidian-800 rounded-lg p-3">
                  <p className="text-xs text-text-tertiary">Nested content example</p>
                </div>
              </Card.Body>
              <Card.Footer>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-text-tertiary">Footer content</span>
                  <div className="flex gap-2">
                    <Star size={14} className="text-text-tertiary hover:text-amber-500 transition-smooth cursor-pointer" />
                    <Heart size={14} className="text-text-tertiary hover:text-coral-500 transition-smooth cursor-pointer" />
                  </div>
                </div>
              </Card.Footer>
            </Card>

            <Card variant="elevated">
              <Card.Header>
                <Card.Title>Simple Card</Card.Title>
              </Card.Header>
              <Card.Body>
                <p className="text-text-secondary text-sm">Sometimes you don't need all sections. Just header and body work perfectly.</p>
              </Card.Body>
            </Card>
          </div>
        </div>

        {/* Dashboard Cards */}
        <div>
          <h4 className="text-lg font-medium text-text-secondary mb-4">Dashboard Cards</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card variant="elevated">
              <Card.Body>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-text-tertiary">Total Revenue</p>
                    <p className="text-2xl font-bold text-text-primary">$45,231</p>
                  </div>
                  <DollarSign size={24} className="text-amber-500" />
                </div>
                <p className="text-xs text-success mt-2">+20.1% from last month</p>
              </Card.Body>
            </Card>

            <Card variant="elevated">
              <Card.Body>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-text-tertiary">Active Users</p>
                    <p className="text-2xl font-bold text-text-primary">2,350</p>
                  </div>
                  <Users size={24} className="text-coral-500" />
                </div>
                <p className="text-xs text-success mt-2">+15.3% from last month</p>
              </Card.Body>
            </Card>

            <Card variant="elevated">
              <Card.Body>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-text-tertiary">Growth Rate</p>
                    <p className="text-2xl font-bold text-text-primary">12.5%</p>
                  </div>
                  <TrendingUp size={24} className="text-lavender-500" />
                </div>
                <p className="text-xs text-success mt-2">+2.4% from last month</p>
              </Card.Body>
            </Card>

            <Card variant="elevated">
              <Card.Body>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-text-tertiary">Activity</p>
                    <p className="text-2xl font-bold text-text-primary">98.2%</p>
                  </div>
                  <Activity size={24} className="text-success" />
                </div>
                <p className="text-xs text-success mt-2">+0.8% from last month</p>
              </Card.Body>
            </Card>
          </div>
        </div>

        {/* Feature Cards */}
        <div>
          <h4 className="text-lg font-medium text-text-secondary mb-4">Feature Cards</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card variant="interactive" className="cursor-pointer">
              <Card.Header>
                <Card.Title>Premium Feature</Card.Title>
                <div className="px-2 py-1 bg-amber-500 text-obsidian-950 text-xs font-medium rounded">
                  PRO
                </div>
              </Card.Header>
              <Card.Body>
                <p className="text-text-secondary text-sm mb-4">Access advanced features and priority support.</p>
                <ul className="text-xs text-text-tertiary space-y-1">
                  <li>• Unlimited projects</li>
                  <li>• Priority support</li>
                  <li>• Advanced analytics</li>
                </ul>
              </Card.Body>
              <Card.Footer>
                <Button variant="primary" size="sm" className="w-full">
                  Upgrade Now
                </Button>
              </Card.Footer>
            </Card>

            <Card variant="default">
              <Card.Header>
                <Card.Title>Free Plan</Card.Title>
                <div className="px-2 py-1 bg-obsidian-700 text-text-secondary text-xs font-medium rounded">
                  FREE
                </div>
              </Card.Header>
              <Card.Body>
                <p className="text-text-secondary text-sm mb-4">Perfect for getting started with basic features.</p>
                <ul className="text-xs text-text-tertiary space-y-1">
                  <li>• 3 projects</li>
                  <li>• Community support</li>
                  <li>• Basic analytics</li>
                </ul>
              </Card.Body>
              <Card.Footer>
                <Button variant="secondary" size="sm" className="w-full">
                  Get Started
                </Button>
              </Card.Footer>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};
