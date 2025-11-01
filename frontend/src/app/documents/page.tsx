import { Metadata } from 'next';
import { DocumentUpload } from '@/components/documents/DocumentUpload';
import { ContentArea } from '@/components/layout';

export const metadata: Metadata = {
  title: 'Documents - Compliance Intelligence Platform',
  description: 'Upload and manage compliance documents for analysis and monitoring',
};

export default function DocumentsPage() {
  return (
    <ContentArea className="max-w-4xl">
      <div role="main" aria-label="Document Upload Interface">
          {/* Page header */}
          <header className="mb-6 sm:mb-8" role="banner">
            <h1 className="text-responsive-3xl font-bold tracking-tight mb-2">
              Document Upload
            </h1>
            <p className="text-responsive-lg text-muted-foreground">
              Upload compliance documents for analysis and monitoring
            </p>
            <p className="text-responsive-sm text-muted-foreground mt-2">
              Supported formats: PDF, TXT, CSV, EPUB
            </p>
          </header>
          
          {/* Main upload interface */}
          <section 
            className="mb-6"
            aria-labelledby="upload-section-heading"
          >
            <h2 id="upload-section-heading" className="sr-only">
              Document Upload Interface
            </h2>
            <DocumentUpload />
          </section>
      </div>
    </ContentArea>
  );
}