'use client';

import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tile, TileStatus } from "@/lib/types";
import { AlertTriangle, CheckCircle, Clock, XCircle } from "lucide-react";

interface ComplianceTileProps {
  tile: Tile;
  title: string;
  className?: string;
}

// Status icon mapping
const statusIcons = {
  clear: CheckCircle,
  attention: Clock,
  action: AlertTriangle,
  error: XCircle,
} as const;

// Status color mapping for backgrounds and borders
const statusColors = {
  clear: "border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950",
  attention: "border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-950",
  action: "border-orange-200 bg-orange-50 dark:border-orange-800 dark:bg-orange-950",
  error: "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950",
} as const;

// Status text colors
const statusTextColors = {
  clear: "text-green-700 dark:text-green-300",
  attention: "text-yellow-700 dark:text-yellow-300",
  action: "text-orange-700 dark:text-orange-300",
  error: "text-red-700 dark:text-red-300",
} as const;

// Badge variant mapping
const statusBadgeVariants = {
  clear: "default" as const,
  attention: "secondary" as const,
  action: "destructive" as const,
  error: "destructive" as const,
};

const statusBadgeClasses = {
  clear: "bg-green-100 text-green-900 border-green-200 dark:bg-green-900 dark:text-green-100 dark:border-green-800",
  attention: "bg-yellow-100 text-yellow-900 border-yellow-200 dark:bg-yellow-900 dark:text-yellow-100 dark:border-yellow-800",
  action: "bg-orange-100 text-orange-900 border-orange-200 dark:bg-orange-900 dark:text-orange-100 dark:border-orange-800",
  error: "bg-red-100 text-red-900 border-red-200 dark:bg-red-900 dark:text-red-100 dark:border-red-800",
};

export function ComplianceTile({ tile, title, className }: ComplianceTileProps) {
  const StatusIcon = statusIcons[tile.status];
  const statusColorClass = statusColors[tile.status];
  const statusTextClass = statusTextColors[tile.status];
  const badgeVariant = statusBadgeVariants[tile.status];
  const badgeClassName = statusBadgeClasses[tile.status];

  // Format the last updated date
  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return 'Unknown';
    }
  };

  // Get status display text
  const getStatusText = (status: TileStatus) => {
    switch (status) {
      case 'clear':
        return 'Compliant';
      case 'attention':
        return 'Needs Attention';
      case 'action':
        return 'Action Required';
      case 'error':
        return 'Error';
      default:
        return 'Unknown';
    }
  };

  const lastUpdated = tile.last_updated ?? '';
  const formattedLastUpdated = formatDate(lastUpdated);

  const tileId = `tile-${title.replace(/\s+/g, '-').toLowerCase()}`;
  const statusId = `${tileId}-status`;
  const descriptionId = `${tileId}-description`;
//TODO: Add a tooltip to the status icon
  return (
    <Card 
      className={cn(
        "transition-all duration-200 hover:shadow-md focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2",
        statusColorClass,
        className
      )}
      role="article"
      aria-labelledby={tileId}
      aria-describedby={`${statusId} ${descriptionId}`}
      tabIndex={0}
    >
      <CardHeader className="p-3 sm:p-4 pb-2 sm:pb-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle 
            id={tileId}
            className="text-responsive-sm font-medium text-foreground leading-tight"
          >
            {title}
          </CardTitle>
          <StatusIcon 
            className={cn("h-4 w-4 flex-shrink-0", statusTextClass)} 
            aria-hidden="true"
            role="img"
            aria-label={`Status indicator: ${getStatusText(tile.status)}`}
          />
        </div>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 sm:gap-2">
          <Badge 
            id={statusId}
            variant={badgeVariant}
            className={cn("text-responsive-xs self-start", badgeClassName)}
            role="status"
            aria-label={`Current status: ${getStatusText(tile.status)}`}
          >
            {getStatusText(tile.status)}
          </Badge>
          <time 
            className="text-responsive-xs text-muted-foreground"
            dateTime={lastUpdated}
            title={lastUpdated ? `Last updated: ${lastUpdated}` : 'Last updated: Unknown'}
            aria-label={`Last updated: ${formattedLastUpdated}`}
          >
            {formattedLastUpdated}
          </time>
        </div>
      </CardHeader>
      <CardContent className="p-3 sm:p-4 pt-0">
        <CardDescription 
          id={descriptionId}
          className="text-responsive-sm leading-relaxed"
        >
          {tile.headline}
        </CardDescription>
        {tile.details_md && (
          <details className="mt-2 sm:mt-3" aria-label={`Additional details for ${title}`}>
            <summary 
              className="cursor-pointer text-responsive-xs text-muted-foreground hover:text-foreground transition-colors touch-target focus-ring list-none"
              aria-expanded="false"
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  e.currentTarget.click();
                }
              }}
            >
              <span className="flex items-center gap-1">
                <span>View details</span>
                <span className="text-xs" aria-hidden="true">▼</span>
              </span>
            </summary>
            <div 
              className="mt-2 text-responsive-xs text-muted-foreground prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: tile.details_md }}
              role="region"
              aria-label={`Detailed information for ${title}`}
            />
          </details>
        )}
      </CardContent>
    </Card>
  );
}

// Alternative interface for design document compatibility
interface LegacyComplianceTileProps {
  title: string;
  status: 'compliant' | 'warning' | 'critical' | 'unknown';
  description: string;
  last_updated: string;
  details?: Record<string, unknown>;
  className?: string;
}

// Legacy component for backward compatibility with design document interface
export function LegacyComplianceTile({
  title,
  status,
  description,
  last_updated,
  details,
  className
}: LegacyComplianceTileProps) {
  // Map legacy status to new TileStatus
  const mapLegacyStatus = (legacyStatus: string): TileStatus => {
    switch (legacyStatus) {
      case 'compliant':
        return 'clear';
      case 'warning':
        return 'attention';
      case 'critical':
        return 'action';
      case 'unknown':
      default:
        return 'error';
    }
  };

  // Convert to new Tile format
  const tile: Tile = {
    status: mapLegacyStatus(status),
    headline: description,
    details_md: details ? JSON.stringify(details, null, 2) : '',
    last_updated,
  };

  return <ComplianceTile tile={tile} title={title} className={className} />;
}
