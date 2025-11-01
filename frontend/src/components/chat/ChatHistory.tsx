'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { User, Bot, AlertCircle } from 'lucide-react';
import { ChatHistoryProps, ChatMessage } from '@/types/chat';

/**
 * ChatHistory - Display chat messages with proper formatting
 * 
 * Features:
 * - Message display with role-based styling
 * - Timestamp formatting
 * - Error message handling
 * - Smooth animations for new messages
 */
export const ChatHistory: React.FC<ChatHistoryProps> = ({
  messages,
  isLoading,
}) => {
  // Format timestamp for display
  const formatTimestamp = (timestamp: Date | string) => {
    const messageTime = timestamp instanceof Date ? timestamp : new Date(timestamp);
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - messageTime.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'Just now';
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    if (diffInMinutes < 1440) return `${Math.floor(diffInMinutes / 60)}h ago`;
    
    return messageTime.toLocaleDateString();
  };



  // Render individual message
  const renderMessage = (message: ChatMessage) => {
    const isUser = message.role === 'user';
    const isError = message.metadata?.error;
    
    return (
      <motion.div
        key={message.id}
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.3 }}
        layout
        className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
        role="article"
        aria-label={`Message from ${isUser ? 'you' : 'assistant'} at ${formatTimestamp(message.timestamp)}`}
      >
        {/* Avatar */}
        <div 
          className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
            isUser 
              ? 'bg-blue-600 text-white' 
              : isError 
                ? 'bg-red-100 text-red-600'
                : 'bg-gray-100 text-gray-600'
          }`}
          aria-hidden="true"
        >
          {isUser ? (
            <User size={16} />
          ) : isError ? (
            <AlertCircle size={16} />
          ) : (
            <Bot size={16} />
          )}
        </div>

        {/* Message Content */}
        <div className={`flex-1 max-w-[280px] ${isUser ? 'text-right' : 'text-left'}`}>
          <div 
            className={`inline-block p-3 rounded-lg text-sm ${
              isUser
                ? 'bg-blue-600 text-white rounded-br-sm'
                : isError
                  ? 'bg-red-50 text-red-800 border border-red-200 rounded-bl-sm'
                  : 'bg-white text-gray-800 border border-gray-200 rounded-bl-sm'
            }`}
            role={isError ? 'alert' : undefined}
            aria-label={isError ? 'Error message' : undefined}
          >
            <div className="whitespace-pre-wrap break-words">
              {message.content}
            </div>
            
            {/* Metadata display for assistant messages */}
            {!isUser && message.metadata && !isError && (
              <div className="mt-2 pt-2 border-t border-gray-100 text-xs text-gray-500">
                {typeof message.metadata.processingTime === 'number' && (
                  <span>Processed in {message.metadata.processingTime}ms</span>
                )}
              </div>
            )}
          </div>
          
          {/* Timestamp */}
          <div 
            className={`text-xs text-gray-400 mt-1 ${isUser ? 'text-right' : 'text-left'}`}
            aria-label={`Sent ${formatTimestamp(message.timestamp)}`}
          >
            <time dateTime={(message.timestamp instanceof Date ? message.timestamp : new Date(message.timestamp)).toISOString()}>
              {formatTimestamp(message.timestamp)}
            </time>
          </div>
        </div>
      </motion.div>
    );
  };

  return (
    <div className="space-y-4">
      <AnimatePresence mode="popLayout">
        {messages.map((message) => renderMessage(message))}
      </AnimatePresence>
      
      {/* Loading indicator */}
      {isLoading && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          className="flex gap-3"
          role="status"
          aria-label="Assistant is typing"
        >
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center" aria-hidden="true">
            <Bot size={16} className="text-gray-600" />
          </div>
          <div className="flex-1">
            <div className="inline-block p-3 bg-white border border-gray-200 rounded-lg rounded-bl-sm">
              <div className="flex gap-1" aria-hidden="true">
                <motion.div
                  className="w-2 h-2 bg-gray-400 rounded-full"
                  animate={{ opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 1.5, repeat: Infinity, delay: 0 }}
                />
                <motion.div
                  className="w-2 h-2 bg-gray-400 rounded-full"
                  animate={{ opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 1.5, repeat: Infinity, delay: 0.2 }}
                />
                <motion.div
                  className="w-2 h-2 bg-gray-400 rounded-full"
                  animate={{ opacity: [0.4, 1, 0.4] }}
                  transition={{ duration: 1.5, repeat: Infinity, delay: 0.4 }}
                />
              </div>
              <span className="sr-only">Assistant is typing a response</span>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  );
};