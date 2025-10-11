import React from 'react';

const StatsCard = ({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  trendValue,
  color = 'amber',
  onClick
}) => {
  const colorClasses = {
    amber: {
      icon: 'text-platinum-500 bg-platinum-500/10',
      trend: {
        up: 'text-success',
        down: 'text-rose-500',
        neutral: 'text-text-tertiary'
      }
    },
    green: {
      icon: 'text-success bg-success/10',
      trend: {
        up: 'text-success',
        down: 'text-rose-500', 
        neutral: 'text-text-tertiary'
      }
    },
    red: {
      icon: 'text-rose-500 bg-rose-500/10',
      trend: {
        up: 'text-rose-500',
        down: 'text-success',
        neutral: 'text-text-tertiary'
      }
    },
    blue: {
      icon: 'text-purple-500 bg-purple-500/10',
      trend: {
        up: 'text-success',
        down: 'text-rose-500',
        neutral: 'text-text-tertiary'
      }
    }
  };

  const getTrendIcon = (trend) => {
    if (trend === 'up') return '↑';
    if (trend === 'down') return '↓';
    return '→';
  };

  return (
    <div 
      className={`
        bg-obsidian-900 border border-obsidian-700 rounded-xl p-6 
        hover:border-obsidian-600 transition-all duration-300 hover-lift
        ${onClick ? 'cursor-pointer' : ''}
      `}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-4">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${colorClasses[color].icon}`}>
          <Icon className="w-6 h-6" />
        </div>
        
        {trend && trendValue && (
          <div className={`text-sm font-medium ${colorClasses[color].trend[trend]}`}>
            <span className="mr-1">{getTrendIcon(trend)}</span>
            {trendValue}
          </div>
        )}
      </div>
      
      <div className="space-y-2">
        <div className="text-3xl font-bold text-text-primary">
          {typeof value === 'number' ? value.toLocaleString() : value}
        </div>
        <div className="text-lg font-semibold text-text-secondary">{title}</div>
        {subtitle && (
          <div className="text-sm text-text-tertiary">{subtitle}</div>
        )}
      </div>
    </div>
  );
};

export default StatsCard;
