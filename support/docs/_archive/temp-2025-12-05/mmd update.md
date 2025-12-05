# **Layered Architecture** diagram

Instead of connecting every agent to every service (which creates a "spiderweb" of 20+ arrows), we can introduce an **"Agent Runtime"** node. This accurately reflects your code structure where `BaseAgent` handles the complexity of connecting to MCP, RAG, State, and LLM services, keeping the individual agent logic focused on their specific domains.

Here is the updated Mermaid code for the **System Overview** tab in `agents.html`.

### Recommended Changes

1.  **Grouped Layers**: Explicitly group "The Kitchen Team" and "Foundation Stack".
2.  **Agent Runtime Node**: Acts as a bus to connect agents to infrastructure, reducing 20 arrows to just 9.
3.  **Horizontal Layouts**: Use `direction LR` within subgraphs to create neat rows.
4.  **Thicker Paths**: Use `==>` for the critical control flow (User → Orchestrator → Agents).

### Code Block

Replace the content inside the `<div class="diagram-content active" id="simplified-arch">` container with this:

```html
<div class="diagram-content active" id="simplified-arch">
  <pre class="mermaid">
%%{init: { 'theme': 'base', 'themeVariables': { 'primaryColor': '#887bb0', 'primaryTextColor': '#fff', 'primaryBorderColor': '#bcece0', 'lineColor': '#4c5270', 'secondaryColor': '#2a2e3f', 'tertiaryColor': '#fff9c4' } }}%%
graph TB
    %% Nodes
    User[("👤 User")]
    Orchestrator{"🎯 Head Chef<br/><small>Orchestrator</small>"}

    subgraph Agents ["The Kitchen Team"]
        direction LR
        FeatureDev[["💻 Sous-Chef"]]
        CodeReview[["🔍 Code Review"]]
        Infra[["☁️ Infra"]]
        CICD[["🚀 CI/CD"]]
        Docs[["📝 Docs"]]
    end

    subgraph Foundation ["Foundation Stack"]
        direction LR
        Runtime{{"⚡ Agent Runtime"}}
        MCP[("🔌 MCP Tools")]
        RAG[("📚 RAG")]
        State[("💾 State")]
        LLM[("⚡ Gradient")]

        Runtime -.-> MCP & RAG & State & LLM
    end

    %% Connections
    User ==> Orchestrator
    Orchestrator ==> FeatureDev & CodeReview & Infra & CICD & Docs
    FeatureDev & CodeReview & Infra & CICD & Docs -.-> Runtime

    %% Styling
    classDef user fill:#bcece0,stroke:#887bb0,stroke-width:2px,color:#4c5270
    classDef orchestrator fill:#887bb0,stroke:#bcece0,stroke-width:3px,color:#fff
    classDef agent fill:#f4b9b8,stroke:#4c5270,stroke-width:2px,color:#4c5270
    classDef foundation fill:#2a2e3f,stroke:#bcece0,stroke-width:2px,color:#bcece0
    classDef runtime fill:#4c5270,stroke:#fff,stroke-width:2px,color:#fff,stroke-dasharray: 5<!-- filepath: support/frontend/agents.html -->
<div class="diagram-content active" id="simplified-arch">
  <pre class="mermaid">
%%{init: { 'theme': 'base', 'themeVariables': { 'primaryColor': '#887bb0', 'primaryTextColor': '#fff', 'primaryBorderColor': '#bcece0', 'lineColor': '#4c5270', 'secondaryColor': '#2a2e3f', 'tertiaryColor': '#fff9c4' } }}%%
graph TB
    %% Nodes
    User[("👤 User")]
    Orchestrator{"🎯 Head Chef<br/><small>Orchestrator</small>"}

    subgraph Agents ["The Kitchen Team"]
        direction LR
        FeatureDev[["💻 Sous-Chef"]]
        CodeReview[["🔍 Code Review"]]
        Infra[["☁️ Infra"]]
        CICD[["🚀 CI/CD"]]
        Docs[["📝 Docs"]]
    end

    subgraph Foundation ["Foundation Stack"]
        direction LR
        Runtime{{"⚡ Agent Runtime"}}
        MCP[("🔌 MCP Tools")]
        RAG[("📚 RAG")]
        State[("💾 State")]
        LLM[("⚡ Gradient")]

        Runtime -.-> MCP & RAG & State & LLM
    end

    %% Connections
    User ==> Orchestrator
    Orchestrator ==> FeatureDev & CodeReview & Infra & CICD & Docs
    FeatureDev & CodeReview & Infra & CICD & Docs -.-> Runtime

    %% Styling
    classDef user fill:#bcece0,stroke:#887bb0,stroke-width:2px,color:#4c5270
    classDef orchestrator fill:#887bb0,stroke:#bcece0,stroke-width:3px,color:#fff
    classDef agent fill:#f4b9b8,stroke:#4c5270,stroke-width:2px,color:#4c5270
    classDef foundation fill:#2a2e3f,stroke:#bcece0,stroke-width:2px,color:#bcece0
    classDef runtime fill:#4c5270,stroke:#fff,stroke-width:2px,color:#fff,stroke-dasharray: 5 5

    class User user
    class Orchestrator orchestrator
    class FeatureDev,CodeReview,Infra,CICD,Docs agent
    class MCP,RAG,State,LLM foundation
    class Runtime runtime
  </pre>
</div>
```
