import { Button } from "@/components/ui/button";
import { useTheme } from "@/contexts/ThemeContext";
import { Github, Moon, Sun } from "lucide-react";
import { Link } from "wouter";

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground font-sans selection:bg-accent selection:text-accent-foreground">
      {/* Navbar */}
      <header className="sticky top-0 z-50 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          <Link href="/">
            <a className="flex items-center hover:opacity-80 transition-opacity">
              <img
                src="/logos/hat_icon_transparent.svg"
                alt="code/chef"
                className="h-12 w-auto"
              />
            </a>
          </Link>
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium">
            <Link href="/">
              <a className="text-foreground transition-colors hover:text-accent">
                Home
              </a>
            </Link>
            <Link href="/agents">
              <a className="text-foreground transition-colors hover:text-accent">
                Agents
              </a>
            </Link>
            <Link href="/servers">
              <a className="text-foreground transition-colors hover:text-accent">
                Servers
              </a>
            </Link>
            <Link href="/cookbook">
              <a className="text-foreground transition-colors hover:text-accent">
                Cookbook
              </a>
            </Link>
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
              asChild
              className="text-foreground hover:text-accent"
            >
              <a
                href="https://github.com/Appsmithery/code-chef"
                target="_blank"
                rel="noreferrer"
              >
                <Github className="h-5 w-5" />
              </a>
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">{children}</main>

      {/* Footer */}
      <footer className="border-t border-border bg-background py-12">
        <div className="container flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              © 2025 code/chef — "Yes, Chef!"
            </span>
          </div>

          <div className="flex items-center gap-6 text-sm text-muted-foreground">
            <Link href="/cookbook">
              <a className="hover:text-accent transition-colors">
                Documentation
              </a>
            </Link>
            <span className="text-border">|</span>
            <a
              href="https://github.com/Appsmithery/code-chef"
              target="_blank"
              rel="noreferrer"
              className="hover:text-accent transition-colors flex items-center gap-2"
            >
              <Github className="h-4 w-4" />
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
