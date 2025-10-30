// Chat state management using Zustand

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { ChatState, ChatMessage } from '@/types/chat';

// Generate a unique session ID
const generateSessionId = (): string => {
  return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      messages: [],
      isExpanded: false,
      unreadCount: 0,
      isLoading: false,
      sessionId: generateSessionId(),
      
      addMessage: (message: ChatMessage) => {
        set((state) => ({
          messages: [...state.messages, message],
          unreadCount: message.role === 'assistant' && !state.isExpanded 
            ? state.unreadCount + 1 
            : state.unreadCount,
        }));
      },
      
      clearHistory: () => {
        set({
          messages: [],
          unreadCount: 0,
          sessionId: generateSessionId(),
        });
      },
      
      toggleExpanded: () => {
        set((state) => {
          const newExpanded = !state.isExpanded;
          return {
            isExpanded: newExpanded,
            unreadCount: newExpanded ? 0 : state.unreadCount, // Clear unread when expanding
          };
        });
      },
      
      markAsRead: () => {
        set({ unreadCount: 0 });
      },
      
      setLoading: (loading: boolean) => {
        set({ isLoading: loading });
      },
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({ 
        messages: state.messages,
        sessionId: state.sessionId,
        isExpanded: state.isExpanded,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          // Convert timestamp strings back to Date objects after rehydration
          state.messages = state.messages.map((message: ChatMessage) => ({
            ...message,
            timestamp: new Date(message.timestamp),
          }));
        }
      },
    }
  )
);