import { Metadata } from 'next';
import { DemoSnapshotCard } from '@/components/snapshot-card';
import { ContentArea } from '@/components/layout';

export const metadata: Metadata = {
  title: 'Compliance - Compliance Intelligence Platform',
  description: 'Real-time compliance monitoring and risk assessment dashboard',
};

export default function CompliancePage() {
  return (
    <ContentArea>
      <div role="main" aria-label="Compliance Monitoring Dashboard">
        {/* Page header */}
        <header className="text-center mb-6 sm:mb-8 lg:mb-12" role="banner">
          <h1 className="text-responsive-4xl font-bold tracking-tight mb-2 sm:mb-4">
            Compliance Dashboard
          </h1>
          <p className="text-responsive-lg text-muted-foreground mb-2 max-w-4xl mx-auto">
            Real-time compliance monitoring and risk assessment for international trade operations
          </p>
          <p className="text-responsive-sm text-muted-foreground max-w-2xl mx-auto">
            Monitor compliance status, track risk levels, and receive intelligent alerts
          </p>
        </header>
        
        {/* Main Compliance Snapshot Card */}
        <section 
          className="mb-6 sm:mb-8 lg:mb-12"
          aria-labelledby="compliance-snapshot-heading"
        >
          <h2 id="compliance-snapshot-heading" className="sr-only">
            Current Compliance Snapshot
          </h2>
          <DemoSnapshotCard className="w-full" />
        </section>

        {/* Additional compliance information - responsive grid */}
        <section 
          className="grid grid-responsive-1-2-3 gap-responsive"
          aria-labelledby="compliance-features-heading"
        >
          <h2 id="compliance-features-heading" className="sr-only">
            Compliance Features
          </h2>
          
          <article className="bg-card border rounded-lg p-responsive hover:shadow-md transition-shadow duration-200 focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2">
            <h3 className="font-semibold text-responsive-lg mb-2" id="real-time-monitoring-heading">
              Real-time Monitoring
            </h3>
            <p className="text-responsive-sm text-muted-foreground leading-relaxed" aria-describedby="real-time-monitoring-heading">
              Continuous monitoring of trade compliance across multiple jurisdictions with instant alerts for violations.
            </p>
          </article>
          
          <article className="bg-card border rounded-lg p-responsive hover:shadow-md transition-shadow duration-200 focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2">
            <h3 className="font-semibold text-responsive-lg mb-2" id="risk-analysis-heading">
              Risk Analysis
            </h3>
            <p className="text-responsive-sm text-muted-foreground leading-relaxed" aria-describedby="risk-analysis-heading">
              AI-powered risk assessment with predictive analytics to identify potential compliance issues before they occur.
            </p>
          </article>
          
          <article className="bg-card border rounded-lg p-responsive hover:shadow-md transition-shadow duration-200 sm:col-span-2 lg:col-span-1 focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2">
            <h3 className="font-semibold text-responsive-lg mb-2" id="regulatory-updates-heading">
              Regulatory Updates
            </h3>
            <p className="text-responsive-sm text-muted-foreground leading-relaxed" aria-describedby="regulatory-updates-heading">
              Stay informed with real-time regulatory changes and their impact on your trade operations and compliance requirements.
            </p>
          </article>
        </section>
      </div>
    </ContentArea>
  );
}