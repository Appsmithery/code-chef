import { Layout } from "@/components/Layout";
import { ServerCard } from "@/components/ServerCard";
import { serverCategories, serverStats } from "@/data/servers";
import { Server, Wrench, Zap } from "lucide-react";

export default function Servers() {
  return (
    <Layout>
      {/* Hero Section */}
      <section className="relative overflow-hidden py-16 md:py-24 bg-gradient-to-br from-background via-background to-muted">
        <div className="absolute top-0 right-0 w-72 h-72 bg-accent/5 rounded-full blur-3xl pointer-events-none -mr-36 -mt-36" />
        <div className="absolute bottom-0 left-0 w-72 h-72 bg-primary/5 rounded-full blur-3xl pointer-events-none -ml-36 -mb-36" />
        
        <div className="container relative z-10 text-center space-y-6">
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold">
            🔌 MCP Servers
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Docker MCP Toolkit — Model Context Protocol integration for AI agents
          </p>
          
          {/* Stats */}
          <div className="flex justify-center gap-8 md:gap-16 pt-6">
            <div className="text-center">
              <div className="flex items-center justify-center gap-2">
                <Server className="h-5 w-5 text-accent" />
                <span className="text-3xl md:text-4xl font-bold text-accent">{serverStats.totalServers}</span>
              </div>
              <span className="text-sm text-muted-foreground">Servers</span>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-2">
                <Wrench className="h-5 w-5 text-accent" />
                <span className="text-3xl md:text-4xl font-bold text-accent">{serverStats.totalTools}+</span>
              </div>
              <span className="text-sm text-muted-foreground">Tools</span>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-2">
                <Zap className="h-5 w-5 text-accent" />
                <span className="text-3xl md:text-4xl font-bold text-accent">{serverStats.tokenSavings}</span>
              </div>
              <span className="text-sm text-muted-foreground">Token Savings</span>
            </div>
          </div>
        </div>
      </section>

      {/* Info Box */}
      <section className="container py-6">
        <div className="rounded-lg border border-primary/30 bg-primary/5 p-4 text-sm">
          <strong className="text-accent">Progressive Disclosure:</strong>{" "}
          <span className="text-muted-foreground">
            Tools load on-demand based on task context, saving 80-90% on tokens. 
            The Head Chef selects relevant tools per delegation.
          </span>
        </div>
      </section>

      {/* Server Categories */}
      <section className="container pb-16 space-y-12">
        {serverCategories.map((category) => (
          <div key={category.id} className="space-y-6">
            <h2 className="text-2xl font-bold border-b-2 border-primary pb-2">
              {category.icon} {category.name}
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {category.servers.map((server) => (
                <ServerCard key={server.id} server={server} />
              ))}
            </div>
          </div>
        ))}
      </section>
    </Layout>
  );
}
