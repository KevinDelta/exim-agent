# Compliance Intelligence Platform - Frontend

A modern NextJS frontend application for the Compliance Intelligence Platform, providing a clean interface for displaying compliance snapshots and monitoring data.

## Technology Stack

- **Framework**: NextJS 13+ with App Router
- **Language**: TypeScript with strict mode
- **Styling**: Tailwind CSS v4 + shadcn/ui components
- **State Management**: React hooks (useState, useEffect)
- **HTTP Client**: Native fetch API with error handling

## Project Structure

```
frontend/
├── src/
│   ├── app/                     # App Router pages
│   │   ├── globals.css         # Global styles and Tailwind config
│   │   ├── layout.tsx          # Root layout with metadata
│   │   ├── page.tsx            # Home page
│   │   └── loading.tsx         # Global loading component
│   ├── components/             # Reusable UI components
│   │   ├── ui/                 # shadcn/ui components
│   │   ├── error-boundary.tsx  # Error handling component
│   │   └── loading-spinner.tsx # Loading state component
│   └── lib/                    # Utility functions
│       ├── api.ts              # API client functions
│       ├── types.ts            # TypeScript type definitions
│       └── utils.ts            # General utilities (shadcn)
├── public/                     # Static assets
├── .env.local                  # Local environment variables
└── .env.example               # Environment template
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

2. Install dependencies:
```bash
npm install
```

3. Copy environment variables:
```bash
cp .env.example .env.local
```

4. Update `.env.local` with your API URL if different from default:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

Start the development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

### Build for Production

```bash
npm run build
npm start
```

## Features

### Current Implementation

- ✅ NextJS 13+ with App Router
- ✅ TypeScript with strict mode
- ✅ Tailwind CSS v4 with custom theme
- ✅ shadcn/ui component library
- ✅ API client with error handling
- ✅ Loading states and error boundaries
- ✅ Responsive design foundation
- ✅ Environment configuration

### Planned Features

- [ ] Compliance snapshot card component
- [ ] Individual compliance tile components
- [ ] Real-time data fetching from API
- [ ] Comprehensive error handling
- [ ] Accessibility features (WCAG 2.1 AA)
- [ ] Unit and integration tests

## API Integration

The frontend connects to the Compliance Intelligence Platform backend API:

- **Base URL**: `http://localhost:8000` (configurable via environment)
- **Endpoints**: `/compliance/snapshot` (planned)
- **Error Handling**: Automatic retry logic with exponential backoff
- **Type Safety**: Full TypeScript interfaces for API requests/responses

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000` |
| `NODE_ENV` | Environment mode | `development` |

## Development Guidelines

### Code Style
- Use TypeScript strict mode
- Follow React/NextJS best practices
- Implement proper error boundaries
- Use semantic HTML and ARIA labels
- Maintain responsive design principles

### Component Structure
- Keep components focused and reusable
- Use proper TypeScript interfaces
- Implement loading and error states
- Follow shadcn/ui patterns

### API Integration
- Use the centralized API client
- Implement proper error handling
- Add request/response validation
- Use environment-based configuration

## Contributing

1. Follow the existing code style and patterns
2. Add TypeScript types for all new interfaces
3. Implement proper error handling
4. Test responsive behavior
5. Ensure accessibility compliance

## License

This project is part of the Compliance Intelligence Platform.
