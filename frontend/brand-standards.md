# code/chef — Brand + Design Standards (Canonical)

**Status:** Canonical reference for the code/chef frontend

This document defines the brand palette, typography, layout principles, and the motion/interaction system used across the site.

---

## 1) Brand fundamentals

### Color palette (official)

- **Frosted Grape (gray-blue):** `#4c5270`
- **Lavender:** `#887bb0`
- **Mint:** `#bcece0`
- **Butter:** `#fff4bd`
- **Flour:** `#fffdf2`
- **Salmon:** `#f4b9b8` (use sparingly)

**Theming guidelines**

**Light mode:**

- Emphasize **Lavender** as the primary accent
- Use **Mint** for secondary highlights
- Keep **Salmon** minimal (only for critical CTAs)
- Background tints of **Flour/Lavender**

**Dark mode:**

- Emphasize **Butter, Mint, Flour** for warmth and calm
- **Lavender** for key UI elements
- Avoid **Salmon** unless absolutely necessary
- Keep backgrounds deep with subtle tints

**General principles:**

- Avoid pure black/white contrast; prefer brand-tinted neutrals
- Red/aggressive colors should be minimal

### Typography

Primary font: **Fira Code** (fallback includes Google Sans Code / system).

**Typographic hierarchy**

- Headlines: bold, tight tracking, strong size jumps.
- Body: 15–17px equivalent, generous line-height (1.6+), muted colors for long copy.

---

## 2) Layout principles (avoid the “AI-generated” look)

The “AI-generated” feel often comes from rigid symmetry, uniform card templates, and centered-everything layouts.

### Do

- Prefer **asymmetry**: varied padding, offsets, and rhythm.
- Use **editorial composition**: alternating alignment, sticky visuals, and narrative sections.
- Add **depth**: layered shadows + subtle gradients.
- **Use tags/badges sparingly**: Only when they provide clear categorical value.
- **Breathe**: Generous whitespace, clear visual hierarchy.

### Don't

- Don't stack identical cards in a perfect grid unless there's a strong reason.
- Don't center every icon/title/paragraph.
- **Don't over-badge**: Avoid decorative tags on every section/card.
- **Don't clutter**: Every visual element should serve a purpose.

---

## 3) Motion & reactive visuals system

Motion should feel editorial: subtle, purposeful, and never distracting.

### Accessibility (non-negotiable)

- Respect reduced motion via `prefers-reduced-motion`.
- Avoid scroll-jank: keep animations light, GPU-friendly, and minimal.

### Standard utilities

**CSS utilities** live in `frontend/src/index.css`:

- `.cc-shimmer-text` — slow, subtle gradient shimmer (use sparingly on a single highlight per section)
- `.cc-float` — gentle vertical float for small accent elements

**Scroll state utilities** live in `frontend/src/lib/scroll.ts`:

- `useActiveSection()` — IntersectionObserver-based active-section tracking
- `usePrefersReducedMotion()` — reduced-motion detection

### Motion rules

- Prefer **opacity + translateY(4–8px)** reveals (small).
- Prefer long durations (600–1200ms) and gentle easing.
- Use shimmer on **one** element per section, not everywhere.

---

## 4) Page patterns (standard building blocks)

### Pattern A — Scrollytelling rails (Home “Capabilities”)

**Intent:** replace rigid bento grids with narrative, alternating left/right sections.

**Guidelines**

- Alternate alignment per row.
- Use a “visual panel” per row that looks like a real artifact (console snippet, diagram, small UI).
- Reuse brand accents but vary gradients/tones by feature.

### Pattern B — Sticky visual, changing copy (Agents)

**Intent:** keep the left visual pinned while the right column scrolls through detail; active section updates the sticky panel.

**Guidelines**

- Sticky panel shows “active agent” and a compact overview.
- Right column contains deeper content per agent (model/provider/port/capabilities/tasks).
- Active section detection should be driven by IntersectionObserver (not scroll events).

---

## 5) Asset guidance (images, GIFs, animations)

### Preferred formats

- Icons/illustrations: **SVG**
- Photos: **AVIF/WebP** (fallback PNG/JPG when needed)
- Animations: **MP4/WebM** instead of GIF (smaller and smoother)
- Rich vector animations: **Lottie** (JSON) or **Rive**

### Where to put assets

- Importable assets (hashed by Vite): `frontend/src/assets/...`
- Public URL assets: `frontend/public/media/...`

Recommended structure:

- `frontend/src/assets/home/`
- `frontend/src/assets/agents/`
- `frontend/public/media/home/`

### How to provide assets to the project

Best options:

1. Commit via PR into the above folders.
2. Upload a zip containing assets + a small manifest:
   - filename
   - target section
   - intended size/ratio
   - light/dark compatibility
   - alt text
3. Provide a CDN URL list with versioned paths.

---

## 6) Implementation notes

- Keep card borders subtle; let shadow define depth.
- Prefer background gradients with low opacity (5–12%).
- For long-scroll sections: use sticky visuals, clear rhythm, and breathing room (`space-y-16` / `space-y-20`).
