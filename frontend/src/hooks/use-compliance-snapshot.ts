import { useState, useEffect, useCallback } from 'react';
import { 
  ComplianceSnapshot, 
  SnapshotRequest, 
  ApiError 
} from '@/lib/types';
import { getComplianceSnapshotWithRetry } from '@/lib/api';

interface UseComplianceSnapshotOptions {
  /** Auto-fetch data on mount */
  autoFetch?: boolean;
  /** Refresh interval in milliseconds */
  refreshInterval?: number;
  /** Initial request parameters */
  initialParams?: SnapshotRequest;
}

interface UseComplianceSnapshotReturn {
  /** Current snapshot data */
  snapshot: ComplianceSnapshot | null;
  /** Loading state */
  loading: boolean;
  /** Error message */
  error: string | null;
  /** Fetch snapshot data */
  fetchSnapshot: (params: SnapshotRequest) => Promise<void>;
  /** Refresh current snapshot */
  refresh: () => Promise<void>;
  /** Clear error state */
  clearError: () => void;
  /** Current request parameters */
  currentParams: SnapshotRequest | null;
}

export function useComplianceSnapshot(
  options: UseComplianceSnapshotOptions = {}
): UseComplianceSnapshotReturn {
  const { autoFetch = false, refreshInterval, initialParams } = options;

  const [snapshot, setSnapshot] = useState<ComplianceSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentParams, setCurrentParams] = useState<SnapshotRequest | null>(
    initialParams || null
  );

  const fetchSnapshot = useCallback(async (params: SnapshotRequest) => {
    setLoading(true);
    setError(null);
    setCurrentParams(params);

    try {
      const result = await getComplianceSnapshotWithRetry(params);
      setSnapshot(result);
    } catch (err) {
      const errorMessage = err instanceof ApiError 
        ? err.message 
        : err instanceof Error 
        ? err.message 
        : 'An unexpected error occurred';
      
      setError(errorMessage);
      setSnapshot(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    if (!currentParams) {
      setError('No parameters available for refresh');
      return;
    }
    await fetchSnapshot(currentParams);
  }, [currentParams, fetchSnapshot]);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Auto-fetch on mount if enabled and initial params provided
  useEffect(() => {
    if (autoFetch && initialParams) {
      fetchSnapshot(initialParams);
    }
  }, [autoFetch, initialParams, fetchSnapshot]);

  // Set up refresh interval if specified
  useEffect(() => {
    if (!refreshInterval || !currentParams) {
      return;
    }

    const interval = setInterval(() => {
      if (!loading) {
        refresh();
      }
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [refreshInterval, currentParams, loading, refresh]);

  return {
    snapshot,
    loading,
    error,
    fetchSnapshot,
    refresh,
    clearError,
    currentParams,
  };
}