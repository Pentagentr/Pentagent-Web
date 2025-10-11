import React, { useState, useEffect } from 'react';

export const SkeletonCard = () => (
  <div className="bg-obsidian-800 rounded-lg p-6 animate-skeleton">
    <div className="flex items-center space-x-4 mb-4">
      <div className="skeleton skeleton-circle w-12 h-12"></div>
      <div className="flex-1">
        <div className="skeleton skeleton-text w-3/4 mb-2"></div>
        <div className="skeleton skeleton-text w-1/2"></div>
      </div>
    </div>
    <div className="space-y-2">
      <div className="skeleton skeleton-text"></div>
      <div className="skeleton skeleton-text"></div>
      <div className="skeleton skeleton-text w-2/3"></div>
    </div>
  </div>
);

export const LoadingSpinner = ({ size = 'md' }) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12'
  };

  return (
    <div className={`${sizeClasses[size]} border-2 border-amber-500 border-t-transparent rounded-full animate-spin`}></div>
  );
};

export const ShimmerCard = () => (
  <div className="bg-obsidian-800 rounded-lg p-6">
    <div className="skeleton skeleton-rectangle h-32 mb-4"></div>
    <div className="space-y-2">
      <div className="skeleton skeleton-text"></div>
      <div className="skeleton skeleton-text w-3/4"></div>
      <div className="skeleton skeleton-text w-1/2"></div>
    </div>
  </div>
);

export const LoadingStatesDemo = () => {
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 3000);

    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="space-y-6">
      <h3 className="text-xl font-semibold text-text-primary">Loading States</h3>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h4 className="text-lg font-medium text-text-secondary mb-4">Skeleton Cards</h4>
          <div className="space-y-4">
            <SkeletonCard />
            <SkeletonCard />
          </div>
        </div>
        
        <div>
          <h4 className="text-lg font-medium text-text-secondary mb-4">Shimmer Effects</h4>
          <div className="space-y-4">
            <ShimmerCard />
            <ShimmerCard />
          </div>
        </div>
      </div>
      
      <div className="text-center">
        <h4 className="text-lg font-medium text-text-secondary mb-4">Loading Spinner</h4>
        <div className="flex justify-center items-center space-x-4">
          <LoadingSpinner size="sm" />
          <LoadingSpinner size="md" />
          <LoadingSpinner size="lg" />
        </div>
      </div>
      
      <div className="text-center">
        <button 
          className="px-6 py-3 bg-amber-500 text-obsidian-950 rounded-lg font-medium button-interactive"
          onClick={() => setIsLoading(!isLoading)}
        >
          {isLoading ? 'Stop Loading' : 'Start Loading'}
        </button>
        {isLoading && (
          <div className="mt-4 animate-pulse">
            <p className="text-text-secondary">Loading content...</p>
          </div>
        )}
      </div>
    </div>
  );
};
