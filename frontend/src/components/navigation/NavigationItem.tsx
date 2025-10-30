'use client';

import React from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { NavigationItemProps } from '@/types/navigation';
import { Badge } from '@/components/ui/badge';

export const NavigationItem = React.memo(function NavigationItem({ 
  item, 
  isActive, 
  isCollapsed, 
  onClick,
  tabIndex,
  ariaSetSize,
  ariaPosInSet
}: NavigationItemProps) {
  const Icon = item.icon;

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    if (!item.disabled) {
      onClick(item.route);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      if (!item.disabled) {
        onClick(item.route);
      }
    }
  };

  return (
    <Link
      href={item.route}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={cn(
        'group relative flex items-center rounded-lg transition-all duration-200',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        'hover:bg-accent hover:text-accent-foreground hover:shadow-sm',
        // Enhanced touch targets for mobile
        'touch-target min-h-[48px]',
        // Enhanced active touch feedback with spring animation
        'active:scale-95 active:bg-accent/80 transform-gpu',
        // Spacing adjustments
        isCollapsed ? 'p-3 justify-center' : 'p-3 space-x-3',
        // Mobile-specific padding for better touch experience
        'sm:min-h-[44px] md:min-h-[40px]',
        // Enhanced active state with subtle glow
        isActive && 'bg-primary text-primary-foreground hover:bg-primary/90 active:bg-primary/80 shadow-md',
        item.disabled && 'opacity-50 cursor-not-allowed pointer-events-none'
      )}
      role="menuitem"
      tabIndex={tabIndex}
      aria-label={`Navigate to ${item.label}${item.badge ? `, ${item.badge} notifications` : ''}`}
      aria-current={isActive ? 'page' : undefined}
      aria-disabled={item.disabled}
      aria-setsize={ariaSetSize}
      aria-posinset={ariaPosInSet}
      aria-describedby={isCollapsed ? `tooltip-${item.id}` : undefined}
    >
      {/* Active indicator */}
      {isActive && (
        <motion.div
          layoutId="activeIndicator"
          className="absolute left-0 top-0 bottom-0 w-1 bg-primary-foreground rounded-r-full"
          initial={false}
          transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        />
      )}

      {/* Icon with enhanced hover animation */}
      <motion.div 
        className="relative flex items-center justify-center"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        transition={{ type: "spring", stiffness: 400, damping: 17 }}
      >
        <Icon 
          className={cn(
            'w-5 h-5 transition-all duration-200',
            isActive ? 'text-primary-foreground' : 'text-muted-foreground group-hover:text-accent-foreground',
            // Add subtle rotation on hover for non-active items
            !isActive && 'group-hover:rotate-3'
          )} 
          aria-hidden="true"
        />
        
        {/* Badge for collapsed state with bounce animation */}
        <AnimatePresence>
          {item.badge && item.badge > 0 && isCollapsed && (
            <motion.div
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0, opacity: 0 }}
              transition={{ type: "spring", stiffness: 500, damping: 30 }}
              className="absolute -top-1 -right-1"
            >
              <Badge 
                variant="destructive" 
                className="h-4 w-4 p-0 text-xs flex items-center justify-center animate-pulse"
              >
                {item.badge > 99 ? '99+' : item.badge}
              </Badge>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* Label and badge for expanded state */}
      <AnimatePresence mode="wait">
        {!isCollapsed && (
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            transition={{ duration: 0.2 }}
            className="flex items-center justify-between flex-1 min-w-0"
          >
            <span className={cn(
              'text-sm font-medium truncate transition-colors duration-200',
              isActive ? 'text-primary-foreground' : 'text-foreground group-hover:text-accent-foreground'
            )}>
              {item.label}
            </span>
            
            {item.badge && item.badge > 0 && (
              <Badge 
                variant={isActive ? "secondary" : "default"}
                className="ml-2 h-5 px-2 text-xs"
              >
                {item.badge > 99 ? '99+' : item.badge}
              </Badge>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Enhanced tooltip for collapsed state with smooth animation */}
      <AnimatePresence>
        {isCollapsed && (
          <motion.div 
            id={`tooltip-${item.id}`}
            className="absolute left-full ml-2 px-3 py-2 bg-popover text-popover-foreground text-sm rounded-lg shadow-lg pointer-events-none z-50 whitespace-nowrap border border-border"
            role="tooltip"
            aria-hidden="true"
            initial={{ opacity: 0, x: -10, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: -10, scale: 0.9 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
            style={{
              opacity: 0,
            }}
            whileHover={{ opacity: 1 }}
          >
            <div className="font-medium">{item.label}</div>
            {item.badge && item.badge > 0 && (
              <div className="text-xs text-muted-foreground mt-1">
                {item.badge > 99 ? '99+' : item.badge} notifications
              </div>
            )}
            <div className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1 w-2 h-2 bg-popover border-l border-t border-border rotate-45" />
          </motion.div>
        )}
      </AnimatePresence>
    </Link>
  );
});