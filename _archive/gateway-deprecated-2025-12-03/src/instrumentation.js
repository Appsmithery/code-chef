/**
 * OpenTelemetry instrumentation for LangSmith tracing
 *
 * Must be imported FIRST before any other imports in app.js
 * Automatically traces all HTTP requests, database calls, and external API calls
 */

import { getNodeAutoInstrumentations } from "@opentelemetry/auto-instrumentations-node";
import { Resource } from "@opentelemetry/resources";
import { NodeSDK } from "@opentelemetry/sdk-node";
import { ATTR_SERVICE_NAME } from "@opentelemetry/semantic-conventions";
import "dotenv/config";

// Configure OpenTelemetry SDK
const sdk = new NodeSDK({
  resource: new Resource({
    [ATTR_SERVICE_NAME]: process.env.SERVICE_NAME || "gateway-mcp",
  }),
  instrumentations: [
    getNodeAutoInstrumentations({
      // Automatically instrument Express, HTTP, DNS, etc.
      "@opentelemetry/instrumentation-fs": { enabled: false }, // Disable noisy filesystem tracing
    }),
  ],
});

// Start the SDK
sdk.start();

console.log("[OTEL] OpenTelemetry SDK started for LangSmith tracing");

// Graceful shutdown
process.on("SIGTERM", () => {
  sdk
    .shutdown()
    .then(() => {
      console.log("[OTEL] SDK shut down successfully");
      process.exit(0);
    })
    .catch((error) => {
      console.error("[OTEL] Error shutting down SDK", error);
      process.exit(1);
    });
});
