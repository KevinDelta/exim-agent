'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { SideNavigation } from '@/components/navigation';

interface AppLayoutProps {
  children: React.ReactNode;
  showNavigation?: boolean;
  className?: string;
}

/**
 * AppLayout - Main layout wrapper that integrates navigation with existing content
 * 
 * Features:
 * - Integrates SideNavigation with responsive behavior
 * - Manages content area positioning based on navigation state
 * - Maintains compatibility with existing pages
 * - Responsive design with mobile-first approach
 */
export function AppLayout({ 
  children, 
  showNavigation = true, 
  className 
}: AppLayoutProps) {

  return (
    <div className={cn('h-screen bg-background flex', className)}>
      {/* Navigation - only show on desktop in flex layout */}
      {showNavigation && (
        <div className="hidden lg:block flex-shrink-0">
          <SideNavigation />
        </div>
      )}

      {/* Mobile Navigation - overlay mode */}
      {showNavigation && (
        <div className="lg:hidden">
          <SideNavigation />
        </div>
      )}

      {/* Main Content Area */}
      <main
        className={cn(
          'flex-1 h-screen overflow-auto',
          // Ensure content takes full width on mobile
          'w-full lg:w-auto'
        )}
        id="main-content"
        role="main"
      >
        {/* Content wrapper with proper spacing */}
        <div className="w-full h-full">
          {children}
        </div>
      </main>

    </div>
  );
}

/**
 * ContentArea - Wrapper for page content with consistent spacing
 * Use this for pages that need standard content padding
 */
export function ContentArea({ 
  children, 
  className 
}: { 
  children: React.ReactNode; 
  className?: string; 
}) {
  return (
    <div className={cn(
      'container mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-12',
      'max-w-7xl',
      'min-h-full', // Ensure content area takes full height
      className
    )}>
      {children}
    </div>
  );
}
