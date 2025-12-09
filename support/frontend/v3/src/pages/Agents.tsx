import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import Layout from "@/components/Layout";
import { agents } from "@/data/platform";
import { Activity, Bot, FileCode, GitPullRequest, Server, Shield } from "lucide-react";

const iconMap: Record<string, React.ReactNode> = {
  orchestrator: <Bot className="h-6 w-6" />,
  "feature-dev": <FileCode className="h-6 w-6" />,
  "code-review": <Shield className="h-6 w-6" />,
  infrastructure: <Server className="h-6 w-6" />,
  cicd: <GitPullRequest className="h-6 w-6" />,
  documentation: <Activity className="h-6 w-6" />,
};

export default function Agents() {
  return (
    <Layout>
      {/* Hero Section */}
      <section className="py-20 md:py-32 bg-gradient-to-br from-background via-background to-muted">
        <div className="container">
          <div className="max-w-3xl mx-auto text-center space-y-6">
            <Badge variant="outline" className="border-accent/30 text-accent bg-accent/5">
              AI Agent Team
            </Badge>
            <h1 className="text-5xl md:text-6xl font-bold tracking-tight">
              Meet the <span className="text-accent">Team</span>
            </h1>
            <p className="text-xl text-muted-foreground leading-relaxed">
              Six specialized AI agents working together to automate your DevOps workflow. Each agent is optimized for specific tasks and powered by state-of-the-art language models.
            </p>
          </div>
        </div>
      </section>

      {/* Agents Grid */}
      <section className="py-24 bg-background">
        <div className="container">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {agents.map((agent) => (
              <Card
                key={agent.id}
                className="bg-card border-border hover:border-accent/50 transition-all duration-300 group"
              >
                <CardHeader>
                  <div className="flex items-start justify-between mb-4">
                    <div className="w-12 h-12 rounded-lg bg-accent/10 flex items-center justify-center text-accent group-hover:scale-110 transition-transform duration-300">
                      {iconMap[agent.id]}
                    </div>
                    <Badge
                      variant={agent.status === "online" ? "default" : "secondary"}
                      className={agent.status === "online" ? "bg-primary/20 text-primary hover:bg-primary/30 border-none" : ""}
                    >
                      {agent.status}
                    </Badge>
                  </div>
                  <CardTitle className="text-xl">{agent.name}</CardTitle>
                  <CardDescription className="text-base mt-2">
                    {agent.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Model:</span>
                    <span className="font-medium text-foreground">{agent.model}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Provider:</span>
                    <span className="font-medium text-foreground">{agent.provider}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Port:</span>
                    <span className="font-mono text-foreground">:{agent.port}</span>
                  </div>
                  <div className="pt-4 border-t border-border">
                    <div className="text-sm font-medium text-muted-foreground mb-2">Capabilities:</div>
                    <div className="flex flex-wrap gap-2">
                      {agent.capabilities.map((capability) => (
                        <Badge
                          key={capability}
                          variant="secondary"
                          className="bg-secondary/10 text-secondary hover:bg-secondary/20 border-none text-xs"
                        >
                          {capability}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Architecture Section */}
      <section className="py-24 border-t border-border bg-muted/30">
        <div className="container">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-4xl font-bold tracking-tight mb-8 text-center">
              How It Works
            </h2>
            <div className="space-y-6 text-muted-foreground leading-relaxed">
              <p>
                The <span className="text-accent font-medium">Orchestrator</span> (Head Chef) receives incoming tasks and intelligently routes them to the most appropriate specialized agent. Using LangGraph's StateGraph workflow engine, it maintains context across multi-step operations and coordinates handoffs between agents.
              </p>
              <p>
                Each agent is powered by carefully selected language models optimized for their specific domain. The <span className="text-accent font-medium">Feature Development</span> agent uses CodeLlama for superior code generation, while review and planning agents leverage Llama 3.3 for reasoning capabilities.
              </p>
              <p>
                Progressive tool loading ensures agents only access the MCP tools they need for each task, reducing token costs by 80-90% while maintaining full capability. All agent interactions are traced via LangSmith for debugging and optimization.
              </p>
            </div>
          </div>
        </div>
      </section>
    </Layout>
  );
}
