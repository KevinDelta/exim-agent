# Compliance Intelligence Platform - Frontend

A modern NextJS frontend application for the Compliance Intelligence Platform, providing a clean, responsive interface for displaying compliance snapshots and monitoring data. Built with NextJS 13+ App Router, TypeScript, and Tailwind CSS.

## Technology Stack

- **Framework**: NextJS 16.0.0 with App Router
- **Language**: TypeScript 5+ with strict mode
- **Styling**: Tailwind CSS v4 + shadcn/ui components
- **State Management**: React hooks (useState, useEffect) with custom hooks
- **HTTP Client**: Native fetch API with retry logic and error handling
- **Icons**: Lucide React
- **Build Tool**: NextJS built-in bundler with optimizations

## Project Structure

```bash
frontend/
├── src/
│   ├── app/                          # App Router pages
│   │   ├── globals.css              # Global styles and Tailwind config
│   │   ├── layout.tsx               # Root layout with metadata
│   │   ├── page.tsx                 # Home page with snapshot display
│   │   └── loading.tsx              # Global loading component
│   ├── components/                  # Reusable UI components
│   │   ├── ui/                      # shadcn/ui base components
│   │   │   ├── badge.tsx           # Status badges
│   │   │   ├── button.tsx          # Interactive buttons
│   │   │   ├── card.tsx            # Card containers
│   │   │   └── spinner.tsx         # Loading spinners
│   │   ├── compliance-tile.tsx      # Individual compliance data tile
│   │   ├── snapshot-card.tsx        # Main compliance snapshot card
│   │   ├── snapshot-card-container.tsx # Container with data fetching
│   │   ├── error-boundary.tsx       # Error handling component
│   │   └── loading-spinner.tsx      # Loading state component
│   ├── hooks/                       # Custom React hooks
│   │   └── use-compliance-snapshot.ts # Data fetching hook
│   └── lib/                         # Utility functions
│       ├── api.ts                   # API client with retry logic
│       ├── types.ts                 # TypeScript type definitions
│       └── utils.ts                 # General utilities (shadcn)
├── public/                          # Static assets
├── .env.local                       # Local environment variables
├── .env.production                  # Production environment variables
└── .env.example                     # Environment template
```

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- The backend API running on `http://localhost:8000`

### Installation

1. Navigate to the frontend directory:

```bash
cd frontend
```

1. Install dependencies:

```bash
npm install
```

1. Copy environment variables:

```bash
cp .env.example .env.local
```

1. Update `.env.local` with your configuration:

```bash

# API Backend URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Enable debug features in development
NEXT_PUBLIC_ENABLE_DEBUG=true

# API timeout (in milliseconds)
NEXT_PUBLIC_API_TIMEOUT=10000
```

### Development

Start the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint
- `npm run lint:fix` - Fix ESLint issues automatically
- `npm run type-check` - Run TypeScript type checking
- `npm run clean` - Clean build artifacts
- `npm run preview` - Build and preview production locally

### Build for Production

```bash
# Build the application
npm run build

# Start production server
npm start

# Or preview locally after build
npm run preview
```

## Features

### Current Implementation

- ✅ NextJS 16.0.0 with App Router
- ✅ TypeScript with strict mode
- ✅ Tailwind CSS v4 with custom theme
- ✅ shadcn/ui component library
- ✅ Compliance snapshot card component
- ✅ Individual compliance tile components
- ✅ API client with retry logic and error handling
- ✅ Custom hooks for data fetching
- ✅ Loading states and error boundaries
- ✅ Responsive design (mobile-first)
- ✅ Accessibility features (WCAG 2.1 AA)
- ✅ Environment configuration for multiple environments
- ✅ Production optimizations

### Future Enhancements

- [ ] Real-time updates with WebSocket support
- [ ] Advanced filtering and search
- [ ] Data export functionality
- [ ] User preferences and settings
- [ ] Comprehensive test suite
- [ ] Performance monitoring
- [ ] Offline support with service workers

## API Integration

The frontend connects to the Compliance Intelligence Platform backend API:

- **Base URL**: Configurable via `NEXT_PUBLIC_API_URL` environment variable
- **Endpoints**:
  - `POST /compliance/snapshot` - Get compliance snapshot data
  - `POST /compliance/ask` - Ask compliance questions (future)
- **Error Handling**: Automatic retry logic with exponential backoff
- **Type Safety**: Full TypeScript interfaces for API requests/responses
- **Timeout**: Configurable request timeout via environment variables

### API Client Features

- **Retry Logic**: Automatic retries for network and server errors
- **Error Classification**: Categorized error types (network, server, validation, timeout)
- **Request Validation**: Type-safe request/response validation
- **Debug Mode**: Optional request/response logging in development
- **Timeout Configuration**: Environment-based timeout settings

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000` | Yes |
| `NEXT_PUBLIC_ENABLE_DEBUG` | Enable debug logging | `false` | No |
| `NEXT_PUBLIC_API_TIMEOUT` | API request timeout (ms) | `10000` | No |
| `NODE_ENV` | Environment mode | `development` | No |

### Environment Files

- `.env.local` - Local development (not committed)
- `.env.production` - Production configuration
- `.env.example` - Template with all available variables

## Component Documentation

### Core Components

#### SnapshotCard

Main component that displays compliance snapshot data in a card format.

**Props:**

```typescript
interface SnapshotCardProps {
  snapshot: ComplianceSnapshot | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}
```

**Usage:**

```tsx
import { SnapshotCard } from '@/components/snapshot-card';

<SnapshotCard 
  snapshot={snapshotData}
  loading={isLoading}
  error={errorMessage}
  onRefresh={handleRefresh}
/>
```

#### ComplianceTile

Individual tile component for displaying specific compliance data.

**Props:**

```typescript
interface ComplianceTileProps {
  title: string;
  status: 'compliant' | 'warning' | 'critical' | 'unknown';
  riskLevel: 'low' | 'medium' | 'high';
  description: string;
  actionItems?: string[];
  lastUpdated: string;
}
```

#### SnapshotCardContainer

Container component that handles data fetching and state management.

**Usage:**

```tsx
import { SnapshotCardContainer } from '@/components/snapshot-card-container';

<SnapshotCardContainer 
  clientId="client-123"
  skuId="sku-456"
  laneId="lane-789"
/>
```

### Custom Hooks

#### useComplianceSnapshot

Hook for fetching and managing compliance snapshot data.

**Usage:**

```tsx
import { useComplianceSnapshot } from '@/hooks/use-compliance-snapshot';

const { snapshot, loading, error, refetch } = useComplianceSnapshot({
  clientId: 'client-123',
  skuId: 'sku-456',
  laneId: 'lane-789'
});
```

## Development Guidelines

### Code Style

- Use TypeScript strict mode with proper type definitions
- Follow React/NextJS best practices and conventions
- Implement proper error boundaries for graceful error handling
- Use semantic HTML and ARIA labels for accessibility
- Maintain responsive design principles (mobile-first)
- Follow consistent naming conventions (camelCase for variables, PascalCase for components)

### Component Structure

- Keep components focused and reusable
- Use proper TypeScript interfaces for all props
- Implement loading and error states consistently
- Follow shadcn/ui patterns and design system
- Separate concerns (presentation vs. logic)
- Use composition over inheritance

### API Integrations

- Use the centralized API client (`lib/api.ts`)
- Implement proper error handling with user-friendly messages
- Add request/response validation with TypeScript
- Use environment-based configuration
- Implement retry logic for transient failures
- Handle loading states appropriately

### Performance Best Practices

- Use React.memo for expensive components
- Implement proper dependency arrays in useEffect
- Avoid unnecessary re-renders
- Use NextJS Image component for optimized images
- Implement code splitting where appropriate

## Troubleshooting

### Common Issues

#### API Connection Issues

```bash
# Check if backend is running
curl http://localhost:8000/health

# Verify environment variables
echo $NEXT_PUBLIC_API_URL
```

#### Build Issues

```bash
# Clear Next.js cache
npm run clean

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Check TypeScript errors
npm run type-check
```

#### Development Server Issues

```bash
# Kill processes on port 3000
lsof -ti:3000 | xargs kill -9

# Start with verbose logging
DEBUG=* npm run dev
```

### Performance Optimization

- Use `npm run build:analyze` to analyze bundle size
- Check Core Web Vitals in browser dev tools
- Monitor network requests in development
- Use React DevTools Profiler for component performance

## Deployment

### Production Build

1. Set up production environment variables:

```bash
cp .env.example .env.production
# Update NEXT_PUBLIC_API_URL with production API URL
```

1. Build the application:

```bash
npm run build
```

1. Start production server:

```bash
npm start
```

### Docker Deployment

```dockerfile
# Example Dockerfile
FROM node:18-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:18-alpine AS builder
WORKDIR /app
COPY . .
COPY --from=deps /app/node_modules ./node_modules
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

### Environment-Specific Configuration

- **Development**: Uses `.env.local` with debug features enabled
- **Production**: Uses `.env.production` with optimizations enabled
- **Staging**: Can use separate environment file for testing

## Contributing

1. Follow the existing code style and patterns
2. Add TypeScript types for all new interfaces
3. Implement proper error handling with user-friendly messages
4. Test responsive behavior across different screen sizes
5. Ensure accessibility compliance (WCAG 2.1 AA)
6. Add appropriate documentation for new components
7. Test API integration thoroughly
8. Follow semantic commit message conventions

### Development Workflow

1. Create feature branch from main
2. Implement changes with proper TypeScript types
3. Test locally with `npm run dev`
4. Run linting with `npm run lint:fix`
5. Check types with `npm run type-check`
6. Build and test production with `npm run preview`
7. Submit pull request with clear description

## License

This project is part of the Compliance Intelligence Platform.
