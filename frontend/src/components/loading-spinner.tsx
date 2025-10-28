import { cn } from "@/lib/utils";
import { Spinner } from "@/components/ui/spinner";

interface LoadingSpinnerProps {
  className?: string;
  size?: "sm" | "md" | "lg";
  text?: string;
  /** Screen reader text for accessibility */
  srText?: string;
}

export function LoadingSpinner({ 
  className, 
  size = "md", 
  text,
  srText = "Loading content, please wait"
}: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: "h-4 w-4",
    md: "h-6 w-6", 
    lg: "h-8 w-8"
  };

  return (
    <div 
      className={cn("flex items-center justify-center space-x-2", className)}
      role="status"
      aria-label={srText}
    >
      <Spinner className={sizeClasses[size]} aria-hidden="true" />
      {text && (
        <span className="text-muted-foreground" aria-live="polite">
          {text}
        </span>
      )}
      {/* Screen reader only text */}
      <span className="sr-only">{srText}</span>
    </div>
  );
}