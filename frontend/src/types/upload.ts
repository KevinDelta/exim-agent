// Document upload types for the Compliance Intelligence Platform

// Core upload interfaces
export interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  status: 'uploading' | 'completed' | 'error';
  progress: number;
  url?: string;
  error?: string;
}

export interface UploadError {
  type: 'size' | 'type' | 'network' | 'server';
  message: string;
  file?: File;
  retryable: boolean;
}

// Component prop interfaces
export interface DocumentUploadProps {
  onUploadComplete: (files: UploadedFile[]) => void;
  onUploadError: (error: UploadError) => void;
  acceptedTypes: string[];
  maxFileSize: number;
}

export interface FileDropZoneProps {
  onFilesSelected: (files: File[]) => void;
  acceptedTypes: string[];
  maxFileSize: number;
  disabled?: boolean;
}

export interface UploadProgressProps {
  files: UploadedFile[];
  onRetry: (fileId: string) => void;
  onRemove: (fileId: string) => void;
}

// API interfaces
export interface DocumentApiClient {
  uploadDocument: (file: File) => Promise<UploadResponse>;
  getUploadStatus: (uploadId: string) => Promise<UploadStatus>;
  deleteDocument: (documentId: string) => Promise<void>;
}

export interface UploadResponse {
  success: boolean;
  uploadId: string;
  url?: string;
  error?: string;
}

export interface UploadStatus {
  uploadId: string;
  status: 'uploading' | 'completed' | 'error';
  progress: number;
  error?: string;
}