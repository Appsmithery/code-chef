import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { Agent } from "@/data/agents";
import { Bot, Code, Search, Server, Settings, FileText, Target } from "lucide-react";

// Map agent IDs to Lucide icons
const iconMap: Record<string, React.ReactNode> = {
  'head-chef': <Target className="h-6 w-6" />,
  'sous-chef': <Code className="h-6 w-6" />,
  'code-review': <Search className="h-6 w-6" />,
  'infrastructure': <Server className="h-6 w-6" />,
  'cicd': <Settings className="h-6 w-6" />,
  'documentation': <FileText className="h-6 w-6" />,
};

// Map role colors to Tailwind classes
const roleColorMap: Record<string, string> = {
  'mint': 'bg-primary text-primary-foreground',
  'lavender': 'bg-accent text-accent-foreground',
  'gray-blue': 'bg-muted text-muted-foreground',
  'salmon': 'bg-secondary text-secondary-foreground',
  'light-yellow': 'bg-warning text-warning-foreground',
  'default': 'bg-muted text-muted-foreground',
};

interface AgentCardProps {
  agent: Agent;
  variant?: 'default' | 'featured';
}

export function AgentCard({ agent, variant = 'default' }: AgentCardProps) {
  const isFeatured = variant === 'featured' || agent.id === 'head-chef';
  
  return (
    <Card className={`group transition-all duration-200 hover:shadow-lg hover:-translate-y-1 ${
      isFeatured ? 'border-primary/50 bg-gradient-to-br from-background to-primary/5' : ''
    }`}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isFeatured ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'}`}>
              {iconMap[agent.id] || <Bot className="h-6 w-6" />}
            </div>
            <div>
              <CardTitle className="text-lg">{agent.name}</CardTitle>
              <Badge className={`mt-1 ${roleColorMap[agent.roleColor] || roleColorMap.default}`}>
                {agent.role}
              </Badge>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <CardDescription className="text-sm leading-relaxed">
          {agent.description}
        </CardDescription>
        
        {/* Model & Specialization */}
        <div className="grid grid-cols-2 gap-3 p-3 rounded-lg bg-muted/50">
          <div>
            <span className="text-xs text-muted-foreground uppercase tracking-wide">Model</span>
            <div className="font-mono text-sm mt-0.5">{agent.model}</div>
          </div>
          <div>
            <span className="text-xs text-muted-foreground uppercase tracking-wide">
              {agent.port ? 'Port' : 'Specialization'}
            </span>
            <div className="font-mono text-sm mt-0.5">
              {agent.port || agent.specialization}
            </div>
          </div>
        </div>
        
        {/* Capabilities */}
        <div className="flex flex-wrap gap-2">
          {agent.capabilities.map((cap) => (
            <Badge key={cap} variant="outline" className="text-xs">
              {cap}
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
