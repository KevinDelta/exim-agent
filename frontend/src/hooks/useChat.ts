// Custom hook for chat functionality

import { useCallback } from 'react';
import { useChatStore } from '@/stores/chatStore';
import { ChatMessage, ChatError } from '@/types/chat';

export const useChat = () => {
  const {
    messages,
    isExpanded,
    unreadCount,
    isLoading,
    sessionId,
    addMessage,
    clearHistory,
    toggleExpanded,
    markAsRead,
    setLoading,
  } = useChatStore();

  // Send a message to the chat API
  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isLoading) return;

    // Create user message
    const userMessage: ChatMessage = {
      id: `msg_${Date.now()}_user`,
      content: content.trim(),
      role: 'user',
      timestamp: new Date(),
    };

    // Add user message immediately
    addMessage(userMessage);
    setLoading(true);

    try {
      // Prepare conversation history for API
      const conversationHistory = messages.map(msg => ({
        role: msg.role,
        content: msg.content,
      }));

      // Add the current user message to history
      conversationHistory.push({
        role: 'user',
        content: content.trim(),
      });

      // Call the actual chat API
      const { sendChatMessageWithRetry } = await import('@/lib/api');
      const response = await sendChatMessageWithRetry({
        message: content.trim(),
        conversation_history: conversationHistory,
        stream: false,
      });

      if (response.success && response.response) {
        const assistantMessage: ChatMessage = {
          id: `msg_${Date.now()}_assistant`,
          content: response.response,
          role: 'assistant',
          timestamp: new Date(),
          metadata: {
            sessionId,
            success: true,
          },
        };

        addMessage(assistantMessage);
      } else {
        throw new Error(response.error || 'Failed to get response from chat service');
      }
    } catch (error) {
      console.error('Chat API error:', error);
      
      // Handle error by adding error message
      const errorMessage: ChatMessage = {
        id: `msg_${Date.now()}_error`,
        content: 'Sorry, I encountered an error processing your message. Please try again.',
        role: 'assistant',
        timestamp: new Date(),
        metadata: {
          error: true,
          sessionId,
          errorDetails: error instanceof Error ? error.message : 'Unknown error',
        },
      };

      addMessage(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [addMessage, setLoading, isLoading, sessionId, messages]);

  // Toggle chat expansion and mark as read
  const handleToggleExpanded = useCallback(() => {
    toggleExpanded();
    if (!isExpanded) {
      markAsRead();
    }
  }, [toggleExpanded, isExpanded, markAsRead]);

  // Clear chat history with confirmation
  const handleClearHistory = useCallback(() => {
    if (messages.length > 0) {
      const confirmed = window.confirm('Are you sure you want to clear the chat history?');
      if (confirmed) {
        clearHistory();
      }
    }
  }, [clearHistory, messages.length]);

  // Get last message
  const getLastMessage = useCallback(() => {
    return messages.length > 0 ? messages[messages.length - 1] : null;
  }, [messages]);

  // Get messages by role
  const getMessagesByRole = useCallback((role: 'user' | 'assistant') => {
    return messages.filter(message => message.role === role);
  }, [messages]);

  // Check if chat has messages
  const hasMessages = messages.length > 0;

  // Check if last message was from assistant
  const lastMessageFromAssistant = useCallback(() => {
    const lastMessage = getLastMessage();
    return lastMessage?.role === 'assistant';
  }, [getLastMessage]);

  return {
    // State
    messages,
    isExpanded,
    unreadCount,
    isLoading,
    sessionId,
    hasMessages,
    
    // Actions
    sendMessage,
    clearHistory: handleClearHistory,
    toggleExpanded: handleToggleExpanded,
    markAsRead,
    
    // Utilities
    getLastMessage,
    getMessagesByRole,
    lastMessageFromAssistant,
  };
};