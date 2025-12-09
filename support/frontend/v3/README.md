# Code/Chef Frontend v3 - React + TypeScript

**Status**: ✅ Production Ready  
**Build**: Vite 5.0 + React 18 + TypeScript 5.3 + Tailwind CSS 4  
**Deployment**: Docker + Caddy (codechef.appsmithery.co)

---

## Quick Start

```bash
# Install dependencies
npm install

# Development server (hot reload)
npm run dev

# Production build
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
v3/
├── src/
│   ├── components/
│   │   ├── ui/              # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── tooltip.tsx
│   │   │   └── sonner.tsx
│   │   └── ErrorBoundary.tsx
│   ├── contexts/
│   │   └── ThemeContext.tsx  # Light/dark theme
│   ├── pages/
│   │   ├── Home.tsx          # Main landing
│   │   └── NotFound.tsx      # 404 page
│   ├── lib/
│   │   └── utils.ts          # Utilities
│   ├── App.tsx               # Root component
│   ├── main.tsx              # Entry point
│   └── index.css             # Global styles + Tailwind
├── public/
│   └── logos/                # SVG/PNG assets
├── dist/                     # Build output (gitignored)
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
└── README.md                 # This file
```

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18.2 | UI library |
| TypeScript | 5.3 | Type safety |
| Vite | 5.0 | Build tool + dev server |
| Tailwind CSS | 4.0 | Utility-first CSS |
| Wouter | 3.0 | Client-side routing |
| Lucide React | 0.312 | Icon library |
| Radix UI | Latest | Accessible primitives |
| Sonner | 1.4 | Toast notifications |

## Design System

### Color Palette (Code/Chef Brand)

| Color | Value | Usage |
|-------|-------|-------|
| Gray-Blue | `#4c5270` | Primary text, dark headers |
| Mint | `#bcece0` | Accent color, CTAs |
| Flour | `#fffdf2` | Light background |
| Salmon | `#f4b9b8` | Secondary accent |
| Lavender | `#887bb0` | Tertiary accent, links |
| Butter | `#fff4bd` | Highlights |

### Typography
- **Primary Font**: Google Sans Code (monospace)
- **Fallback**: Segoe UI, system-ui, -apple-system

### Components
- Built with Radix UI primitives for accessibility
- Styled with Tailwind CSS utility classes
- Custom brand colors via CSS variables

## Development

### Hot Module Replacement (HMR)
Vite provides instant HMR for `.tsx` and `.css` files. Changes appear immediately without full page reload.

### Type Checking
```bash
# Check types without building
npm run lint
```

### Adding Components
```bash
# Example: Add a new page
touch src/pages/Agents.tsx

# Import and route in App.tsx
import Agents from './pages/Agents';
// <Route path="/agents" component={Agents} />
```

## Building for Production

### Build Command
```bash
npm run build
```

**Output**:
```
dist/
├── index.html          # Entry HTML (7KB)
├── assets/
│   ├── index-*.js      # App bundle (~90KB)
│   ├── vendor-*.js     # React + deps (~146KB)
│   ├── ui-*.js         # UI components (~38KB)
│   └── index-*.css     # Styles (~69KB)
```

### Build Optimization
- **Tree Shaking**: Dead code elimination
- **Code Splitting**: Vendor, UI, and app chunks
- **CSS Purging**: Unused Tailwind classes removed
- **Minification**: JavaScript and CSS minified
- **Gzip**: Caddy serves with gzip encoding

**Total Bundle Size**: 343KB raw, ~89KB gzipped

## Deployment

### Docker Compose (Production)
```yaml
# deploy/docker-compose.yml
caddy:
  volumes:
    - ../support/frontend/v3/dist:/srv/frontend:ro
```

### Caddyfile (SPA Routing)
```caddyfile
# config/caddy/Caddyfile
handle {
  root * /srv/frontend
  encode gzip
  try_files {path} /index.html
  file_server
}
```

### Deployment Steps
1. Build: `npm run build`
2. Commit `dist/` or rebuild on server
3. Restart Caddy: `docker compose restart caddy`
4. Verify: https://codechef.appsmithery.co

## Routing

### Client-Side Routes (Wouter)
- `/` - Home page
- `/404` - Not found page

**SPA Fallback**: All unmatched routes serve `index.html` for client-side routing.

### Adding Routes
```tsx
// src/App.tsx
import NewPage from './pages/NewPage';

<Route path="/new" component={NewPage} />
```

## Theme Support

### Light/Dark Mode
Toggle via button in navbar. Preference stored in `localStorage`.

```typescript
// Usage
import { useTheme } from '@/contexts/ThemeContext';

function Component() {
  const { theme, toggleTheme } = useTheme();
  
  return (
    <button onClick={toggleTheme}>
      {theme === 'light' ? '🌙' : '☀️'}
    </button>
  );
}
```

### Theme Colors
Defined in `src/index.css` using CSS variables:
```css
:root {
  --background: oklch(...);
  --foreground: oklch(...);
  --primary: oklch(...);
  /* ... */
}
```

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start dev server (port 5173) |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |

## Performance

### Lighthouse Scores (Target)
- Performance: > 95
- Accessibility: > 95
- Best Practices: > 95
- SEO: > 90

### Core Web Vitals
- **LCP** (Largest Contentful Paint): < 2s
- **FID** (First Input Delay): < 100ms
- **CLS** (Cumulative Layout Shift): < 0.1

## Troubleshooting

### Build Errors
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json dist
npm install
npm run build
```

### 404 on Page Refresh
Ensure Caddyfile has `try_files {path} /index.html` for SPA routing.

### Theme Not Persisting
Check browser localStorage:
```javascript
localStorage.getItem('theme') // should be 'light' or 'dark'
```

### Icons Not Loading
Lucide React icons imported from `lucide-react`:
```tsx
import { Bot, Server, Activity } from 'lucide-react';
```

## Contributing

### Code Style
- Use TypeScript strict mode
- Follow ESLint rules
- Use functional components with hooks
- Prefer named exports for components

### Component Guidelines
1. Place in appropriate directory (`components/`, `pages/`)
2. Use TypeScript interfaces for props
3. Apply Tailwind classes via `className`
4. Export component and type definitions

### Commit Messages
Follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `refactor:` Code refactoring
- `style:` Visual/CSS changes
- `docs:` Documentation

## Resources

- **Vite Docs**: https://vitejs.dev
- **React Docs**: https://react.dev
- **Tailwind CSS**: https://tailwindcss.com
- **Wouter**: https://github.com/molefrog/wouter
- **Lucide Icons**: https://lucide.dev
- **Radix UI**: https://radix-ui.com

## License

Proprietary - Appsmithery LLC

---

**Maintained by**: Alex Torelli (@alextorelli28)  
**Last Updated**: December 9, 2025  
**Version**: 1.0.0
