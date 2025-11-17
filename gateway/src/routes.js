import express from "express";
import { buildLinearAuthorizeUrl } from "./config/linearConfig.js";
import {
  exchangeAuthorizationCode,
  fetchProjectRoadmap,
  fetchRoadmapIssues,
  getTokenStatus,
  LinearAuthErrors,
} from "./services/linear.js";
import { consumeState, createState } from "./utils/oauthState.js";

const router = express.Router();

router.get("/oauth/linear/install", (req, res) => {
  try {
    const returnTo =
      typeof req.query.returnTo === "string" ? req.query.returnTo : undefined;
    const state = createState({ returnTo });
    const authorizeUrl = buildLinearAuthorizeUrl(state);
    res.redirect(authorizeUrl);
  } catch (error) {
    console.error("[linear] Failed to start install flow:", error.message);
    res.status(500).json({
      success: false,
      error:
        "Unable to start Linear OAuth flow. Check server logs for details.",
    });
  }
});

router.get("/oauth/linear/callback", async (req, res) => {
  const { code, state } = req.query;
  if (!code || !state) {
    return res.status(400).json({
      success: false,
      error: "Missing code or state in callback request.",
    });
  }

  const metadata = consumeState(state);
  if (!metadata) {
    return res.status(400).json({
      success: false,
      error: "The provided state is invalid or has expired.",
    });
  }

  try {
    const record = await exchangeAuthorizationCode(code);
    const payload = {
      success: true,
      workspaceId: record.workspaceId,
      viewerId: record.viewerId,
      scope: record.scope,
      expiresAt: record.expiresAt,
    };

    const returnTo = metadata.returnTo;
    const isRelative = typeof returnTo === "string" && returnTo.startsWith("/");
    if (isRelative) {
      const url = new URL(returnTo, `${req.protocol}://${req.get("host")}`);
      url.searchParams.set("linearInstall", "success");
      res.redirect(url.toString());
    } else {
      res.json(payload);
    }
  } catch (error) {
    console.error("[linear] OAuth callback failure:", error.message);
    res.status(500).json({
      success: false,
      error: "Failed to finalize Linear OAuth installation.",
    });
  }
});

router.get("/oauth/linear/status", async (req, res) => {
  try {
    const status = await getTokenStatus();
    res.json({ success: true, status });
  } catch (error) {
    console.error("[linear] Status error:", error.message);
    res.status(500).json({
      success: false,
      error: "Unable to retrieve Linear token status.",
    });
  }
});

router.get("/api/linear-issues", async (req, res) => {
  try {
    const issues = await fetchRoadmapIssues();
    res.json({
      success: true,
      count: issues.length,
      issues,
    });
  } catch (error) {
    if (error.code === LinearAuthErrors.TOKEN_MISSING) {
      return res.status(503).json({
        success: false,
        error:
          "Linear OAuth token unavailable. Visit /oauth/linear/install to authorize access.",
      });
    }

    console.error("Linear API error:", error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

router.get("/api/linear-project/:projectId", async (req, res) => {
  try {
    const { projectId } = req.params;
    const roadmap = await fetchProjectRoadmap(projectId);
    res.json({ success: true, roadmap });
  } catch (error) {
    if (error.code === LinearAuthErrors.TOKEN_MISSING) {
      return res.status(503).json({
        success: false,
        error:
          "Linear OAuth token unavailable. Visit /oauth/linear/install to authorize access.",
      });
    }

    console.error("Linear project API error:", error);
    res.status(500).json({
      success: false,
      error: error.message,
    });
  }
});

export default router;
