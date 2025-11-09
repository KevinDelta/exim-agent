# API Endpoints - Compliance Intelligence Platform

## Overview

This document outlines the API endpoints used by the integrated compliance workflow, including request/response formats, authentication, and error handling.

## Base Configuration

```typescript
// Environment Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const API_TIMEOUT = parseInt(process.env.NEXT_PUBLIC_API_TIMEOUT || '10000', 10);
```

## Compliance Endpoints

### 1. Generate Compliance Snapshot

**Endpoint:** `POST /compliance/snapshot`

**Purpose:** Generate comprehensive compliance analysis for HTS code and trade lane

**Request:**

```typescript
interface SnapshotRequest {
  client_id: string;      // Client identifier
  sku_id: string;         // SKU identifier  
  lane_id: string;        // Trade lane (e.g., "CN-US")
  hts_code?: string;      // Optional HTS code override
}

// Example
{
  "client_id": "default-client",
  "sku_id": "sku-8517.12.00", 
  "lane_id": "CN-US",
  "hts_code": "8517.12.00"
}
```

**Response:**

```typescript
interface SnapshotResponse {
  success: boolean;
  snapshot?: {
    client_id: string;
    sku_id: string;
    lane_id: string;
    tiles: Record<string, Tile>;
    overall_risk_level: 'low' | 'warn' | 'high';
    risk_score: number;
    active_alerts_count: number;
    last_change_detected?: string;
    sources: Evidence[];
    processing_time_ms: number;
    generated_at: string;
  };
  citations?: Evidence[];
  error?: string;
  metadata?: {
    generated_at: string;
    client_id: string;
    sku_id: string;
    lane_id: string;
  };
}

// Example Response
{
  "success": true,
  "snapshot": {
    "client_id": "default-client",
    "sku_id": "sku-8517.12.00",
    "lane_id": "CN-US",
    "tiles": {
      "hts_classification": {
        "status": "clear",
        "headline": "HTS 8517.12.00 - 25% Duty Rate",
        "details_md": "**Description:** Smartphones\n**Duty Rate:** 25%",
        "last_updated": "2024-01-15T10:30:00Z"
      },
      "sanctions_screening": {
        "status": "clear", 
        "headline": "No Sanctions Issues",
        "details_md": "**Matches Found:** 0",
        "last_updated": "2024-01-15T10:30:00Z"
      }
    },
    "overall_risk_level": "low",
    "risk_score": 0.1,
    "active_alerts_count": 0,
    "processing_time_ms": 1250,
    "generated_at": "2024-01-15T10:30:00Z"
  }
}
```

**Backend Processing:**

1. **Compliance Service** initializes LangGraph
2. **Compliance Graph** executes domain tools:
   - HTSTool (classification and duty rates)
   - SanctionsTool (screening against OFAC lists)
   - RefusalsTool (import refusal history)
   - RulingsTool (relevant CBP rulings)
3. **ChromaDB** queries for relevant compliance documents
4. **LLM** generates tile summaries and risk assessment

### 2. Ask Compliance Question

**Endpoint:** `POST /compliance/ask`

**Purpose:** Answer compliance questions using RAG with compliance context

**Request:**

```typescript
interface AskRequest {
  client_id: string;      // Client identifier
  question: string;       // Natural language question
  sku_id?: string;        // Optional SKU context
  lane_id?: string;       // Optional lane context
}

// Example
{
  "client_id": "default-client",
  "question": "What are the special requirements for importing smartphones from China?",
  "sku_id": "sku-8517.12.00",
  "lane_id": "CN-US"
}
```

**Response:**

```typescript
interface AskResponse {
  success: boolean;
  answer?: string;
  citations?: Evidence[];
  question: string;
  error?: string;
}

// Example Response
{
  "success": true,
  "answer": "For importing smartphones (HTS 8517.12.00) from China, the main requirements are: 1) Section 301 tariffs of 25%, 2) FCC certification for wireless devices, 3) Potential forced labor compliance under UFLPA, 4) Standard customs documentation including commercial invoice and packing list.",
  "citations": [
    {
      "source": "USITC HTS Database",
      "url": "https://hts.usitc.gov",
      "snippet": "HTS 8517.12.00 covers smartphones and similar devices",
      "last_updated": "2024-01-15T10:30:00Z",
      "confidence": 0.95
    }
  ],
  "question": "What are the special requirements for importing smartphones from China?"
}
```

## Chat Endpoints

### 1. Send Chat Message

**Endpoint:** `POST /chat`

**Purpose:** Send message to context-aware chat system with Mem0 memory

**Request:**

```typescript
interface ChatRequest {
  message: string;
  conversation_history?: Array<{
    role: 'user' | 'assistant';
    content: string;
  }>;
  stream?: boolean;
}

// Example (Enhanced with Compliance Context)
{
  "message": "Current compliance context:\n- HTS Code: 8517.12.00\n- Trade Lane: CN-US\n- Risk Level: low\n- Active Alerts: 0\n- Analysis Areas: hts_classification, sanctions_screening\n\nUser question: What are the risks for this HTS code?",
  "conversation_history": [
    {
      "role": "user", 
      "content": "What are the risks for HTS 8517.12.00?"
    }
  ]
}
```

**Response:**

```typescript
interface ChatResponse {
  response: string;
  success: boolean;
  error?: string;
}

// Example Response
{
  "success": true,
  "response": "Based on your compliance analysis for HTS 8517.12.00 (smartphones) from China to the US, the main risks are:\n\n1. **Tariff Risk**: 25% Section 301 tariffs apply, significantly increasing landed costs\n2. **Regulatory Risk**: FCC certification required for all wireless devices\n3. **Supply Chain Risk**: Potential UFLPA (forced labor) compliance issues\n4. **Documentation Risk**: Ensure proper commercial invoices and country of origin marking\n\nYour current risk level is 'low' with 0 active alerts, which suggests good compliance posture. However, monitor for any changes in trade policies or supplier certifications."
}
```

**Backend Processing:**

1. **Chat Service** receives enhanced message with compliance context
2. **Chat Graph (LangGraph)** processes through:
   - **load_memories**: Query Mem0 for conversation history
   - **query_documents**: Search ChromaDB for relevant documents
   - **rerank_and_fuse**: Combine and rerank Mem0 + RAG context
   - **generate_response**: LLM generates context-aware response
   - **update_memories**: Store conversation in Mem0

## Utility Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Purpose:** Check system status and service availability

**Response:**

```typescript
interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy';
  stack?: {
    langgraph: boolean;
    mem0: boolean;
    reranking: boolean;
    zenml: boolean;
    compliance: boolean;
  };
  rag_documents?: {
    count: number;
    collection_name: string;
  };
  error?: string;
}

// Example Response
{
  "status": "healthy",
  "stack": {
    "langgraph": true,
    "mem0": true,
    "reranking": true,
    "zenml": true,
    "compliance": true
  },
  "rag_documents": {
    "count": 1250,
    "collection_name": "documents"
  }
}
```

### 2. Collections Status

**Endpoint:** `GET /compliance/collections/status`

**Purpose:** Get status of compliance data collections

**Response:**

```typescript
interface CollectionsStatusResponse {
  success: boolean;
  collections: Record<string, {
    count?: number;
    name?: string;
    metadata?: Record<string, unknown>;
  }>;
  total_documents: number;
}

// Example Response
{
  "success": true,
  "collections": {
    "hts_notes": {
      "count": 450,
      "name": "HTS Classification Notes"
    },
    "cbp_rulings": {
      "count": 320,
      "name": "CBP Rulings Database"
    },
    "sanctions_lists": {
      "count": 180,
      "name": "OFAC Sanctions Lists"
    }
  },
  "total_documents": 950
}
```

## Error Handling

### Error Response Format

```typescript
// Standard Error Response
{
  "success": false,
  "error": "Detailed error message",
  "detail": "Additional error context"  // FastAPI standard
}

// HTTP Status Codes
400 - Bad Request (validation errors)
401 - Unauthorized (authentication required)
403 - Forbidden (insufficient permissions)  
404 - Not Found (resource not found)
429 - Too Many Requests (rate limiting)
500 - Internal Server Error (server errors)
503 - Service Unavailable (service down)
```

### Frontend Error Handling

```typescript
class ApiError extends Error {
  public type: ApiErrorType;
  public statusCode?: number;
  public retryable: boolean;

  constructor(type: ApiErrorType, message: string, statusCode?: number, retryable: boolean = false) {
    super(message);
    this.name = 'ApiError';
    this.type = type;
    this.statusCode = statusCode;
    this.retryable = retryable;
  }
}

enum ApiErrorType {
  NETWORK_ERROR = 'network_error',
  SERVER_ERROR = 'server_error', 
  VALIDATION_ERROR = 'validation_error',
  TIMEOUT_ERROR = 'timeout_error'
}

// Error Handling with Retry Logic
const apiClient = {
  async withRetry<T>(
    operation: () => Promise<T>,
    maxRetries: number = 3,
    delay: number = 1000
  ): Promise<T> {
    let lastError: ApiError;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = this.handleApiError(error);

        if (!lastError.retryable || attempt === maxRetries) {
          throw lastError;
        }

        // Exponential backoff
        await new Promise(resolve => 
          setTimeout(resolve, delay * Math.pow(2, attempt - 1))
        );
      }
    }

    throw lastError!;
  }
};
```

## Authentication & Security

### API Key Authentication (Future)

```typescript
// Headers for authenticated requests
const headers = {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${apiKey}`,
  'X-Client-ID': clientId
};
```

### Rate Limiting

```typescript
// Rate limiting headers in response
{
  'X-RateLimit-Limit': '100',
  'X-RateLimit-Remaining': '95', 
  'X-RateLimit-Reset': '1640995200'
}
```

## Integration Examples

### Complete Compliance Workflow

```typescript
// 1. User submits HTS code and lane
const snapshotRequest: SnapshotRequest = {
  client_id: 'default-client',
  sku_id: 'sku-8517.12.00',
  lane_id: 'CN-US', 
  hts_code: '8517.12.00'
};

// 2. Fetch compliance snapshot
const snapshot = await apiClient.getComplianceSnapshot(snapshotRequest);

// 3. User asks follow-up question with context
const chatRequest: ChatRequest = {
  message: `Current compliance context:
- HTS Code: 8517.12.00
- Trade Lane: CN-US  
- Risk Level: ${snapshot.snapshot?.overall_risk_level}
- Active Alerts: ${snapshot.snapshot?.active_alerts_count}

User question: What documentation do I need for customs clearance?`,
  conversation_history: []
};

// 4. Get context-aware response
const chatResponse = await apiClient.sendChatMessage(chatRequest);
```

This API design provides **comprehensive compliance intelligence** with **context-aware chat functionality**, enabling users to get both structured compliance analysis and natural language assistance within a single integrated workflow.
