import React from 'react';

const Logo = ({ variant = 'full', size = 'md', className = '' }) => {
  const sizes = {
    sm: 'text-sm',
    md: 'text-lg',
    lg: 'text-xl',
    xl: 'text-2xl',
  };

  const variants = {
    icon: (
      <div className="w-8 h-8 bg-gradient-to-br from-platinum-500 to-platinum-600 rounded-lg" />
    ),
    full: (
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-gradient-to-br from-platinum-500 to-platinum-600 rounded-lg" />
        <span className={`font-semibold text-text-primary tracking-tight ${sizes[size]}`}>
          PENTAGENT
        </span>
      </div>
    ),
  };

  return (
    <div className={className}>
      {variants[variant]}
    </div>
  );
};

export default Logo;
