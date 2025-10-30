import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ErrorBoundary } from "@/components/error-boundary";
import { AppLayout } from "@/components/layout";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Compliance Intelligence Platform",
  description: "AI-powered compliance monitoring and advisory services for international trade operations",
  keywords: ["compliance", "trade", "international", "monitoring", "AI"],
  authors: [{ name: "Compliance Intelligence Platform" }],
  openGraph: {
    title: "Compliance Intelligence Platform",
    description: "AI-powered compliance monitoring and advisory services for international trade operations",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Compliance Intelligence Platform",
    description: "AI-powered compliance monitoring and advisory services for international trade operations",
  },
};

export const viewport = {
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="scroll-smooth">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {/* Skip to main content link for keyboard navigation */}
        <a 
          href="#main-content" 
          className="skip-link focus-visible-ring"
          aria-label="Skip to main content"
        >
          Skip to main content
        </a>
        
        <ErrorBoundary>
          <div id="root" role="application" aria-label="Compliance Intelligence Platform">
            <AppLayout>
              {children}
            </AppLayout>
          </div>
        </ErrorBoundary>
      </body>
    </html>
  );
}
