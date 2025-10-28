# API Integration Guide

This guide explains how to integrate with the Compliance Intelligence Platform API from the frontend application.

## Overview

The frontend uses a centralized API client (`lib/api.ts`) to communicate with the backend FastAPI service. The client provides type-safe methods, error handling, and retry logic.

## Configuration

### Environment Variables

Set up your environment variables in `.env.local` for development:

```bash
# Required: Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Optional: Enable debug logging
NEXT_PUBLIC_ENABLE_DEBUG=true

# Optional: Request timeout in milliseconds
NEXT_PUBLIC_API_TIMEOUT=10000
```

For production, use `.env.production`:

```bash
NEXT_PUBLIC_API_URL=https://your-production-api.com
NEXT_PUBLIC_ENABLE_DEBUG=false
NEXT_PUBLIC_API_TIMEOUT=5000
```

## API Client Usage

### Basic Usage

```tsx
import { apiClient } from '@/lib/api';

// Get compliance snapshot
const snapshot = await apiClient.getComplianceSnapshot({
  client_id: 'client-123',
  sku_id: 'sku-456',
  lane_id: 'lane-789'
});
```

### With Error Handling

```tsx
import { apiClient, ApiError, ApiErrorType } from '@/lib/api';

try {
  const snapshot = await apiClient.getComplianceSnapshot(request);
  console.log('Success:', snapshot);
} catch (error) {
  if (error instanceof ApiError) {
    switch (error.type) {
      case ApiErrorType.NETWORK_ERROR:
        console.error('Network issue:', error.message);
        break;
      case ApiErrorType.SERVER_ERROR:
        console.error('Server error:', error.message);
        break;
      case ApiErrorType.VALIDATION_ERROR:
        console.error('Invalid request:', error.message);
        break;
      case ApiErrorType.TIMEOUT_ERROR:
        console.error('Request timeout:', error.message);
        break;
    }
  }
}
```

### With Retry Logic

```tsx
import { apiClient } from '@/lib/api';

// Automatic retry for failed requests
const snapshot = await apiClient.withRetry(
  () => apiClient.getComplianceSnapshot(request),
  3, // max retries
  1000 // initial delay in ms
);
```

## Available Endpoints

### Compliance Snapshot

**Endpoint:** `POST /compliance/snapshot`

**Request:**
```typescript
interface SnapshotRequest {
  client_id: string;
  sku_id: string;
  lane_id: string;
  hts_code?: string;
}
```

**Response:**
```typescript
interface ComplianceSnapshot {
  success: boolean;
  snapshot: {
    hts_classification: ComplianceTile;
    sanctions_screening: ComplianceTile;
    refusal_history: ComplianceTile;
    cbp_rulings: ComplianceTile;
  };
  citations: Citation[];
  metadata: SnapshotMetadata;
}
```

**Usage:**
```tsx
const snapshot = await apiClient.getComplianceSnapshot({
  client_id: 'acme-corp',
  sku_id: 'widget-001',
  lane_id: 'us-to-eu'
});
```

### Compliance Q&A (Future)

**Endpoint:** `POST /compliance/ask`

**Request:**
```typescript
interface AskRequest {
  question: string;
  context?: {
    client_id?: string;
    sku_id?: string;
    lane_id?: string;
  };
}
```

**Response:**
```typescript
interface AskResponse {
  success: boolean;
  question: string;
  answer: string;
  sources: Citation[];
  confidence: number;
}
```

## Error Handling

### Error Types

The API client categorizes errors into specific types:

```typescript
enum ApiErrorType {
  NETWORK_ERROR = 'network_error',     // Connection issues
  SERVER_ERROR = 'server_error',       // 5xx responses
  VALIDATION_ERROR = 'validation_error', // 4xx responses
  TIMEOUT_ERROR = 'timeout_error'       // Request timeout
}
```

### Error Response Format

```typescript
class ApiError extends Error {
  type: ApiErrorType;
  message: string;
  statusCode?: number;
  retryable: boolean;
}
```

### Handling Different Error Types

```tsx
function handleApiError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.retryable) {
      // Show retry option to user
      return {
        message: error.message,
        action: 'retry'
      };
    } else {
      // Show error without retry
      return {
        message: error.message,
        action: 'none'
      };
    }
  }
  
  // Unknown error
  return {
    message: 'An unexpected error occurred',
    action: 'none'
  };
}
```

## React Integration

### Using with React Hooks

```tsx
import { useState, useEffect } from 'react';
import { apiClient, ApiError } from '@/lib/api';

function useComplianceData(params: SnapshotRequest) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        setLoading(true);
        setError(null);
        const result = await apiClient.getComplianceSnapshot(params);
        setData(result);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message);
        } else {
          setError('An unexpected error occurred');
        }
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [params.client_id, params.sku_id, params.lane_id]);

  return { data, loading, error };
}
```

### Custom Hook with Retry

```tsx
import { useCallback } from 'react';

function useComplianceSnapshotWithRetry(params: SnapshotRequest) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const result = await apiClient.withRetry(
        () => apiClient.getComplianceSnapshot(params)
      );
      
      setData(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [params]);

  return { data, loading, error, refetch: fetchData };
}
```

## Request/Response Validation

### Type Guards

The API client includes validation for responses:

```typescript
function isValidSnapshotResponse(data: unknown): data is ComplianceSnapshot {
  if (!data || typeof data !== 'object') {
    return false;
  }
  
  const response = data as Record<string, unknown>;
  return typeof response.success === 'boolean';
}
```

### Custom Validation

Add your own validation for specific use cases:

```typescript
function validateSnapshotData(snapshot: ComplianceSnapshot): boolean {
  // Check required fields
  if (!snapshot.snapshot) {
    return false;
  }

  // Validate tile data
  const tiles = Object.values(snapshot.snapshot);
  return tiles.every(tile => 
    tile.title && 
    tile.status && 
    tile.risk_level
  );
}
```

## Performance Optimization

### Request Caching

Implement simple caching for repeated requests:

```typescript
class CachedApiClient extends ApiClient {
  private cache = new Map<string, { data: any; timestamp: number }>();
  private cacheTimeout = 5 * 60 * 1000; // 5 minutes

  async getComplianceSnapshotCached(request: SnapshotRequest) {
    const key = JSON.stringify(request);
    const cached = this.cache.get(key);
    
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      return cached.data;
    }

    const data = await this.getComplianceSnapshot(request);
    this.cache.set(key, { data, timestamp: Date.now() });
    
    return data;
  }
}
```

### Request Deduplication

Prevent duplicate requests:

```typescript
class DedupedApiClient extends ApiClient {
  private pendingRequests = new Map<string, Promise<any>>();

  async getComplianceSnapshotDeduped(request: SnapshotRequest) {
    const key = JSON.stringify(request);
    
    if (this.pendingRequests.has(key)) {
      return this.pendingRequests.get(key);
    }

    const promise = this.getComplianceSnapshot(request);
    this.pendingRequests.set(key, promise);
    
    try {
      const result = await promise;
      return result;
    } finally {
      this.pendingRequests.delete(key);
    }
  }
}
```

## Testing API Integration

### Mocking API Responses

```typescript
// __mocks__/api.ts
export const mockApiClient = {
  getComplianceSnapshot: jest.fn(),
  askComplianceQuestion: jest.fn(),
};

// In tests
import { mockApiClient } from '../__mocks__/api';

beforeEach(() => {
  mockApiClient.getComplianceSnapshot.mockResolvedValue({
    success: true,
    snapshot: {
      hts_classification: {
        title: 'HTS Classification',
        status: 'compliant',
        risk_level: 'low',
        description: 'Classification is current',
        action_items: [],
        last_updated: '2024-01-01T00:00:00Z'
      }
      // ... other tiles
    }
  });
});
```

### Integration Tests

```typescript
import { apiClient } from '@/lib/api';

describe('API Integration', () => {
  test('fetches compliance snapshot successfully', async () => {
    const request = {
      client_id: 'test-client',
      sku_id: 'test-sku',
      lane_id: 'test-lane'
    };

    const response = await apiClient.getComplianceSnapshot(request);
    
    expect(response.success).toBe(true);
    expect(response.snapshot).toBeDefined();
  });

  test('handles network errors gracefully', async () => {
    // Mock network failure
    global.fetch = jest.fn().mockRejectedValue(new Error('Network error'));

    await expect(
      apiClient.getComplianceSnapshot({
        client_id: 'test',
        sku_id: 'test',
        lane_id: 'test'
      })
    ).rejects.toThrow('Unable to connect to the server');
  });
});
```

## Debugging

### Enable Debug Mode

Set `NEXT_PUBLIC_ENABLE_DEBUG=true` to see request/response logs:

```typescript
// In development console
API Request: {
  url: "http://localhost:8000/compliance/snapshot",
  request: {
    client_id: "client-123",
    sku_id: "sku-456",
    lane_id: "lane-789"
  }
}
```

### Network Monitoring

Use browser dev tools to monitor API requests:

1. Open Developer Tools (F12)
2. Go to Network tab
3. Filter by "Fetch/XHR"
4. Monitor request/response details

### Error Logging

Add custom error logging:

```typescript
function logApiError(error: ApiError, context: any) {
  console.error('API Error:', {
    type: error.type,
    message: error.message,
    statusCode: error.statusCode,
    retryable: error.retryable,
    context
  });
  
  // Send to monitoring service in production
  if (process.env.NODE_ENV === 'production') {
    // analytics.track('api_error', { error, context });
  }
}
```

## Best Practices

1. **Always handle errors gracefully** - Show user-friendly messages
2. **Use TypeScript types** - Ensure type safety for requests/responses
3. **Implement retry logic** - For transient failures
4. **Cache when appropriate** - Avoid unnecessary requests
5. **Validate responses** - Don't trust external data
6. **Monitor performance** - Track request times and error rates
7. **Use environment variables** - For different deployment environments
8. **Test thoroughly** - Include both success and error scenarios