# Component Usage Guide

This guide provides detailed information about using the components in the Compliance Intelligence Platform frontend.

## Navigation System

The navigation system provides a modern, responsive side menu with persistent chat functionality and document upload capabilities.

### SideNavigation

The main navigation container component with collapsible functionality.

#### Basic Usage

```tsx
import { SideNavigation } from '@/components/navigation';

function Layout({ children }) {
  return (
    <div className="flex h-screen">
      <SideNavigation />
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
```

#### Features

- **Collapsible sidebar**: 280px expanded, 64px collapsed
- **Responsive design**: Auto-collapse on mobile, overlay mode
- **Keyboard navigation**: Arrow keys, Home/End, Ctrl+B to toggle
- **Touch gestures**: Swipe to close on mobile
- **Accessibility**: Full ARIA support, screen reader announcements

#### Navigation Items

Default navigation includes:

- **Home**: Dashboard overview
- **Compliance**: Snapshot container  
- **Documents**: Upload interface
- **Profile**: User settings

### NavigationItem

Individual navigation menu items with icons and badges.

#### Basic Usage

```tsx
import { NavigationItem } from '@/components/navigation';

const navigationItem = {
  id: 'home',
  label: 'Home',
  icon: Home,
  route: '/',
  badge: 3, // Optional notification count
  disabled: false
};

<NavigationItem
  item={navigationItem}
  isActive={currentRoute === navigationItem.route}
  isCollapsed={false}
  onClick={handleNavigation}
/>
```

#### Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `item` | `NavigationItem` | Yes | Navigation item configuration |
| `isActive` | `boolean` | Yes | Whether this item is currently active |
| `isCollapsed` | `boolean` | Yes | Whether navigation is collapsed |
| `onClick` | `(route: string) => void` | Yes | Click handler for navigation |

#### NavigationItem Interface

```tsx
interface NavigationItem {
  id: string;
  label: string;
  icon: LucideIcon;
  route: string;
  badge?: number;
  disabled?: boolean;
}
```

### NavigationToggle

Toggle button for collapsing/expanding the navigation.

#### Basic Usage

```tsx
import { NavigationToggle } from '@/components/navigation';

<NavigationToggle 
  isCollapsed={isCollapsed}
  onToggle={toggleNavigation}
/>
```

#### Features

- **Animated icon**: Smooth rotation on state change
- **Keyboard support**: Enter/Space to toggle
- **Touch optimized**: Enhanced touch targets for mobile
- **Accessibility**: Proper ARIA labels and keyboard shortcuts

### ProfileSection

User profile display at the bottom of navigation.

#### Basic Usage

```tsx
import { ProfileSection } from '@/components/navigation';

<ProfileSection 
  isCollapsed={isCollapsed}
  onProfileClick={navigateToProfile}
/>
```

#### Features

- **User avatar**: Displays user profile image or initials
- **Authentication status**: Shows login state
- **Profile navigation**: Click to access profile settings
- **Responsive**: Adapts to collapsed/expanded states

### PersistentChat

Fixed-position chat interface at bottom of screen.

#### Basic Usage

```tsx
import { PersistentChat } from '@/components/chat';

function App() {
  return (
    <div>
      {/* Your app content */}
      <PersistentChat />
    </div>
  );
}
```

#### Features

- **Fixed positioning**: Bottom-right corner, stays above content
- **Expandable interface**: 60px collapsed to 400px expanded
- **Unread indicators**: Badge showing unread message count
- **Keyboard shortcuts**: Ctrl+/ to toggle, Escape to close
- **Mobile optimized**: Full-width overlay on mobile
- **Touch gestures**: Swipe down to close on mobile

#### Chat Integration

```tsx
// The chat automatically connects to your backend API
// Configure the API endpoint in your environment variables
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### DocumentUpload

Document upload interface with drag-and-drop functionality.

#### Basic Usage

```tsx
import { DocumentUpload } from '@/components/documents';

function DocumentsPage() {
  return (
    <div className="p-6">
      <h1>Upload Documents</h1>
      <DocumentUpload />
    </div>
  );
}
```

#### Features

- **Drag-and-drop**: Visual feedback for file drops
- **File validation**: Type and size checking
- **Progress tracking**: Upload progress indicators
- **Error handling**: User-friendly error messages
- **Multiple formats**: PDF, TXT, CSV, EPUB support

### FileDropZone

Core drag-and-drop component for file uploads.

#### Basic Usage

```tsx
import { FileDropZone } from '@/components/documents';

<FileDropZone
  onFilesSelected={handleFiles}
  onUploadError={handleError}
  acceptedTypes={['.pdf', '.txt', '.csv', '.epub']}
  maxFileSize={10 * 1024 * 1024} // 10MB
  disabled={isUploading}
/>
```

#### Props

| Prop | Type | Required | Description |
|------|------|----------|-------------|
| `onFilesSelected` | `(files: File[]) => void` | Yes | Callback for valid files |
| `onUploadError` | `(error: UploadError) => void` | Yes | Error handling callback |
| `acceptedTypes` | `string[]` | Yes | Allowed file extensions |
| `maxFileSize` | `number` | Yes | Maximum file size in bytes |
| `disabled` | `boolean` | No | Disable the drop zone |

## Navigation Hooks

### useNavigation

Hook for navigation state management.

```tsx
import { useNavigation } from '@/hooks/useNavigation';

function NavigationComponent() {
  const {
    isCollapsed,
    currentRoute,
    navigationItems,
    toggleCollapse,
    navigateTo
  } = useNavigation();

  return (
    <nav>
      <button onClick={toggleCollapse}>
        {isCollapsed ? 'Expand' : 'Collapse'}
      </button>
      {navigationItems.map(item => (
        <button 
          key={item.id}
          onClick={() => navigateTo(item.route)}
          className={currentRoute === item.route ? 'active' : ''}
        >
          {item.label}
        </button>
      ))}
    </nav>
  );
}
```

### useChat

Hook for chat functionality.

```tsx
import { useChat } from '@/hooks/useChat';

function ChatComponent() {
  const {
    messages,
    isExpanded,
    unreadCount,
    isLoading,
    sendMessage,
    clearHistory,
    toggleExpanded
  } = useChat();

  return (
    <div>
      <button onClick={toggleExpanded}>
        Chat {unreadCount > 0 && `(${unreadCount})`}
      </button>
      {isExpanded && (
        <div>
          {messages.map(msg => (
            <div key={msg.id}>{msg.content}</div>
          ))}
          <input 
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                sendMessage(e.target.value);
                e.target.value = '';
              }
            }}
          />
        </div>
      )}
    </div>
  );
}
```

## State Management

### Navigation Store (Zustand)

```tsx
import { useNavigationStore } from '@/stores/navigationStore';

const navigationStore = useNavigationStore();

// Available methods:
navigationStore.toggleCollapse();
navigationStore.setCurrentRoute('/documents');
navigationStore.updateNavigationItems(newItems);
```

### Chat Store (Zustand)

```tsx
import { useChatStore } from '@/stores/chatStore';

const chatStore = useChatStore();

// Available methods:
chatStore.addMessage(message);
chatStore.clearHistory();
chatStore.toggleExpanded();
chatStore.markAsRead();
```

## Styling and Theming

### CSS Variables

The navigation system uses CSS custom properties for theming:

```css
:root {
  --navigation-width-expanded: 280px;
  --navigation-width-collapsed: 64px;
  --chat-height-collapsed: 60px;
  --chat-height-expanded: 400px;
  --animation-duration: 0.3s;
  --animation-easing: cubic-bezier(0.4, 0.0, 0.2, 1);
}
```

### Responsive Breakpoints

```css
/* Mobile: < 768px */
@media (max-width: 767px) {
  /* Navigation becomes overlay */
  /* Chat takes full width */
}

/* Tablet: 768px - 1024px */
@media (min-width: 768px) and (max-width: 1023px) {
  /* Navigation can be toggled */
  /* Chat maintains fixed width */
}

/* Desktop: > 1024px */
@media (min-width: 1024px) {
  /* Full navigation functionality */
  /* Chat positioned bottom-right */
}
```

### Animation Classes

```css
.navigation-enter {
  transform: translateX(-100%);
  opacity: 0;
}

.navigation-enter-active {
  transform: translateX(0);
  opacity: 1;
  transition: all 0.3s ease-out;
}

.chat-expand {
  transform: scale(0.9);
  opacity: 0;
}

.chat-expand-active {
  transform: scale(1);
  opacity: 1;
  transition: all 0.2s ease-out;
}
```

## Accessibility Features

### Keyboard Navigation

- **Tab**: Navigate through focusable elements
- **Arrow Keys**: Navigate within navigation menu
- **Enter/Space**: Activate buttons and links
- **Escape**: Close expanded elements
- **Ctrl+B**: Toggle navigation
- **Ctrl+/**: Toggle chat

### Screen Reader Support

- **ARIA landmarks**: Navigation, main content areas
- **ARIA labels**: Descriptive labels for all interactive elements
- **ARIA live regions**: Announcements for state changes
- **Focus management**: Proper focus handling during state changes

### Color and Contrast

- **WCAG 2.1 AA compliance**: All text meets contrast requirements
- **Focus indicators**: Visible focus rings for keyboard users
- **Color independence**: Information not conveyed by color alone

## Performance Optimizations

### Code Splitting

```tsx
// Lazy load heavy components
const ChatWindow = lazy(() => import('./ChatWindow'));

<Suspense fallback={<ChatSkeleton />}>
  <ChatWindow />
</Suspense>
```

### Memoization

```tsx
// Prevent unnecessary re-renders
const NavigationItem = memo(function NavigationItem(props) {
  // Component implementation
});

// Memoize expensive calculations
const navigationItems = useMemo(() => 
  computeNavigationItems(user, permissions),
  [user, permissions]
);
```

### Virtual Scrolling

For large chat histories:

```tsx
import { FixedSizeList as List } from 'react-window';

<List
  height={400}
  itemCount={messages.length}
  itemSize={60}
  itemData={messages}
>
  {MessageItem}
</List>
```

## Error Handling

### NavigationErrorBoundary

```tsx
import { NavigationErrorBoundary } from '@/components/navigation';

<NavigationErrorBoundary>
  <SideNavigation />
</NavigationErrorBoundary>
```

### Error Recovery

```tsx
// Automatic retry for failed API calls
const { data, error, retry } = useApiCall(endpoint, {
  retries: 3,
  retryDelay: 1000
});

if (error) {
  return (
    <div>
      <p>Something went wrong</p>
      <button onClick={retry}>Try Again</button>
    </div>
  );
}
```

## Testing

### Component Testing

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { SideNavigation } from '@/components/navigation';

test('toggles navigation on button click', () => {
  render(<SideNavigation />);
  
  const toggleButton = screen.getByLabelText(/toggle navigation/i);
  fireEvent.click(toggleButton);
  
  expect(screen.getByRole('navigation')).toHaveAttribute('aria-expanded', 'false');
});
```

### Hook Testing

```tsx
import { renderHook, act } from '@testing-library/react';
import { useNavigation } from '@/hooks/useNavigation';

test('navigation hook manages state correctly', () => {
  const { result } = renderHook(() => useNavigation());
  
  act(() => {
    result.current.toggleCollapse();
  });
  
  expect(result.current.isCollapsed).toBe(true);
});
```

### Integration Testing

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from '@/App';

test('navigation integrates with routing', async () => {
  const user = userEvent.setup();
  render(<App />);
  
  await user.click(screen.getByText('Documents'));
  
  expect(screen.getByText('Upload Documents')).toBeInTheDocument();
});
```

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