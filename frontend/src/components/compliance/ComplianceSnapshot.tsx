'use client';

import React from 'react';
import { SnapshotCard } from '@/components/snapshot-card';
import { ComplianceSnapshot as ComplianceSnapshotType } from '@/lib/types';

interface ComplianceSnapshotProps {
  snapshot: ComplianceSnapshotType | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

/**
 * ComplianceSnapshot - Wrapper around SnapshotCard for the compliance workflow
 * 
 * This component adapts the existing SnapshotCard to work within the new
 * integrated compliance workflow while maintaining all existing functionality.
 */
export function ComplianceSnapshot({
  snapshot,
  loading,
  error,
  onRefresh
}: ComplianceSnapshotProps) {
  return (
    <SnapshotCard
      snapshot={snapshot}
      loading={loading}
      error={error}
      onRefresh={onRefresh}
    />
  );
}