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

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setIsRefreshing(false);
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
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Compliance Snapshot</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={loading || isRefreshing}
              aria-label="Refresh compliance data"
            >
              <RefreshCw className={cn("h-4 w-4", (loading || isRefreshing) && "animate-spin")} />
            </Button>
          </div>
          <CardDescription>Loading compliance monitoring data...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-muted animate-pulse rounded-lg" />
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
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-destructive">Compliance Snapshot</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={loading || isRefreshing}
              aria-label="Retry loading compliance data"
            >
              <RefreshCw className={cn("h-4 w-4", isRefreshing && "animate-spin")} />
            </Button>
          </div>
          <CardDescription>Failed to load compliance data</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 space-y-4">
            <AlertTriangle className="h-12 w-12 text-destructive" />
            <div className="text-center space-y-2">
              <p className="text-sm font-medium">Unable to load compliance data</p>
              <p className="text-xs text-muted-foreground max-w-md">
                {error}
              </p>
            </div>
            <Button onClick={handleRefresh} disabled={isRefreshing}>
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
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Compliance Snapshot</CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={loading || isRefreshing}
              aria-label="Refresh compliance data"
            >
              <RefreshCw className={cn("h-4 w-4", isRefreshing && "animate-spin")} />
            </Button>
          </div>
          <CardDescription>No compliance data available</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 space-y-4">
            <Clock className="h-12 w-12 text-muted-foreground" />
            <div className="text-center space-y-2">
              <p className="text-sm font-medium">No data available</p>
              <p className="text-xs text-muted-foreground">
                Click refresh to load compliance monitoring data
              </p>
            </div>
            <Button onClick={handleRefresh} disabled={isRefreshing}>
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
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardTitle>Compliance Snapshot</CardTitle>
            <CardDescription>
              Client: {snapshotData.client_id} • SKU: {snapshotData.sku_id} • Lane: {snapshotData.lane_id}
            </CardDescription>
          </div>
          <CardAction>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={loading || isRefreshing}
              aria-label="Refresh compliance data"
            >
              <RefreshCw className={cn("h-4 w-4", isRefreshing && "animate-spin")} />
            </Button>
          </CardAction>
        </div>
        
        {/* Risk level and metadata */}
        <div className="flex items-center justify-between pt-2">
          <div className="flex items-center space-x-2">
            <Badge 
              className={cn("border", riskLevelColors[snapshotData.overall_risk_level])}
              variant="outline"
            >
              <RiskIcon className="h-3 w-3 mr-1" />
              {getRiskLevelText(snapshotData.overall_risk_level)}
            </Badge>
            {snapshotData.active_alerts_count > 0 && (
              <Badge variant="destructive">
                {snapshotData.active_alerts_count} Alert{snapshotData.active_alerts_count !== 1 ? 's' : ''}
              </Badge>
            )}
          </div>
          <time 
            className="text-xs text-muted-foreground"
            dateTime={snapshotData.generated_at}
            title={`Generated at: ${snapshotData.generated_at}`}
          >
            Updated {formatTimestamp(snapshotData.generated_at)}
          </time>
        </div>
      </CardHeader>

      <CardContent>
        {/* Compliance tiles grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-4 gap-4">
          {tileConfig.map(({ key, title }) => {
            const tile = snapshotData.tiles[key];
            if (!tile) {
              return (
                <div key={key} className="h-32 bg-muted rounded-lg flex items-center justify-center">
                  <span className="text-xs text-muted-foreground">No data</span>
                </div>
              );
            }
            return (
              <ComplianceTile
                key={key}
                tile={tile}
                title={title}
                className="h-full"
              />
            );
          })}
        </div>

        {/* Processing time and metadata */}
        <div className="mt-6 pt-4 border-t flex items-center justify-between text-xs text-muted-foreground">
          <span>
            Processed in {snapshotData.processing_time_ms}ms
          </span>
          {snapshotData.last_change_detected && (
            <span>
              Last change: {formatTimestamp(snapshotData.last_change_detected)}
            </span>
          )}
        </div>
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