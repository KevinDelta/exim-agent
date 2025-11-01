'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { ChevronLeft, Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { NavigationToggleProps } from '@/types/navigation';

const iconVariants = {
  collapsed: { rotate: 180 },
  expanded: { rotate: 0 }
};

export const NavigationToggle = React.memo(function NavigationToggle({ isCollapsed, onToggle }: NavigationToggleProps) {
  const handleClick = () => {
    onToggle();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onToggle();
    }
  };

  return (
    <Button
      variant="ghost"
      size="icon-sm"
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        'relative rounded-md transition-all duration-200 transform-gpu',
        'hover:bg-accent hover:text-accent-foreground hover:shadow-sm',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        'active:scale-95 active:bg-accent/80',
        // Enhanced touch targets for mobile
        'touch-target min-h-[44px] min-w-[44px]',
        // Responsive sizing
        'h-8 w-8 sm:h-9 sm:w-9 md:h-8 md:w-8',
        // Add subtle border for better definition
        'border border-transparent hover:border-border/50'
      )}
      aria-label={isCollapsed ? 'Expand navigation menu' : 'Collapse navigation menu'}
      aria-expanded={!isCollapsed}
      aria-controls="main-navigation"
      aria-describedby="navigation-toggle-help"
      title={isCollapsed ? 'Expand navigation (Ctrl+B)' : 'Collapse navigation (Ctrl+B)'}
      type="button"
    >
      {/* Desktop icon - ChevronLeft with enhanced rotation and scale */}
      <motion.div
        variants={iconVariants}
        animate={isCollapsed ? 'collapsed' : 'expanded'}
        transition={{ 
          duration: 0.3, 
          ease: [0.4, 0.0, 0.2, 1],
          type: "spring",
          stiffness: 300,
          damping: 30
        }}
        className="hidden md:block"
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
      >
        <ChevronLeft className="h-4 w-4" aria-hidden="true" />
      </motion.div>

      {/* Mobile icon - Menu with pulse animation */}
      <motion.div 
        className="md:hidden"
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.9 }}
        transition={{ type: "spring", stiffness: 400, damping: 17 }}
      >
        <Menu className="h-4 w-4" aria-hidden="true" />
      </motion.div>

      {/* Enhanced ripple effect on click */}
      <motion.div
        className="absolute inset-0 rounded-md bg-current"
        initial={{ opacity: 0, scale: 0.8 }}
        whileTap={{ 
          opacity: [0, 0.15, 0], 
          scale: [0.8, 1.2, 1.4],
          transition: { duration: 0.3, ease: "easeOut" }
        }}
      />

      {/* Subtle glow effect on hover */}
      <motion.div
        className="absolute inset-0 rounded-md bg-current opacity-0"
        whileHover={{ 
          opacity: 0.05,
          transition: { duration: 0.2 }
        }}
      />
      
      {/* Hidden help text for screen readers */}
      <span id="navigation-toggle-help" className="sr-only">
        Use Ctrl+B keyboard shortcut to toggle navigation
      </span>
    </Button>
  );
});