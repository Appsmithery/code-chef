# Site Branding Updates

### 1. Global Header Consistency

The screenshots show that subpages (`Agents`, `Servers`) still have the text "code/chef" in the header, whereas the Home page correctly shows only the logo.

**Recommendation:** Remove the text from the header in all subpages to match the Home page.

**Apply to:** `agents.html`, `servers.html`, `docs-overview-new.html`

```html
<!-- In header section of all subpages -->
<a href="index.html" class="header-brand">
  <!-- Use the transparent banner logo like index.html -->
  <img src="logos/banner_logo_transparent.svg" alt="code/chef logo" />
  <!-- REMOVE any text here -->
</a>
```

### 2. Agents Page (`agents.html`)

The Mermaid diagram currently uses the old color scheme (blues/greys). Let's update it to use your new **Purple (`#887bb0`)**, **Mint (`#bcece0`)**, and **Cream** palette so it feels like part of the "kitchen".

**Recommendation:** Update the Mermaid initialization config.

```html
<!-- Replace the existing %%{init: ... }%% block -->
%%{init: { 'theme': 'base', 'themeVariables': { 'primaryColor': '#887bb0',
'primaryTextColor': '#fff', 'primaryBorderColor': '#bcece0', 'lineColor':
'#4c5270', 'secondaryColor': '#2a2e3f', 'tertiaryColor': '#fff9c4' } }}%%
```

### 3. Servers Page (`servers.html`)

The server cards need to adopt the new "Light Purple" background in Day Mode to match the index page. Additionally, the tool badges can be styled to look more like "ingredients".

**Recommendation:**

1.  Ensure `.server-card` inherits the new background color in Day Mode.
2.  Update badges to use the **Google Sans Code** font.

**CSS Updates (add to `styles.css` or internal style block):**

```css
/* Match the main .card styling for server cards */
.server-card {
  /* ... existing styles ... */
  border: 1px solid rgba(136, 123, 176, 0.2);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

/* Day Mode: Light Purple Background */
body:not([data-theme="dark"]) .server-card {
  background-color: #887bb0; /* The requested light purple */
  color: #fff; /* White text for better contrast on purple */
}

/* Update Badges to use new font */
.param-badge {
  font-family: "Google Sans Code", monospace;
  background: rgba(188, 236, 224, 0.2); /* Mint tint */
  color: #bcece0; /* Mint text */
  border: 1px solid rgba(188, 236, 224, 0.4);
}

/* Day Mode Badge Adjustment */
body:not([data-theme="dark"]) .param-badge {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
  border-color: rgba(255, 255, 255, 0.5);
}
```

### 4. Cookbook / Docs Page (`docs-overview-new.html`)

The code blocks are the star of this page. They should look like "recipes" or "tickets".

**Recommendation:**

1.  Style `.recipe-card` to match the purple theme.
2.  Give `<pre>` blocks a "ticket" look with the new font.

**CSS Updates:**

```css
/* Day Mode: Recipe Cards */
body:not([data-theme="dark"]) .recipe-card {
  background-color: #887bb0;
  color: #fff;
  border: none;
}

/* Headings inside purple cards need to be white/mint, not lavender */
body:not([data-theme="dark"]) .recipe-card h3 {
  color: #bcece0 !important; /* Mint color pops on purple */
}

/* Code Blocks - "Ticket" Style */
pre {
  font-family: "Google Sans Code", monospace;
  background: #2a2e3f; /* Always dark background for code */
  color: #bcece0; /* Mint text */
  border-radius: 8px;
  border-left: 4px solid #bcece0; /* Mint accent line */
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
```

### 5. Typography Update (All Pages)

Ensure the new font is actually applied to the specific elements in subpages that might have overrides.

**HTML Head Update (All Subpages):**
Make sure this link is present in `<head>`:

```html
<link
  href="https://fonts.googleapis.com/css2?family=Google+Sans+Code:ital,wght@0,300..800;1,300..800&display=swap"
  rel="stylesheet"
/>
```

**CSS Update:**

```css
/* Force font on all interactive elements */
button, input, select, textarea, .badge, ./* Force font on all interactive elements */
button, input, select, textarea, .badge, .tag, pre, code {
  font-family: "Google Sans Code", monospace;
}
```
