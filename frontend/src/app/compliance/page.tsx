'use client';

import { Metadata } from 'next';
import { ComplianceWorkflow } from '@/components/compliance/ComplianceWorkflow';
import { ContentArea } from '@/components/layout';

// Note: metadata export removed since this is now a client component
// The metadata will be handled by the parent layout or a separate metadata API

export default function CompliancePage() {
  return (
    <ContentArea className="max-w-6xl">
      <div role="main" aria-label="Interactive Compliance Dashboard">
        {/* Page header */}
        <header className="mb-6 sm:mb-8" role="banner">
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-2">
            Compliance Dashboard
          </h1>
          <p className="text-lg text-muted-foreground mb-2">
            Enter HTS code and lane information to get real-time compliance analysis
          </p>
          <p className="text-sm text-muted-foreground">
            Use the chat interface below to ask follow-up questions about your compliance data
          </p>
        </header>
        
        {/* Main Compliance Workflow */}
        <ComplianceWorkflow />
      </div>
    </ContentArea>
  );
}