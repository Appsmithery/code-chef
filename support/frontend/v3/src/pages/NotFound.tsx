export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="text-center space-y-4">
        <h1 className="text-6xl font-bold text-accent">404</h1>
        <p className="text-xl text-muted-foreground">Page not found</p>
        <a
          href="/"
          className="inline-block px-6 py-3 bg-accent text-accent-foreground rounded-md hover:bg-accent/90 transition-colors"
        >
          Go Home
        </a>
      </div>
    </div>
  );
}
