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
} from "lucide-react";

export default function Home() {
  const capabilityRails = [
    {
      id: "orchestration",
      title: "Smart Task Routing",
      description:
        "Automatically routes work to the right specialist agent. When critical changes arise, humans approve before execution—keeping you in control without slowing you down.",
      Icon: Bot,
      accent: "lavender" as const,
      bullets: [
        "Intelligent agent selection",
        "Seamless handoffs",
        "Human approval for high-risk operations",
      ],
    },
    {
      id: "efficiency",
      title: "Up to 90% Lower Token Costs",
      description:
        "Loads only the tools and context needed for each task. Smart retrieval finds relevant code patterns instantly, drastically reducing token waste.",
      Icon: Sparkles,
      accent: "mint" as const,
      bullets: [
        "Progressive tool loading",
        "Semantic code search",
        "Context-aware retrieval",
      ],
    },
    {
      id: "learning",
      title: "Learns Your Codebase",
      description:
        "Fine-tune models on your code in about an hour. Test improvements automatically, then deploy with confidence—or roll back instantly if needed.",
      Icon: Sparkles,
      accent: "butter" as const,
      bullets: [
        "One-hour training runs",
        "Automatic performance testing",
        "Safe, instant rollback",
      ],
    },
    {
      id: "deployment",
      title: "Production-Ready from Day One",
      description:
        "Runs on secure cloud infrastructure with automatic HTTPS, health monitoring, and zero-downtime deploys. Built for teams that ship.",
      Icon: Cloud,
      accent: "mint" as const,
      bullets: [
        "Secure cloud hosting",
        "Health checks & monitoring",
        "No-downtime updates",
      ],
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
                  <div className="text-3xl font-bold text-emerald-400">6</div>
                  <div className="text-sm text-muted-foreground mt-1">
                    AI Agents
                  </div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-emerald-400">20+</div>
                  <div className="text-sm text-muted-foreground mt-1">
                    MCP Servers
                  </div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-emerald-400">
                    178+
                  </div>
                  <div className="text-sm text-muted-foreground mt-1">
                    Tools Available
                  </div>
                </div>
              </div>
            </div>

            {/* Hero Visual - Screenshot */}
            <div className="relative hidden lg:block">
              <div className="absolute -inset-1 bg-gradient-to-r from-purple-500 to-emerald-400 rounded-2xl blur opacity-10"></div>
              <div className="relative bg-card rounded-xl overflow-hidden shadow-2xl dark:shadow-[0_25px_50px_-12px_rgb(0_0_0_/_0.5)]">
                <img
                  src="/screenshots/hello-chef.png"
                  alt="code/chef Orchestrator interface showing intelligent task routing"
                  className="w-full h-auto"
                />
              </div>

              {/* Floating Status Card */}
              <Card className="absolute -bottom-10 -right-6 w-64 bg-card/25 backdrop-blur-sm shadow-medium dark:shadow-medium-dark border-border/30">
                <CardHeader className="p-4 pb-2">
                  <CardTitle className="text-sm font-medium flex items-center gap-2">
                    <Activity className="h-4 w-4 text-emerald-400" />
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
                rail.accent === "lavender"
                  ? "from-purple-500/10 to-purple-400/5"
                  : rail.accent === "mint"
                  ? "from-emerald-400/10 to-emerald-300/5"
                  : "from-amber-300/10 to-yellow-200/5";
              const accentIcon =
                rail.accent === "lavender"
                  ? "text-purple-400 bg-purple-500/10 border-purple-400/20"
                  : rail.accent === "mint"
                  ? "text-emerald-400 bg-emerald-400/10 border-emerald-400/20"
                  : "text-amber-300 bg-amber-300/10 border-amber-300/20";

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
                                {rail.id === "orchestration" && (
                                  <>
                                    Route tasks like a head chef—fast, calm, and
                                    consistent.
                                  </>
                                )}
                                {rail.id === "efficiency" && (
                                  <>
                                    Tools appear only when needed. Less noise.
                                    More signal.
                                  </>
                                )}
                                {rail.id === "learning" && (
                                  <>
                                    Teach the kitchen your recipes—then deploy
                                    with confidence.
                                  </>
                                )}
                                {rail.id === "deployment" && (
                                  <>
                                    Ship it with confidence: health checks,
                                    HTTPS, and clean deploys.
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
                              {rail.id === "orchestration" && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2">
                                    <span className="text-purple-400">➜</span>
                                    <span className="text-foreground">
                                      route task
                                    </span>
                                    <span className="text-muted-foreground">
                                      /api/auth
                                    </span>
                                  </div>
                                  <div className="grid grid-cols-3 gap-3">
                                    <div className="rounded-md bg-purple-500/10 border border-purple-400/20 p-3">
                                      <div className="text-xs text-muted-foreground">
                                        dispatch
                                      </div>
                                      <div className="font-semibold">
                                        feature-dev
                                      </div>
                                    </div>
                                    <div className="rounded-md bg-emerald-400/10 border border-emerald-400/20 p-3">
                                      <div className="text-xs text-muted-foreground">
                                        guardrails
                                      </div>
                                      <div className="font-semibold">
                                        code-review
                                      </div>
                                    </div>
                                    <div className="rounded-md bg-amber-300/10 border border-amber-300/20 p-3">
                                      <div className="text-xs text-muted-foreground">
                                        ship
                                      </div>
                                      <div className="font-semibold">cicd</div>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-2 mt-3">
                                    <ShieldCheck className="h-4 w-4 text-purple-400" />
                                    <span className="text-xs text-muted-foreground">
                                      High-risk detected: awaiting approval
                                    </span>
                                  </div>
                                </div>
                              )}

                              {rail.id === "efficiency" && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2">
                                    <span className="text-emerald-400">➜</span>
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
                                        className="bg-emerald-400/10 text-emerald-400 border-none text-xs"
                                      >
                                        {t}
                                      </Badge>
                                    ))}
                                  </div>
                                  <div className="flex items-center gap-2 mt-3">
                                    <Search className="h-4 w-4 text-emerald-400" />
                                    <span className="text-xs text-muted-foreground">
                                      Token savings:{" "}
                                      <span className="text-emerald-400 font-semibold">
                                        87%
                                      </span>
                                    </span>
                                  </div>
                                </div>
                              )}

                              {rail.id === "learning" && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2">
                                    <Sparkles className="h-4 w-4 text-amber-300" />
                                    <span className="text-muted-foreground">
                                      Pipeline:
                                    </span>
                                    <span className="font-medium">
                                      train → evaluate → deploy
                                    </span>
                                  </div>
                                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                    <span className="px-2 py-1 rounded bg-amber-300/10 border border-amber-300/20">
                                      demo
                                    </span>
                                    <ArrowRight className="h-3 w-3" />
                                    <span className="px-2 py-1 rounded bg-amber-300/10 border border-amber-300/20">
                                      production
                                    </span>
                                  </div>
                                  <div className="text-xs text-muted-foreground mt-2">
                                    Improvement:{" "}
                                    <span className="text-amber-300 font-semibold">
                                      +18%
                                    </span>{" "}
                                    accuracy
                                  </div>
                                </div>
                              )}

                              {rail.id === "deployment" && (
                                <div className="space-y-2">
                                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                                    <span>Droplet</span>
                                    <span className="text-emerald-400">
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
