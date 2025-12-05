# **Global CSS Variables for Brand Palette (Light \& Dark Modes)**

Insert near the top of your CSS or `<style>` section in all files:

```css
:root {
  /* Light mode */
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

[data-theme="dark"] {
  /* Dark mode overrides */
  --bg: var(--gray-blue);
  --card-bg: #2a2e3f;
  --text: var(--mint);
  --accent: var(--salmon);
}
```

**Add a dark mode toggle** in your site header footer:

```html
<button onclick="document.body.dataset.theme = (document.body.dataset.theme === 'dark' ? '' : 'dark')">🌙/☀️</button>
```


***

# **Header Layout \& Branding**

Add chef hat logo and use brand wordmark:

```html
<div class="header">
  <img src="codechef-18.jpg" alt="Code/chef logo" style="height: 40px; margin-right: 12px;" />
  <h1 style="color:var(--gray-blue); font-size:2.5rem;">
    <span style="font-weight:700;">code/chef</span>
  </h1>
  <nav>
    <a href="index.html">Home</a>
    <a href="agents.html">Le Brigade</a>
    <a href="servers.html">Servers</a>
    <a href="docs-overview-new.html">Cookbook</a>
    <button id="themeToggle">🌑/🌕</button>
  </nav>
</div>
```

*Make sure nav links inherit `--text` color.*

***

# **Hero Section Example (production-landing.html, index.html)**

```html
<section class="hero" style="background: var(--bg); border-radius:12px; padding:3rem; box-shadow: 0 20px 60px #4c527033;">
  <div style="display:flex; gap:2rem; align-items:center;">
    <img src="codechef-13.jpg" alt="Chef hat" style="height:60px;"/>
    <div>
      <h1 style="color:var(--gray-blue);font-size:3rem;font-weight:bold;margin-bottom:1rem;">code/chef</h1>
      <p style="color:var(--lavender);font-size:1.1rem;">AI-Powered DevOps Tools for the Modern Kitchen</p>
      <div class="cta-group">
        <a class="btn" href="agents.html" style="background:var(--salmon);color:var(--text)">View Agents</a>
        <a class="btn" href="docs-overview-new.html" style="background:var(--mint);color:var(--text)">Docs</a>
      </div>
    </div>
  </div>
</section>
```


***

# **Agent Grid (Le Brigade) - agents.html**

Use chef brigade and kitchen roles:

```html
<div class="agent-grid">
  <div class="agent-card chef" style="border-left:8px solid var(--mint);background:var(--card-bg);">
    <img src="hat.icon.mint.jpg" alt="Chef hat" style="height:32px;"/>
    <h2>Orchestrator <span class="role">Chef</span></h2>
    <p>Task routing, agent selection, workflow orchestration</p>
  </div>
  <div class="agent-card sous-chef" style="border-left:8px solid var(--lavender);background:var(--card-bg)">
    <img src="hat.icon.jpg" alt="Sous hat" style="height:32px;"/>
    <h2>Feature-Dev <span class="role">Sous-Chef</span></h2>
    <p>Feature implementation, code generation, testing</p>
  </div>
  <!-- Repeat for Saucier, Hands, Bus-Boy, Recipe-Writer -->
</div>
```

Role-to-agent mapping and colors:

- Chef: mint, Orchestrator
- Sous-Chef: lavender, Feature-Dev
- Saucier: salmon, Infrastructure
- Hands: gray-blue, Code-Review
- Bus-Boy: light-yellow, CICD
- Recipe-Writer: mint, Documentation

***

# **Cards, Containers, Info Boxes — Shared Format**

All cards and floating containers:

```css
.card, .service-card, .agent-card {
  background: var(--card-bg);
  border-radius: 12px;
  box-shadow: 0 4px 12px #4c52701c;
  color: var(--text);
}
.info-box, .success-box, .warning-box {
  background: var(--accent);
  border-left: 4px solid var(--lavender);
  border-radius: 6px;
  color: var(--text);
}
```


***

# **Footer**

Simple sticky footer, chef slang:

```html
<footer style="background:var(--bg);color:var(--text);padding:1rem;text-align:center;border-top:2px solid var(--mint);">
  <img src="codechef-18.jpg" alt="logo" style="height:20px;margin-right:10px;"/>
  <span>© Code/chef — “Yes, Chef!”</span>
  <span style="margin-left:1rem;">| <a href="docs-overview-new.html" style="color:var(--mint);">Docs</a></span>
</footer>
```


***

# **Dark Mode JavaScript**

Include in root or a JS bundle:

```js
document.querySelector('#themeToggle').addEventListener('click', function() {
  document.body.dataset.theme = document.body.dataset.theme === 'dark' ? '' : 'dark';
});
```


***

# **Docs Page (docs-overview-new.html: Recipe Card Example)**

```html
<div class="recipe-card" style="background: var(--light-yellow); border-left:8px solid var(--mint);">
  <h2 class="recipe-title" style="color:var(--gray-blue);font-weight:700;">How to deploy a Chef</h2>
  <p><strong>Ingredients:</strong> Docker, Python, Caddy, MCP agents.</p>
  <p><strong>Preparation:</strong> Follow these steps for a perfect orchestration.</p>
</div>
```


***

# **Accessibility Improvements**

- Always use good color contrast ratios.
- All buttons should have visible focus states (box-shadow or border).
- Use icons (hat files) with alt text for non-visual users.

***

# **Summary**

Apply:

- Brand palette variables across all containers, backgrounds, text, and CTAs.
- Hero, nav, agent grid, and cards customized by agent type and kitchen role.
- Chef hat logos prominent on all pages, especially nav/hero/footer.
- Theme toggle for dark mode; respects palette inversion by data attribute.
- “Le Brigade” role-to-agent UI everywhere, with code snippets above as templates.
