'use client';

import { useState, useCallback } from 'react';
import { FileDropZone } from './FileDropZone';
import { UploadProgress } from './UploadProgress';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { FileText, Upload, AlertCircle, CheckCircle } from 'lucide-react';
import type { UploadedFile, UploadError } from '@/types/upload';

// Configuration constants
const ACCEPTED_TYPES = ['.pdf', '.txt', '.csv', '.epub'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export function DocumentUpload() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<UploadError | null>(null);
  const [uploadStats, setUploadStats] = useState({
    total: 0,
    completed: 0,
    failed: 0
  });

  // Handle file selection from drop zone
  const handleFilesSelected = useCallback(async (files: File[]) => {
    setUploadError(null);
    setIsUploading(true);

    // Create initial file entries
    const newFiles: UploadedFile[] = files.map(file => ({
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      name: file.name,
      size: file.size,
      type: file.type,
      status: 'uploading',
      progress: 0
    }));

    setUploadedFiles(prev => [...prev, ...newFiles]);
    setUploadStats(prev => ({ ...prev, total: prev.total + files.length }));

    // Simulate upload process for each file
    for (const [index] of files.entries()) {
      const fileEntry = newFiles[index];
      
      try {
        await simulateFileUpload(fileEntry, (progress) => {
          setUploadedFiles(prev => 
            prev.map(f => 
              f.id === fileEntry.id 
                ? { ...f, progress }
                : f
            )
          );
        });

        // Mark as completed
        setUploadedFiles(prev => 
          prev.map(f => 
            f.id === fileEntry.id 
              ? { ...f, status: 'completed', progress: 100 }
              : f
          )
        );
        
        setUploadStats(prev => ({ ...prev, completed: prev.completed + 1 }));
      } catch (error) {
        // Mark as failed
        setUploadedFiles(prev => 
          prev.map(f => 
            f.id === fileEntry.id 
              ? { 
                  ...f, 
                  status: 'error', 
                  error: error instanceof Error ? error.message : 'Upload failed'
                }
              : f
          )
        );
        
        setUploadStats(prev => ({ ...prev, failed: prev.failed + 1 }));
      }
    }

    setIsUploading(false);
  }, []);

  // Handle upload errors
  const handleUploadError = useCallback((error: UploadError) => {
    setUploadError(error);
  }, []);

  // Handle file retry
  const handleRetry = useCallback(async (fileId: string) => {
    const fileToRetry = uploadedFiles.find(f => f.id === fileId);
    if (!fileToRetry) return;

    setUploadedFiles(prev => 
      prev.map(f => 
        f.id === fileId 
          ? { ...f, status: 'uploading', progress: 0, error: undefined }
          : f
      )
    );

    try {
      await simulateFileUpload(fileToRetry, (progress) => {
        setUploadedFiles(prev => 
          prev.map(f => 
            f.id === fileId 
              ? { ...f, progress }
              : f
          )
        );
      });

      setUploadedFiles(prev => 
        prev.map(f => 
          f.id === fileId 
            ? { ...f, status: 'completed', progress: 100 }
            : f
        )
      );
      
      setUploadStats(prev => ({ 
        ...prev, 
        completed: prev.completed + 1,
        failed: prev.failed - 1
      }));
    } catch (error) {
      setUploadedFiles(prev => 
        prev.map(f => 
          f.id === fileId 
            ? { 
                ...f, 
                status: 'error', 
                error: error instanceof Error ? error.message : 'Upload failed'
              }
            : f
        )
      );
    }
  }, [uploadedFiles]);

  // Handle file removal
  const handleRemove = useCallback((fileId: string) => {
    const fileToRemove = uploadedFiles.find(f => f.id === fileId);
    if (!fileToRemove) return;

    setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
    
    setUploadStats(prev => ({
      total: prev.total - 1,
      completed: fileToRemove.status === 'completed' ? prev.completed - 1 : prev.completed,
      failed: fileToRemove.status === 'error' ? prev.failed - 1 : prev.failed
    }));
  }, [uploadedFiles]);

  // Clear all files
  const handleClearAll = useCallback(() => {
    setUploadedFiles([]);
    setUploadStats({ total: 0, completed: 0, failed: 0 });
    setUploadError(null);
  }, []);

  return (
    <div className="space-y-6">
      {/* Upload Statistics */}
      {uploadStats.total > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Upload Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline" className="flex items-center gap-1">
                <Upload className="h-3 w-3" />
                Total: {uploadStats.total}
              </Badge>
              <Badge variant="default" className="flex items-center gap-1 bg-green-100 text-green-800 hover:bg-green-200">
                <CheckCircle className="h-3 w-3" />
                Completed: {uploadStats.completed}
              </Badge>
              {uploadStats.failed > 0 && (
                <Badge variant="destructive" className="flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" />
                  Failed: {uploadStats.failed}
                </Badge>
              )}
            </div>
            {uploadStats.total > 0 && (
              <div className="mt-3 flex justify-end">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={handleClearAll}
                  disabled={isUploading}
                >
                  Clear All
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Error Display */}
      {uploadError && (
        <Card className="border-destructive">
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              Upload Error
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-destructive">{uploadError.message}</p>
            {uploadError.retryable && (
              <Button 
                variant="outline" 
                size="sm" 
                className="mt-2"
                onClick={() => setUploadError(null)}
              >
                Dismiss
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* File Drop Zone */}
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Upload Documents</CardTitle>
          <CardDescription>
            Drag and drop files here or click to browse. 
            Supported formats: {ACCEPTED_TYPES.join(', ')}. 
            Maximum file size: {Math.round(MAX_FILE_SIZE / (1024 * 1024))}MB.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <FileDropZone
            onFilesSelected={handleFilesSelected}
            onUploadError={handleUploadError}
            acceptedTypes={ACCEPTED_TYPES}
            maxFileSize={MAX_FILE_SIZE}
            disabled={isUploading}
          />
        </CardContent>
      </Card>

      {/* Upload Progress */}
      {uploadedFiles.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Upload Progress</CardTitle>
            <CardDescription>
              Track the status of your document uploads
            </CardDescription>
          </CardHeader>
          <CardContent>
            <UploadProgress
              files={uploadedFiles}
              onRetry={handleRetry}
              onRemove={handleRemove}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// Simulate file upload with progress updates
async function simulateFileUpload(
  file: UploadedFile, 
  onProgress: (progress: number) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 20;
      if (progress >= 100) {
        progress = 100;
        clearInterval(interval);
        // Simulate occasional failures for demo
        if (Math.random() < 0.1) {
          reject(new Error('Network error during upload'));
        } else {
          resolve();
        }
      }
      onProgress(Math.min(progress, 100));
    }, 200);
  });
}