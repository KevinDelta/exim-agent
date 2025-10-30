'use client';

import React from 'react';
import { SideNavigation } from './SideNavigation';

/**
 * Demo component to showcase the navigation system
 * This can be used for testing and development
 */
export function NavigationDemo() {
  return (
    <div className="flex h-screen bg-background">
      <SideNavigation />
      <main className="flex-1 p-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold text-foreground mb-6">
            Navigation System Demo
          </h1>
          <div className="space-y-4 text-muted-foreground">
            <p>
              The navigation system is now active. You can:
            </p>
            <ul className="list-disc list-inside space-y-2 ml-4">
              <li>Click the toggle button to collapse/expand the navigation</li>
              <li>Use Ctrl+B (or Cmd+B on Mac) to toggle navigation</li>
              <li>Navigate between different sections using the menu items</li>
              <li>View your profile information at the bottom</li>
              <li>Experience responsive behavior on mobile devices</li>
            </ul>
            <p className="mt-6">
              The navigation includes accessibility features like keyboard navigation,
              ARIA labels, and focus management.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}