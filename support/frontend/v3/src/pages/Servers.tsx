import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import Layout from "@/components/Layout";
import { mcpServers, totalTools } from "@/data/platform";
import { Package, Cloud, GitBranch, Database, FileText, Settings } from "lucide-react";

const categoryIcons: Record<string, React.ReactNode> = {
  containers: <Package className="h-6 w-6" />,
  vcs: <GitBranch className="h-6 w-6" />,
  project: <Settings className="h-6 w-6" />,
  storage: <Database className="h-6 w-6" />,
  cloud: <Cloud className="h-6 w-6" />,
  documentation: <FileText className="h-6 w-6" />,
};

const categoryColors: Record<string, string> = {
  containers: "bg-blue-500/10 text-blue-500",
  vcs: "bg-green-500/10 text-green-500",
  project: "bg-purple-500/10 text-purple-500",
  storage: "bg-orange-500/10 text-orange-500",
  cloud: "bg-cyan-500/10 text-cyan-500",
  documentation: "bg-pink-500/10 text-pink-500",
};

export default function Servers() {
  return (
    <Layout>
      {/* Hero Section */}
      <section className="py-20 md:py-32 bg-gradient-to-br from-background via-background to-muted">
        <div className="container">
          <div className="max-w-3xl mx-auto text-center space-y-6">
            <Badge variant="outline" className="border-accent/30 text-accent bg-accent/5">
              Model Context Protocol
            </Badge>
            <h1 className="text-5xl md:text-6xl font-bold tracking-tight">
              MCP <span className="text-accent">Servers</span>
            </h1>
            <p className="text-xl text-muted-foreground leading-relaxed">
              {totalTools}+ tools across {mcpServers.length} MCP servers. Progressive loading keeps costs down while maintaining full capability when needed.
            </p>
          </div>
        </div>
      </section>

      {/* Servers Grid */}
      <section className="py-24 bg-background">
        <div className="container">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {mcpServers.map((server) => (
              <Card
                key={server.id}
                className="bg-card border-border hover:border-accent/50 transition-all duration-300 group"
              >
                <CardHeader>
                  <div className="flex items-start justify-between mb-4">
                    <div className={`w-12 h-12 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform duration-300 ${
                      categoryColors[server.category] || "bg-accent/10 text-accent"
                    }`}>
                      {categoryIcons[server.category] || <Settings className="h-6 w-6" />}
                    </div>
                    <Badge
                      variant={server.status === "active" ? "default" : "secondary"}
                      className={server.status === "active" ? "bg-primary/20 text-primary hover:bg-primary/30 border-none" : ""}
                    >
                      {server.status}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 mb-2">
                    <CardTitle className="text-xl">{server.name}</CardTitle>
                  </div>
                  <CardDescription className="text-base">
                    {server.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                    <span className="text-sm text-muted-foreground">Available Tools</span>
                    <span className="text-2xl font-bold text-accent">{server.toolCount}</span>
                  </div>
                  <div className="pt-2">
                    <Badge
                      variant="outline"
                      className="border-border/50 text-muted-foreground bg-background hover:bg-background capitalize"
                    >
                      {server.category}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Progressive Loading Section */}
      <section className="py-24 border-t border-border bg-muted/30">
        <div className="container">
          <div className="max-w-4xl mx-auto">
            <h2 className="text-4xl font-bold tracking-tight mb-8 text-center">
              Progressive Tool Loading
            </h2>
            <div className="space-y-6 text-muted-foreground leading-relaxed">
              <p>
                Instead of loading all {totalTools}+ tools for every request, agents use a <span className="text-accent font-medium">three-tier strategy</span> that balances capability with token efficiency:
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 my-8">
                <Card className="bg-card border-accent/20">
                  <CardHeader>
                    <CardTitle className="text-lg text-accent">Minimal</CardTitle>
                    <CardDescription>10-30 tools</CardDescription>
                  </CardHeader>
                  <CardContent className="text-sm">
                    Core tools matched by keywords. Used for simple, well-defined tasks.
                  </CardContent>
                </Card>
                <Card className="bg-card border-accent/20">
                  <CardHeader>
                    <CardTitle className="text-lg text-accent">Progressive</CardTitle>
                    <CardDescription>30-60 tools</CardDescription>
                  </CardHeader>
                  <CardContent className="text-sm">
                    Agent-priority tools plus keyword matches. Balances cost and capability.
                  </CardContent>
                </Card>
                <Card className="bg-card border-accent/20">
                  <CardHeader>
                    <CardTitle className="text-lg text-accent">Full</CardTitle>
                    <CardDescription>150+ tools</CardDescription>
                  </CardHeader>
                  <CardContent className="text-sm">
                    All available tools. Reserved for complex debugging and discovery.
                  </CardContent>
                </Card>
              </div>
              <p>
                This approach reduces token costs by <span className="text-accent font-medium">80-90%</span> on typical workflows while maintaining full access when agents need it. Tools are bound at invoke-time, not initialization, allowing dynamic strategy selection per request.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Integration Section */}
      <section className="py-24 border-t border-border">
        <div className="container">
          <div className="max-w-4xl mx-auto text-center space-y-6">
            <h2 className="text-4xl font-bold tracking-tight">
              Seamless Integration
            </h2>
            <p className="text-xl text-muted-foreground leading-relaxed">
              All MCP servers are configured via <code className="px-2 py-1 rounded bg-muted text-accent font-mono text-sm">config/mcp-agent-tool-mapping.yaml</code> with environment-based authentication. Agents automatically discover available tools through the ProgressiveMCPLoader without manual configuration changes.
            </p>
          </div>
        </div>
      </section>
    </Layout>
  );
}
