import React from 'react';
import { Loader2 } from 'lucide-react';

const Button = ({
  children,
  variant = 'primary',
  size = 'md',
  isLoading = false,
  disabled = false,
  onClick,
  className = '',
  ...props
}) => {
  const baseStyles = 'inline-flex items-center justify-center font-medium transition-smooth rounded-lg focus:outline-none focus:ring-2 focus:ring-platinum-500 focus:ring-offset-2 focus:ring-offset-obsidian-950 disabled:opacity-40 disabled:cursor-not-allowed';
  
  const variants = {
    primary: 'bg-gradient-to-r from-platinum-500 to-platinum-600 text-obsidian-950 hover-lift hover-glow active:scale-95',
    secondary: 'border-2 border-platinum-500 text-platinum-500 hover:bg-platinum-500 hover:text-obsidian-950',
    ghost: 'text-platinum-500 hover:bg-obsidian-850',
  };
  
  const sizes = {
    sm: 'h-9 px-3 text-sm',
    md: 'h-11 px-4 text-base',
    lg: 'h-13 px-6 text-lg',
  };
  
  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      disabled={disabled || isLoading}
      onClick={onClick}
      {...props}
    >
      {isLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
      {children}
    </button>
  );
};

export default Button;
