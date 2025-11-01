import { ContentArea } from "@/components/layout";

export default function Home() {
  return (
    <ContentArea>
      <div role="main" aria-label="Compliance Intelligence Platform Dashboard">
          {/* Hero section with responsive text */}
          <header className="text-center mb-6 sm:mb-8 lg:mb-12" role="banner">
            <h1 className="text-responsive-4xl font-bold tracking-tight mb-2 sm:mb-4">
              Compliance Intelligence Platform
            </h1>
            <p className="text-responsive-lg text-muted-foreground mb-2 max-w-4xl mx-auto">
              AI-powered compliance monitoring and advisory services for international trade operations
            </p>
            <p className="text-responsive-sm text-muted-foreground max-w-2xl mx-auto">
              Real-time compliance monitoring dashboard with intelligent risk assessment
            </p>
          </header>

          {/* Additional dashboard information - responsive grid */}
          <section 
            className="grid grid-responsive-1-2-3 gap-responsive"
            aria-labelledby="platform-features-heading"
          >
            <h2 id="platform-features-heading" className="sr-only">
              Platform Features
            </h2>
            
            <article className="bg-card border rounded-lg p-responsive hover:shadow-md transition-shadow duration-200 focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2">
              <h3 className="font-semibold text-responsive-lg mb-2" id="live-monitoring-heading">
                Live Monitoring
              </h3>
              <p className="text-responsive-sm text-muted-foreground leading-relaxed" aria-describedby="live-monitoring-heading">
                Continuous monitoring of trade compliance across multiple jurisdictions and regulatory frameworks.
              </p>
            </article>
            
            <article className="bg-card border rounded-lg p-responsive hover:shadow-md transition-shadow duration-200 focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2">
              <h3 className="font-semibold text-responsive-lg mb-2" id="risk-assessment-heading">
                Risk Assessment
              </h3>
              <p className="text-responsive-sm text-muted-foreground leading-relaxed" aria-describedby="risk-assessment-heading">
                AI-powered risk analysis with real-time alerts for compliance violations and regulatory changes.
              </p>
            </article>
            
            <article className="bg-card border rounded-lg p-responsive hover:shadow-md transition-shadow duration-200 sm:col-span-2 lg:col-span-1 focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2">
              <h3 className="font-semibold text-responsive-lg mb-2" id="intelligent-insights-heading">
                Intelligent Insights
              </h3>
              <p className="text-responsive-sm text-muted-foreground leading-relaxed" aria-describedby="intelligent-insights-heading">
                Advanced analytics and recommendations to optimize compliance processes and reduce operational risk.
              </p>
            </article>
          </section>
      </div>
    </ContentArea>
  );
}
