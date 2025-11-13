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
const DEFAULT_TIMEOUT = Number(process.env.NEXT_PUBLIC_API_TIMEOUT ?? 100000);
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
    // Default to POST when a request body is provided unless a method was explicitly set.
    const method = options.method ?? (options.body !== undefined ? 'POST' : 'GET');
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const init: RequestInit = {
      method,
      headers,
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
      let parseError: Error | undefined;
      
      if (text) {
        try {
          data = JSON.parse(text) as T;
        } catch (e) {
          parseError = e as Error;
          this.logDebug('JSON parse failed', { text: text.substring(0, 200), error: parseError.message });
          // If response is OK but JSON parsing failed, this is a problem
          if (response.ok) {
            throw new ApiError(
              ApiErrorType.SERVER_ERROR,
              `Invalid JSON response from server: ${parseError.message}`,
              response.status,
              false
            );
          }
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

      // If we have a successful response but no data, that's unexpected
      if (!data && text) {
        throw new ApiError(
          ApiErrorType.SERVER_ERROR,
          'Received empty response body from server',
          response.status,
          false
        );
      }

      // If response is truly empty (no text), return empty object only if that's acceptable
      // Otherwise, log a warning
      if (!data && !text) {
        this.logDebug('Empty response body', { url, status: response.status });
      }

      this.logDebug('Response', { 
        url, 
        status: response.status, 
        data,
        dataType: typeof data,
        hasData: !!data,
        keys: data ? Object.keys(data as Record<string, unknown>) : []
      });
      
      // Validate response structure for AskResponse
      if (path.includes('/compliance/ask') && data) {
        const askData = data as unknown as AskResponse;
        this.logDebug('AskResponse validation', {
          hasSuccess: 'success' in askData,
          success: askData.success,
          hasAnswer: 'answer' in askData,
          answer: askData.answer ? askData.answer.substring(0, 100) : null,
          hasQuestion: 'question' in askData,
          question: askData.question ? askData.question.substring(0, 100) : null,
          hasCitations: 'citations' in askData,
          citationsCount: Array.isArray(askData.citations) ? askData.citations.length : 0,
          hasError: 'error' in askData,
          error: askData.error,
        });
      }
      
      return (data ?? ({} as T)) as T;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }

      throw new ApiError(
        ApiErrorType.NETWORK_ERROR,
        (error as Error).message || 'Network error',
        undefined,
        true,
      );
    }
  }

  async withRetry<T>(
    fn: () => Promise<T>,
    options: RetryOptions = {},
  ): Promise<T> {
    const maxRetries = options.maxRetries ?? 1;
    let delay = options.initialDelayMs ?? 500;
    let attempt = 0;

    
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
