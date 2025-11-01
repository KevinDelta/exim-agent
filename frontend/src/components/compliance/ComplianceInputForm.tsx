'use client';

import React, { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card } from '@/components/ui/card';
import { Search, Loader2, HelpCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ComplianceInputFormProps {
  initialHtsCode?: string;
  initialLaneId?: string;
  onSubmit: (htsCode: string, laneId: string) => Promise<void>;
  loading?: boolean;
}

/**
 * ComplianceInputForm - Input form for HTS code and lane information
 * 
 * Features:
 * - Real-time validation
 * - Example suggestions
 * - Loading states
 * - Accessibility support
 */
export function ComplianceInputForm({
  initialHtsCode = '',
  initialLaneId = '',
  onSubmit,
  loading = false
}: ComplianceInputFormProps) {
  const [htsCode, setHtsCode] = useState(initialHtsCode);
  const [laneId, setLaneId] = useState(initialLaneId);
  const [errors, setErrors] = useState<{ hts?: string; lane?: string }>({});

  // Validation
  const validateInputs = useCallback(() => {
    const newErrors: { hts?: string; lane?: string } = {};

    // HTS Code validation (basic format check)
    if (!htsCode.trim()) {
      newErrors.hts = 'HTS code is required';
    } else if (!/^\d{4,10}(\.\d{2}(\.\d{2})?)?$/.test(htsCode.trim())) {
      newErrors.hts = 'Invalid HTS code format (e.g., 8517.12.00)';
    }

    // Lane ID validation
    if (!laneId.trim()) {
      newErrors.lane = 'Lane information is required';
    } else if (laneId.trim().length < 2) {
      newErrors.lane = 'Lane must be at least 2 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [htsCode, laneId]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateInputs()) {
      return;
    }

    try {
      await onSubmit(htsCode.trim(), laneId.trim());
    } catch (error) {
      console.error('Failed to submit compliance query:', error);
    }
  }, [htsCode, laneId, validateInputs, onSubmit]);

  const handleHtsCodeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setHtsCode(value);
    
    // Clear error when user starts typing
    if (errors.hts) {
      setErrors(prev => ({ ...prev, hts: undefined }));
    }
  }, [errors.hts]);

  const handleLaneIdChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setLaneId(value);
    
    // Clear error when user starts typing
    if (errors.lane) {
      setErrors(prev => ({ ...prev, lane: undefined }));
    }
  }, [errors.lane]);

  // Example suggestions
  const htsExamples = [
    { code: '8517.12.00', description: 'Smartphones' },
    { code: '6203.42.40', description: 'Men\'s cotton trousers' },
    { code: '9403.60.80', description: 'Wooden furniture' }
  ];

  const laneExamples = [
    { id: 'CN-US', description: 'China to United States' },
    { id: 'MX-US', description: 'Mexico to United States' },
    { id: 'DE-US', description: 'Germany to United States' }
  ];

  return (
    <div className="space-y-6">
      {/* Main Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* HTS Code Input */}
          <div className="space-y-2">
            <Label htmlFor="hts-code" className="text-sm font-medium">
              HTS Code
              <span className="text-destructive ml-1" aria-label="required">*</span>
            </Label>
            <div className="relative">
              <Input
                id="hts-code"
                type="text"
                placeholder="e.g., 8517.12.00"
                value={htsCode}
                onChange={handleHtsCodeChange}
                disabled={loading}
                className={cn(
                  'pr-10',
                  errors.hts && 'border-destructive focus-visible:ring-destructive'
                )}
                aria-describedby={errors.hts ? 'hts-error' : 'hts-help'}
                aria-invalid={!!errors.hts}
              />
              <HelpCircle className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            </div>
            {errors.hts ? (
              <p id="hts-error" className="text-sm text-destructive" role="alert">
                {errors.hts}
              </p>
            ) : (
              <p id="hts-help" className="text-sm text-muted-foreground">
                Enter the Harmonized Tariff Schedule code for your product
              </p>
            )}
          </div>

          {/* Lane ID Input */}
          <div className="space-y-2">
            <Label htmlFor="lane-id" className="text-sm font-medium">
              Trade Lane
              <span className="text-destructive ml-1" aria-label="required">*</span>
            </Label>
            <div className="relative">
              <Input
                id="lane-id"
                type="text"
                placeholder="e.g., CN-US"
                value={laneId}
                onChange={handleLaneIdChange}
                disabled={loading}
                className={cn(
                  'pr-10',
                  errors.lane && 'border-destructive focus-visible:ring-destructive'
                )}
                aria-describedby={errors.lane ? 'lane-error' : 'lane-help'}
                aria-invalid={!!errors.lane}
              />
              <HelpCircle className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            </div>
            {errors.lane ? (
              <p id="lane-error" className="text-sm text-destructive" role="alert">
                {errors.lane}
              </p>
            ) : (
              <p id="lane-help" className="text-sm text-muted-foreground">
                Enter the trade lane (e.g., CN-US for China to US)
              </p>
            )}
          </div>
        </div>

        {/* Submit Button */}
        <div className="flex justify-center pt-2">
          <Button
            type="submit"
            disabled={loading || !htsCode.trim() || !laneId.trim()}
            className="min-w-[200px]"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Search className="h-4 w-4 mr-2" />
                Get Compliance Analysis
              </>
            )}
          </Button>
        </div>
      </form>

      {/* Examples */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t">
        {/* HTS Examples */}
        <div>
          <h3 className="text-sm font-medium mb-2">HTS Code Examples</h3>
          <div className="space-y-1">
            {htsExamples.map((example) => (
              <button
                key={example.code}
                type="button"
                onClick={() => setHtsCode(example.code)}
                disabled={loading}
                className="block w-full text-left p-2 text-sm rounded hover:bg-muted transition-colors disabled:opacity-50"
              >
                <span className="font-mono text-primary">{example.code}</span>
                <span className="text-muted-foreground ml-2">- {example.description}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Lane Examples */}
        <div>
          <h3 className="text-sm font-medium mb-2">Trade Lane Examples</h3>
          <div className="space-y-1">
            {laneExamples.map((example) => (
              <button
                key={example.id}
                type="button"
                onClick={() => setLaneId(example.id)}
                disabled={loading}
                className="block w-full text-left p-2 text-sm rounded hover:bg-muted transition-colors disabled:opacity-50"
              >
                <span className="font-mono text-primary">{example.id}</span>
                <span className="text-muted-foreground ml-2">- {example.description}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}