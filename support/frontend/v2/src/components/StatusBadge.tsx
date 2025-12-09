import { Badge } from "@/components/ui/badge";
import { CheckCircle2, AlertCircle, Activity, Wifi } from "lucide-react";

type StatusType = 'live' | 'connected' | 'metrics' | 'warning' | 'error';

interface StatusBadgeProps {
  status: StatusType;
  label?: string;
}

const statusConfig: Record<StatusType, { icon: React.ReactNode; className: string; defaultLabel: string }> = {
  live: {
    icon: <CheckCircle2 className="h-3 w-3" />,
    className: 'bg-green-500/10 text-green-600 border-green-500/20',
    defaultLabel: 'Live',
  },
  connected: {
    icon: <Wifi className="h-3 w-3" />,
    className: 'bg-blue-500/10 text-blue-600 border-blue-500/20',
    defaultLabel: 'Connected',
  },
  metrics: {
    icon: <Activity className="h-3 w-3" />,
    className: 'bg-purple-500/10 text-purple-600 border-purple-500/20',
    defaultLabel: 'Metrics',
  },
  warning: {
    icon: <AlertCircle className="h-3 w-3" />,
    className: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20',
    defaultLabel: 'Warning',
  },
  error: {
    icon: <AlertCircle className="h-3 w-3" />,
    className: 'bg-red-500/10 text-red-600 border-red-500/20',
    defaultLabel: 'Error',
  },
};

export function StatusBadge({ status, label }: StatusBadgeProps) {
  const config = statusConfig[status];
  
  return (
    <Badge variant="outline" className={`gap-1 ${config.className}`}>
      {config.icon}
      {label || config.defaultLabel}
    </Badge>
  );
}
