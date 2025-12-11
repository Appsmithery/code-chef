import type { Config } from "tailwindcss";

export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      boxShadow: {
        // Light mode: darker shadows for better contrast
        // Dark mode: lighter shadows to show against dark backgrounds
        'soft': '0 2px 10px rgb(0 0 0 / 0.08), 0 1px 3px rgb(0 0 0 / 0.05)',
        'medium': '0 4px 20px rgb(0 0 0 / 0.12), 0 2px 8px rgb(0 0 0 / 0.08)',
        'hover': '0 10px 30px rgb(0 0 0 / 0.15), 0 4px 12px rgb(0 0 0 / 0.1)',
        // Dark mode variants (applied via dark: modifier)
        'soft-dark': '0 2px 10px rgb(0 0 0 / 0.3), 0 1px 3px rgb(0 0 0 / 0.2)',
        'medium-dark': '0 4px 20px rgb(0 0 0 / 0.4), 0 2px 8px rgb(0 0 0 / 0.3)',
        'hover-dark': '0 10px 30px rgb(0 0 0 / 0.5), 0 4px 12px rgb(0 0 0 / 0.4)',
      },
    },
  },
  plugins: [],
} satisfies Config;
