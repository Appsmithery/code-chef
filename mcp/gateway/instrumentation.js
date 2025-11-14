/**
 * OpenTelemetry instrumentation with Langfuse integration
 *
 * Must be imported FIRST before any other imports in app.js
 * Automatically traces all HTTP requests, database calls, and external API calls
 */

import { Langfuse } from "@langfuse/node";
import { getNodeAutoInstrumentations } from "@opentelemetry/auto-instrumentations-node";
import { Resource } from "@opentelemetry/resources";
import { NodeSDK } from "@opentelemetry/sdk-node";
import { ATTR_SERVICE_NAME } from "@opentelemetry/semantic-conventions";
import "dotenv/config";

// Initialize Langfuse client
const langfuse = new Langfuse({
  secretKey: process.env.LANGFUSE_SECRET_KEY,
  publicKey: process.env.LANGFUSE_PUBLIC_KEY,
  baseUrl: process.env.LANGFUSE_HOST || "https://us.cloud.langfuse.com",
  enabled: !!(
    process.env.LANGFUSE_SECRET_KEY && process.env.LANGFUSE_PUBLIC_KEY
  ),
  flushAt: 1, // Send traces immediately for testing
  flushInterval: 1000, // Flush every second
});

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

console.log("[OTEL] OpenTelemetry SDK started");
console.log(`[LANGFUSE] Tracing ${langfuse.enabled ? "ENABLED" : "DISABLED"}`);
if (!langfuse.enabled) {
  console.warn("[LANGFUSE] Missing LANGFUSE_SECRET_KEY or LANGFUSE_PUBLIC_KEY");
}

// Graceful shutdown
process.on("SIGTERM", () => {
  sdk
    .shutdown()
    .then(() => {
      console.log("[OTEL] SDK shut down successfully");
      langfuse.shutdownAsync().then(() => {
        console.log("[LANGFUSE] Flushed pending traces");
        process.exit(0);
      });
    })
    .catch((error) => {
      console.error("[OTEL] Error shutting down SDK", error);
      process.exit(1);
    });
});

// Export langfuse instance for manual tracing if needed
export { langfuse };
