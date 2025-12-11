import Layout from "@/components/Layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Activity,
  ArrowRight,
  BookOpen,
  Bot,
  Cloud,
  Search,
  ShieldCheck,
  Sparkles,
  Terminal,
  Wrench,
} from "lucide-react";

export default function Home() {
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
              <div className="relative bg-card border border-border rounded-xl overflow-hidden shadow-lg">
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
              <Card className="absolute -bottom-6 -left-6 w-64 bg-card border-border shadow-lg">
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
          <div className="flex flex-col items-center text-center mb-16 space-y-4">
            <Badge
              variant="outline"
              className="border-accent/30 text-accent bg-accent/5"
            >
              Capabilities
            </Badge>
            <h2 className="text-4xl md:text-5xl font-bold tracking-tight">
              What's Cookin'?
            </h2>
            <p className="text-muted-foreground max-w-[700px]">
              A complete menu of DevOps automation tools, served hot and ready
              for production.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[minmax(200px,auto)]">
            {/* Large Feature */}
            <Card className="md:col-span-2 bg-card border-border hover:border-accent/50 transition-all duration-300 group">
              <CardHeader>
                <div className="mb-2 w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center text-accent group-hover:scale-110 transition-transform duration-300">
                  <Bot className="h-6 w-6" />
                </div>
                <CardTitle className="text-xl">
                  Multi-Agent Orchestration
                </CardTitle>
                <CardDescription className="text-base">
                  LangGraph StateGraph workflow with intelligent task routing.
                  The Head Chef (Orchestrator) coordinates specialized agents
                  for optimal results.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-32 w-full bg-gradient-to-br from-accent/5 to-primary/5 rounded-lg border border-border relative overflow-hidden">
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="flex gap-8">
                      <div className="w-12 h-12 rounded-full bg-accent/20 flex items-center justify-center border border-accent/30">
                        <Bot className="h-6 w-6 text-accent" />
                      </div>
                      <div className="flex items-center text-muted-foreground">
                        <ArrowRight className="h-4 w-4 animate-pulse" />
                      </div>
                      <div className="w-12 h-12 rounded-full bg-secondary/20 flex items-center justify-center border border-secondary/30">
                        <Terminal className="h-6 w-6 text-secondary" />
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Standard Feature */}
            <Card className="bg-card border-border hover:border-accent/50 transition-all duration-300 group">
              <CardHeader>
                <div className="mb-2 w-10 h-10 rounded-lg bg-secondary/10 flex items-center justify-center text-secondary group-hover:scale-110 transition-transform duration-300">
                  <Wrench className="h-6 w-6" />
                </div>
                <CardTitle className="text-lg">MCP Tool Integration</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  Docker MCP Toolkit with 20 servers and 178+ tools. Progressive
                  disclosure saves 80-90% on token costs.
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Secondary Features - Evenly Spaced */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mt-6">
            {/* RAG Semantic Search */}
            <Card className="bg-card border-border hover:border-accent/50 transition-all duration-300 group">
              <CardHeader>
                <div className="mb-2 w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary group-hover:scale-110 transition-transform duration-300">
                  <Search className="h-6 w-6" />
                </div>
                <CardTitle className="text-lg">RAG Semantic Search</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-sm leading-relaxed mb-3">
                  Qdrant Cloud with 1,200+ vectors across code patterns, Linear
                  issues, and documentation for contextual assistance.
                </p>
                <div className="flex gap-2 flex-wrap">
                  <Badge
                    variant="secondary"
                    className="bg-secondary/10 text-secondary hover:bg-secondary/20 border-none text-xs"
                  >
                    Code Patterns
                  </Badge>
                  <Badge
                    variant="secondary"
                    className="bg-secondary/10 text-secondary hover:bg-secondary/20 border-none text-xs"
                  >
                    Linear Issues
                  </Badge>
                  <Badge
                    variant="secondary"
                    className="bg-secondary/10 text-secondary hover:bg-secondary/20 border-none text-xs"
                  >
                    Documentation
                  </Badge>
                </div>
              </CardContent>
            </Card>

            {/* Full Observability */}
            <Card className="bg-card border-border hover:border-accent/50 transition-all duration-300 group">
              <CardHeader>
                <div className="mb-2 w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary group-hover:scale-110 transition-transform duration-300">
                  <Activity className="h-6 w-6" />
                </div>
                <CardTitle className="text-lg">Full Observability</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  LangSmith tracing for LLM calls, Grafana Cloud for metrics,
                  and PostgreSQL checkpointing for durable workflows.
                </p>
              </CardContent>
            </Card>

            {/* Human-in-the-Loop */}
            <Card className="bg-card border-border hover:border-accent/50 transition-all duration-300 group">
              <CardHeader>
                <div className="mb-2 w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary group-hover:scale-110 transition-transform duration-300">
                  <ShieldCheck className="h-6 w-6" />
                </div>
                <CardTitle className="text-lg">Human-in-the-Loop</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  Risk-based approval workflows via Linear integration. Critical
                  changes require human sign-off.
                </p>
              </CardContent>
            </Card>

            {/* Cloud-Native Agents */}
            <Card className="bg-card border-border hover:border-accent/50 transition-all duration-300 group">
              <CardHeader>
                <div className="mb-2 w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center text-accent group-hover:scale-110 transition-transform duration-300">
                  <Cloud className="h-6 w-6" />
                </div>
                <CardTitle className="text-lg">Cloud-Native Agents</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-sm leading-relaxed">
                  Running on DigitalOcean with Caddy reverse proxy, automatic
                  HTTPS, and optimized for 2GB memory footprint.
                </p>
              </CardContent>
            </Card>
          </div>

          {/* ModelOps Feature */}
          <div className="mt-6">
            <Card className="bg-gradient-to-br from-secondary/10 to-accent/10 border-secondary hover:border-secondary transition-all duration-300 group">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="mb-2 w-10 h-10 rounded-lg bg-secondary/20 flex items-center justify-center text-secondary group-hover:scale-110 transition-transform duration-300">
                      <Sparkles className="h-6 w-6" />
                    </div>
                    <CardTitle className="text-2xl mb-2">
                      Train Your Own AI
                    </CardTitle>
                    <CardDescription className="text-base">
                      Want code/chef to write code exactly how your team likes
                      it? Teach it your style.
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <p className="text-muted-foreground leading-relaxed">
                    ModelOps makes it easy to fine-tune AI models on your
                    codebase—no machine learning expertise required. Train in
                    about an hour, test the results, and deploy with one click.
                    The AI learns your coding patterns, naming conventions, and
                    project structure.
                  </p>
                  <div className="flex flex-wrap gap-2">
                    <Badge
                      variant="secondary"
                      className="bg-secondary/20 text-secondary-foreground border-secondary/30"
                    >
                      One-Hour Training
                    </Badge>
                    <Badge
                      variant="secondary"
                      className="bg-secondary/20 text-secondary-foreground border-secondary/30"
                    >
                      Automatic Testing
                    </Badge>
                    <Badge
                      variant="secondary"
                      className="bg-secondary/20 text-secondary-foreground border-secondary/30"
                    >
                      Safe Rollback
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
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
              <Card className="h-full bg-card border-border hover:border-accent transition-all duration-300 hover:shadow-md">
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
              <Card className="h-full bg-card border-border hover:border-secondary transition-all duration-300 hover:shadow-md">
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
              <Card className="h-full bg-card border-border hover:border-primary transition-all duration-300 hover:shadow-md">
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
