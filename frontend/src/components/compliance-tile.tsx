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

export function ComplianceTile({ tile, title, className }: ComplianceTileProps) {
  const StatusIcon = statusIcons[tile.status];
  const statusColorClass = statusColors[tile.status];
  const statusTextClass = statusTextColors[tile.status];
  const badgeVariant = statusBadgeVariants[tile.status];

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

  return (
    <Card 
      className={cn(
        "transition-all duration-200 hover:shadow-md",
        statusColorClass,
        className
      )}
      role="article"
      aria-labelledby={`tile-title-${title.replace(/\s+/g, '-').toLowerCase()}`}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle 
            id={`tile-title-${title.replace(/\s+/g, '-').toLowerCase()}`}
            className="text-sm font-medium text-foreground"
          >
            {title}
          </CardTitle>
          <StatusIcon 
            className={cn("h-4 w-4", statusTextClass)} 
            aria-hidden="true"
          />
        </div>
        <div className="flex items-center justify-between">
          <Badge 
            variant={badgeVariant}
            className="text-xs"
            aria-label={`Status: ${getStatusText(tile.status)}`}
          >
            {getStatusText(tile.status)}
          </Badge>
          <time 
            className="text-xs text-muted-foreground"
            dateTime={tile.last_updated}
            title={`Last updated: ${tile.last_updated}`}
          >
            {formatDate(tile.last_updated)}
          </time>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <CardDescription className="text-sm leading-relaxed">
          {tile.headline}
        </CardDescription>
        {tile.details_md && (
          <details className="mt-3">
            <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground transition-colors">
              View details
            </summary>
            <div 
              className="mt-2 text-xs text-muted-foreground prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: tile.details_md }}
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