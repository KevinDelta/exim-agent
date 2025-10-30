'use client';

import React, { useState, useCallback, useRef, DragEvent, ChangeEvent } from 'react';
import { Button } from '@/components/ui/button';
import { Upload, FileText } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { UploadError } from '@/types/upload';

interface FileDropZoneProps {
  onFilesSelected: (files: File[]) => void;
  onUploadError: (error: UploadError) => void;
  acceptedTypes: string[];
  maxFileSize: number;
  disabled?: boolean;
}

const ACCEPTED_MIME_TYPES = [
  'application/pdf',
  'text/plain',
  'text/csv',
  'application/epub+zip'
];

export const FileDropZone = React.memo(function FileDropZone({
  onFilesSelected,
  onUploadError,
  acceptedTypes,
  maxFileSize,
  disabled = false
}: FileDropZoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [, setDragCounter] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Validate file type
  const isValidFileType = useCallback((file: File): boolean => {
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    return acceptedTypes.includes(fileExtension) || ACCEPTED_MIME_TYPES.includes(file.type);
  }, [acceptedTypes]);

  // Validate file size
  const isValidFileSize = useCallback((file: File): boolean => {
    return file.size <= maxFileSize;
  }, [maxFileSize]);

  // Validate files and filter out invalid ones
  const validateFiles = useCallback((files: File[]): { validFiles: File[], errors: UploadError[] } => {
    const validFiles: File[] = [];
    const errors: UploadError[] = [];

    files.forEach(file => {
      if (!isValidFileType(file)) {
        errors.push({
          type: 'type',
          message: `File "${file.name}" has an unsupported format. Supported formats: ${acceptedTypes.join(', ')}`,
          file,
          retryable: false
        });
        return;
      }

      if (!isValidFileSize(file)) {
        const maxSizeMB = Math.round(maxFileSize / (1024 * 1024));
        errors.push({
          type: 'size',
          message: `File "${file.name}" is too large. Maximum size: ${maxSizeMB}MB`,
          file,
          retryable: false
        });
        return;
      }

      validFiles.push(file);
    });

    return { validFiles, errors };
  }, [acceptedTypes, maxFileSize, isValidFileType, isValidFileSize]);

  // Handle drag enter
  const handleDragEnter = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (disabled) return;
    
    setDragCounter(prev => prev + 1);
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragOver(true);
    }
  }, [disabled]);

  // Handle drag leave
  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (disabled) return;
    
    setDragCounter(prev => {
      const newCounter = prev - 1;
      if (newCounter === 0) {
        setIsDragOver(false);
      }
      return newCounter;
    });
  }, [disabled]);

  // Handle drag over
  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (disabled) return;
    
    // Set the dropEffect to indicate this is a valid drop target
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'copy';
    }
  }, [disabled]);

  // Handle drop
  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (disabled) return;
    
    setIsDragOver(false);
    setDragCounter(0);

    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length === 0) return;

    const { validFiles, errors } = validateFiles(droppedFiles);

    // Report errors for invalid files
    errors.forEach(error => onUploadError(error));

    // Process valid files
    if (validFiles.length > 0) {
      onFilesSelected(validFiles);
    }
  }, [disabled, validateFiles, onFilesSelected, onUploadError]);

  // Handle file input change
  const handleFileInputChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    if (selectedFiles.length === 0) return;

    const { validFiles, errors } = validateFiles(selectedFiles);

    // Report errors for invalid files
    errors.forEach(error => onUploadError(error));

    // Process valid files
    if (validFiles.length > 0) {
      onFilesSelected(validFiles);
    }

    // Reset the input value to allow selecting the same file again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }, [validateFiles, onFilesSelected, onUploadError]);

  // Handle browse button click
  const handleBrowseClick = useCallback(() => {
    if (disabled) return;
    fileInputRef.current?.click();
  }, [disabled]);

  // Handle keyboard interaction
  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLDivElement>) => {
    if (disabled) return;
    
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleBrowseClick();
    }
  }, [disabled, handleBrowseClick]);

  return (
    <div
      className={cn(
        "relative border-2 border-dashed rounded-lg p-8 text-center transition-all duration-300 transform-gpu",
        "focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2",
        {
          "border-primary bg-primary/5 scale-[1.02] shadow-lg": isDragOver && !disabled,
          "border-muted-foreground/25 hover:border-muted-foreground/50 hover:bg-muted/10 hover:scale-[1.01] hover:shadow-md": !isDragOver && !disabled,
          "border-muted-foreground/10 bg-muted/20 cursor-not-allowed": disabled,
          "cursor-pointer": !disabled
        }
      )}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onClick={handleBrowseClick}
      onKeyDown={handleKeyDown}
      tabIndex={disabled ? -1 : 0}
      role="button"
      aria-label="Upload files by dragging and dropping or clicking to browse"
      aria-disabled={disabled}
    >
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={acceptedTypes.join(',')}
        onChange={handleFileInputChange}
        className="sr-only"
        disabled={disabled}
        aria-describedby="file-upload-description"
      />

      {/* Drop zone content */}
      <div className="space-y-4">
        {/* Icon with enhanced animations */}
        <div className="flex justify-center">
          {isDragOver ? (
            <div className="p-3 bg-primary/10 rounded-full animate-pulse">
              <Upload className="h-8 w-8 text-primary animate-bounce" />
            </div>
          ) : (
            <div className={cn(
              "p-3 rounded-full transition-all duration-300 group-hover:scale-110",
              disabled ? "bg-muted" : "bg-muted/50 hover:bg-muted/70"
            )}>
              <FileText className={cn(
                "h-8 w-8 transition-all duration-300",
                disabled ? "text-muted-foreground/50" : "text-muted-foreground hover:text-foreground hover:rotate-3"
              )} />
            </div>
          )}
        </div>

        {/* Text content */}
        <div className="space-y-2">
          <h3 className={cn(
            "text-lg font-semibold",
            disabled ? "text-muted-foreground/50" : "text-foreground"
          )}>
            {isDragOver ? 'Drop files here' : 'Upload Documents'}
          </h3>
          
          <p 
            id="file-upload-description"
            className={cn(
              "text-sm",
              disabled ? "text-muted-foreground/50" : "text-muted-foreground"
            )}
          >
            {isDragOver ? (
              'Release to upload your files'
            ) : (
              <>
                Drag and drop files here, or{' '}
                <span className="font-medium text-primary">click to browse</span>
              </>
            )}
          </p>

          {/* File format info */}
          <div className={cn(
            "text-xs space-y-1",
            disabled ? "text-muted-foreground/50" : "text-muted-foreground"
          )}>
            <p>Supported formats: {acceptedTypes.join(', ')}</p>
            <p>Maximum file size: {Math.round(maxFileSize / (1024 * 1024))}MB</p>
          </div>
        </div>

        {/* Browse button for better accessibility with enhanced hover */}
        <div className="pt-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleBrowseClick}
            disabled={disabled}
            className="pointer-events-none transition-all duration-200 hover:scale-105 hover:shadow-md" // Prevent double-click since parent div handles clicks
          >
            <Upload className="h-4 w-4 mr-2 transition-transform duration-200 group-hover:rotate-12" />
            Browse Files
          </Button>
        </div>
      </div>

      {/* Enhanced drag overlay for better visual feedback */}
      {isDragOver && !disabled && (
        <div className="absolute inset-0 bg-primary/10 border-2 border-primary border-dashed rounded-lg flex items-center justify-center backdrop-blur-sm animate-pulse">
          <div className="text-center">
            <div className="relative">
              <Upload className="h-12 w-12 text-primary mx-auto mb-2 animate-bounce" />
              <div className="absolute inset-0 h-12 w-12 mx-auto bg-primary/20 rounded-full animate-ping" />
            </div>
            <p className="text-lg font-semibold text-primary animate-pulse">Drop files here</p>
          </div>
        </div>
      )}
    </div>
  );
});