# Component Usage Guide

This guide provides detailed information about using the components in the Compliance Intelligence Platform frontend.

## Core Components

### SnapshotCard

The main component for displaying compliance snapshot data.

#### Basic Usage

```tsx
import { SnapshotCard } from '@/components/snapshot-card';

function Dashboard() {
  return (
    <SnapshotCard 
      snapshot={snapshotData}
      loading={false}
      error={null}
      onRefresh={() => console.log('Refreshing...')}
    />
  );
}
```

#### Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `snapshot` | `ComplianceSnapshot \| null` | Yes | The compliance data to display |
| `loading` | `boolean` | Yes | Whether data is currently loading |
| `error` | `string \| null` | Yes | Error message if any |
| `onRefresh` | `() => void` | Yes | Callback for refresh action |

#### States

- **Loading**: Shows skeleton placeholders
- **Error**: Displays error message with retry option
- **Success**: Shows compliance data in tile format
- **Empty**: Shows message when no data available

### ComplianceTile

Individual tile component for specific compliance areas.

#### Basic Usage

```tsx
import { ComplianceTile } from '@/components/compliance-tile';

function ComplianceSection() {
  return (
    <ComplianceTile
      title="HTS Classification"
      status="compliant"
      riskLevel="low"
      description="Product classification is up to date"
      actionItems={["Review quarterly", "Update documentation"]}
      lastUpdated="2024-01-15T10:30:00Z"
    />
  );
}
```

#### Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `title` | `string` | Yes | Title of the compliance area |
| `status` | `ComplianceStatus` | Yes | Current compliance status |
| `riskLevel` | `RiskLevel` | Yes | Risk assessment level |
| `description` | `string` | Yes | Description of current status |
| `actionItems` | `string[]` | No | List of recommended actions |
| `lastUpdated` | `string` | Yes | ISO timestamp of last update |

#### Status Types

- `compliant`: Green indicator, no issues
- `warning`: Yellow indicator, attention needed
- `critical`: Red indicator, immediate action required
- `unknown`: Gray indicator, status unclear

#### Risk Levels

- `low`: Minimal risk, routine monitoring
- `medium`: Moderate risk, regular review needed
- `high`: High risk, immediate attention required

### SnapshotCardContainer

Container component that handles data fetching and state management.

#### Basic Usage

```tsx
import { SnapshotCardContainer } from '@/components/snapshot-card-container';

function ComplianceDashboard() {
  return (
    <SnapshotCardContainer 
      clientId="client-123"
      skuId="sku-456"
      laneId="lane-789"
    />
  );
}
```

#### Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `clientId` | `string` | Yes | Client identifier |
| `skuId` | `string` | Yes | SKU identifier |
| `laneId` | `string` | Yes | Trade lane identifier |
| `htsCode` | `string` | No | Optional HTS code filter |

## UI Components (shadcn/ui)

### Badge

Status indicators for compliance states.

```tsx
import { Badge } from '@/components/ui/badge';

<Badge variant="success">Compliant</Badge>
<Badge variant="warning">Warning</Badge>
<Badge variant="destructive">Critical</Badge>
```

### Button

Interactive elements for actions.

```tsx
import { Button } from '@/components/ui/button';

<Button onClick={handleRefresh}>Refresh Data</Button>
<Button variant="outline" size="sm">Details</Button>
```

### Card

Container components for content sections.

```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

<Card>
  <CardHeader>
    <CardTitle>Compliance Status</CardTitle>
  </CardHeader>
  <CardContent>
    <p>Content goes here</p>
  </CardContent>
</Card>
```

### Spinner

Loading indicators for async operations.

```tsx
import { Spinner } from '@/components/ui/spinner';

<Spinner size="sm" />
<Spinner size="lg" className="text-blue-500" />
```

## Utility Components

### ErrorBoundary

Catches and displays React errors gracefully.

```tsx
import { ErrorBoundary } from '@/components/error-boundary';

<ErrorBoundary>
  <YourComponent />
</ErrorBoundary>
```

### LoadingSpinner

Consistent loading state component.

```tsx
import { LoadingSpinner } from '@/components/loading-spinner';

<LoadingSpinner />
```

## Custom Hooks

### useComplianceSnapshot

Hook for fetching compliance snapshot data.

```tsx
import { useComplianceSnapshot } from '@/hooks/use-compliance-snapshot';

function MyComponent() {
  const { snapshot, loading, error, refetch } = useComplianceSnapshot({
    clientId: 'client-123',
    skuId: 'sku-456',
    laneId: 'lane-789'
  });

  if (loading) return <LoadingSpinner />;
  if (error) return <div>Error: {error}</div>;
  
  return <SnapshotCard snapshot={snapshot} />;
}
```

#### Return Values

| Property | Type | Description |
|----------|------|-------------|
| `snapshot` | `ComplianceSnapshot \| null` | Fetched snapshot data |
| `loading` | `boolean` | Loading state |
| `error` | `string \| null` | Error message if any |
| `refetch` | `() => void` | Function to refetch data |

## Styling Guidelines

### Tailwind CSS Classes

Use consistent spacing and color schemes:

```tsx
// Spacing
className="p-4 m-2 space-y-4"

// Colors (compliance status)
className="text-green-600"    // Compliant
className="text-yellow-600"   // Warning  
className="text-red-600"      // Critical
className="text-gray-600"     // Unknown

// Responsive design
className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4"
```

### Custom CSS Variables

Available in `globals.css`:

```css
:root {
  --compliance-green: #10b981;
  --compliance-yellow: #f59e0b;
  --compliance-red: #ef4444;
  --compliance-gray: #6b7280;
}
```

## Accessibility Features

### ARIA Labels

All components include proper ARIA labels:

```tsx
<button aria-label="Refresh compliance data">
  <RefreshIcon />
</button>

<div role="status" aria-live="polite">
  {loading ? 'Loading...' : 'Data loaded'}
</div>
```

### Keyboard Navigation

- All interactive elements are keyboard accessible
- Focus indicators are visible
- Tab order is logical

### Screen Reader Support

- Semantic HTML structure
- Descriptive text for status changes
- Proper heading hierarchy

## Error Handling

### Component-Level Errors

```tsx
try {
  // Component logic
} catch (error) {
  console.error('Component error:', error);
  // Show user-friendly error message
}
```

### API Errors

```tsx
const { snapshot, error } = useComplianceSnapshot(params);

if (error) {
  return (
    <div className="text-red-600">
      <p>Failed to load compliance data</p>
      <button onClick={refetch}>Try Again</button>
    </div>
  );
}
```

## Performance Considerations

### Memoization

Use React.memo for expensive components:

```tsx
import { memo } from 'react';

export const ComplianceTile = memo(function ComplianceTile(props) {
  // Component implementation
});
```

### Lazy Loading

For large components:

```tsx
import { lazy, Suspense } from 'react';

const HeavyComponent = lazy(() => import('./HeavyComponent'));

<Suspense fallback={<LoadingSpinner />}>
  <HeavyComponent />
</Suspense>
```

## Testing Components

### Basic Component Test

```tsx
import { render, screen } from '@testing-library/react';
import { ComplianceTile } from './compliance-tile';

test('renders compliance tile with correct status', () => {
  render(
    <ComplianceTile
      title="Test Tile"
      status="compliant"
      riskLevel="low"
      description="Test description"
      lastUpdated="2024-01-01T00:00:00Z"
    />
  );
  
  expect(screen.getByText('Test Tile')).toBeInTheDocument();
  expect(screen.getByText('Test description')).toBeInTheDocument();
});
```

### Hook Testing

```tsx
import { renderHook, waitFor } from '@testing-library/react';
import { useComplianceSnapshot } from './use-compliance-snapshot';

test('fetches compliance snapshot data', async () => {
  const { result } = renderHook(() => 
    useComplianceSnapshot({
      clientId: 'test-client',
      skuId: 'test-sku',
      laneId: 'test-lane'
    })
  );

  await waitFor(() => {
    expect(result.current.loading).toBe(false);
  });

  expect(result.current.snapshot).toBeDefined();
});
```