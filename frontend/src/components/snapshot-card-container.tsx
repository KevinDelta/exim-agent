'use client';

import { useEffect } from 'react';
import { SnapshotCard } from './snapshot-card';
import { useComplianceSnapshot } from '@/hooks/use-compliance-snapshot';
import { SnapshotRequest } from '@/lib/types';

interface SnapshotCardContainerProps {
  /** Request parameters for fetching snapshot data */
  params: SnapshotRequest;
  /** Auto-refresh interval in milliseconds (optional) */
  refreshInterval?: number;
  /** Additional CSS classes */
  className?: string;
}

export function SnapshotCardContainer({ 
  params, 
  refreshInterval,
  className 
}: SnapshotCardContainerProps) {
  const {
    snapshot,
    loading,
    error,
    fetchSnapshot,
    refresh,
    currentParams,
  } = useComplianceSnapshot({
    autoFetch: true,
    initialParams: params,
    refreshInterval,
  });

  // Refetch data when params change
  useEffect(() => {
    if (
      !currentParams ||
      currentParams.client_id !== params.client_id ||
      currentParams.sku_id !== params.sku_id ||
      currentParams.lane_id !== params.lane_id ||
      currentParams.hts_code !== params.hts_code
    ) {
      fetchSnapshot(params);
    }
  }, [params, currentParams, fetchSnapshot]);

  return (
    <div className={className}>
      <SnapshotCard
        snapshot={snapshot}
        loading={loading}
        error={error}
        onRefresh={refresh}
      />
    </div>
  );
}

// Export a simple version with default demo parameters for development
export function DemoSnapshotCard({ className }: { className?: string }) {
  const demoParams: SnapshotRequest = {
    client_id: 'demo-client',
    sku_id: 'demo-sku-001',
    lane_id: 'us-to-eu',
    hts_code: '8471.30.0100',
  };

  return (
    <SnapshotCardContainer 
      params={demoParams} 
      className={className}
      refreshInterval={30000} // Refresh every 30 seconds
    />
  );
}