'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { 
  FileText, 
  CheckCircle, 
  AlertCircle, 
  Loader2, 
  RotateCcw, 
  X,
  Eye,
  Download
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { UploadedFile } from '@/types/upload';

interface UploadProgressProps {
  files: UploadedFile[];
  onRetry: (fileId: string) => void;
  onRemove: (fileId: string) => void;
}

export function UploadProgress({ files, onRetry, onRemove }: UploadProgressProps) {
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());

  // Toggle file details expansion
  const toggleFileExpansion = (fileId: string) => {
    setExpandedFiles(prev => {
      const newSet = new Set(prev);
      if (newSet.has(fileId)) {
        newSet.delete(fileId);
      } else {
        newSet.add(fileId);
      }
      return newSet;
    });
  };

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Get status icon
  const getStatusIcon = (file: UploadedFile) => {
    switch (file.status) {
      case 'uploading':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <FileText className="h-4 w-4 text-muted-foreground" />;
    }
  };

  // Get status badge
  const getStatusBadge = (file: UploadedFile) => {
    switch (file.status) {
      case 'uploading':
        return (
          <Badge variant="secondary" className="bg-blue-100 text-blue-800 hover:bg-blue-200">
            Uploading
          </Badge>
        );
      case 'completed':
        return (
          <Badge variant="default" className="bg-green-100 text-green-800 hover:bg-green-200">
            Completed
          </Badge>
        );
      case 'error':
        return (
          <Badge variant="destructive">
            Failed
          </Badge>
        );
      default:
        return (
          <Badge variant="outline">
            Pending
          </Badge>
        );
    }
  };

  if (files.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
        <p>No files uploaded yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {files.map((file) => {
        const isExpanded = expandedFiles.has(file.id);
        
        return (
          <div
            key={file.id}
            className={cn(
              "border rounded-lg p-4 transition-all duration-200",
              {
                "border-green-200 bg-green-50/50": file.status === 'completed',
                "border-red-200 bg-red-50/50": file.status === 'error',
                "border-blue-200 bg-blue-50/50": file.status === 'uploading',
                "border-border": file.status !== 'completed' && file.status !== 'error' && file.status !== 'uploading'
              }
            )}
          >
            {/* File header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3 min-w-0 flex-1">
                {getStatusIcon(file)}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center space-x-2">
                    <p className="text-sm font-medium truncate" title={file.name}>
                      {file.name}
                    </p>
                    {getStatusBadge(file)}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {formatFileSize(file.size)} • {file.type || 'Unknown type'}
                  </p>
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex items-center space-x-1 ml-2">
                {file.status === 'completed' && (
                  <>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleFileExpansion(file.id)}
                      className="h-8 w-8 p-0"
                      title="View details"
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                    {file.url && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => window.open(file.url, '_blank')}
                        className="h-8 w-8 p-0"
                        title="Download file"
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                    )}
                  </>
                )}
                
                {file.status === 'error' && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => onRetry(file.id)}
                    className="h-8 w-8 p-0"
                    title="Retry upload"
                  >
                    <RotateCcw className="h-4 w-4" />
                  </Button>
                )}
                
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onRemove(file.id)}
                  className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                  title="Remove file"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Progress bar for uploading files */}
            {file.status === 'uploading' && (
              <div className="mt-3">
                <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
                  <span>Uploading...</span>
                  <span>{Math.round(file.progress)}%</span>
                </div>
                <Progress value={file.progress} className="h-2" />
              </div>
            )}

            {/* Error message */}
            {file.status === 'error' && file.error && (
              <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-md">
                <div className="flex items-start space-x-2">
                  <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-red-800 font-medium">Upload Failed</p>
                    <p className="text-xs text-red-700 mt-1">{file.error}</p>
                  </div>
                </div>
              </div>
            )}

            {/* Expanded details for completed files */}
            {file.status === 'completed' && isExpanded && (
              <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-md">
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-green-700 font-medium">Status:</span>
                    <span className="text-green-800">Successfully uploaded</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-green-700 font-medium">File Size:</span>
                    <span className="text-green-800">{formatFileSize(file.size)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-green-700 font-medium">File Type:</span>
                    <span className="text-green-800">{file.type || 'Unknown'}</span>
                  </div>
                  {file.url && (
                    <div className="flex justify-between">
                      <span className="text-green-700 font-medium">File ID:</span>
                      <span className="text-green-800 font-mono text-xs">{file.id}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })}

      {/* Summary statistics */}
      <div className="pt-4 border-t">
        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
          <span>
            Total files: <span className="font-medium text-foreground">{files.length}</span>
          </span>
          <span>
            Completed: <span className="font-medium text-green-600">
              {files.filter(f => f.status === 'completed').length}
            </span>
          </span>
          <span>
            Uploading: <span className="font-medium text-blue-600">
              {files.filter(f => f.status === 'uploading').length}
            </span>
          </span>
          {files.some(f => f.status === 'error') && (
            <span>
              Failed: <span className="font-medium text-red-600">
                {files.filter(f => f.status === 'error').length}
              </span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}