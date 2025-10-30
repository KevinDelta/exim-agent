# Development Setup Guide

## Prerequisites

Before setting up the development environment, ensure you have:

- **Node.js 18+** (LTS recommended)
- **npm 9+** or **yarn 1.22+**
- **Git** for version control
- **VS Code** (recommended) with suggested extensions

## Initial Setup

### 1. Clone and Install

```bash
# Clone the repository
git clone <repository-url>
cd compliance-intelligence-platform/frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env.local
```

### 2. Environment Configuration

Update `.env.local` with your local settings:

```env
# Backend API URL
NEXT_PUBLIC_API_URL=http://localhost:8000

# Enable development features
NEXT_PUBLIC_ENABLE_DEBUG=true
NEXT_PUBLIC_DEBUG_NAVIGATION=true

# Chat configuration
NEXT_PUBLIC_CHAT_ENABLED=true
NEXT_PUBLIC_CHAT_API_URL=http://localhost:8000/api/chat

# Upload configuration
NEXT_PUBLIC_UPLOAD_MAX_SIZE=10485760
NEXT_PUBLIC_UPLOAD_ALLOWED_TYPES=.pdf,.txt,.csv,.epub

# Development settings
NODE_ENV=development
```

### 3. Start Development Server

```bash
# Start the development server
npm run dev

# Or with debug output
DEBUG=* npm run dev
```

The application will be available at [http://localhost:3000](http://localhost:3000).

## Development Tools

### VS Code Extensions

Install these recommended extensions:

```json
{
  "recommendations": [
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "ms-vscode.vscode-typescript-next",
    "formulahendry.auto-rename-tag",
    "christian-kohler.path-intellisense",
    "ms-vscode.vscode-json",
    "bradlc.vscode-tailwindcss"
  ]
}
```

### VS Code Settings

Create `.vscode/settings.json`:

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "typescript.preferences.importModuleSpecifier": "relative",
  "tailwindCSS.experimental.classRegex": [
    ["cn\\(([^)]*)\\)", "'([^']*)'"],
    ["cva\\(([^)]*)\\)", "[\"'`]([^\"'`]*).*?[\"'`]"]
  ]
}
```

### Browser Extensions

For development, install:

- **React Developer Tools**
- **Redux DevTools** (if using Redux)
- **Lighthouse** for performance auditing
- **axe DevTools** for accessibility testing

## Development Workflow

### 1. Code Style and Linting

```bash
# Run ESLint
npm run lint

# Fix ESLint issues automatically
npm run lint:fix

# Check TypeScript types
npm run type-check

# Format code with Prettier
npm run format
```

### 2. Testing

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run specific test file
npm test -- NavigationItem.test.tsx
```

### 3. Building and Preview

```bash
# Build for production
npm run build

# Preview production build locally
npm run preview

# Analyze bundle size
npm run build:analyze
```

## Navigation System Development

### Component Development

When working on navigation components:

1. **Start with the design system**: Use existing shadcn/ui components
2. **Follow accessibility guidelines**: Implement proper ARIA labels
3. **Test responsive behavior**: Check mobile, tablet, and desktop
4. **Add animations carefully**: Use Framer Motion for smooth transitions
5. **Implement error boundaries**: Handle errors gracefully

### Testing Navigation Components

```bash
# Test navigation functionality
npm test -- --testPathPattern=navigation

# Test chat functionality
npm test -- --testPathPattern=chat

# Test document upload
npm test -- --testPathPattern=documents
```

### Debugging Navigation Issues

Enable debug mode for detailed logging:

```tsx
// In your component
if (process.env.NEXT_PUBLIC_DEBUG_NAVIGATION === 'true') {
  console.log('Navigation state:', navigationState);
  console.log('Current route:', currentRoute);
}
```

## API Development

### Backend Integration

Ensure the backend is running:

```bash
# In the backend directory
cd ../
make start-project

# Or manually
docker-compose up -d
```

### API Testing

Test API endpoints:

```bash
# Health check
curl http://localhost:8000/health

# Chat endpoint
curl -X POST http://localhost:8000/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "sessionId": "test-session"}'

# Upload endpoint
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@test.pdf"
```

### Mock API for Development

Create mock API responses for development:

```tsx
// lib/mockApi.ts
export const mockChatResponse = {
  message: "This is a mock response",
  sessionId: "mock-session",
  timestamp: new Date().toISOString()
};

export const mockUploadResponse = {
  id: "mock-upload-id",
  filename: "test.pdf",
  status: "completed",
  progress: 100
};
```

## Performance Optimization

### Bundle Analysis

Analyze bundle size:

```bash
# Generate bundle analysis
npm run build:analyze

# View the analysis
open .next/analyze/client.html
```

### Performance Monitoring

Monitor performance during development:

```tsx
// lib/performance.ts
import { measurePerformance } from '@/lib/performance';

// Measure component render time
measurePerformance('NavigationRender', () => {
  // Component rendering logic
});
```

### Memory Profiling

Check for memory leaks:

```tsx
// Enable memory logging in development
if (process.env.NODE_ENV === 'development') {
  setInterval(() => {
    if (performance.memory) {
      console.log('Memory usage:', {
        used: Math.round(performance.memory.usedJSHeapSize / 1048576) + 'MB',
        total: Math.round(performance.memory.totalJSHeapSize / 1048576) + 'MB'
      });
    }
  }, 10000);
}
```

## Debugging

### Common Development Issues

#### Hot Reload Not Working

```bash
# Clear Next.js cache
rm -rf .next
npm run dev
```

#### TypeScript Errors

```bash
# Restart TypeScript server in VS Code
Ctrl+Shift+P -> "TypeScript: Restart TS Server"

# Check for type errors
npm run type-check
```

#### Styling Issues

```bash
# Regenerate Tailwind CSS
npm run dev

# Check for conflicting styles in browser dev tools
```

### Debug Tools

#### React DevTools

Use React DevTools to inspect:

- Component hierarchy
- Props and state
- Performance profiling
- Hook usage

#### Browser DevTools

Use browser DevTools for:

- Network requests
- Console logging
- Performance profiling
- Accessibility auditing

#### VS Code Debugging

Configure VS Code debugging in `.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Next.js: debug server-side",
      "type": "node",
      "request": "attach",
      "port": 9229,
      "skipFiles": ["<node_internals>/**"]
    },
    {
      "name": "Next.js: debug client-side",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:3000"
    }
  ]
}
```

## Git Workflow

### Branch Naming

Use descriptive branch names:

```bash
# Feature branches
git checkout -b feature/navigation-improvements
git checkout -b feature/chat-persistence

# Bug fixes
git checkout -b fix/navigation-mobile-issue
git checkout -b fix/chat-scroll-behavior

# Documentation
git checkout -b docs/navigation-guide
```

### Commit Messages

Follow conventional commit format:

```bash
# Features
git commit -m "feat(navigation): add keyboard navigation support"

# Bug fixes
git commit -m "fix(chat): resolve message persistence issue"

# Documentation
git commit -m "docs(navigation): add component usage examples"

# Performance
git commit -m "perf(navigation): optimize re-rendering with React.memo"
```

### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality:

```bash
# Install pre-commit hooks
npm run prepare

# Manually run pre-commit checks
npm run pre-commit
```

## Troubleshooting

### Port Conflicts

```bash
# Find process using port 3000
lsof -ti:3000

# Kill process
kill -9 $(lsof -ti:3000)

# Use different port
npm run dev -- -p 3001
```

### Dependency Issues

```bash
# Clear npm cache
npm cache clean --force

# Remove node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Check for outdated packages
npm outdated
```

### Build Issues

```bash
# Clear all caches
rm -rf .next node_modules package-lock.json
npm install
npm run build

# Check for TypeScript errors
npm run type-check

# Check for ESLint errors
npm run lint
```

## Production Deployment

### Environment Setup

Create production environment file:

```env
# .env.production
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_ENABLE_DEBUG=false
NEXT_PUBLIC_CHAT_ENABLED=true
NODE_ENV=production
```

### Build and Deploy

```bash
# Build for production
npm run build

# Test production build locally
npm run preview

# Deploy (example with PM2)
pm2 start npm --name "compliance-frontend" -- start
```

### Performance Checklist

Before deploying:

- [ ] Bundle size is optimized
- [ ] Images are optimized
- [ ] Unused code is removed
- [ ] Environment variables are set correctly
- [ ] Error boundaries are in place
- [ ] Accessibility is tested
- [ ] Performance metrics are acceptable

## Resources

### Documentation

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [Framer Motion Documentation](https://www.framer.com/motion/)
- [shadcn/ui Documentation](https://ui.shadcn.com)

### Tools

- [React DevTools](https://react.dev/learn/react-developer-tools)
- [Lighthouse](https://developers.google.com/web/tools/lighthouse)
- [axe DevTools](https://www.deque.com/axe/devtools/)
- [Bundle Analyzer](https://www.npmjs.com/package/@next/bundle-analyzer)

### Community

- [Next.js GitHub](https://github.com/vercel/next.js)
- [React Community](https://reactjs.org/community/support.html)
- [Tailwind CSS Discord](https://tailwindcss.com/discord)

## Getting Help

If you encounter issues:

1. Check this documentation
2. Search existing issues in the repository
3. Check the browser console for errors
4. Review the network tab for API issues
5. Create a detailed issue report with:
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Environment details
   - Screenshots if applicable.
  