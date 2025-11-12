import {
  ApiClientOptions,
  ApiError,
  ApiErrorType,
  AskRequest,
  AskResponse,
  ChatRequest,
  ChatResponsePayload,
  ComplianceSnapshot,
  RetryOptions,
  SnapshotRequest,
} from '@/lib/types';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

interface RequestOptions {
  method?: HttpMethod;
  body?: unknown;
  headers?: Record<string, string>;
  timeoutMs?: number;
}

const DEFAULT_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, '') || 'http://localhost:8000';
const DEFAULT_TIMEOUT = Number(process.env.NEXT_PUBLIC_API_TIMEOUT ?? 10000);
const DEBUG_ENABLED = process.env.NEXT_PUBLIC_ENABLE_DEBUG === 'true';

export class ApiClient {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;
  private readonly debug: boolean;

  constructor(baseUrl = DEFAULT_BASE_URL, options: ApiClientOptions = {}) {
    this.baseUrl = baseUrl;
    this.timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT;
    this.debug = options.debug ?? DEBUG_ENABLED;
  }

  private buildUrl(path: string): string {
    if (/^https?:\/\//i.test(path)) {
      return path;
    }
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    return `${this.baseUrl}${normalizedPath}`;
  }

  private logDebug(message: string, payload?: unknown): void {
    if (this.debug) {
      // eslint-disable-next-line no-console
      console.debug(`[api] ${message}`, payload);
    }
  }

  private mapStatusToErrorType(status: number): ApiErrorType {
    if (status === 408) {
      return ApiErrorType.TIMEOUT_ERROR;
    }
    if (status >= 500) {
      return ApiErrorType.SERVER_ERROR;
    }
    if (status >= 400) {
      return ApiErrorType.VALIDATION_ERROR;
    }
    return ApiErrorType.UNKNOWN_ERROR;
  }

  private isRetryable(type: ApiErrorType): boolean {
    return (
      type === ApiErrorType.NETWORK_ERROR ||
      type === ApiErrorType.SERVER_ERROR ||
      type === ApiErrorType.TIMEOUT_ERROR
    );
  }

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const url = this.buildUrl(path);
    const method = options.method ?? 'GET';
    const controller = new AbortController();
    const timeout = options.timeoutMs ?? this.timeoutMs;
    const timer = timeout ? setTimeout(() => controller.abort(), timeout) : null;

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const init: RequestInit = {
      method,
      headers,
      signal: controller.signal,
    };

    if (options.body !== undefined) {
      init.body =
        typeof options.body === 'string' ? options.body : JSON.stringify(options.body);
    }

    try {
      this.logDebug('Request', { url, method, body: options.body });
      const response = await fetch(url, init);
      const text = await response.text();
      let data: T | undefined;
      if (text) {
        try {
          data = JSON.parse(text) as T;
        } catch {
          data = undefined;
        }
      }

      if (!response.ok) {
        const payload = (data as Record<string, unknown>) ?? {};
        const errorMessage =
          typeof payload.error === 'string' ? payload.error : undefined;
        const detailMessage =
          typeof payload.detail === 'string' ? payload.detail : undefined;
        const message =
          errorMessage ?? detailMessage ?? response.statusText ?? 'Request failed';
        const type = this.mapStatusToErrorType(response.status);
        throw new ApiError(type, message, response.status, this.isRetryable(type));
      }

      this.logDebug('Response', { url, status: response.status, data });
      return (data ?? ({} as T)) as T;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }

      if ((error as Error).name === 'AbortError') {
        throw new ApiError(
          ApiErrorType.TIMEOUT_ERROR,
          'Request timed out',
          undefined,
          true,
        );
      }

      throw new ApiError(
        ApiErrorType.NETWORK_ERROR,
        (error as Error).message || 'Network error',
        undefined,
        true,
      );
    } finally {
      if (timer) {
        clearTimeout(timer);
      }
    }
  }

  async withRetry<T>(
    fn: () => Promise<T>,
    options: RetryOptions = {},
  ): Promise<T> {
    const maxRetries = options.maxRetries ?? 2;
    let delay = options.initialDelayMs ?? 500;
    let attempt = 0;

    // eslint-disable-next-line no-constant-condition
    while (true) {
      try {
        return await fn();
      } catch (error) {
        if (!(error instanceof ApiError)) {
          throw error;
        }

        attempt += 1;
        if (attempt > maxRetries || !error.retryable) {
          throw error;
        }

        await new Promise((resolve) => setTimeout(resolve, delay));
        delay *= 2;
      }
    }
  }

  getComplianceSnapshot(request: SnapshotRequest): Promise<ComplianceSnapshot> {
    return this.request<ComplianceSnapshot>('/compliance/snapshot', {
      method: 'POST',
      body: request,
    });
  }

  sendChatMessage(request: ChatRequest): Promise<ChatResponsePayload> {
    return this.request<ChatResponsePayload>('/chat', {
      method: 'POST',
      body: request,
    });
  }

  askComplianceQuestion(request: AskRequest): Promise<AskResponse> {
    return this.request<AskResponse>('/compliance/ask', {
      method: 'POST',
      body: request,
    });
  }
}

export const apiClient = new ApiClient();

export function getComplianceSnapshotWithRetry(
  request: SnapshotRequest,
  retryOptions?: RetryOptions,
) {
  return apiClient.withRetry(
    () => apiClient.getComplianceSnapshot(request),
    retryOptions,
  );
}

export function sendChatMessageWithRetry(
  request: ChatRequest,
  retryOptions?: RetryOptions,
) {
  return apiClient.withRetry(() => apiClient.sendChatMessage(request), retryOptions);
}

export function askComplianceQuestionWithRetry(
  request: AskRequest,
  retryOptions?: RetryOptions,
) {
  return apiClient.withRetry(
    () => apiClient.askComplianceQuestion(request),
    retryOptions,
  );
}
