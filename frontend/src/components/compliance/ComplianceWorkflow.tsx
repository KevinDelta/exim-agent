'use client';

import React, { useCallback } from 'react';
import { ComplianceInputForm } from './ComplianceInputForm';
import { ComplianceSnapshot } from './ComplianceSnapshot';
import { ComplianceChat } from './ComplianceChat';
import { useComplianceWorkflow } from '@/hooks/useComplianceWorkflow';
import { Card } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { AlertCircle, MessageSquare } from 'lucide-react';

/**
 * ComplianceWorkflow - Main orchestrator for the integrated compliance experience
 * 
 * Flow:
 * 1. User enters HTS code and lane information
 * 2. System fetches compliance snapshot from backend
 * 3. User can chat with context-aware AI about the compliance data
 * 4. Chat responses can trigger new compliance queries
 */
export function ComplianceWorkflow() {
  const {
    // Input state
    htsCode,
    laneId,
    setHtsCode,
    setLaneId,
    
    // Compliance data
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
  } = useComplianceWorkflow();

  // Show chat when we have compliance data
  const showChat = !!snapshot;

  const handleInputSubmit = useCallback(async (hts: string, lane: string) => {
    setHtsCode(hts);
    setLaneId(lane);
    await fetchSnapshot({
      client_id: 'default-client', // TODO: Get from user context
      sku_id: `sku-${hts}`, // Generate SKU from HTS for now
      lane_id: lane,
      hts_code: hts
    });
  }, [setHtsCode, setLaneId, fetchSnapshot]);

  const handleChatMessage = useCallback(async (message: string) => {
    // Send message with current compliance context
    await sendChatMessage(message, {
      htsCode: lastQueryParams?.hts_code,
      laneId: lastQueryParams?.lane_id,
      hasComplianceData: !!snapshot,
      snapshotSummary: snapshot ? {
        riskLevel: snapshot.snapshot?.overall_risk_level,
        alertCount: snapshot.snapshot?.active_alerts_count,
        tiles: Object.keys(snapshot.snapshot?.tiles || {})
      } : undefined
    });
  }, [sendChatMessage, lastQueryParams, snapshot]);

  return (
    <div className="space-y-6">
      {/* Input Form */}
      <Card className="p-6">
        <ComplianceInputForm
          initialHtsCode={htsCode}
          initialLaneId={laneId}
          onSubmit={handleInputSubmit}
          loading={snapshotLoading}
        />
      </Card>

      {/* Compliance Snapshot */}
      {(hasActiveQuery || snapshot || snapshotError) && (
        <Card className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertCircle className="h-5 w-5 text-primary" />
            <h2 className="text-xl font-semibold">Compliance Analysis</h2>
            {lastQueryParams && (
              <div className="text-sm text-muted-foreground ml-auto">
                HTS: {lastQueryParams.hts_code} • Lane: {lastQueryParams.lane_id}
              </div>
            )}
          </div>
          
          <ComplianceSnapshot
            snapshot={snapshot}
            loading={snapshotLoading}
            error={snapshotError}
            onRefresh={() => lastQueryParams && fetchSnapshot(lastQueryParams)}
          />
        </Card>
      )}

      {/* Chat Interface */}
      {showChat && (
        <>
          <Separator className="my-6" />
          
          <Card className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <MessageSquare className="h-5 w-5 text-primary" />
              <h2 className="text-xl font-semibold">Compliance Assistant</h2>
              <div className="text-sm text-muted-foreground ml-auto">
                Ask questions about your compliance data
              </div>
            </div>
            
            <ComplianceChat
              messages={chatMessages}
              loading={chatLoading}
              onSendMessage={handleChatMessage}
              onClearHistory={clearChatHistory}
              complianceContext={{
                htsCode: lastQueryParams?.hts_code,
                laneId: lastQueryParams?.lane_id,
                hasData: !!snapshot,
                riskLevel: snapshot?.snapshot?.overall_risk_level
              }}
            />
          </Card>
        </>
      )}

      {/* Help Text */}
      {!hasActiveQuery && (
        <Card className="p-6 bg-muted/50">
          <div className="text-center space-y-2">
            <h3 className="font-medium">Get Started</h3>
            <p className="text-sm text-muted-foreground max-w-2xl mx-auto">
              Enter an HTS code and lane information above to get a comprehensive compliance analysis. 
              Once you have results, you can use the chat interface to ask specific questions about 
              your compliance data, regulations, or get recommendations.
            </p>
          </div>
        </Card>
      )}
    </div>
  );
}