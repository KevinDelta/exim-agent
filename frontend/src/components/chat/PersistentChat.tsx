'use client';

import React, { Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageCircle, Minimize2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useChat } from '@/hooks/useChat';


// Lazy load ChatWindow for better performance
const LazyLoadedChatWindow = React.lazy(() => import('./ChatWindow').then(module => ({ default: module.ChatWindow })));

/**
 * PersistentChat - Fixed-position chat interface at bottom of screen
 * 
 * Features:
 * - Fixed position at bottom-right of screen
 * - Expandable from 60px height to 400px
 * - Unread message indicator
 * - Smooth expand/collapse animations
 * - Z-index management to stay above content
 */
const PersistentChatComponent: React.FC = () => {
  const {
    messages,
    isExpanded,
    unreadCount,
    isLoading,
    sendMessage,
    clearHistory,
    toggleExpanded,
  } = useChat();

  const chatRef = React.useRef<HTMLDivElement>(null);
  const previousFocusRef = React.useRef<HTMLElement | null>(null);

  // Handle keyboard shortcuts for chat toggle
  React.useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Toggle chat with Ctrl/Cmd + /
      if ((event.ctrlKey || event.metaKey) && event.key === '/') {
        event.preventDefault();
        
        if (!isExpanded) {
          // Store current focus before opening chat
          previousFocusRef.current = document.activeElement as HTMLElement;
        }
        
        toggleExpanded();
        
        // Announce state change to screen readers
        const announcement = isExpanded ? 'Chat closed' : 'Chat opened';
        const ariaLiveRegion = document.getElementById('chat-announcements');
        if (ariaLiveRegion) {
          ariaLiveRegion.textContent = announcement;
        }
        return;
      }

      // Handle Escape key to close chat
      if (event.key === 'Escape' && isExpanded) {
        event.preventDefault();
        toggleExpanded();
        
        // Restore focus to previous element
        if (previousFocusRef.current) {
          previousFocusRef.current.focus();
          previousFocusRef.current = null;
        }
        return;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isExpanded, toggleExpanded]);

  // Focus trap for expanded chat
  React.useEffect(() => {
    if (!isExpanded || !chatRef.current) return;

    const chatElement = chatRef.current;
    const focusableElements = chatElement.querySelectorAll(
      'button:not([disabled]), [href]:not([disabled]), input:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"]):not([disabled])'
    );
    
    const firstFocusable = focusableElements[0] as HTMLElement;
    const lastFocusable = focusableElements[focusableElements.length - 1] as HTMLElement;

    const handleTabKey = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return;

      if (event.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstFocusable) {
          event.preventDefault();
          lastFocusable.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastFocusable) {
          event.preventDefault();
          firstFocusable.focus();
        }
      }
    };

    // Focus the first focusable element when chat opens
    if (firstFocusable) {
      firstFocusable.focus();
    }

    chatElement.addEventListener('keydown', handleTabKey);
    return () => chatElement.removeEventListener('keydown', handleTabKey);
  }, [isExpanded]);

  // Handle touch gestures for mobile swipe-to-close
  React.useEffect(() => {
    let touchStartY = 0;
    let touchStartTime = 0;


    const handleTouchStart = (e: TouchEvent) => {
      if (!isExpanded || window.innerWidth >= 768) return;
      
      touchStartY = e.touches[0].clientY;
      touchStartTime = Date.now();
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (!isExpanded || window.innerWidth >= 768 || !touchStartY) return;

      const touchCurrentY = e.touches[0].clientY;
      const diffY = touchCurrentY - touchStartY;
      const timeDiff = Date.now() - touchStartTime;

      // Swipe down to close (mobile only)
      if (diffY > 50 && timeDiff < 300) {
        toggleExpanded();
      }
    };

    const handleTouchEnd = () => {
      touchStartY = 0;
      touchStartTime = 0;
    };

    // Only add touch listeners on mobile devices
    if (typeof window !== 'undefined' && 'ontouchstart' in window) {
      document.addEventListener('touchstart', handleTouchStart, { passive: true });
      document.addEventListener('touchmove', handleTouchMove, { passive: true });
      document.addEventListener('touchend', handleTouchEnd, { passive: true });

      return () => {
        document.removeEventListener('touchstart', handleTouchStart);
        document.removeEventListener('touchmove', handleTouchMove);
        document.removeEventListener('touchend', handleTouchEnd);
      };
    }
  }, [isExpanded, toggleExpanded]);

  // Enhanced animation variants with responsive sizing and spring physics
  const chatVariants = {
    collapsed: {
      height: 60,
      width: 320,
      transition: {
        duration: 0.4,
        ease: [0.4, 0.0, 0.2, 1] as [number, number, number, number],
        type: "spring" as const,
        stiffness: 300,
        damping: 30
      }
    },
    expanded: {
      height: 500,
      width: 400,
      transition: {
        duration: 0.4,
        ease: [0.4, 0.0, 0.2, 1] as [number, number, number, number],
        type: "spring" as const,
        stiffness: 300,
        damping: 30
      }
    },
    // Mobile variants for full-width experience
    mobileCollapsed: {
      height: 60,
      width: '100vw',
      bottom: 0,
      right: 0,
      left: 0,
      transition: {
        duration: 0.3,
        ease: [0.4, 0.0, 0.2, 1] as [number, number, number, number]
      }
    },
    mobileExpanded: {
      height: '70vh',
      width: '100vw',
      bottom: 0,
      right: 0,
      left: 0,
      transition: {
        duration: 0.4,
        ease: [0.4, 0.0, 0.2, 1] as [number, number, number, number],
        type: "spring" as const,
        stiffness: 300,
        damping: 30
      }
    },
  };

  // Determine which variant to use based on screen size
  const getChatVariant = () => {
    if (typeof window !== 'undefined') {
      const isMobile = window.innerWidth < 768;
      if (isMobile) {
        return isExpanded ? 'mobileExpanded' : 'mobileCollapsed';
      }
    }
    return isExpanded ? 'expanded' : 'collapsed';
  };



  return (
    <>
      {/* Mobile backdrop overlay */}
      <AnimatePresence>
        {isExpanded && typeof window !== 'undefined' && window.innerWidth < 768 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/30 z-40 md:hidden"
            onClick={toggleExpanded}
            aria-hidden="true"
          />
        )}
      </AnimatePresence>

      <motion.div
        ref={chatRef}
        className={cn(
          'fixed z-50 bg-white border border-gray-200 shadow-lg overflow-hidden',
          // Mobile: full width at bottom, no margin
          'bottom-0 right-0 left-0 mx-0',
          // Desktop: positioned at bottom-right with margin
          'md:bottom-4 md:right-4 md:left-auto md:mx-0',
          // Enhanced shadow for mobile overlay
          'shadow-2xl md:shadow-lg'
        )}
        variants={chatVariants}
        animate={getChatVariant()}
        initial={typeof window !== 'undefined' && window.innerWidth < 768 ? 'mobileCollapsed' : 'collapsed'}
        style={{
          borderRadius: typeof window !== 'undefined' && window.innerWidth < 768 
            ? (isExpanded ? '12px 12px 0 0' : '12px 12px 0 0')
            : '12px',
        }}
        role="dialog"
        aria-label="Compliance Assistant Chat"
        aria-describedby="chat-description"
      >
      {/* Chat Header with enhanced interactions */}
      <motion.button
        className={cn(
          'flex items-center justify-between bg-blue-600 text-white cursor-pointer select-none w-full text-left transform-gpu',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-blue-600',
          'hover:bg-blue-700 active:bg-blue-800 transition-colors duration-150',
          // Enhanced touch target for mobile
          'touch-target min-h-[60px] p-3',
          // Mobile-specific styling
          'md:min-h-[48px] md:p-3'
        )}
        animate={{ 
          borderRadius: typeof window !== 'undefined' && window.innerWidth < 768
            ? '12px 12px 0 0'
            : (isExpanded ? '12px 12px 0 0' : '12px')
        }}
        transition={{ duration: 0.2 }}
        whileHover={{ scale: 1.01 }}
        whileTap={{ scale: 0.99 }}
        onClick={toggleExpanded}
        aria-label={isExpanded ? 'Collapse chat (Escape or Ctrl+/)' : 'Expand chat (Ctrl+/)'}
        aria-expanded={isExpanded}
        aria-controls="chat-content"
        type="button"
      >
        <div className="flex items-center gap-2">
          <MessageCircle size={20} />
          <span className="font-medium text-sm">
            {isExpanded ? 'Compliance Assistant' : 'Chat'}
          </span>
          
          {/* Unread message indicator */}
          <AnimatePresence>
            {unreadCount > 0 && !isExpanded && (
              <motion.div
                className="bg-red-500 text-white text-xs rounded-full min-w-[20px] h-5 flex items-center justify-center px-1"
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                {unreadCount > 99 ? '99+' : unreadCount}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className="flex items-center gap-1">
          {/* Loading indicator */}
          {isLoading && (
            <motion.div
              className="w-4 h-4 border-2 border-white border-t-transparent rounded-full"
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
            />
          )}
          
          {/* Expand/Collapse icon with enhanced animation */}
          <motion.div
            animate={{ 
              rotate: isExpanded ? 180 : 0,
              scale: isExpanded ? 1.1 : 1
            }}
            transition={{ 
              duration: 0.3,
              type: "spring",
              stiffness: 400,
              damping: 25
            }}
            whileHover={{ scale: 1.2 }}
            whileTap={{ scale: 0.9 }}
            aria-hidden="true"
          >
            {isExpanded ? <Minimize2 size={16} /> : <MessageCircle size={16} />}
          </motion.div>
        </div>
      </motion.button>

      {/* Chat Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            id="chat-content"
            className="h-full"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.2, delay: 0.1 }}
            role="region"
            aria-label="Chat conversation"
          >
            <Suspense fallback={
              <div className="flex items-center justify-center h-full p-4">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
              </div>
            }>
              <LazyLoadedChatWindow
                messages={messages}
                isLoading={isLoading}
                onSendMessage={sendMessage}
                onClearHistory={clearHistory}
              />
            </Suspense>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Collapsed state preview */}
      {!isExpanded && messages.length > 0 && (
        <div className="px-3 pb-2">
          <div className="text-xs text-gray-600 truncate" aria-hidden="true">
            {messages[messages.length - 1]?.content || 'Start a conversation...'}
          </div>
        </div>
      )}

      {/* Hidden description for screen readers */}
      <div id="chat-description" className="sr-only">
        AI-powered compliance assistant. Use Ctrl+/ to toggle, Escape to close when expanded.
        {unreadCount > 0 && ` ${unreadCount} unread messages.`}
      </div>
      </motion.div>

      {/* ARIA live region for chat announcements */}
      <div
        id="chat-announcements"
        className="sr-only"
        aria-live="polite"
        aria-atomic="true"
      />
    </>
  );
};

PersistentChatComponent.displayName = 'PersistentChat';

export const PersistentChat = React.memo(PersistentChatComponent);