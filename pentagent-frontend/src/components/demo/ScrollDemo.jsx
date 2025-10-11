import React from 'react';
import { useScrollAnimation } from '../../hooks/useAnimations';

export const ScrollAnimationDemo = () => {
  const [ref1, isVisible1] = useScrollAnimation();
  const [ref2, isVisible2] = useScrollAnimation();
  const [ref3, isVisible3] = useScrollAnimation();
  const [ref4, isVisible4] = useScrollAnimation();

  return (
    <div className="space-y-6">
      <h3 className="text-xl font-semibold text-text-primary">Scroll Animations</h3>
      
      <div className="space-y-20">
        <div 
          ref={ref1}
          className={`scroll-fadeIn ${isVisible1 ? 'visible' : ''}`}
        >
          <div className="bg-obsidian-800 rounded-lg p-8 text-center">
            <h4 className="text-2xl font-semibold text-text-primary mb-4">Fade In Animation</h4>
            <p className="text-text-secondary">
              This content fades in as you scroll down the page.
            </p>
          </div>
        </div>

        <div 
          ref={ref2}
          className={`scroll-slideLeft ${isVisible2 ? 'visible' : ''}`}
        >
          <div className="bg-obsidian-800 rounded-lg p-8 text-center">
            <h4 className="text-2xl font-semibold text-text-primary mb-4">Slide Left Animation</h4>
            <p className="text-text-secondary">
              This content slides in from the left when it becomes visible.
            </p>
          </div>
        </div>

        <div 
          ref={ref3}
          className={`scroll-slideRight ${isVisible3 ? 'visible' : ''}`}
        >
          <div className="bg-obsidian-800 rounded-lg p-8 text-center">
            <h4 className="text-2xl font-semibold text-text-primary mb-4">Slide Right Animation</h4>
            <p className="text-text-secondary">
              This content slides in from the right when it becomes visible.
            </p>
          </div>
        </div>

        <div 
          ref={ref4}
          className={`scroll-scaleIn ${isVisible4 ? 'visible' : ''}`}
        >
          <div className="bg-obsidian-800 rounded-lg p-8 text-center">
            <h4 className="text-2xl font-semibold text-text-primary mb-4">Scale In Animation</h4>
            <p className="text-text-secondary">
              This content scales up when it becomes visible.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export const StaggeredAnimationDemo = () => {
  const items = [
    { id: 1, title: 'Item 1', color: 'bg-amber-500' },
    { id: 2, title: 'Item 2', color: 'bg-coral-500' },
    { id: 3, title: 'Item 3', color: 'bg-lavender-500' },
    { id: 4, title: 'Item 4', color: 'bg-amber-600' },
    { id: 5, title: 'Item 5', color: 'bg-coral-600' },
    { id: 6, title: 'Item 6', color: 'bg-lavender-600' },
  ];

  return (
    <div className="space-y-6">
      <h3 className="text-xl font-semibold text-text-primary">Staggered Animations</h3>
      
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {items.map((item, index) => (
          <div
            key={item.id}
            className={`${item.color} rounded-lg p-6 text-center text-white font-medium animate-slideUp stagger-${index + 1}`}
          >
            {item.title}
          </div>
        ))}
      </div>
    </div>
  );
};
