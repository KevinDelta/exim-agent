'use client';

import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useNavigation } from '@/hooks/useNavigation';
import { NavigationItem } from './NavigationItem';
import { NavigationToggle } from './NavigationToggle';
import { ProfileSection } from './ProfileSection';
import { NavigationErrorBoundary } from './NavigationErrorBoundary';

interface SideNavigationProps {
  className?: string;
}

const navigationVariants = {
  expanded: { 
    width: 280,
    transition: {
      duration: 0.3,
      ease: [0.4, 0.0, 0.2, 1] as [number, number, number, number],
      type: "spring" as const,
      stiffness: 300,
      damping: 30
    }
  },
  collapsed: { 
    width: 64,
    transition: {
      duration: 0.3,
      ease: [0.4, 0.0, 0.2, 1] as [number, number, number, number],
      type: "spring" as const,
      stiffness: 300,
      damping: 30
    }
  }
};

export const SideNavigation = React.memo(function SideNavigation({ className }: SideNavigationProps) {
  const navigationRef = useRef<HTMLElement>(null);
  const { 
    isCollapsed, 
    currentRoute, 
    navigationItems, 
    toggleCollapse, 
    navigateTo 
  } = useNavigation();

  // Handle keyboard navigation and focus management
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (!navigationRef.current) return;

      // Toggle navigation with Ctrl/Cmd + B
      if ((event.ctrlKey || event.metaKey) && event.key === 'b') {
        event.preventDefault();
        toggleCollapse();
        
        // Announce state change to screen readers
        const announcement = isCollapsed ? 'Navigation expanded' : 'Navigation collapsed';
        const ariaLiveRegion = document.getElementById('navigation-announcements');
        if (ariaLiveRegion) {
          ariaLiveRegion.textContent = announcement;
        }
        return;
      }

      // Handle arrow key navigation within the sidebar
      if (document.activeElement && navigationRef.current.contains(document.activeElement)) {
        const focusableElements = navigationRef.current.querySelectorAll(
          'button:not([disabled]), [href]:not([disabled]), [tabindex]:not([tabindex="-1"]):not([disabled])'
        );
        const currentIndex = Array.from(focusableElements).indexOf(document.activeElement as Element);

        if (event.key === 'ArrowDown') {
          event.preventDefault();
          const nextIndex = (currentIndex + 1) % focusableElements.length;
          (focusableElements[nextIndex] as HTMLElement).focus();
        } else if (event.key === 'ArrowUp') {
          event.preventDefault();
          const prevIndex = currentIndex === 0 ? focusableElements.length - 1 : currentIndex - 1;
          (focusableElements[prevIndex] as HTMLElement).focus();
        } else if (event.key === 'Home') {
          event.preventDefault();
          (focusableElements[0] as HTMLElement).focus();
        } else if (event.key === 'End') {
          event.preventDefault();
          (focusableElements[focusableElements.length - 1] as HTMLElement).focus();
        } else if (event.key === 'Escape' && !isCollapsed && window.innerWidth < 768) {
          // Close mobile navigation on Escape
          event.preventDefault();
          toggleCollapse();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [toggleCollapse, isCollapsed]);

  // Enhanced mobile behavior with responsive breakpoints
  useEffect(() => {
    const handleResize = () => {
      const isMobile = window.innerWidth < 768;

      
      // Auto-collapse on mobile if expanded
      if (isMobile && !isCollapsed) {
        toggleCollapse();
      }
      
      // Optional: Auto-expand on desktop if collapsed and user prefers expanded
      // This can be controlled by user preference in the future
    };

    handleResize(); // Check on mount
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [isCollapsed, toggleCollapse]);

  // Handle touch gestures for mobile
  useEffect(() => {
    let touchStartX = 0;
    let touchStartY = 0;


    const handleTouchStart = (e: TouchEvent) => {
      touchStartX = e.touches[0].clientX;
      touchStartY = e.touches[0].clientY;
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (!touchStartX || !touchStartY) return;

      const touchCurrentX = e.touches[0].clientX;
      const touchCurrentY = e.touches[0].clientY;
      const diffX = touchStartX - touchCurrentX;
      const diffY = touchStartY - touchCurrentY;

      // Only consider horizontal swipes
      if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > 50) {
        // Swipe left to close navigation (mobile only)
        if (diffX > 0 && !isCollapsed && window.innerWidth < 768) {
          e.preventDefault();
          toggleCollapse();
        }
      }
    };

    const handleTouchEnd = () => {
      touchStartX = 0;
      touchStartY = 0;
    };

    // Only add touch listeners on mobile devices
    if (typeof window !== 'undefined' && 'ontouchstart' in window) {
      document.addEventListener('touchstart', handleTouchStart, { passive: true });
      document.addEventListener('touchmove', handleTouchMove, { passive: false });
      document.addEventListener('touchend', handleTouchEnd, { passive: true });

      return () => {
        document.removeEventListener('touchstart', handleTouchStart);
        document.removeEventListener('touchmove', handleTouchMove);
        document.removeEventListener('touchend', handleTouchEnd);
      };
    }
  }, [isCollapsed, toggleCollapse]);

  const handleNavigationClick = React.useCallback((route: string) => {
    navigateTo(route);
    // Auto-collapse on mobile and tablet after navigation for better UX
    if (window.innerWidth < 1024 && !isCollapsed) {
      toggleCollapse();
    }
  }, [navigateTo, isCollapsed, toggleCollapse]);

  return (
    <NavigationErrorBoundary>
      {/* Mobile overlay */}
      <AnimatePresence>
        {!isCollapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/50 z-40 md:hidden"
            onClick={toggleCollapse}
            aria-hidden="true"
          />
        )}
      </AnimatePresence>

      <motion.nav
        ref={navigationRef}
        variants={navigationVariants}
        animate={isCollapsed ? 'collapsed' : 'expanded'}
        className={cn(
          // Base styles - full height navigation
          'h-screen bg-background border-r border-border flex flex-col',
          // Mobile: fixed overlay
          'fixed left-0 top-0 z-50 shadow-2xl md:shadow-lg',
          // Desktop: relative positioning for flex layout
          'lg:relative lg:z-auto lg:shadow-none',
          // Touch-friendly spacing on mobile
          'touch-target',
          className
        )}
        role="navigation"
        aria-label="Main navigation"
        id="main-navigation"
      >
        {/* Navigation Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <AnimatePresence mode="wait">
            {!isCollapsed && (
              <motion.div
                initial={{ opacity: 0, x: -20, scale: 0.9 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: -20, scale: 0.9 }}
                transition={{ 
                  duration: 0.3, 
                  delay: 0.1,
                  type: "spring",
                  stiffness: 400,
                  damping: 25
                }}
                className="flex items-center space-x-2"
              >
                <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                  <Shield className="w-5 h-5 text-primary-foreground" />
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-semibold text-foreground">
                    Compliance
                  </span>
                  <span className="text-xs text-muted-foreground">
                    Intelligence
                  </span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          
          <NavigationToggle 
            isCollapsed={isCollapsed} 
            onToggle={toggleCollapse} 
          />
        </div>

        {/* Navigation Items */}
        <div className="flex-1 overflow-y-auto py-4" role="region" aria-label="Navigation menu">
          <ul className="space-y-1 px-3" role="list">
            {React.useMemo(() => 
              navigationItems.map((item, index) => (
                <li key={item.id} role="listitem">
                  <NavigationItem
                    item={item}
                    isActive={currentRoute === item.route}
                    isCollapsed={isCollapsed}
                    onClick={handleNavigationClick}
                    tabIndex={0}
                    ariaSetSize={navigationItems.length}
                    ariaPosInSet={index + 1}
                  />
                </li>
              )), 
              [navigationItems, currentRoute, isCollapsed, handleNavigationClick]
            )}
          </ul>
        </div>

        {/* Profile Section */}
        <ProfileSection isCollapsed={isCollapsed} />
      </motion.nav>

      {/* ARIA live region for navigation announcements */}
      <div
        id="navigation-announcements"
        className="sr-only"
        aria-live="polite"
        aria-atomic="true"
      />
    </NavigationErrorBoundary>
  );
});