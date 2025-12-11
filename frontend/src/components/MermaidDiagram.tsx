import { useEffect, useRef } from "react";

interface MermaidDiagramProps {
  chart: string;
}

export default function MermaidDiagram({ chart }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const renderDiagram = async () => {
      if (containerRef.current) {
        try {
          // @ts-ignore - mermaid is loaded via CDN
          const mermaid = window.mermaid;
          if (mermaid) {
            // Clear any existing content
            containerRef.current.innerHTML = chart;
            // Render the diagram
            await mermaid.run({
              nodes: [containerRef.current],
            });
          }
        } catch (error) {
          console.error("Error rendering mermaid diagram:", error);
        }
      }
    };

    // Wait for mermaid to be loaded
    const checkMermaid = setInterval(() => {
      // @ts-ignore
      if (window.mermaid) {
        clearInterval(checkMermaid);
        renderDiagram();
      }
    }, 100);

    return () => clearInterval(checkMermaid);
  }, [chart]);

  return (
    <div
      ref={containerRef}
      className="mermaid flex items-center justify-center"
      style={{ minHeight: "400px" }}
    />
  );
}
