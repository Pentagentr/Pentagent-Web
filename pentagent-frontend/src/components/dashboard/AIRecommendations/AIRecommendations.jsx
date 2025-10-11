import React, { useState } from 'react';
import { 
  Brain, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  ArrowRight,
  Lightbulb,
  Shield,
  Zap,
  Target
} from 'lucide-react';
import Card from '../../common/Card';
import Button from '../../common/Button';

const AIRecommendations = () => {
  const [activeTab, setActiveTab] = useState('recommendations');

  const recommendations = [
    {
      id: '1',
      type: 'critical',
      icon: AlertTriangle,
      title: 'Critical SQL Injection Found',
      description: 'Multiple SQL injection vulnerabilities detected on example.com login page. Immediate attention required.',
      action: 'Review Findings',
      priority: 'high',
      estimatedTime: '15 min',
      impact: 'High risk of data breach'
    },
    {
      id: '2', 
      type: 'optimization',
      icon: Zap,
      title: 'Scan Schedule Optimization',
      description: 'AI suggests scheduling weekly scans for api.testsite.io based on deployment patterns.',
      action: 'Configure Schedule',
      priority: 'medium',
      estimatedTime: '5 min',
      impact: 'Improve security coverage'
    },
    {
      id: '3',
      type: 'insight',
      icon: Lightbulb,
      title: 'New Attack Vector Detected',
      description: 'AI identified a potential new attack pattern targeting your authentication system.',
      action: 'Learn More',
      priority: 'medium',
      estimatedTime: '10 min',
      impact: 'Stay ahead of threats'
    },
    {
      id: '4',
      type: 'maintenance',
      icon: Shield,
      title: 'Security Tool Update Available',
      description: 'XSS detection engine has been updated with new payload signatures.',
      action: 'Update Now',
      priority: 'low',
      estimatedTime: '2 min',
      impact: 'Enhanced detection capabilities'
    }
  ];

  const quickActions = [
    {
      id: '1',
      icon: Target,
      title: 'Start Quick Scan',
      description: 'Run OWASP Top 10 scan on your most critical assets',
      action: () => console.log('Quick scan started'),
      color: 'amber'
    },
    {
      id: '2', 
      icon: Brain,
      title: 'AI Security Review',
      description: 'Get AI analysis of your current security posture',
      action: () => console.log('AI review started'),
      color: 'blue'
    },
    {
      id: '3',
      icon: Shield,
      title: 'Generate Report',
      description: 'Create executive summary of recent findings',
      action: () => console.log('Report generation started'),
      color: 'green'
    }
  ];

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'high': return 'text-rose-500 bg-rose-500/10';
      case 'medium': return 'text-warning bg-warning/10';
      case 'low': return 'text-purple-500 bg-purple-500/10';
      default: return 'text-text-tertiary bg-obsidian-800';
    }
  };

  const getTypeColor = (type) => {
    switch (type) {
      case 'critical': return 'text-rose-500';
      case 'optimization': return 'text-platinum-500';
      case 'insight': return 'text-purple-500';
      case 'maintenance': return 'text-text-tertiary';
      default: return 'text-text-tertiary';
    }
  };

  const RecommendationItem = ({ recommendation }) => {
    const Icon = recommendation.icon;
    
    return (
      <div className="p-4 bg-obsidian-850 rounded-lg hover:bg-obsidian-800 transition-colors group">
        <div className="flex items-start gap-4">
          <div className={`w-10 h-10 rounded-lg bg-obsidian-900 border border-obsidian-700 flex items-center justify-center ${getTypeColor(recommendation.type)}`}>
            <Icon className="w-5 h-5" />
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <h4 className="font-medium text-text-primary">{recommendation.title}</h4>
              <span className={`px-2 py-1 text-xs rounded-full capitalize ${getPriorityColor(recommendation.priority)}`}>
                {recommendation.priority}
              </span>
            </div>
            
            <p className="text-sm text-text-secondary mb-3 leading-relaxed">
              {recommendation.description}
            </p>
            
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4 text-xs text-text-tertiary">
                <div className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  <span>{recommendation.estimatedTime}</span>
                </div>
                <span>{recommendation.impact}</span>
              </div>
              
              <Button variant="ghost" size="sm" className="opacity-0 group-hover:opacity-100 transition-opacity">
                {recommendation.action}
                <ArrowRight className="w-3 h-3 ml-1" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const QuickActionCard = ({ action }) => {
    const Icon = action.icon;
    const colorClasses = {
      amber: 'border-platinum-500/20 hover:border-platinum-500/40 hover:bg-platinum-500/5',
      blue: 'border-purple-500/20 hover:border-purple-500/40 hover:bg-purple-500/5',
      green: 'border-success/20 hover:border-success/40 hover:bg-success/5'
    };
    
    return (
      <button
        onClick={action.action}
        className={`w-full p-4 border border-obsidian-700 rounded-lg text-left transition-all hover-lift ${colorClasses[action.color]}`}
      >
        <div className="flex items-center gap-3 mb-3">
          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
            action.color === 'amber' ? 'bg-platinum-500/10 text-platinum-500' :
            action.color === 'blue' ? 'bg-purple-500/10 text-purple-500' :
            'bg-success/10 text-success'
          }`}>
            <Icon className="w-4 h-4" />
          </div>
          <h4 className="font-medium text-text-primary">{action.title}</h4>
        </div>
        <p className="text-sm text-text-secondary">{action.description}</p>
      </button>
    );
  };

  const tabs = [
    { id: 'recommendations', label: 'AI Recommendations' },
    { id: 'actions', label: 'Quick Actions' }
  ];

  return (
    <Card>
      <Card.Header>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-platinum-500 to-platinum-600 rounded-xl flex items-center justify-center">
            <Brain className="w-5 h-5 text-obsidian-950" />
          </div>
          <div>
            <Card.Title>AI Security Assistant</Card.Title>
            <p className="text-sm text-text-tertiary">Intelligent recommendations and insights</p>
          </div>
        </div>
      </Card.Header>
      
      {/* Tabs */}
      <div className="px-6 border-b border-obsidian-700">
        <div className="flex gap-4">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-platinum-500 text-platinum-500'
                  : 'border-transparent text-text-secondary hover:text-text-primary'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>
      
      <Card.Body>
        {activeTab === 'recommendations' && (
          <div className="space-y-4">
            {recommendations.map(recommendation => (
              <RecommendationItem key={recommendation.id} recommendation={recommendation} />
            ))}
            
            {recommendations.length === 0 && (
              <div className="text-center py-8">
                <Brain className="w-12 h-12 text-text-tertiary mx-auto mb-4" />
                <h3 className="text-text-primary font-medium mb-2">No recommendations yet</h3>
                <p className="text-text-secondary text-sm">
                  AI will analyze your security data and provide personalized recommendations.
                </p>
              </div>
            )}
          </div>
        )}
        
        {activeTab === 'actions' && (
          <div className="grid gap-4">
            {quickActions.map(action => (
              <QuickActionCard key={action.id} action={action} />
            ))}
          </div>
        )}
      </Card.Body>
      
      <Card.Footer>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-text-tertiary">
            <div className="w-2 h-2 bg-success rounded-full animate-pulse" />
            <span>AI assistant is active</span>
          </div>
          <Button variant="ghost" size="sm">
            View All Insights →
          </Button>
        </div>
      </Card.Footer>
    </Card>
  );
};

export default AIRecommendations;
