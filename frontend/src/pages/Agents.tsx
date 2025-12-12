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
import { useActiveSection } from "@/lib/scroll";
import {
  Activity,
  Bot,
  FileCode,
  GitPullRequest,
  Server,
  Shield,
  type LucideIcon,
} from "lucide-react";

const iconMap: Record<string, LucideIcon> = {
  orchestrator: Bot,
  "feature-dev": FileCode,
  "code-review": Shield,
  infrastructure: Server,
  cicd: GitPullRequest,
  documentation: Activity,
};

const agentPlaybooks: Record<
  string,
  {
    title: string;
    bullets: string[];
    accent: "primary" | "secondary" | "accent";
  }
> = {
  orchestrator: {
    title: "Direct the kitchen",
    bullets: [
      "Choose the right agent for the task",
      "Maintain state across multi-step workflows",
      "Gate risky operations for approval",
    ],
    accent: "accent",
  },
  "feature-dev": {
    title: "Ship features",
    bullets: [
      "Generate code and refactors",
      "Implement new endpoints and UI changes",
      "Wire tools + tests into the workflow",
    ],
    accent: "secondary",
  },
  "code-review": {
    title: "Raise quality",
    bullets: [
      "Find security issues early",
      "Enforce style and architecture norms",
      "Recommend safe fixes + edge-case tests",
    ],
    accent: "primary",
  },
  infrastructure: {
    title: "Operate reliably",
    bullets: [
      "Compose/Terraform changes",
      "Secrets and environment management",
      "Health checks + rollbacks",
    ],
    accent: "accent",
  },
  cicd: {
    title: "Automate delivery",
    bullets: [
      "GitHub Actions workflows",
      "Release + deploy pipelines",
      "Test gates and artifacts",
    ],
    accent: "secondary",
  },
  documentation: {
    title: "Explain the system",
    bullets: [
      "Docs that match the code",
      "Runbooks and operator guidance",
      "Architecture diagrams and examples",
    ],
    accent: "primary",
  },
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
  const { activeId, register } = useActiveSection({
    initialActiveId: agents[0]?.id,
    rootMargin: "-45% 0px -50% 0px",
  });

  const activeAgent =
    agents.find((a) => a.id === activeId) ?? agents[0] ?? null;
  const ActiveIcon = activeAgent ? iconMap[activeAgent.id] ?? Bot : Bot;

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

      {/* Agents: Sticky Console + Long Scroll */}
      <section className="py-24 bg-background">
        <div className="container">
          <div className="flex flex-col mb-12 space-y-4">
            <Badge
              variant="outline"
              className="border-accent/30 text-accent bg-accent/5"
            >
              Team
            </Badge>
            <h2 className="text-4xl md:text-5xl font-bold tracking-tight">
              A brigade that ships.
            </h2>
            <p className="text-muted-foreground max-w-[750px] leading-relaxed">
              Scroll to meet each agent in detail. The console stays pinned so
              you can feel the handoff—routing, execution, review, and delivery.
            </p>
          </div>

          <div className="grid lg:grid-cols-12 gap-10 items-start">
            {/* Sticky agent console */}
            <div className="lg:col-span-4 lg:sticky lg:top-24 space-y-6">
              <div className="relative">
                <div className="absolute -inset-1 bg-gradient-to-r from-accent to-secondary rounded-2xl blur opacity-10" />
                <div className="relative rounded-xl border border-border bg-card shadow-medium dark:shadow-medium-dark overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-muted">
                    <div className="text-xs font-medium text-muted-foreground">
                      agent-console
                    </div>
                    <Badge className="bg-primary/20 text-primary hover:bg-primary/30 border-none">
                      live
                    </Badge>
                  </div>
                  <div className="p-6">
                    <div className="flex items-start justify-between gap-6">
                      <div>
                        <div className="text-xs uppercase tracking-wider text-muted-foreground">
                          Active
                        </div>
                        <div className="text-2xl font-bold tracking-tight mt-1">
                          {activeAgent?.name ?? "Agents"}
                        </div>
                        <div className="text-sm text-muted-foreground mt-2 leading-relaxed">
                          {activeAgent?.description ??
                            "A specialist crew that handles routing, implementation, review, infrastructure, and docs."}
                        </div>
                      </div>
                      <div className="shrink-0 w-14 h-14 rounded-xl bg-accent/10 border border-accent/20 flex items-center justify-center text-accent cc-float">
                        <ActiveIcon className="h-7 w-7" />
                      </div>
                    </div>

                    <div className="mt-6 grid grid-cols-3 gap-3">
                      {agents.map((a) => {
                        const Icon = iconMap[a.id] ?? Bot;
                        const isActive = a.id === (activeAgent?.id ?? "");
                        return (
                          <div
                            key={a.id}
                            className={
                              "rounded-lg border p-3 transition-all duration-300 " +
                              (isActive
                                ? "bg-secondary/10 border-secondary/30"
                                : "bg-card/60 border-border hover:border-accent/40")
                            }
                          >
                            <div className="flex items-center justify-between">
                              <div
                                className={
                                  "w-9 h-9 rounded-md flex items-center justify-center " +
                                  (isActive
                                    ? "bg-secondary/15 text-secondary"
                                    : "bg-accent/10 text-accent")
                                }
                              >
                                <Icon className="h-5 w-5" />
                              </div>
                              <div
                                className={
                                  "text-[10px] uppercase tracking-wider " +
                                  (isActive
                                    ? "text-secondary"
                                    : "text-muted-foreground")
                                }
                              >
                                {a.status}
                              </div>
                            </div>
                            <div className="mt-2 text-xs font-medium truncate">
                              {a.id}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Scroll narrative */}
            <div className="lg:col-span-8 space-y-10">
              {agents.map((agent) => {
                const Icon = iconMap[agent.id] ?? Bot;
                const playbook = agentPlaybooks[agent.id];
                const accentBadge =
                  playbook?.accent === "secondary"
                    ? "bg-secondary/20 text-secondary-foreground border-none"
                    : playbook?.accent === "primary"
                    ? "bg-primary/20 text-primary border-none"
                    : "bg-accent/20 text-accent-foreground border-none";

                return (
                  <section
                    key={agent.id}
                    id={agent.id}
                    ref={register(agent.id)}
                    className="scroll-mt-28"
                  >
                    <Card className="bg-gradient-to-br from-card to-muted/30 shadow-soft dark:shadow-soft-dark border-border">
                      <CardHeader className="p-8 pb-6">
                        <div className="flex items-start justify-between gap-6">
                          <div className="space-y-2">
                            <div className="flex items-center gap-3 flex-wrap">
                              <div className="w-12 h-12 rounded-lg bg-accent/10 border border-accent/20 flex items-center justify-center text-accent">
                                <Icon className="h-6 w-6" />
                              </div>
                              <Badge className={accentBadge}>
                                {playbook?.title ?? "Agent"}
                              </Badge>
                              <Badge
                                variant={
                                  agent.status === "online"
                                    ? "default"
                                    : "secondary"
                                }
                                className={
                                  agent.status === "online"
                                    ? "bg-primary/20 text-primary hover:bg-primary/30 border-none"
                                    : ""
                                }
                              >
                                {agent.status}
                              </Badge>
                              <Badge
                                variant="secondary"
                                className="bg-secondary/10 text-secondary border-none"
                              >
                                :{agent.port}
                              </Badge>
                            </div>
                            <CardTitle className="text-2xl md:text-3xl">
                              {agent.name}
                            </CardTitle>
                            <CardDescription className="text-base leading-relaxed">
                              {agent.description}
                            </CardDescription>
                          </div>
                          <div className="hidden md:block text-right">
                            <div className="text-xs text-muted-foreground uppercase tracking-wider">
                              Model
                            </div>
                            <div className="text-sm font-medium mt-1">
                              {agent.provider} · {agent.model}
                            </div>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="p-8 pt-0 space-y-6">
                        <div className="grid md:grid-cols-2 gap-6">
                          <div>
                            <div className="text-sm font-medium text-muted-foreground mb-2">
                              Capabilities
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

                          <div>
                            <div className="text-sm font-medium text-muted-foreground mb-2">
                              Typical tasks
                            </div>
                            <ul className="space-y-2 text-sm text-muted-foreground leading-relaxed">
                              {(playbook?.bullets ?? []).map((b) => (
                                <li key={b} className="flex gap-2">
                                  <span className="text-primary">•</span>
                                  <span>{b}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>

                        <div className="rounded-lg border border-border bg-background/50 p-4">
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span className="text-primary">➜</span>
                            <span className="font-medium text-foreground">
                              @chef
                            </span>
                            <span>
                              {agent.id === "orchestrator"
                                ? "route a deployment with approval gates"
                                : agent.id === "feature-dev"
                                ? "implement JWT middleware and tests"
                                : agent.id === "code-review"
                                ? "audit for auth bypass and injection"
                                : agent.id === "infrastructure"
                                ? "update compose + verify health"
                                : agent.id === "cicd"
                                ? "add CI workflow with caching"
                                : "draft docs for the new endpoint"}
                            </span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </section>
                );
              })}
            </div>
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
