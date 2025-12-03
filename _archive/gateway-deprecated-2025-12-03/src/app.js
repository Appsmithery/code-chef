// Must import instrumentation FIRST for OpenTelemetry to auto-instrument Express
import "dotenv/config";
import express from "express";
import promClient from "prom-client";
import "./instrumentation.js";
import routes from "./routes.js";

const app = express();
const PORT = process.env.PORT || 8000;

// Prometheus metrics
const register = new promClient.Registry();
promClient.collectDefaultMetrics({ register });

app.use(express.json());

app.get("/health", (req, res) => {
  res.json({
    status: "ok",
    service: "mcp-gateway",
    timestamp: new Date().toISOString(),
  });
});

app.get("/.well-known/oauth-protected-resource/mcp", (req, res) => {
  res.json({
    mcp: "metadata",
    endpoints: [
      "/api/linear-issues",
      "/api/linear-project/:projectId",
      "/oauth/linear/install",
      "/oauth/linear/status",
    ],
  });
});

app.use("/", routes);

app.get("/", (req, res) => {
  res.send(
    "MCP Gateway is running. Authorize via /oauth/linear/install then query /api/linear-issues."
  );
});

// Prometheus /metrics endpoint
app.get("/metrics", async (req, res) => {
  res.set("Content-Type", register.contentType);
  res.end(await register.metrics());
});

app.listen(PORT, () => {
  console.log(`MCP Gateway running at http://localhost:${PORT}`);
  console.log(`Health: http://localhost:${PORT}/health`);
  console.log(`Metrics: http://localhost:${PORT}/metrics`);
});
