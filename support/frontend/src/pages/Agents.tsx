import Layout from "@/components/Layout";
import MermaidDiagram from "@/components/MermaidDiagram";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { agents } from "@/data/platform";
import {
  Activity,
  Bot,
  FileCode,
  GitPullRequest,
  Server,
  Shield,
} from "lucide-react";

const iconMap: Record<string, React.ReactNode> = {
  orchestrator: <Bot className="h-6 w-6" />,
  "feature-dev": <FileCode className="h-6 w-6" />,
  "code-review": <Shield className="h-6 w-6" />,
  infrastructure: <Server className="h-6 w-6" />,
  cicd: <GitPullRequest className="h-6 w-6" />,
  documentation: <Activity className="h-6 w-6" />,
};

const architectureDiagram = `flowchart TB
    subgraph VSCode["🖥️ VS Code"]
        Chat["@chef Add JWT auth to my Express API"]
    end

    subgraph Orchestrator["🧑‍🍳 code/chef Orchestrator"]
        Supervisor["Supervisor\\n(Head Chef)"]
        
        subgraph Agents["Specialized Agents"]
            FeatureDev["🚀 Feature Dev"]
            CodeReview["🔍 Code Review"]
            CICD["⚡ CI/CD"]
            Infra["🏗️ Infrastructure"]
            Docs["📚 Documentation"]
        end
        
        Tools["🔧 150+ MCP Tools"]
    end

    subgraph Integrations["External Services"]
        GitHub["🐙 GitHub"]
        Linear["📋 Linear"]
        Docker["🐳 Docker"]
        Metrics["📊 Metrics"]
    end

    Chat --> Supervisor
    Supervisor --> FeatureDev
    Supervisor --> CodeReview
    Supervisor --> CICD
    Supervisor --> Infra
    Supervisor --> Docs
    
    FeatureDev --> Tools
    CodeReview --> Tools
    CICD --> Tools
    Infra --> Tools
    Docs --> Tools
    
    Tools --> GitHub
    Tools --> Linear
    Tools --> Docker
    Tools --> Metrics

    style VSCode fill:transparent,stroke:#4c5270
    style Orchestrator fill:transparent,stroke:#4c5270
    style Agents fill:transparent,stroke:#4c5270
    style Integrations fill:transparent,stroke:#4c5270
    style Chat fill:transparent,stroke:#bcece0
    style Supervisor fill:transparent,stroke:#bcece0
    style FeatureDev fill:transparent,stroke:#bcece0
    style CodeReview fill:transparent,stroke:#bcece0
    style CICD fill:transparent,stroke:#bcece0
    style Infra fill:transparent,stroke:#bcece0
    style Docs fill:transparent,stroke:#bcece0
    style Tools fill:transparent,stroke:#bcece0
    style GitHub fill:transparent,stroke:#f4b9b8
    style Linear fill:transparent,stroke:#f4b9b8
    style Docker fill:transparent,stroke:#f4b9b8
    style Metrics fill:transparent,stroke:#f4b9b8`;

export default function Agents() {
  return (
    <Layout>
      {/* Hero Section */}
      <section className="relative overflow-hidden py-20 md:py-32 lg:py-40 bg-gradient-to-br from-background via-background to-muted">
        {/* Decorative Background */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-primary/5 rounded-full blur-3xl pointer-events-none -mr-48 -mt-48" />
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-accent/5 rounded-full blur-3xl pointer-events-none -ml-48 -mb-48" />

        <div className="container relative z-10">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-8">
              <div className="space-y-4">
                <Badge
                  variant="outline"
                  className="border-accent/30 text-accent bg-accent/5"
                >
                  AI Agent Team
                </Badge>
                <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-tight">
                  <span style={{ color: "#887bb0" }}>Le</span>{" "}
                  <span style={{ color: "#fffdf2" }} className="italic">
                    Brigade
                  </span>
                </h1>
                <p className="text-xl md:text-2xl text-muted-foreground max-w-[600px] leading-relaxed">
                  The code/chef kitchen comes fully-staffed with six specialized
                  AI agents working together to automate your DevOps workflow.
                  Each agent is optimized for specific tasks and powered by
                  state-of-the-art LLMs.
                </p>
              </div>
            </div>

            {/* Logo Visual */}
            <div className="relative hidden lg:flex items-center justify-center">
              <div className="absolute -inset-1 bg-gradient-to-r from-accent to-secondary rounded-full blur opacity-20"></div>
              <img
                src="/logos/knives_icon_transparent.svg"
                alt="code/chef"
                className="relative w-64 h-64 object-contain"
              />
            </div>
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
                      variant={
                        agent.status === "online" ? "default" : "secondary"
                      }
                      className={
                        agent.status === "online"
                          ? "bg-primary/20 text-primary hover:bg-primary/30 border-none"
                          : ""
                      }
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
                  <div>
                    <div className="text-sm font-medium text-muted-foreground mb-2">
                      Capabilities:
                    </div>
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
                The{" "}
                <span className="text-accent font-medium">Orchestrator</span>{" "}
                (Head Chef) receives incoming tasks and intelligently routes
                them to the most appropriate specialized agent. Using
                LangGraph's StateGraph workflow engine, it maintains context
                across multi-step operations and coordinates handoffs between
                agents.
              </p>
              <p>
                Each agent is powered by carefully selected language models
                optimized for their specific domain. The{" "}
                <span className="text-accent font-medium">
                  Feature Development
                </span>{" "}
                agent uses CodeLlama for superior code generation, while review
                and planning agents leverage Llama 3.3 for reasoning
                capabilities.
              </p>
              <p>
                Progressive tool loading ensures agents only access the MCP
                tools they need for each task, reducing token costs by 80-90%
                while maintaining full capability. All agent interactions are
                traced via LangSmith for debugging and optimization.
              </p>
            </div>

            {/* Architecture Diagram */}
            <div className="mt-12 relative">
              <div className="absolute -inset-1 bg-gradient-to-r from-accent to-secondary rounded-2xl blur opacity-10"></div>
              <div className="relative bg-transparent border border-border rounded-xl overflow-hidden shadow-lg">
                <div className="p-8">
                  <MermaidDiagram chart={architectureDiagram} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </Layout>
  );
}
