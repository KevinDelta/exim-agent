// ---------------------------------------------------------------------------
// Compliance snapshot domain types
// ---------------------------------------------------------------------------

export type TileStatus = 'clear' | 'attention' | 'action' | 'error';

export type RiskLevel = 'low' | 'warn' | 'high';

export interface Tile {
  status: TileStatus;
  headline: string;
  details_md?: string;
  last_updated?: string;
  summary_md?: string;
  action_items?: string[];
}

export interface Citation {
  source: string;
  url?: string;
  snippet?: string;
  last_updated?: string;
  confidence?: number;
}

export interface SnapshotMetadata {
  generated_at?: string;
  client_id?: string;
  sku_id?: string;
  lane_id?: string;
  [key: string]: unknown;
}

export interface ComplianceSnapshotData {
  client_id: string;
  sku_id: string;
  lane_id: string;
  tiles: Record<string, Tile>;
  overall_risk_level: RiskLevel;
  risk_score?: number;
  active_alerts_count: number;
  processing_time_ms: number;
  generated_at: string;
  last_change_detected?: string;
  sources?: Citation[];
}

export interface ComplianceSnapshot {
  success: boolean;
  snapshot: ComplianceSnapshotData | null;
  citations?: Citation[];
  error?: string | null;
  metadata?: SnapshotMetadata | null;
}

export interface SnapshotRequest {
  client_id: string;
  sku_id: string;
  lane_id: string;
  hts_code?: string;
}

export interface AskRequest {
  client_id: string;
  question: string;
  sku_id?: string;
  lane_id?: string;
}

export interface AskResponse {
  success: boolean;
  answer?: string | null;
  citations?: Citation[] | null;
  question: string;
  error?: string | null;
}

export interface SnapshotCardProps {
  snapshot: ComplianceSnapshot | null;
  loading: boolean;
  error: string | null;
  onRefresh: () => Promise<void> | void;
}

// ---------------------------------------------------------------------------
// Chat + API payloads
// ---------------------------------------------------------------------------

export type ChatMessagePayload = string | Record<string, unknown>;

export interface ConversationTurn {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface ChatRequest {
  message: ChatMessagePayload;
  conversation_history?: ConversationTurn[];
  stream?: boolean;
}

export interface ChatResponsePayload {
  success: boolean;
  response?: string;
  error?: string | null;
}

// ---------------------------------------------------------------------------
// API client + error handling
// ---------------------------------------------------------------------------

export interface ApiClientOptions {
  timeoutMs?: number;
  debug?: boolean;
}

export interface RetryOptions {
  maxRetries?: number;
  initialDelayMs?: number;
}

export enum ApiErrorType {
  NETWORK_ERROR = 'network_error',
  SERVER_ERROR = 'server_error',
  VALIDATION_ERROR = 'validation_error',
  TIMEOUT_ERROR = 'timeout_error',
  UNKNOWN_ERROR = 'unknown_error',
}

export class ApiError extends Error {
  readonly type: ApiErrorType;
  readonly statusCode?: number;
  readonly retryable: boolean;

  constructor(
    type: ApiErrorType,
    message: string,
    statusCode?: number,
    retryable = false
  ) {
    super(message);
    this.name = 'ApiError';
    this.type = type;
    this.statusCode = statusCode;
    this.retryable = retryable;
  }
}
