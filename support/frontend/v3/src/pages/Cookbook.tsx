import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Layout from "@/components/Layout";
import { BookOpen, Code, GitBranch, Layers, Workflow, Zap, ExternalLink } from "lucide-react";

const recipes = [
  {
    category: "Getting Started",
    icon: <Zap className="h-5 w-5" />,
    items: [
      {
        title: "Quick Start Guide",
        description: "Get code-chef running locally in under 5 minutes",
        link: "https://github.com/Appsmithery/code-chef/blob/main/README.md",
      },
      {
        title: "Docker Compose Setup",
        description: "Deploy all services with a single command",
        link: "https://github.com/Appsmithery/code-chef/blob/main/deploy/docker-compose.yml",
      },
      {
        title: "Environment Configuration",
        description: "Configure API keys, secrets, and service endpoints",
        link: "https://github.com/Appsmithery/code-chef/blob/main/config/env/README.md",
      },
    ],
  },
  {
    category: "Architecture",
    icon: <Layers className="h-5 w-5" />,
    items: [
      {
        title: "System Architecture",
        description: "LangGraph workflows, StateGraph, and agent coordination",
        link: "https://github.com/Appsmithery/code-chef/blob/main/support/docs/ARCHITECTURE.md",
      },
      {
        title: "Workflow Routing",
        description: "Heuristic + LLM routing with confidence scoring",
        link: "https://github.com/Appsmithery/code-chef/blob/main/agent_orchestrator/workflows/workflow_router.py",
      },
      {
        title: "Progressive MCP Loading",
        description: "Token-efficient tool binding strategies",
        link: "https://github.com/Appsmithery/code-chef/blob/main/shared/lib/progressive_mcp_loader.py",
      },
    ],
  },
  {
    category: "Workflows",
    icon: <Workflow className="h-5 w-5" />,
    items: [
      {
        title: "Workflow Templates",
        description: "Declarative YAML workflow definitions",
        link: "https://github.com/Appsmithery/code-chef/tree/main/agent_orchestrator/workflows/templates",
      },
      {
        title: "HITL Approvals",
        description: "Human-in-the-loop gating with Linear webhooks",
        link: "https://github.com/Appsmithery/code-chef/blob/main/config/hitl/approval-policies.yaml",
      },
      {
        title: "Event Sourcing",
        description: "Workflow state persistence with PostgreSQL",
        link: "https://github.com/Appsmithery/code-chef/blob/main/config/state/workflow_events.sql",
      },
    ],
  },
  {
    category: "Development",
    icon: <Code className="h-5 w-5" />,
    items: [
      {
        title: "Adding New Agents",
        description: "Create custom agents with BaseAgent inheritance",
        link: "https://github.com/Appsmithery/code-chef/blob/main/.github/copilot-instructions.md",
      },
      {
        title: "Agent Tool Configuration",
        description: "Map MCP tools to agent nodes",
        link: "https://github.com/Appsmithery/code-chef/blob/main/config/mcp-agent-tool-mapping.yaml",
      },
      {
        title: "Model Configuration",
        description: "Configure LLM providers and model selection",
        link: "https://github.com/Appsmithery/code-chef/blob/main/config/agents/models.yaml",
      },
    ],
  },
  {
    category: "CI/CD",
    icon: <GitBranch className="h-5 w-5" />,
    items: [
      {
        title: "GitHub Actions Workflows",
        description: "Automated testing, linting, and deployment",
        link: "https://github.com/Appsmithery/code-chef/tree/main/.github/workflows",
      },
      {
        title: "Deployment Procedures",
        description: "Production deployment to DigitalOcean",
        link: "https://github.com/Appsmithery/code-chef/blob/main/support/docs/DEPLOYMENT.md",
      },
      {
        title: "Health Monitoring",
        description: "Service health endpoints and observability",
        link: "https://github.com/Appsmithery/code-chef/blob/main/agent_orchestrator/main.py",
      },
    ],
  },
  {
    category: "API Reference",
    icon: <BookOpen className="h-5 w-5" />,
    items: [
      {
        title: "Orchestrator API",
        description: "FastAPI endpoints, webhooks, and /resume",
        link: "https://codechef.appsmithery.co/docs",
      },
      {
        title: "State Persistence",
        description: "PostgreSQL schema for checkpointing",
        link: "https://github.com/Appsmithery/code-chef/blob/main/config/state/schema.sql",
      },
      {
        title: "Linear Integration",
        description: "Issue tracking, webhooks, and project mapping",
        link: "https://github.com/Appsmithery/code-chef/blob/main/config/linear/linear-config.yaml",
      },
    ],
  },
];

export default function Cookbook() {
  return (
    <Layout>
      {/* Hero Section */}
      <section className="py-20 md:py-32 bg-gradient-to-br from-background via-background to-muted">
        <div className="container">
          <div className="max-w-3xl mx-auto text-center space-y-6">
            <Badge variant="outline" className="border-accent/30 text-accent bg-accent/5">
              Documentation
            </Badge>
            <h1 className="text-5xl md:text-6xl font-bold tracking-tight">
              The <span className="text-accent">Cookbook</span>
            </h1>
            <p className="text-xl text-muted-foreground leading-relaxed">
              Recipes, guides, and reference documentation for building with code-chef. From quick start to advanced workflows.
            </p>
          </div>
        </div>
      </section>

      {/* Recipes Grid */}
      <section className="py-24 bg-background">
        <div className="container space-y-16">
          {recipes.map((section) => (
            <div key={section.category}>
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center text-accent">
                  {section.icon}
                </div>
                <h2 className="text-3xl font-bold tracking-tight">{section.category}</h2>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {section.items.map((item) => (
                  <Card
                    key={item.title}
                    className="bg-card border-border hover:border-accent/50 transition-all duration-300 group"
                  >
                    <CardHeader>
                      <CardTitle className="text-lg group-hover:text-accent transition-colors">
                        {item.title}
                      </CardTitle>
                      <CardDescription className="text-base">
                        {item.description}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <Button
                        variant="outline"
                        className="w-full border-accent/30 text-accent hover:bg-accent/10 hover:border-accent"
                        asChild
                      >
                        <a href={item.link} target="_blank" rel="noopener noreferrer">
                          View Documentation
                          <ExternalLink className="ml-2 h-4 w-4" />
                        </a>
                      </Button>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Contributing Section */}
      <section className="py-24 border-t border-border bg-muted/30">
        <div className="container">
          <div className="max-w-4xl mx-auto text-center space-y-6">
            <h2 className="text-4xl font-bold tracking-tight">
              Contributing to the Cookbook
            </h2>
            <p className="text-xl text-muted-foreground leading-relaxed">
              Found a recipe missing? Documentation unclear? Submit a PR to improve the cookbook for everyone.
            </p>
            <Button
              size="lg"
              className="bg-accent hover:bg-accent/90 text-background mt-4"
              asChild
            >
              <a
                href="https://github.com/Appsmithery/code-chef/blob/main/CONTRIBUTING.md"
                target="_blank"
                rel="noopener noreferrer"
              >
                Contribution Guidelines
                <ExternalLink className="ml-2 h-5 w-5" />
              </a>
            </Button>
          </div>
        </div>
      </section>

      {/* Observability Section */}
      <section className="py-24 border-t border-border">
        <div className="container">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-4xl font-bold tracking-tight mb-8 text-center">
              Observability & Debugging
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card className="bg-card border-accent/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BookOpen className="h-5 w-5 text-accent" />
                    LangSmith Tracing
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground">
                    All agent interactions traced with @traceable decorators. Per-agent projects for isolated debugging.
                  </p>
                  <Button variant="outline" className="w-full" asChild>
                    <a href="https://smith.langchain.com" target="_blank" rel="noopener noreferrer">
                      Open LangSmith
                      <ExternalLink className="ml-2 h-4 w-4" />
                    </a>
                  </Button>
                </CardContent>
              </Card>
              <Card className="bg-card border-accent/20">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Layers className="h-5 w-5 text-accent" />
                    Grafana Dashboards
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground">
                    Prometheus metrics and Loki logs visualized in Grafana. Real-time service health monitoring.
                  </p>
                  <Button variant="outline" className="w-full" asChild>
                    <a href="https://appsmithery.grafana.net" target="_blank" rel="noopener noreferrer">
                      Open Grafana
                      <ExternalLink className="ml-2 h-4 w-4" />
                    </a>
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>
    </Layout>
  );
}
