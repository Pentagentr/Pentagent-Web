import React, { useState } from 'react';
import { Mail, Lock } from 'lucide-react';
import Button from '../common/Button';
import Input from '../common/Input';

export const ButtonDemo = () => {
  const [isPressed, setIsPressed] = useState(false);

  const handlePress = () => {
    setIsPressed(true);
    setTimeout(() => setIsPressed(false), 200);
  };

  return (
    <div className="space-y-4">
      <h3 className="text-xl font-semibold text-text-primary">Premium Button Component</h3>
      
      <div className="space-y-6">
        {/* Variants */}
        <div>
          <h4 className="text-lg font-medium text-text-secondary mb-4">Variants</h4>
          <div className="flex gap-4 flex-wrap">
            <Button variant="primary">Primary Button</Button>
            <Button variant="secondary">Secondary Button</Button>
            <Button variant="ghost">Ghost Button</Button>
          </div>
        </div>

        {/* Sizes */}
        <div>
          <h4 className="text-lg font-medium text-text-secondary mb-4">Sizes</h4>
          <div className="flex gap-4 items-center flex-wrap">
            <Button variant="primary" size="sm">Small</Button>
            <Button variant="primary" size="md">Medium</Button>
            <Button variant="primary" size="lg">Large</Button>
          </div>
        </div>

        {/* States */}
        <div>
          <h4 className="text-lg font-medium text-text-secondary mb-4">States</h4>
          <div className="flex gap-4 flex-wrap">
            <Button variant="primary" isLoading>Loading...</Button>
            <Button variant="primary" disabled>Disabled</Button>
            <Button variant="secondary" isLoading>Loading...</Button>
          </div>
        </div>

        {/* Interactive Demo */}
        <div>
          <h4 className="text-lg font-medium text-text-secondary mb-4">Interactive Demo</h4>
          <div className="flex gap-4 flex-wrap">
            <Button 
              variant="primary" 
              onClick={handlePress}
              className={isPressed ? 'animate-buttonPress' : ''}
            >
              Press Me
            </Button>
            <Button variant="secondary" onClick={() => alert('Button clicked!')}>
              Click Me
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export const FormDemo = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleInputChange = (field) => (e) => {
    const value = e.target.value;
    setFormData(prev => ({ ...prev, [field]: value }));
    
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.email) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Invalid email format';
    }
    
    if (!formData.password) {
      newErrors.password = 'Password is required';
    } else if (formData.password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters';
    }
    
    if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = 'Passwords do not match';
    }
    
    return newErrors;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const newErrors = validateForm();
    
    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }
    
    setIsSubmitting(true);
    
    // Simulate API call
    setTimeout(() => {
      alert('Form submitted successfully!');
      setIsSubmitting(false);
      setFormData({ email: '', password: '', confirmPassword: '' });
    }, 2000);
  };

  return (
    <div className="space-y-4">
      <h3 className="text-xl font-semibold text-text-primary">Form Validation Demo</h3>
      
      <div className="max-w-md">
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input 
            label="Email Address"
            type="email"
            placeholder="you@example.com"
            value={formData.email}
            onChange={handleInputChange('email')}
            error={errors.email}
            icon={Mail}
          />
          
          <Input 
            label="Password"
            type="password"
            placeholder="Enter password"
            value={formData.password}
            onChange={handleInputChange('password')}
            error={errors.password}
            icon={Lock}
          />
          
          <Input 
            label="Confirm Password"
            type="password"
            placeholder="Confirm password"
            value={formData.confirmPassword}
            onChange={handleInputChange('confirmPassword')}
            error={errors.confirmPassword}
            icon={Lock}
          />
          
          <Button 
            type="submit"
            variant="primary" 
            isLoading={isSubmitting}
            className="w-full"
          >
            {isSubmitting ? 'Creating Account...' : 'Create Account'}
          </Button>
        </form>
      </div>
    </div>
  );
};
