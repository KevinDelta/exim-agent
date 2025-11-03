import { useState, useCallback, useRef } from 'react';
import { 
  ComplianceSnapshot, 
  SnapshotRequest,
  ChatRequest,
  ApiError 
} from '@/lib/types';
import { getComplianceSnapshotWithRetry, sendChatMessageWithRetry } from '@/lib/api';

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
      // Prepare enhanced message with compliance context
      let enhancedMessage = message;
      
      if (context?.hasComplianceData && context.snapshotSummary) {
        const contextInfo = [
          `Current compliance context:`,
          context.htsCode ? `- HTS Code: ${context.htsCode}` : '',
          context.laneId ? `- Trade Lane: ${context.laneId}` : '',
          context.snapshotSummary.riskLevel ? `- Risk Level: ${context.snapshotSummary.riskLevel}` : '',
          context.snapshotSummary.alertCount !== undefined ? `- Active Alerts: ${context.snapshotSummary.alertCount}` : '',
          context.snapshotSummary.tiles ? `- Analysis Areas: ${context.snapshotSummary.tiles.join(', ')}` : '',
          '',
          `User question: ${message}`
        ].filter(Boolean).join('\n');
        
        enhancedMessage = contextInfo;
      }

      const chatRequest: ChatRequest = {
        message: enhancedMessage
        // Note: Mem0 handles conversation history automatically
      };

      const response = await sendChatMessageWithRetry(chatRequest);

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
        throw new Error(response.error || 'Failed to get response from chat service');
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
  }, []);

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