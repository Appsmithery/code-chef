import { Button } from "@/components/ui/button";
import { useTheme } from "@/contexts/ThemeContext";
import { Github, Moon, Sun } from "lucide-react";
import { Link, useLocation } from "wouter";

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const { theme, toggleTheme } = useTheme();
  const [location] = useLocation();

  const navLinks = [
    { href: "/", label: "Home" },
    { href: "/agents", label: "Agents" },
    { href: "/servers", label: "Servers" },
    // { href: "/cookbook", label: "Cookbook" }, // Deferred
  ];

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground font-sans selection:bg-accent selection:text-accent-foreground">
      {/* Navbar */}
      <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          <Link href="/" className="flex items-center">
            <img 
              src="/logos/banner_logo_transparent.svg" 
              alt="code/chef logo" 
              className="h-10 w-auto" 
            />
          </Link>
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`transition-colors hover:text-accent ${
                  location === link.href ? 'text-accent' : 'text-foreground'
                }`}
              >
                {link.label}
              </Link>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              className="text-foreground hover:text-accent transition-colors"
              aria-label="Toggle theme"
            >
              {theme === "light" ? (
                <Moon className="h-5 w-5" />
              ) : (
                <Sun className="h-5 w-5" />
              )}
            </Button>
            <Button 
              variant="ghost" 
              size="icon" 
              className="text-foreground hover:text-accent"
              asChild
            >
              <a href="https://github.com/Appsmithery/code-chef" target="_blank" rel="noopener noreferrer">
                <Github className="h-5 w-5" />
              </a>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-muted/30 py-8">
        <div className="container flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <img 
              src="/logos/hat_icon_transparent.svg" 
              alt="code/chef" 
              className="h-8 w-8" 
            />
            <span className="text-sm text-muted-foreground">
              © 2025 code/chef — "Yes, Chef!"
            </span>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <Link href="/agents" className="text-muted-foreground hover:text-accent transition-colors">
              Agents
            </Link>
            <span className="text-muted-foreground">|</span>
            <Link href="/servers" className="text-muted-foreground hover:text-accent transition-colors">
              Servers
            </Link>
            <span className="text-muted-foreground">|</span>
            <a 
              href="https://github.com/Appsmithery/code-chef" 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-accent transition-colors"
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
