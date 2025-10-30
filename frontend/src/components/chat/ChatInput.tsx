'use client';

import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Send, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { ChatInputProps } from '@/types/chat';

/**
 * ChatInput - Message input component with send functionality
 * 
 * Features:
 * - Auto-resizing textarea
 * - Send on Enter (Shift+Enter for new line)
 * - Loading state handling
 * - Character limit and validation
 */
export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isLoading,
  disabled = false,
}) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const maxLength = 1000;

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [message]);

  // Focus textarea when component mounts
  useEffect(() => {
    if (textareaRef.current && !disabled) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  // Handle message submission
  const handleSubmit = () => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage || isLoading || disabled) return;
    
    onSendMessage(trimmedMessage);
    setMessage('');
    
    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  // Handle key press events
  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Handle input change
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    if (value.length <= maxLength) {
      setMessage(value);
    }
  };

  const isDisabled = disabled || isLoading;
  const canSend = message.trim().length > 0 && !isDisabled;

  return (
    <div className={cn(
      // Enhanced padding for mobile touch targets
      'p-3 md:p-3',
      // Ensure proper spacing from screen edges on mobile
      'pb-safe-area-inset-bottom'
    )}>
      <div className="flex gap-2 items-end">
        {/* Message Input */}
        <div className="flex-1 relative">
          <label htmlFor="chat-message-input" className="sr-only">
            Type your message about compliance, regulations, or documents
          </label>
          <textarea
            id="chat-message-input"
            ref={textareaRef}
            value={message}
            onChange={handleChange}
            onKeyPress={handleKeyPress}
            placeholder={isDisabled ? 'Please wait...' : 'Ask about compliance, regulations, or documents...'}
            disabled={isDisabled}
            className={cn(
              'w-full resize-none rounded-lg border border-gray-300 transition-all',
              // Enhanced touch targets for mobile
              'px-3 py-3 md:py-2',
              'text-sm md:text-sm',
              // Better focus states
              'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
              // Responsive styling
              'min-h-[48px] md:min-h-[40px]',
              isDisabled 
                ? 'bg-gray-100 text-gray-500 cursor-not-allowed' 
                : 'bg-white text-gray-900'
            )}
            style={{
              maxHeight: '120px',
            }}
            rows={1}
            aria-describedby="chat-input-help"
            aria-invalid={message.length > maxLength}
          />
          
          {/* Character counter */}
          {message.length > maxLength * 0.8 && (
            <div 
              className={cn(
                'absolute bottom-1 right-2 text-xs',
                message.length >= maxLength ? 'text-red-500' : 'text-gray-400'
              )}
              aria-live="polite"
              aria-label={`${message.length} of ${maxLength} characters used`}
            >
              {message.length}/{maxLength}
            </div>
          )}
        </div>

        {/* Send Button */}
        <motion.button
          onClick={handleSubmit}
          disabled={!canSend}
          className={cn(
            'flex items-center justify-center rounded-lg transition-all',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2',
            // Enhanced touch targets for mobile
            'touch-target min-h-[48px] min-w-[48px]',
            'md:w-10 md:h-10 md:min-h-[40px] md:min-w-[40px]',
            canSend
              ? 'bg-blue-600 text-white hover:bg-blue-700 active:bg-blue-800 shadow-sm'
              : 'bg-gray-200 text-gray-400 cursor-not-allowed'
          )}
          whileHover={canSend ? { scale: 1.05 } : {}}
          whileTap={canSend ? { scale: 0.95 } : {}}
          type="submit"
          aria-label={isLoading ? 'Sending message...' : 'Send message'}
          aria-describedby="send-button-help"
        >
          {isLoading ? (
            <Loader2 size={16} className="animate-spin md:w-4 md:h-4" aria-hidden="true" />
          ) : (
            <Send size={16} className="md:w-4 md:h-4" aria-hidden="true" />
          )}
        </motion.button>
      </div>

      {/* Helper text - hide on mobile to save space */}
      <div id="chat-input-help" className="mt-2 text-xs text-gray-500 hidden md:block">
        Press Enter to send, Shift+Enter for new line
      </div>
      
      {/* Hidden help text for screen readers */}
      <div id="send-button-help" className="sr-only">
        {canSend ? 'Click to send your message' : 'Type a message to enable sending'}
      </div>
    </div>
  );
};