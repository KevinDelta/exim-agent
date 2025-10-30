'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { Send, Trash2, Bot, User, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

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

interface ComplianceContext {
  htsCode?: string;
  laneId?: string;
  hasData: boolean;
  riskLevel?: string;
}

interface ComplianceChatProps {
  messages: ChatMessage[];
  loading: boolean;
  onSendMessage: (message: string) => Promise<void>;
  onClearHistory: () => void;
  complianceContext?: ComplianceContext;
}

/**
 * ComplianceChat - Context-aware chat interface for compliance questions
 * 
 * Features:
 * - Context-aware responses based on current compliance data
 * - Suggested questions based on compliance results
 * - Message history with compliance context indicators
 * - Real-time typing indicators
 */
export function ComplianceChat({
  messages,
  loading,
  onSendMessage,
  onClearHistory,
  complianceContext
}: ComplianceChatProps) {
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when component mounts
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSendMessage = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!inputMessage.trim() || loading) {
      return;
    }

    const message = inputMessage.trim();
    setInputMessage('');
    setIsTyping(true);

    try {
      await onSendMessage(message);
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsTyping(false);
    }
  }, [inputMessage, loading, onSendMessage]);

  const handleSuggestedQuestion = useCallback(async (question: string) => {
    setIsTyping(true);
    try {
      await onSendMessage(question);
    } catch (error) {
      console.error('Failed to send suggested question:', error);
    } finally {
      setIsTyping(false);
    }
  }, [onSendMessage]);

  // Generate suggested questions based on compliance context
  const getSuggestedQuestions = useCallback(() => {
    if (!complianceContext?.hasData) {
      return [
        "What information do I need for a compliance analysis?",
        "How do HTS codes affect import compliance?",
        "What are the main compliance risks for international trade?"
      ];
    }

    const suggestions = [];
    
    if (complianceContext.htsCode) {
      suggestions.push(`What are the specific requirements for HTS ${complianceContext.htsCode}?`);
      suggestions.push(`Are there any recent changes to regulations for ${complianceContext.htsCode}?`);
    }
    
    if (complianceContext.laneId) {
      suggestions.push(`What are the trade requirements for ${complianceContext.laneId}?`);
      suggestions.push(`Are there any sanctions affecting ${complianceContext.laneId}?`);
    }
    
    if (complianceContext.riskLevel === 'high') {
      suggestions.push("What steps should I take to reduce compliance risk?");
      suggestions.push("What are the potential consequences of these compliance issues?");
    }
    
    suggestions.push("Can you explain the compliance analysis results?");
    suggestions.push("What documentation do I need for customs clearance?");
    
    return suggestions.slice(0, 3); // Limit to 3 suggestions
  }, [complianceContext]);

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const suggestedQuestions = getSuggestedQuestions();

  return (
    <div className="space-y-4">
      {/* Context Indicator */}
      {complianceContext && (
        <div className="flex flex-wrap items-center gap-2 p-3 bg-muted/50 rounded-lg">
          <span className="text-sm font-medium">Context:</span>
          {complianceContext.htsCode && (
            <Badge variant="outline" className="text-xs">
              HTS: {complianceContext.htsCode}
            </Badge>
          )}
          {complianceContext.laneId && (
            <Badge variant="outline" className="text-xs">
              Lane: {complianceContext.laneId}
            </Badge>
          )}
          {complianceContext.hasData && (
            <Badge variant="secondary" className="text-xs">
              Compliance Data Available
            </Badge>
          )}
        </div>
      )}

      {/* Messages */}
      <Card className="h-96">
        <ScrollArea className="h-full p-4">
          <div className="space-y-4">
            {messages.length === 0 ? (
              <div className="text-center text-muted-foreground py-8">
                <Bot className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">
                  {complianceContext?.hasData 
                    ? "Ask me anything about your compliance analysis results"
                    : "I'm here to help with compliance questions. Start by entering HTS and lane information above."
                  }
                </p>
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={cn(
                    'flex gap-3',
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  )}
                >
                  {message.role === 'assistant' && (
                    <div className="flex-shrink-0 w-8 h-8 bg-primary rounded-full flex items-center justify-center">
                      <Bot className="h-4 w-4 text-primary-foreground" />
                    </div>
                  )}
                  
                  <div
                    className={cn(
                      'max-w-[80%] rounded-lg px-3 py-2',
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted'
                    )}
                  >
                    <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                    <div className="flex items-center justify-between mt-1">
                      <span className="text-xs opacity-70">
                        {formatTimestamp(message.timestamp)}
                      </span>
                      {message.context && (
                        <div className="flex gap-1">
                          {message.context.htsCode && (
                            <Badge variant="outline" className="text-xs h-4 px-1">
                              {message.context.htsCode}
                            </Badge>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {message.role === 'user' && (
                    <div className="flex-shrink-0 w-8 h-8 bg-muted rounded-full flex items-center justify-center">
                      <User className="h-4 w-4" />
                    </div>
                  )}
                </div>
              ))
            )}
            
            {/* Typing indicator */}
            {(loading || isTyping) && (
              <div className="flex gap-3 justify-start">
                <div className="flex-shrink-0 w-8 h-8 bg-primary rounded-full flex items-center justify-center">
                  <Bot className="h-4 w-4 text-primary-foreground" />
                </div>
                <div className="bg-muted rounded-lg px-3 py-2">
                  <div className="flex items-center gap-1">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    <span className="text-sm text-muted-foreground">Thinking...</span>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
      </Card>

      {/* Suggested Questions */}
      {suggestedQuestions.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium">Suggested questions:</p>
          <div className="flex flex-wrap gap-2">
            {suggestedQuestions.map((question, index) => (
              <Button
                key={index}
                variant="outline"
                size="sm"
                onClick={() => handleSuggestedQuestion(question)}
                disabled={loading || isTyping}
                className="text-xs h-auto py-1 px-2 whitespace-normal text-left"
              >
                {question}
              </Button>
            ))}
          </div>
        </div>
      )}

      {/* Input Form */}
      <form onSubmit={handleSendMessage} className="flex gap-2">
        <Input
          ref={inputRef}
          value={inputMessage}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setInputMessage(e.target.value)}
          placeholder={
            complianceContext?.hasData
              ? "Ask about your compliance results..."
              : "Ask a compliance question..."
          }
          disabled={loading || isTyping}
          className="flex-1"
          maxLength={500}
        />
        <Button
          type="submit"
          disabled={!inputMessage.trim() || loading || isTyping}
          size="icon"
        >
          <Send className="h-4 w-4" />
        </Button>
        {messages.length > 0 && (
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={onClearHistory}
            disabled={loading || isTyping}
            title="Clear chat history"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </form>

      {/* Character count */}
      <div className="text-xs text-muted-foreground text-right">
        {inputMessage.length}/500
      </div>
    </div>
  );
}