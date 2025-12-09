import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { MCPServer } from "@/data/servers";

interface ServerCardProps {
  server: MCPServer;
}

export function ServerCard({ server }: ServerCardProps) {
  return (
    <Card className="group transition-all duration-200 hover:shadow-lg hover:-translate-y-1 border-l-4 border-l-accent">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{server.icon}</span>
            <CardTitle className="text-base">{server.name}</CardTitle>
          </div>
          <Badge className="bg-primary text-primary-foreground">
            {server.toolCount} tools
          </Badge>
        </div>
        <span className="text-xs text-accent uppercase tracking-wide font-medium">
          {server.category}
        </span>
      </CardHeader>
      <CardContent>
        <CardDescription className="text-sm leading-relaxed">
          {server.description}
        </CardDescription>
      </CardContent>
    </Card>
  );
}
