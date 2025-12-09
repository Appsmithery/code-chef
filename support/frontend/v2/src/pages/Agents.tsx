import { Layout } from "@/components/Layout";
import { AgentCard } from "@/components/AgentCard";
import { agents, agentStats } from "@/data/agents";
import { Bot, Cpu, Wrench } from "lucide-react";

export default function Agents() {
  return (
    <Layout>
      {/* Hero Section */}
      <section className="relative overflow-hidden py-16 md:py-24 bg-gradient-to-br from-background via-background to-muted">
        <div className="absolute top-0 right-0 w-72 h-72 bg-accent/5 rounded-full blur-3xl pointer-events-none -mr-36 -mt-36" />
        <div className="absolute bottom-0 left-0 w-72 h-72 bg-primary/5 rounded-full blur-3xl pointer-events-none -ml-36 -mb-36" />
        
        <div className="container relative z-10 text-center space-y-6">
          <div className="flex justify-center">
            <img 
              src="/logos/knives_icon_transparent.svg" 
              alt="Le Brigade" 
              className="h-20 w-auto opacity-80"
            />
          </div>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold">
            <em>Le Brigade</em>
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            6 specialized AI agents powered by Gradient AI with LangSmith tracing
          </p>
          
          {/* Stats */}
          <div className="flex justify-center gap-8 md:gap-16 pt-6">
            <div className="text-center">
              <div className="flex items-center justify-center gap-2">
                <Bot className="h-5 w-5 text-accent" />
                <span className="text-3xl md:text-4xl font-bold text-accent">{agentStats.totalAgents}</span>
              </div>
              <span className="text-sm text-muted-foreground">Agents</span>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-2">
                <Cpu className="h-5 w-5 text-accent" />
                <span className="text-3xl md:text-4xl font-bold text-accent">{agentStats.totalModels}</span>
              </div>
              <span className="text-sm text-muted-foreground">LLM Models</span>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-2">
                <Wrench className="h-5 w-5 text-accent" />
                <span className="text-3xl md:text-4xl font-bold text-accent">{agentStats.totalTools}+</span>
              </div>
              <span className="text-sm text-muted-foreground">Tools</span>
            </div>
          </div>
        </div>
      </section>

      {/* Info Box */}
      <section className="container py-6">
        <div className="rounded-lg border border-primary/30 bg-primary/5 p-4 text-sm">
          <strong className="text-accent">Architecture:</strong>{" "}
          <span className="text-muted-foreground">
            Each agent is a specialized node in the LangGraph workflow with dedicated LLM models, 
            MCP tool access, RAG context, and comprehensive observability via LangSmith + Prometheus.
          </span>
        </div>
      </section>

      {/* Agent Grid */}
      <section className="container pb-16">
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <AgentCard 
              key={agent.id} 
              agent={agent} 
              variant={agent.id === 'head-chef' ? 'featured' : 'default'}
            />
          ))}
        </div>
      </section>

      {/* Observability Info */}
      <section className="container pb-16">
        <div className="rounded-lg border border-accent/30 bg-accent/5 p-4 text-sm">
          <strong className="text-accent">📊 Observability:</strong>{" "}
          <span className="text-muted-foreground">
            All agents automatically trace to{" "}
            <a 
              href="https://smith.langchain.com/o/5029c640-3f73-480c-82f3-58e402ed4207/" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-accent hover:underline"
            >
              LangSmith
            </a>{" "}
            for debugging and performance analysis. Metrics are available in{" "}
            <a 
              href="https://appsmithery.grafana.net" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-accent hover:underline"
            >
              Grafana Cloud
            </a>.
          </span>
        </div>
      </section>
    </Layout>
  );
}
