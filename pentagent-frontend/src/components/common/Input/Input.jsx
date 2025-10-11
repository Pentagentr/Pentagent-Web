import React from 'react';

const Input = ({
  label,
  type = 'text',
  placeholder,
  value,
  onChange,
  error,
  disabled = false,
  icon: Icon,
  className = '',
  ...props
}) => {
  return (
    <div className={`w-full ${className}`}>
      {label && (
        <label className="block text-sm font-medium text-text-secondary mb-2">
          {label}
        </label>
      )}
      
      <div className="relative">
        {Icon && (
          <div className="absolute left-4 top-1/2 -translate-y-1/2 text-text-tertiary">
            <Icon size={18} />
          </div>
        )}
        
        <input
          type={type}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          disabled={disabled}
          className={`
            w-full h-11 px-4 
            ${Icon ? 'pl-11' : ''} 
            bg-obsidian-900 
            border border-obsidian-700 
            rounded-lg 
            text-text-primary 
            placeholder:text-text-tertiary
            transition-smooth
            focus:outline-none 
            focus:border-platinum-500 
            focus:ring-2 
            focus:ring-platinum-500/10
            disabled:opacity-50 
            disabled:cursor-not-allowed
            ${error ? 'border-rose-500 focus:border-rose-500 focus:ring-rose-500/10' : ''}
          `}
          {...props}
        />
      </div>
      
      {error && (
        <p className="mt-1 text-xs text-rose-500">{error}</p>
      )}
    </div>
  );
};

export default Input;
