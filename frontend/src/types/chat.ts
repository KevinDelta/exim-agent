// Chat system types for the Compliance Intelligence Platform

// Core chat interfaces
export interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  metadata?: Record<string, unknown>;
}

export interface ChatState {
  messages: ChatMessage[];
  isExpanded: boolean;
  unreadCount: number;
  isLoading: boolean;
  sessionId: string;
  addMessage: (message: ChatMessage) => void;
  clearHistory: () => void;
  toggleExpanded: () => void;
  markAsRead: () => void;
  setLoading: (loading: boolean) => void;
}

// Component prop interfaces
export interface PersistentChatProps {
  isExpanded: boolean;
  onToggle: () => void;
  unreadCount: number;
}

export interface ChatWindowProps {
  messages: ChatMessage[];
  isLoading: boolean;
  onSendMessage: (message: string) => void;
  onClearHistory: () => void;
}

export interface ChatInputProps {
  onSendMessage: (message: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export interface ChatHistoryProps {
  messages: ChatMessage[];
  isLoading: boolean;
}

// API interfaces
export interface ChatApiClient {
  sendMessage: (message: string, sessionId: string) => Promise<ChatResponse>;
  getChatHistory: (sessionId: string) => Promise<ChatMessage[]>;
  clearChatHistory: (sessionId: string) => Promise<void>;
}

export interface ChatResponse {
  message: string;
  sessionId: string;
  metadata?: Record<string, unknown>;
}

// Error handling
export interface ChatError {
  type: 'network' | 'server' | 'validation' | 'timeout';
  message: string;
  retryable: boolean;
  timestamp: Date;
}