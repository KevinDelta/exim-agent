import { useState, useCallback, useRef } from 'react';
import { 
  ComplianceSnapshot, 
  SnapshotRequest,
  ChatRequest,
  AskRequest,
  ApiError 
} from '@/lib/types';
import { 
  getComplianceSnapshotWithRetry, 
  sendChatMessageWithRetry,
  askComplianceQuestionWithRetry 
} from '@/lib/api';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  context?: {
    htsCode?: string;
    laneId?: string;
    complianceData?: boolean;
  };
}

interface ChatContext {
  htsCode?: string;
  laneId?: string;
  hasComplianceData?: boolean;
  snapshotSummary?: {
    riskLevel?: string;
    alertCount?: number;
    tiles?: string[];
  };
}

interface UseComplianceWorkflowReturn {
  // Input state
  htsCode: string;
  laneId: string;
  setHtsCode: (code: string) => void;
  setLaneId: (id: string) => void;
  
  // Compliance snapshot state
  snapshot: ComplianceSnapshot | null;
  snapshotLoading: boolean;
  snapshotError: string | null;
  fetchSnapshot: (params: SnapshotRequest) => Promise<void>;
  
  // Chat state
  chatMessages: ChatMessage[];
  chatLoading: boolean;
  sendChatMessage: (message: string, context?: ChatContext) => Promise<void>;
  clearChatHistory: () => void;
  
  // Integration state
  hasActiveQuery: boolean;
  lastQueryParams: SnapshotRequest | null;
}

/**
 * useComplianceWorkflow - Main hook for the integrated compliance workflow
 * 
 * This hook manages the state and interactions between:
 * - User input (HTS code, lane)
 * - Compliance snapshot fetching
 * - Context-aware chat functionality
 * - Integration between compliance data and chat responses
 */
export function useComplianceWorkflow(): UseComplianceWorkflowReturn {
  // Input state
  const [htsCode, setHtsCode] = useState('');
  const [laneId, setLaneId] = useState('');
  
  // Compliance snapshot state
  const [snapshot, setSnapshot] = useState<ComplianceSnapshot | null>(null);
  const [snapshotLoading, setSnapshotLoading] = useState(false);
  const [snapshotError, setSnapshotError] = useState<string | null>(null);
  const [lastQueryParams, setLastQueryParams] = useState<SnapshotRequest | null>(null);
  
  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  
  // Refs for managing conversation context
  const messageIdCounter = useRef(0);

  // Fetch compliance snapshot
  const fetchSnapshot = useCallback(async (params: SnapshotRequest) => {
    setSnapshotLoading(true);
    setSnapshotError(null);
    setLastQueryParams(params);

    try {
      const result = await getComplianceSnapshotWithRetry(params);
      setSnapshot(result);
      
      // Add system message to chat about new compliance data
      if (result.success && result.snapshot) {
        const systemMessage: ChatMessage = {
          id: `system-${messageIdCounter.current++}`,
          role: 'assistant',
          content: `I've analyzed the compliance data for HTS ${params.hts_code} on lane ${params.lane_id}. The overall risk level is ${result.snapshot.overall_risk_level} with ${result.snapshot.active_alerts_count} active alerts. Feel free to ask me any questions about these results!`,
          timestamp: new Date(),
          context: {
            htsCode: params.hts_code,
            laneId: params.lane_id,
            complianceData: true
          }
        };
        
        setChatMessages(prev => [...prev, systemMessage]);
      }
    } catch (err) {
      const errorMessage = err instanceof ApiError 
        ? err.message 
        : err instanceof Error 
        ? err.message 
        : 'An unexpected error occurred';
      
      setSnapshotError(errorMessage);
      setSnapshot(null);
    } finally {
      setSnapshotLoading(false);
    }
  }, []);

  // Send chat message with compliance context
  const sendChatMessage = useCallback(async (message: string, context?: ChatContext) => {
    setChatLoading(true);

    // Add user message immediately
    const userMessage: ChatMessage = {
      id: `user-${messageIdCounter.current++}`,
      role: 'user',
      content: message,
      timestamp: new Date(),
      context: context ? {
        htsCode: context.htsCode,
        laneId: context.laneId,
        complianceData: context.hasComplianceData
      } : undefined
    };

    setChatMessages(prev => [...prev, userMessage]);

    try {
      // Use compliance ask endpoint when compliance context is available
      if (context?.hasComplianceData && lastQueryParams) {
        const askRequest: AskRequest = {
          client_id: lastQueryParams.client_id,
          question: message,
          sku_id: lastQueryParams.sku_id,
          lane_id: lastQueryParams.lane_id
        };

        const response = await askComplianceQuestionWithRetry(askRequest);

        // Debug logging
        if (process.env.NODE_ENV === 'development') {
          console.debug('[useComplianceWorkflow] Compliance ask response:', {
            success: response.success,
            hasAnswer: !!response.answer,
            error: response.error,
            citationsCount: response.citations?.length || 0
          });
        }

        // Handle response - AskResponse uses 'answer' instead of 'response'
        if (response.success && response.answer) {
          const assistantMessage: ChatMessage = {
            id: `assistant-${messageIdCounter.current++}`,
            role: 'assistant',
            content: response.answer,
            timestamp: new Date(),
            context: {
              htsCode: context.htsCode,
              laneId: context.laneId,
              complianceData: true
            }
          };

          setChatMessages(prev => [...prev, assistantMessage]);
        } else {
          const errorMsg = response.error || 'Failed to get answer from compliance service';
          throw new Error(errorMsg);
        }
      } else {
        // Fallback to generic chat endpoint when no compliance context
        const chatRequest: ChatRequest = {
          message: message
          // Note: Mem0 handles conversation history automatically
        };

        const response = await sendChatMessageWithRetry(chatRequest);

        // Debug logging to help identify root cause
        if (process.env.NODE_ENV === 'development') {
          console.debug('[useComplianceWorkflow] Chat response:', {
            success: response.success,
            hasResponse: !!response.response,
            error: response.error,
            responsePreview: response.response?.substring(0, 100)
          });
        }

        // Handle response - check for both success flag and actual response content
        if (response.success && response.response) {
          const assistantMessage: ChatMessage = {
            id: `assistant-${messageIdCounter.current++}`,
            role: 'assistant',
            content: response.response,
            timestamp: new Date(),
            context: context ? {
              htsCode: context.htsCode,
              laneId: context.laneId,
              complianceData: context.hasComplianceData
            } : undefined
          };

          setChatMessages(prev => [...prev, assistantMessage]);
        } else {
          // Backend returned success: false or missing response
          // Use error message if available, otherwise use response content if it exists
          const errorMsg = response.error || response.response || 'Failed to get response from chat service';
          throw new Error(errorMsg);
        }
      }
    } catch (err) {
      const errorMessage = err instanceof ApiError 
        ? err.message 
        : err instanceof Error 
        ? err.message 
        : 'Failed to send message';

      const errorResponse: ChatMessage = {
        id: `error-${messageIdCounter.current++}`,
        role: 'assistant',
        content: `I apologize, but I encountered an error: ${errorMessage}. Please try again.`,
        timestamp: new Date()
      };

      setChatMessages(prev => [...prev, errorResponse]);
    } finally {
      setChatLoading(false);
    }
  }, [lastQueryParams]);

  // Clear chat history
  const clearChatHistory = useCallback(() => {
    setChatMessages([]);
    messageIdCounter.current = 0;
  }, []);

  const hasActiveQuery = !!lastQueryParams;

  return {
    // Input state
    htsCode,
    laneId,
    setHtsCode,
    setLaneId,
    
    // Compliance snapshot state
    snapshot,
    snapshotLoading,
    snapshotError,
    fetchSnapshot,
    
    // Chat state
    chatMessages,
    chatLoading,
    sendChatMessage,
    clearChatHistory,
    
    // Integration state
    hasActiveQuery,
    lastQueryParams
  };
}