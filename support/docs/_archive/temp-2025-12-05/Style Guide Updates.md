# Recommended Updates to the Style Guide

### 1. **Missing Image Assets**

The style guide references images that don't exist in frontend:

- `codechef-13.jpg`, `codechef-18.jpg` (chef hat logos)
- `hat.icon.mint.jpg`, `hat.icon.jpg` (agent role icons)

**Recommendation:** Add a section documenting where to source/create these assets, or update references to use the existing icon at hat_icon.jpg.

### 2. **Update MCP Servers Count**

The style guide doesn't mention MCP stats, but the current pages show "10+ servers" and "150+ tools" with outdated port `8000`. Per copilot-instructions.md:

- Update to: **20 MCP servers, 178+ tools** (Docker MCP Toolkit)
- Gateway port is no longer `8000` - services are on ports 8001, 8007, 8008, 8010

### 3. **Tracing Reference Error in agents.html**

The subtitle says "Langfuse tracing" but Langfuse has been **deprecated** (per copilot-instructions). Update to "LangSmith tracing".

### 4. **Add Supervisor Agent**

The current pages show 6 agents, but the style guide's "Le Brigade" only maps 6 roles. Per the architecture, there's also a **Supervisor** agent. Add:

- **Expeditor: gray-blue, Supervisor** (coordinates between Chef and line cooks)

### 5. **Production Domain Updates**

The docs-overview page still references `theshop.appsmithery.co` but production is now `codechef.appsmithery.co`.

### 6. **Add Shared CSS File Recommendation**

Instead of inline styles in each HTML file, recommend creating a shared `styles.css` to avoid duplication:

```css
:root {
  --gray-blue: #4c5270;
  --mint: #bcece0;
  --light-yellow: #fff4bd;
  --salmon: #f4b9b8;
  --lavender: #887bb0;
  --bg: var(--light-yellow);
  --card-bg: #ffffff;
  --text: var(--gray-blue);
  --accent: var(--mint);
}
/* ... rest of shared styles */
```

### 7. **Add Nav Link Structure**

The style guide nav omits production-landing.html. Recommend consistent nav across all pages:

```html
<nav>
  <a href="index.html">Home</a>
  <a href="agents.html">Le Brigade</a>
  <a href="servers.html">Servers</a>
  <a href="docs-overview-new.html">Cookbook</a>
  <button id="themeToggle">🌑/🌕</button>
</nav>
```

### 8. **Complete Role-to-Agent Mapping**

Update the brigade mapping to match actual agents in agents:

| Kitchen Role | Agent          | Color        | Description                             |
| ------------ | -------------- | ------------ | --------------------------------------- |
| Chef         | Orchestrator   | mint         | Task routing, workflow orchestration    |
| Sous-Chef    | Feature-Dev    | lavender     | Feature implementation, code generation |
| Saucier      | Infrastructure | salmon       | IaC, Docker, Kubernetes                 |
| Garde Manger | Code-Review    | gray-blue    | Security, quality analysis              |
| Entremetier  | CI/CD          | light-yellow | Pipeline automation                     |
| Pâtissier    | Documentation  | mint         | Technical writing                       |
| Expeditor    | Supervisor     | lavender     | Agent coordination                      |

### 9. **Add Grafana Dashboard Link**

Replace the deprecated Prometheus localhost link with Grafana Cloud:

```html
<a href="https://appsmithery.grafana.net" target="_blank" class="btn"
  >📊 Grafana</a
>
```

---

## Priority Implementation Order

1. **Create image assets** (blocking for chef hat branding)
2. **Create shared `styles.css`** with CSS variables
3. **Update agents.html** first (most visible, has Langfuse error)
4. **Update index.html / production-landing.html**
5. **Update servers.html** (convert to recipe card format)
6. **Update docs-overview-new.html** (fix domain references)
