# Navigation System Documentation

## Overview

The Navigation System is a comprehensive, modern side menu implementation for the Compliance Intelligence Platform. It provides seamless navigation between application sections, persistent chat functionality, and document upload capabilities.

## Architecture

### Component Structure

```bash
components/
├── navigation/
│   ├── SideNavigation.tsx          # Main navigation container
│   ├── NavigationItem.tsx          # Individual menu items
│   ├── NavigationToggle.tsx        # Collapse/expand button
│   ├── ProfileSection.tsx          # User profile area
│   ├── NavigationErrorBoundary.tsx # Error handling
│   └── index.ts                    # Exports
├── chat/
│   ├── PersistentChat.tsx          # Fixed chat interface
│   ├── ChatWindow.tsx              # Expandable chat UI
│   ├── ChatHistory.tsx             # Message history
│   ├── ChatInput.tsx               # Message input
│   └── index.ts                    # Exports
└── documents/
    ├── DocumentUpload.tsx          # Upload page component
    ├── FileDropZone.tsx            # Drag-and-drop zone
    ├── UploadProgress.tsx          # Progress indicators
    └── index.ts                    # Exports
```

### State Management

```bash
stores/
├── navigationStore.ts              # Navigation state (Zustand)
├── chatStore.ts                    # Chat persistence (Zustand)
└── userStore.ts                    # User profile state
```

### Custom Hooks

```bash
hooks/
├── useNavigation.ts                # Navigation functionality
├── useChat.ts                      # Chat functionality
└── useFileUpload.ts                # File upload handling
```

## Layout Behavior

### Desktop Layout (≥1024px)

- **Navigation**: Fixed sidebar that spans full screen height
- **Content Area**: Automatically adjusts width when navigation expands/collapses
- **Expanded State**: Navigation is 280px wide, content area starts at 280px from left
- **Collapsed State**: Navigation is 64px wide, content area starts at 64px from left
- **Smooth Transitions**: Content area smoothly animates when navigation state changes

### Tablet Layout (768px - 1023px)

- **Navigation**: Overlay mode - navigation appears over content when expanded
- **Content Area**: Always full width, navigation doesn't push content
- **Auto-collapse**: Navigation automatically collapses after navigation for better UX

### Mobile Layout (<768px)

- **Navigation**: Full-screen overlay with backdrop
- **Content Area**: Always full width
- **Touch Gestures**: Swipe left to close navigation
- **Auto-collapse**: Navigation closes automatically after navigation

## Features

### 🎯 Core Navigation

- **Responsive Design**: Adapts to mobile, tablet, and desktop
- **Collapsible Sidebar**: 280px expanded, 64px collapsed
- **Active State Highlighting**: Visual indication of current page
- **Badge Support**: Notification counters on menu items
- **Keyboard Navigation**: Full keyboard accessibility

### 💬 Persistent Chat

- **Fixed Positioning**: Always accessible at bottom of screen
- **Expandable Interface**: Smooth animations between states
- **Message Persistence**: Chat history maintained across sessions
- **Real-time Updates**: Live message handling
- **Mobile Optimized**: Full-width overlay on mobile devices

### 📁 Document Upload

- **Drag-and-Drop**: Intuitive file upload experience
- **File Validation**: Type and size checking
- **Progress Tracking**: Visual upload progress
- **Error Handling**: User-friendly error messages
- **Multiple Formats**: PDF, TXT, CSV, EPUB support

### ♿ Accessibility

- **WCAG 2.1 AA Compliant**: Meets accessibility standards
- **Keyboard Navigation**: Full keyboard support
- **Screen Reader Support**: Proper ARIA implementation
- **Focus Management**: Logical tab order and focus handling
- **High Contrast**: Sufficient color contrast ratios

### 🚀 Performance

- **Code Splitting**: Lazy loading for heavy components
- **Memoization**: Optimized re-rendering with React.memo
- **Error Boundaries**: Graceful error handling
- **Bundle Optimization**: Minimal bundle size impact

## Installation & Setup

### 1. Dependencies

The navigation system requires these dependencies (already included in package.json):

```json
{
  "dependencies": {
    "framer-motion": "^10.16.4",
    "lucide-react": "^0.263.1",
    "zustand": "^4.4.1",
    "@radix-ui/react-*": "^1.0.0"
  }
}
```

### 2. Environment Variables

Configure your environment variables:

```env
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CHAT_ENABLED=true
NEXT_PUBLIC_UPLOAD_MAX_SIZE=10485760
```

### 3. Basic Implementation

The navigation system is automatically integrated through the AppLayout component:

```tsx
// app/layout.tsx (already configured)
import { AppLayout } from '@/components/layout';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AppLayout>
          {children}
        </AppLayout>
      </body>
    </html>
  );
}
```

The AppLayout component handles:

- **Responsive Navigation**: Automatically adjusts between mobile overlay and desktop sidebar
- **Content Area Adjustment**: Main content automatically resizes when navigation expands/collapses
- **Full Height Layout**: Navigation spans full screen height, content area adjusts accordingly
- **Persistent Chat**: Integrated chat interface that doesn't interfere with navigation

## Configuration

### Navigation Items

Customize navigation items in your navigation store:

```tsx
// stores/navigationStore.ts
const defaultNavigationItems: NavigationItem[] = [
  {
    id: 'home',
    label: 'Home',
    icon: Home,
    route: '/',
    badge: 0,
    disabled: false
  },
  {
    id: 'compliance',
    label: 'Compliance',
    icon: Shield,
    route: '/compliance',
    badge: 3, // Notification count
    disabled: false
  },
  {
    id: 'documents',
    label: 'Documents',
    icon: FileText,
    route: '/documents',
    badge: 0,
    disabled: false
  },
  {
    id: 'profile',
    label: 'Profile',
    icon: User,
    route: '/profile',
    badge: 0,
    disabled: false
  }
];
```

### Chat Configuration

Configure chat settings:

```tsx
// stores/chatStore.ts
interface ChatConfig {
  maxMessages: number;
  persistHistory: boolean;
  apiEndpoint: string;
  retryAttempts: number;
  retryDelay: number;
}

const chatConfig: ChatConfig = {
  maxMessages: 100,
  persistHistory: true,
  apiEndpoint: '/api/chat',
  retryAttempts: 3,
  retryDelay: 1000
};
```

### Upload Configuration

Configure file upload settings:

```tsx
// components/documents/DocumentUpload.tsx
const uploadConfig = {
  acceptedTypes: ['.pdf', '.txt', '.csv', '.epub'],
  maxFileSize: 10 * 1024 * 1024, // 10MB
  maxFiles: 10,
  allowedMimeTypes: [
    'application/pdf',
    'text/plain',
    'text/csv',
    'application/epub+zip'
  ]
};
```

## Customization

### Theming

Override CSS custom properties for theming:

```css
/* globals.css */
:root {
  /* Navigation */
  --navigation-width-expanded: 320px;  /* Default: 280px */
  --navigation-width-collapsed: 80px;  /* Default: 64px */
  
  /* Chat */
  --chat-width: 450px;                 /* Default: 400px */
  --chat-height-expanded: 600px;       /* Default: 500px */
  
  /* Animations */
  --animation-duration: 0.4s;          /* Default: 0.3s */
  --animation-easing: ease-in-out;     /* Default: cubic-bezier */
  
  /* Colors */
  --navigation-bg: hsl(var(--background));
  --navigation-border: hsl(var(--border));
  --navigation-active: hsl(var(--primary));
}
```

### Custom Icons

Replace default icons with your own:

```tsx
// stores/navigationStore.ts
import { 
  CustomHomeIcon, 
  CustomComplianceIcon,
  CustomDocumentsIcon,
  CustomProfileIcon 
} from '@/components/icons';

const navigationItems = [
  {
    id: 'home',
    label: 'Dashboard',
    icon: CustomHomeIcon, // Your custom icon
    route: '/',
  },
  // ... other items
];
```

### Animation Variants

Customize animations:

```tsx
// components/navigation/SideNavigation.tsx
const customNavigationVariants = {
  expanded: { 
    width: 320,
    transition: {
      duration: 0.4,
      ease: "easeInOut",
      type: "spring",
      stiffness: 200,
      damping: 25
    }
  },
  collapsed: { 
    width: 80,
    transition: {
      duration: 0.4,
      ease: "easeInOut",
      type: "spring",
      stiffness: 200,
      damping: 25
    }
  }
};
```

## API Integration

### Chat API

The chat system expects these API endpoints:

```typescript
// API Endpoints
POST /api/chat/send
GET  /api/chat/history/:sessionId
DELETE /api/chat/history/:sessionId

// Request/Response Types
interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  sessionId: string;
  metadata?: Record<string, any>;
}

interface ChatResponse {
  message: string;
  sessionId: string;
  metadata?: Record<string, any>;
}
```

### Document Upload API

Document upload expects these endpoints:

```typescript
// API Endpoints
POST /api/documents/upload
GET  /api/documents/status/:uploadId
DELETE /api/documents/:documentId

// Request/Response Types
interface UploadResponse {
  id: string;
  filename: string;
  size: number;
  type: string;
  status: 'uploading' | 'completed' | 'error';
  progress: number;
  url?: string;
}
```

## Troubleshooting

### Common Issues

#### Navigation Not Responsive

```tsx
// Ensure proper CSS classes are applied
<div className="flex h-screen">
  <SideNavigation className="flex-shrink-0" />
  <main className="flex-1 min-w-0 overflow-auto">
    {children}
  </main>
</div>
```

#### Chat Messages Not Persisting

```tsx
// Check localStorage availability
if (typeof window !== 'undefined' && window.localStorage) {
  // Chat persistence will work
} else {
  // Fallback to session-only storage
}
```

#### File Upload Failing

```tsx
// Verify file validation
const isValidFile = (file: File) => {
  const validTypes = ['.pdf', '.txt', '.csv', '.epub'];
  const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
  const validSize = file.size <= maxFileSize;
  
  return validTypes.includes(fileExtension) && validSize;
};
```

### Performance Issues

#### Slow Navigation Animations

```tsx
// Enable hardware acceleration
<motion.nav
  className="transform-gpu" // Add this class
  variants={navigationVariants}
  animate={isCollapsed ? 'collapsed' : 'expanded'}
/>
```

#### Memory Leaks

```tsx
// Proper cleanup in useEffect
useEffect(() => {
  const handleResize = () => {
    // Handle resize
  };
  
  window.addEventListener('resize', handleResize);
  
  return () => {
    window.removeEventListener('resize', handleResize);
  };
}, []);
```

### Debugging

Enable debug mode for detailed logging:

```tsx
// Set environment variable
NEXT_PUBLIC_DEBUG_NAVIGATION=true

// Or programmatically
if (process.env.NODE_ENV === 'development') {
  console.log('Navigation state:', navigationState);
  console.log('Chat messages:', messages);
}
```

## Browser Support

### Supported Browsers

- **Chrome**: 88+
- **Firefox**: 85+
- **Safari**: 14+
- **Edge**: 88+

### Feature Detection

```tsx
// Check for required features
const hasIntersectionObserver = 'IntersectionObserver' in window;
const hasResizeObserver = 'ResizeObserver' in window;
const hasLocalStorage = 'localStorage' in window;

if (!hasIntersectionObserver) {
  // Provide fallback for older browsers
}
```

## Contributing

### Development Setup

1. Clone the repository
2. Install dependencies: `npm install`
3. Start development server: `npm run dev`
4. Run tests: `npm test`

### Code Style

- Use TypeScript for all components
- Follow ESLint configuration
- Use Prettier for formatting
- Write tests for new features

### Pull Request Guidelines

1. Create feature branch from `main`
2. Write comprehensive tests
3. Update documentation
4. Ensure all checks pass
5. Request review from maintainers

## License

This navigation system is part of the Compliance Intelligence Platform and follows the project's licensing terms.
