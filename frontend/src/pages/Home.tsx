import Layout from "@/components/Layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Activity,
  ArrowRight,
  BookOpen,
  Bot,
  Cloud,
  Search,
  ShieldCheck,
  Sparkles,
  Wrench,
} from "lucide-react";

export default function Home() {
  const capabilityRails = [
    {
      id: "multi-agent",
      title: "Multi-Agent Orchestration",
      description:
        "LangGraph StateGraph workflow with intelligent task routing. The Head Chef (Orchestrator) coordinates specialized agents for optimal results.",
      Icon: Bot,
      accent: "accent" as const,
      bullets: [
        "LangGraph StateGraph",
        "Deterministic handoffs",
        "Context-aware routing",
      ],
    },
    {
      id: "mcp-tools",
      title: "MCP Tool Integration",
      description:
        "Docker MCP Toolkit with 20 servers and 178+ tools. Progressive disclosure saves 80–90% on token costs.",
      Icon: Wrench,
      accent: "secondary" as const,
      bullets: ["20 MCP servers", "178+ tools", "Invoke-time tool binding"],
    },
    {
      id: "rag",
      title: "RAG Semantic Search",
      description:
        "Qdrant-backed retrieval across code patterns, Linear issues, and documentation for contextual assistance.",
      Icon: Search,
      accent: "primary" as const,
      bullets: ["Code patterns", "Linear issues", "Documentation"],
    },
    {
      id: "observability",
      title: "Full Observability",
      description:
        "LangSmith tracing for LLM calls, Grafana Cloud for metrics, and PostgreSQL checkpointing for durable workflows.",
      Icon: Activity,
      accent: "primary" as const,
      bullets: [
        "LangSmith traces",
        "Grafana dashboards",
        "Postgres checkpoints",
      ],
    },
    {
      id: "hitl",
      title: "Human-in-the-Loop",
      description:
        "Risk-based approval workflows via Linear integration. Critical changes require human sign-off.",
      Icon: ShieldCheck,
      accent: "primary" as const,
      bullets: ["Risk assessment", "Approval policies", "Audit trail"],
    },
    {
      id: "cloud",
      title: "Cloud-Native Agents",
      description:
        "Running on DigitalOcean with Caddy reverse proxy, automatic HTTPS, and optimized for a small memory footprint.",
      Icon: Cloud,
      accent: "accent" as const,
      bullets: ["Caddy + HTTPS", "Compose deploy", "Health endpoints"],
    },
    {
      id: "modelops",
      title: "Train Your Own AI",
      description:
        "ModelOps makes it easy to fine-tune on your codebase—train in about an hour, test results, and deploy with one click.",
      Icon: Sparkles,
      accent: "secondary" as const,
      bullets: ["One-hour training", "Automatic testing", "Safe rollback"],
    },
  ];

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
                <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-tight">
                  <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                    code/chef
                  </span>
                </h1>
                <p className="text-2xl md:text-3xl text-muted-foreground max-w-[600px] leading-relaxed">
                  AI DevOps agents and workflows for the modern code kitchen.
                </p>
              </div>

              <div className="flex flex-wrap gap-4">
                <Button
                  size="lg"
                  className="bg-accent text-accent-foreground hover:bg-accent/90 h-12 px-8 font-medium"
                  onClick={() => (window.location.href = "/agents")}
                >
                  <Bot className="mr-2 h-5 w-5" />
                  Meet the Team
                </Button>
                <Button
                  size="lg"
                  variant="outline"
                  className="border-accent/30 text-accent hover:bg-accent hover:text-accent-foreground h-12 px-8 font-medium"
                  onClick={() => (window.location.href = "/cookbook")}
                >
                  <BookOpen className="mr-2 h-5 w-5" />
                  Read Cookbook
                </Button>
              </div>

              <div className="grid grid-cols-3 gap-8 pt-8 border-t border-border">
                <div>
                  <div
                    className="text-3xl font-bold"
                    style={{ color: "#f4b9b8" }}
                  >
                    6
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    AI Agents
                  </div>
                </div>
                <div>
                  <div
                    className="text-3xl font-bold"
                    style={{ color: "#f4b9b8" }}
                  >
                    20+
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    MCP Servers
                  </div>
                </div>
                <div>
                  <div
                    className="text-3xl font-bold"
                    style={{ color: "#f4b9b8" }}
                  >
                    178+
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    Tools Available
                  </div>
                </div>
              </div>
            </div>

            {/* Hero Visual - Terminal */}
            <div className="relative hidden lg:block">
              <div className="absolute -inset-1 bg-gradient-to-r from-accent to-secondary rounded-2xl blur opacity-10"></div>
              <div className="relative bg-card rounded-xl overflow-hidden shadow-2xl dark:shadow-[0_25px_50px_-12px_rgb(0_0_0_/_0.5)]">
                <div className="flex items-center px-4 py-3 border-b border-border bg-muted">
                  <div className="flex gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-400"></div>
                    <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
                    <div className="w-3 h-3 rounded-full bg-green-400"></div>
                  </div>
                  <div className="ml-4 text-xs font-medium text-muted-foreground">
                    chef-orchestrator — zsh — 80x24
                  </div>
                </div>
                <div className="p-6 font-medium text-sm space-y-4 bg-gradient-to-b from-card to-muted/50">
                  <div className="flex gap-2">
                    <span className="text-primary">➜</span>
                    <span className="text-secondary">~</span>
                    <span className="text-foreground">chef status --all</span>
                  </div>
                  <div className="space-y-2 text-muted-foreground">
                    <div className="flex justify-between">
                      <span>[Orchestrator]</span>
                      <span className="text-primary">● Online</span>
                    </div>
                    <div className="flex justify-between">
                      <span>[Sous-Chef]</span>
                      <span className="text-primary">● Online</span>
                    </div>
                    <div className="flex justify-between">
                      <span>[Code-Review]</span>
                      <span className="text-primary">● Online</span>
                    </div>
                    <div className="flex justify-between">
                      <span>[Infrastructure]</span>
                      <span className="text-primary">● Online</span>
                    </div>
                  </div>
                  <div className="flex gap-2 pt-4">
                    <span className="text-primary">➜</span>
                    <span className="text-secondary">~</span>
                    <span className="text-foreground animate-pulse">_</span>
                  </div>
                </div>
              </div>

              {/* Floating Status Card */}
              <Card className="absolute -bottom-6 -left-6 w-64 bg-card shadow-medium dark:shadow-medium-dark">
                <CardHeader className="p-4 pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Activity className="h-4 w-4 text-primary" />
                    System Load
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  <div className="text-2xl font-bold">24%</div>
                  <div className="text-xs text-muted-foreground">
                    Optimal performance
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-24 bg-background relative">
        <div className="container">
          <div className="flex flex-col mb-16 space-y-4">
            <h2 className="text-4xl md:text-5xl font-bold tracking-tight">
              What's Cookin'?
            </h2>
            <p className="text-muted-foreground max-w-[700px]">
              A complete menu of DevOps automation tools, served hot and ready
              for production.
            </p>
          </div>

          {/* Scrollytelling Rails */}
          <div className="space-y-20">
            {capabilityRails.map((rail, idx) => {
              const alignRight = idx % 2 === 1;
              const Icon = rail.Icon;
              const accentTone =
                rail.accent === "primary"
                  ? "from-primary/10 to-primary/5"
                  : rail.accent === "secondary"
                  ? "from-secondary/10 to-secondary/5"
                  : "from-accent/10 to-accent/5";
              const accentIcon =
                rail.accent === "primary"
                  ? "text-primary bg-primary/10 border-primary/20"
                  : rail.accent === "secondary"
                  ? "text-secondary bg-secondary/10 border-secondary/20"
                  : "text-accent bg-accent/10 border-accent/20";

              return (
                <div
                  key={rail.id}
                  className="grid lg:grid-cols-12 gap-8 items-center"
                >
                  <div
                    className={
                      "lg:col-span-5 space-y-5 " +
                      (alignRight ? "lg:order-2" : "")
                    }
                  >
                    <h3 className="text-3xl md:text-4xl font-bold tracking-tight leading-tight">
                      {rail.title}
                    </h3>
                    <p className="text-muted-foreground leading-relaxed">
                      {rail.description}
                    </p>
                  </div>

                  <div
                    className={
                      "lg:col-span-7 " + (alignRight ? "lg:order-1" : "")
                    }
                  >
                    <div className="relative">
                      <div
                        className={
                          "absolute -inset-1 bg-gradient-to-r from-accent to-secondary rounded-2xl blur opacity-10"
                        }
                      />
                      <div
                        className={
                          "relative rounded-xl border border-border bg-gradient-to-br " +
                          accentTone +
                          " shadow-medium dark:shadow-medium-dark overflow-hidden"
                        }
                      >
                        <div className="p-8">
                          <div className="flex items-start justify-between gap-6">
                            <div className="space-y-2">
                              <div className="text-sm text-muted-foreground">
                                Kitchen Note
                              </div>
                              <div className="text-lg font-semibold leading-snug">
                                {rail.id === "multi-agent" && (
                                  <>
                                    Route tasks like a head chef—fast, calm, and
                                    consistent.
                                  </>
                                )}
                                {rail.id === "mcp-tools" && (
                                  <>
                                    Tools appear only when needed. Less noise.
                                    More signal.
                                  </>
                                )}
                                {rail.id === "rag" && (
                                  <>
                                    Find the right pattern, instantly—without
                                    losing context.
                                  </>
                                )}
                                {rail.id === "observability" && (
                                  <>
                                    Every call traceable. Every workflow
                                    durable.
                                  </>
                                )}
                                {rail.id === "hitl" && (
                                  <>
                                    Let humans sign off where it matters.
                                    Automate the rest.
                                  </>
                                )}
                                {rail.id === "cloud" && (
                                  <>
                                    Ship it with confidence: health checks,
                                    HTTPS, and clean deploys.
                                  </>
                                )}
                                {rail.id === "modelops" && (
                                  <>
                                    Teach the kitchen your recipes—then deploy
                                    the new taste.
                                  </>
                                )}
                              </div>
                            </div>
                            <div
                              className={
                                "shrink-0 w-12 h-12 rounded-lg border flex items-center justify-center " +
                                accentIcon +
                                " cc-float"
                              }
                            >
                              <Icon className="h-6 w-6" />
                            </div>
                          </div>

                          {/* Free-form visual area */}
                          <div className="mt-6 rounded-lg border border-border/60 bg-background/40 backdrop-blur-sm overflow-hidden">
                            <div className="px-4 py-3 border-b border-border/60 text-xs text-muted-foreground flex items-center justify-between">
                              <span className="font-medium">chef console</span>
                              <span className="opacity-70">{rail.id}</span>
                            </div>
                            <div className="p-4 space-y-3 text-sm">
                              {rail.id === "multi-agent" && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2">
                                    <span className="text-primary">➜</span>
                                    <span className="text-foreground">
                                      route task
                                    </span>
                                    <span className="text-muted-foreground">
                                      /api/auth
                                    </span>
                                  </div>
                                  <div className="grid grid-cols-3 gap-3">
                                    <div className="rounded-md bg-primary/10 border border-primary/20 p-3">
                                      <div className="text-xs text-muted-foreground">
                                        dispatch
                                      </div>
                                      <div className="font-semibold">
                                        feature-dev
                                      </div>
                                    </div>
                                    <div className="rounded-md bg-secondary/10 border border-secondary/20 p-3">
                                      <div className="text-xs text-muted-foreground">
                                        guardrails
                                      </div>
                                      <div className="font-semibold">
                                        code-review
                                      </div>
                                    </div>
                                    <div className="rounded-md bg-accent/10 border border-accent/20 p-3">
                                      <div className="text-xs text-muted-foreground">
                                        ship
                                      </div>
                                      <div className="font-semibold">cicd</div>
                                    </div>
                                  </div>
                                </div>
                              )}

                              {rail.id === "mcp-tools" && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2">
                                    <span className="text-primary">➜</span>
                                    <span className="text-foreground">
                                      tools
                                    </span>
                                    <span className="text-muted-foreground">
                                      bound at invoke-time
                                    </span>
                                  </div>
                                  <div className="flex flex-wrap gap-2">
                                    {[
                                      "docker",
                                      "github",
                                      "linear",
                                      "git",
                                      "postgres",
                                    ].map((t) => (
                                      <Badge
                                        key={t}
                                        variant="secondary"
                                        className="bg-secondary/10 text-secondary border-none text-xs"
                                      >
                                        {t}
                                      </Badge>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {rail.id === "rag" && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2">
                                    <Search className="h-4 w-4 text-primary" />
                                    <span className="text-muted-foreground">
                                      Search:
                                    </span>
                                    <span className="font-medium">
                                      "retry with exponential backoff"
                                    </span>
                                  </div>
                                  <div className="rounded-md bg-card/60 border border-border p-3 text-xs text-muted-foreground">
                                    Top hits:{" "}
                                    <span className="text-foreground">
                                      workflow_engine.py
                                    </span>
                                    ,{" "}
                                    <span className="text-foreground">
                                      self_healing.py
                                    </span>
                                    ,{" "}
                                    <span className="text-foreground">
                                      DEPLOYMENT.md
                                    </span>
                                  </div>
                                </div>
                              )}

                              {rail.id === "observability" && (
                                <div className="space-y-2">
                                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                                    <span>llm_latency_seconds (p95)</span>
                                    <span className="text-primary">1.8s</span>
                                  </div>
                                  <div className="h-10 rounded-md bg-card/60 border border-border p-2 flex items-end gap-1">
                                    {[3, 6, 4, 8, 5, 7, 6, 9].map((h, i) => (
                                      <div
                                        key={i}
                                        className="flex-1 rounded-sm bg-primary/25"
                                        style={{ height: `${h * 4}px` }}
                                      />
                                    ))}
                                  </div>
                                </div>
                              )}

                              {rail.id === "hitl" && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2">
                                    <ShieldCheck className="h-4 w-4 text-accent" />
                                    <span className="text-muted-foreground">
                                      Pending operation:
                                    </span>
                                    <span className="font-medium">
                                      deploy to production
                                    </span>
                                  </div>
                                  <div className="flex items-center gap-2 text-xs">
                                    <Badge className="bg-secondary/20 text-secondary-foreground border-none">
                                      requires approval
                                    </Badge>
                                    <span className="text-muted-foreground">
                                      via Linear webhook
                                    </span>
                                  </div>
                                </div>
                              )}

                              {rail.id === "cloud" && (
                                <div className="space-y-2">
                                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                                    <span>Droplet</span>
                                    <span className="text-primary">
                                      healthy
                                    </span>
                                  </div>
                                  <div className="rounded-md bg-card/60 border border-border p-3 text-xs text-muted-foreground">
                                    Caddy:{" "}
                                    <span className="text-foreground">
                                      HTTPS
                                    </span>{" "}
                                    · Compose:{" "}
                                    <span className="text-foreground">
                                      up -d
                                    </span>{" "}
                                    · Health:{" "}
                                    <span className="text-foreground">
                                      /health
                                    </span>
                                  </div>
                                </div>
                              )}

                              {rail.id === "modelops" && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2">
                                    <Sparkles className="h-4 w-4 text-secondary" />
                                    <span className="text-muted-foreground">
                                      Pipeline:
                                    </span>
                                    <span className="font-medium">
                                      train → evaluate → deploy
                                    </span>
                                  </div>
                                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                    <span className="px-2 py-1 rounded bg-secondary/10 border border-secondary/20">
                                      demo
                                    </span>
                                    <ArrowRight className="h-3 w-3" />
                                    <span className="px-2 py-1 rounded bg-secondary/10 border border-secondary/20">
                                      production
                                    </span>
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Quick Links Section */}
      <section className="py-24 border-t border-border bg-muted/30">
        <div className="container">
          <div className="flex flex-col items-center text-center mb-12">
            <h2 className="text-4xl font-bold tracking-tight mb-4">
              Quick Links
            </h2>
            <p className="text-muted-foreground">
              Direct access to the kitchen's vital systems.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <a
              href="https://codechef.appsmithery.co/api/health"
              target="_blank"
              rel="noreferrer"
              className="group"
            >
              <Card className="h-full bg-card shadow-soft hover:-translate-y-1 hover:shadow-hover hover:bg-muted/50 dark:shadow-soft-dark dark:hover:shadow-hover-dark transition-all duration-300">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-2xl font-bold">
                    Orchestrator API
                  </CardTitle>
                  <Badge className="bg-primary/20 text-primary hover:bg-primary/30 border-none">
                    Live
                  </Badge>
                </CardHeader>
                <CardContent>
                  <div className="text-lg font-medium text-muted-foreground group-hover:text-foreground transition-colors">
                    :8001
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    Main orchestrator service with health endpoints
                  </p>
                </CardContent>
              </Card>
            </a>

            <a
              href="https://smith.langchain.com"
              target="_blank"
              rel="noreferrer"
              className="group"
            >
              <Card className="h-full bg-card shadow-soft hover:-translate-y-1 hover:shadow-hover hover:bg-muted/50 dark:shadow-soft-dark dark:hover:shadow-hover-dark transition-all duration-300">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-2xl font-bold">Tracing</CardTitle>
                  <Badge className="bg-secondary/20 text-secondary hover:bg-secondary/30 border-none">
                    Connected
                  </Badge>
                </CardHeader>
                <CardContent>
                  <div className="text-lg font-medium text-muted-foreground group-hover:text-foreground transition-colors">
                    LangSmith
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    LLM tracing and debugging dashboard
                  </p>
                </CardContent>
              </Card>
            </a>

            <a
              href="https://appsmithery.grafana.net/a/grafana-lokiexplore-app/explore"
              target="_blank"
              rel="noreferrer"
              className="group"
            >
              <Card className="h-full bg-card shadow-soft hover:-translate-y-1 hover:shadow-hover hover:bg-muted/50 dark:shadow-soft-dark dark:hover:shadow-hover-dark transition-all duration-300">
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-2xl font-bold">
                    Monitoring
                  </CardTitle>
                  <Badge className="bg-primary/20 text-primary hover:bg-primary/30 border-none">
                    Metrics
                  </Badge>
                </CardHeader>
                <CardContent>
                  <div className="text-lg font-medium text-muted-foreground group-hover:text-foreground transition-colors">
                    Grafana Cloud
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">
                    Prometheus metrics and dashboards
                  </p>
                </CardContent>
              </Card>
            </a>
          </div>
        </div>
      </section>
    </Layout>
  );
}
