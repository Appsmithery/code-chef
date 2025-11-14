// Must import instrumentation FIRST for OpenTelemetry to auto-instrument Express
import "./instrumentation.js";
import "dotenv/config";
import express from "express";
import routes from "./routes.js";

const app = express();
const PORT = process.env.PORT || 8000;

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

app.listen(PORT, () => {
  console.log(`MCP Gateway running at http://localhost:${PORT}`);
  console.log(`Health: http://localhost:${PORT}/health`);
});
