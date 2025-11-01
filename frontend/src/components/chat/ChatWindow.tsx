'use client';

import React, { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Trash2, Send } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ChatWindowProps } from '@/types/chat';
import { ChatHistory } from '.';
import { ChatInput } from '.';

/**
 * ChatWindow - Main chat interface when expanded
 * 
 * Features:
 * - Main chat interface with message display
 * - Message input and send functionality
 * - Chat history scrolling and management
 * - Clear history functionality
 */
export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  isLoading,
  onSendMessage,
  onClearHistory,
}) => {
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatContainerRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = chatContainerRef.current;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
      
      if (isNearBottom) {
        chatContainerRef.current.scrollTo({
          top: scrollHeight,
          behavior: 'smooth',
        });
      }
    }
  }, [messages]);

  // Announce new messages to screen readers
  useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.role === 'assistant') {
        const ariaLiveRegion = document.getElementById('chat-messages-live');
        if (ariaLiveRegion) {
          ariaLiveRegion.textContent = `Assistant: ${lastMessage.content}`;
        }
      }
    }
  }, [messages]);

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Chat Header with Actions */}
      <div className={cn(
        'flex items-center justify-between bg-white border-b border-gray-200',
        // Enhanced touch targets for mobile
        'p-3 min-h-[56px]',
        'md:p-3 md:min-h-[48px]'
      )} role="banner">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" aria-hidden="true" />
          <span className={cn(
            'text-gray-600',
            // Responsive text sizing
            'text-sm md:text-sm'
          )} aria-live="polite">
            {messages.length === 0 
              ? 'Start a conversation' 
              : `${messages.length} message${messages.length !== 1 ? 's' : ''}`
            }
          </span>
        </div>
        
        {messages.length > 0 && (
          <motion.button
            onClick={onClearHistory}
            className={cn(
              'flex items-center gap-1 text-red-600 hover:bg-red-50 rounded transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2',
              // Enhanced touch targets
              'touch-target min-h-[40px] px-3 py-2',
              'md:px-2 md:py-1 md:min-h-[32px]',
              'text-xs md:text-xs'
            )}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            aria-label="Clear all chat messages"
            type="button"
          >
            <Trash2 size={12} aria-hidden="true" />
            <span className="hidden sm:inline">Clear</span>
          </motion.button>
        )}
      </div>

      {/* Chat Messages Area */}
      <div
        ref={chatContainerRef}
        className={cn(
          'flex-1 overflow-y-auto space-y-3',
          // Responsive padding and height
          'p-2 md:p-3',
          // Mobile: use more screen space, Desktop: fixed height
          'max-h-[50vh] md:max-h-[320px]'
        )}
        role="log"
        aria-label="Chat messages"
        aria-live="polite"
        aria-relevant="additions"
      >
        {messages.length === 0 ? (
          <div className={cn(
            'flex flex-col items-center justify-center h-full text-center',
            // Responsive padding
            'py-6 px-4 md:py-8 md:px-6'
          )} role="status">
            <div className={cn(
              'bg-blue-100 rounded-full flex items-center justify-center mb-3',
              // Responsive icon size
              'w-10 h-10 md:w-12 md:h-12'
            )} aria-hidden="true">
              <Send size={20} className="text-blue-600 md:w-6 md:h-6" />
            </div>
            <h3 className={cn(
              'font-medium text-gray-900 mb-1',
              // Responsive text sizing
              'text-sm md:text-sm'
            )}>
              Welcome to Compliance Assistant
            </h3>
            <p className={cn(
              'text-gray-500 max-w-xs',
              // Responsive text sizing
              'text-xs md:text-xs'
            )}>
              Ask me anything about trade compliance, regulations, or document requirements.
            </p>
          </div>
        ) : (
          <ChatHistory messages={messages} isLoading={isLoading} />
        )}
        
        {/* Invisible element to mark end of messages for screen readers */}
        <div ref={messagesEndRef} aria-hidden="true" />
      </div>

      {/* Chat Input */}
      <div className="border-t border-gray-200 bg-white" role="region" aria-label="Message input">
        <ChatInput
          onSendMessage={onSendMessage}
          isLoading={isLoading}
        />
      </div>

      {/* ARIA live region for new messages */}
      <div
        id="chat-messages-live"
        className="sr-only"
        aria-live="polite"
        aria-atomic="false"
      />
    </div>
  );
};