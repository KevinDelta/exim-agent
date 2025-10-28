'use client';

import { useState, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardAction } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ComplianceTile } from '@/components/compliance-tile';
import { LoadingSpinner } from '@/components/loading-spinner';
import { ErrorBoundary } from '@/components/error-boundary';
import { cn } from '@/lib/utils';
import { 
  ComplianceSnapshot, 
  SnapshotCardProps,
  RiskLevel 
} from '@/lib/types';
import { RefreshCw, AlertTriangle, CheckCircle, Clock } from 'lucide-react';

// Risk level color mapping
const riskLevelColors = {
  low: 'bg-green-100 text-green-800 border-green-200 dark:bg-green-900 dark:text-green-300 dark:border-green-800',
  warn: 'bg-yellow-100 text-yellow-800 border-yellow-200 dark:bg-yellow-900 dark:text-yellow-300 dark:border-yellow-800',
  high: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-900 dark:text-red-300 dark:border-red-800',
} as const;

// Risk level icons
const riskLevelIcons = {
  low: CheckCircle,
  warn: Clock,
  high: AlertTriangle,
} as const;

interface SnapshotCardInternalProps extends Omit<SnapshotCardProps, 'snapshot'> {
  snapshot: ComplianceSnapshot | null;
}

function SnapshotCardContent({ snapshot, loading, error, onRefresh }: SnapshotCardInternalProps) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [announceMessage, setAnnounceMessage] = useState<string>('');

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    setAnnounceMessage('Refreshing compliance data...');
    try {
      await onRefresh();
      setAnnounceMessage('Compliance data refreshed successfully');
    } catch {
      setAnnounceMessage('Failed to refresh compliance data');
    } finally {
      setIsRefreshing(false);
      // Clear announcement after a delay
      setTimeout(() => setAnnounceMessage(''), 3000);
    }
  }, [onRefresh]);

  // Format timestamp for display
  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return 'Unknown';
    }
  };

  // Get risk level display text
  const getRiskLevelText = (riskLevel: RiskLevel) => {
    switch (riskLevel) {
      case 'low':
        return 'Low Risk';
      case 'warn':
        return 'Medium Risk';
      case 'high':
        return 'High Risk';
      default:
        return 'Unknown Risk';
    }
  };

  // Loading state
  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader className="p-responsive">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div className="space-y-1">
              <CardTitle className="text-responsive-lg">Compliance Snapshot</CardTitle>
              <CardDescription className="text-responsive-sm">Loading compliance monitoring data...</CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={loading || isRefreshing}
              aria-label="Refresh compliance data"
              className="touch-target self-start sm:self-auto"
            >
              <RefreshCw className={cn("h-4 w-4", (loading || isRefreshing) && "animate-spin")} />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-responsive pt-0">
          <div className="grid grid-responsive-tiles gap-responsive">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 sm:h-36 bg-muted animate-pulse rounded-lg" />
            ))}
          </div>
          <div className="mt-6 flex justify-center">
            <LoadingSpinner 
              size="md" 
              text="Fetching compliance data..." 
              srText="Loading compliance snapshot data"
            />
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card className="w-full border-destructive">
        <CardHeader className="p-responsive">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div className="space-y-1">
              <CardTitle className="text-destructive text-responsive-lg">Compliance Snapshot</CardTitle>
              <CardDescription className="text-responsive-sm">Failed to load compliance data</CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={loading || isRefreshing}
              aria-label="Retry loading compliance data"
              className="touch-target self-start sm:self-auto"
            >
              <RefreshCw className={cn("h-4 w-4", isRefreshing && "animate-spin")} />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-responsive pt-0">
          <div className="flex flex-col items-center justify-center py-6 sm:py-8 space-responsive-y">
            <AlertTriangle className="h-10 w-10 sm:h-12 sm:w-12 text-destructive" />
            <div className="text-center space-y-2 max-w-md">
              <p className="text-responsive-sm font-medium">Unable to load compliance data</p>
              <p className="text-responsive-xs text-muted-foreground break-words">
                {error}
              </p>
            </div>
            <Button 
              onClick={handleRefresh} 
              disabled={isRefreshing}
              className="touch-target"
            >
              {isRefreshing ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Retrying...
                </>
              ) : (
                'Try Again'
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // No data state
  if (!snapshot || !snapshot.success || !snapshot.snapshot) {
    return (
      <Card className="w-full">
        <CardHeader className="p-responsive">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div className="space-y-1">
              <CardTitle className="text-responsive-lg">Compliance Snapshot</CardTitle>
              <CardDescription className="text-responsive-sm">No compliance data available</CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={loading || isRefreshing}
              aria-label="Refresh compliance data"
              className="touch-target self-start sm:self-auto"
            >
              <RefreshCw className={cn("h-4 w-4", isRefreshing && "animate-spin")} />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-responsive pt-0">
          <div className="flex flex-col items-center justify-center py-6 sm:py-8 space-responsive-y">
            <Clock className="h-10 w-10 sm:h-12 sm:w-12 text-muted-foreground" />
            <div className="text-center space-y-2">
              <p className="text-responsive-sm font-medium">No data available</p>
              <p className="text-responsive-xs text-muted-foreground">
                Click refresh to load compliance monitoring data
              </p>
            </div>
            <Button 
              onClick={handleRefresh} 
              disabled={isRefreshing}
              className="touch-target"
            >
              {isRefreshing ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Loading...
                </>
              ) : (
                'Load Data'
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const snapshotData = snapshot.snapshot;
  const RiskIcon = riskLevelIcons[snapshotData.overall_risk_level];

  // Define the standard tile order and titles
  const tileConfig = [
    { key: 'hts_classification', title: 'HTS Classification' },
    { key: 'sanctions_screening', title: 'Sanctions Screening' },
    { key: 'refusal_history', title: 'Refusal History' },
    { key: 'cbp_rulings', title: 'CBP Rulings' },
  ];

  return (
    <Card 
      className="w-full focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2"
      role="region"
      aria-labelledby="snapshot-card-title"
      aria-describedby="snapshot-card-description"
    >
      {/* Screen reader announcements */}
      <div 
        aria-live="polite" 
        aria-atomic="true" 
        className="sr-only"
        role="status"
      >
        {announceMessage}
      </div>

      <CardHeader className="p-responsive">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 sm:gap-4">
          <div className="space-y-1 min-w-0 flex-1">
            <CardTitle 
              id="snapshot-card-title"
              className="text-responsive-lg"
            >
              Compliance Snapshot
            </CardTitle>
            <CardDescription 
              id="snapshot-card-description"
              className="text-responsive-sm break-words"
            >
              <span className="block sm:inline">Client: {snapshotData.client_id}</span>
              <span className="hidden sm:inline"> • </span>
              <span className="block sm:inline">SKU: {snapshotData.sku_id}</span>
              <span className="hidden sm:inline"> • </span>
              <span className="block sm:inline">Lane: {snapshotData.lane_id}</span>
            </CardDescription>
          </div>
          <CardAction>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={loading || isRefreshing}
              aria-label={isRefreshing ? "Refreshing compliance data" : "Refresh compliance data"}
              className="touch-target focus-ring"
            >
              <RefreshCw 
                className={cn("h-4 w-4", isRefreshing && "animate-spin")} 
                aria-hidden="true"
              />
              <span className="sr-only">
                {isRefreshing ? "Refreshing..." : "Refresh"}
              </span>
            </Button>
          </CardAction>
        </div>
        
        {/* Risk level and metadata */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pt-2">
          <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Risk level and alerts">
            <Badge 
              className={cn("border", riskLevelColors[snapshotData.overall_risk_level])}
              variant="outline"
              role="status"
              aria-label={`Overall risk level: ${getRiskLevelText(snapshotData.overall_risk_level)}`}
            >
              <RiskIcon className="h-3 w-3 mr-1" aria-hidden="true" />
              {getRiskLevelText(snapshotData.overall_risk_level)}
            </Badge>
            {snapshotData.active_alerts_count > 0 && (
              <Badge 
                variant="destructive"
                role="alert"
                aria-label={`${snapshotData.active_alerts_count} active alert${snapshotData.active_alerts_count !== 1 ? 's' : ''}`}
              >
                {snapshotData.active_alerts_count} Alert{snapshotData.active_alerts_count !== 1 ? 's' : ''}
              </Badge>
            )}
          </div>
          <time 
            className="text-responsive-xs text-muted-foreground self-start sm:self-auto"
            dateTime={snapshotData.generated_at}
            title={`Generated at: ${snapshotData.generated_at}`}
            aria-label={`Last updated: ${formatTimestamp(snapshotData.generated_at)}`}
          >
            Updated {formatTimestamp(snapshotData.generated_at)}
          </time>
        </div>
      </CardHeader>

      <CardContent className="p-responsive pt-0">
        {/* Compliance tiles grid */}
        <div 
          className="grid grid-responsive-tiles gap-responsive"
          role="grid"
          aria-label="Compliance monitoring tiles"
        >
          {tileConfig.map(({ key, title }) => {
            const tile = snapshotData.tiles[key];
            if (!tile) {
              return (
                <div 
                  key={key} 
                  className="h-32 sm:h-36 bg-muted rounded-lg flex items-center justify-center"
                  role="gridcell"
                  aria-label={`${title}: No data available`}
                >
                  <span className="text-responsive-xs text-muted-foreground">No data</span>
                </div>
              );
            }
            return (
              <div key={key} role="gridcell">
                <ComplianceTile
                  tile={tile}
                  title={title}
                  className="h-full"
                />
              </div>
            );
          })}
        </div>

        {/* Processing time and metadata */}
        <footer 
          className="mt-4 sm:mt-6 pt-4 border-t flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-responsive-xs text-muted-foreground"
          role="contentinfo"
          aria-label="Processing metadata"
        >
          <span aria-label={`Processing time: ${snapshotData.processing_time_ms} milliseconds`}>
            Processed in {snapshotData.processing_time_ms}ms
          </span>
          {snapshotData.last_change_detected && (
            <span aria-label={`Last change detected: ${formatTimestamp(snapshotData.last_change_detected)}`}>
              Last change: {formatTimestamp(snapshotData.last_change_detected)}
            </span>
          )}
        </footer>
      </CardContent>
    </Card>
  );
}

export function SnapshotCard(props: SnapshotCardProps) {
  return (
    <ErrorBoundary>
      <SnapshotCardContent {...props} />
    </ErrorBoundary>
  );
}

// Re-export the container component for convenience
export { SnapshotCardContainer, DemoSnapshotCard } from './snapshot-card-container';