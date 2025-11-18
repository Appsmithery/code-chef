#!/usr/bin/env python3
"""Provision Gradient workspaces, agents, and API keys from a manifest."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib import error, parse, request

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV = REPO_ROOT / "config" / "env" / ".env"
DEFAULT_MANIFEST = REPO_ROOT / "config" / "env" / "workspaces" / "the-shop.json"
GENAI_BASE_ENV = "GRADIENT_GENAI_BASE_URL"
DEFAULT_GENAI_BASE = "https://api.digitalocean.com"
USER_AGENT = "Dev-Tools-GradientSync/1.0"


class GradientSyncError(Exception):
    """Raised when the Gradient control-plane call fails."""


def load_env_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        raise GradientSyncError(f"Missing env file: {path}")

    values: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        sanitized = value.strip()
        if sanitized.startswith(("'", '"')) and sanitized.endswith(("'", '"')) and sanitized[:1] == sanitized[-1:]:
            sanitized = sanitized[1:-1]
        values[key.strip()] = sanitized
    return values


class GradientAPI:
    def __init__(self, token: str, base_url: str) -> None:
        self.token = token
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, *, payload: Optional[Dict[str, Any]] = None,
                query: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{parse.urlencode({k: v for k, v in query.items() if v is not None})}"
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=data, method=method.upper())
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", USER_AGENT)

        try:
            with request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except error.HTTPError as http_err:
            error_body = http_err.read().decode("utf-8", errors="ignore") if hasattr(http_err, "read") else ""
            raise GradientSyncError(
                f"{method.upper()} {path} failed with {http_err.code}: {error_body or http_err.reason}"
            ) from http_err
        except error.URLError as url_err:
            raise GradientSyncError(f"Failed to call {method.upper()} {path}: {url_err.reason}") from url_err

    def fetch_collection(self, path: str, root_key: str, *, query: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        page = 1
        while True:
            merged_query = dict(query or {})
            merged_query.setdefault("page", page)
            response = self.request("GET", path, query=merged_query)
            chunk = response.get(root_key) or []
            items.extend(chunk)
            meta = response.get("meta") or {}
            total_pages = meta.get("pages")
            if not total_pages or page >= total_pages:
                break
            page += 1
        return items


def load_manifest(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise GradientSyncError(f"Manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def persist_manifest(path: Path, manifest: Dict[str, Any]) -> None:
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def ensure_workspace(api: GradientAPI, manifest: Dict[str, Any], *, dry_run: bool) -> Tuple[Dict[str, Any], bool]:
    workspace_cfg = manifest.get("workspace") or {}
    target_name = workspace_cfg.get("name")
    if not target_name:
        raise GradientSyncError("Manifest.workspace.name is required")

    existing = None
    for ws in api.fetch_collection("/v2/gen-ai/workspaces", "workspaces"):
        if ws.get("name", "").lower() == target_name.lower():
            existing = ws
            break

    changed = False
    if existing:
        if workspace_cfg.get("uuid") != existing.get("uuid"):
            workspace_cfg["uuid"] = existing.get("uuid")
            changed = True
        print(f"✅ Workspace '{target_name}' found ({workspace_cfg['uuid']}).")
    else:
        if dry_run:
            print(f"🛈 Dry-run: would create workspace '{target_name}'.")
            return workspace_cfg, changed
        payload = {
            "name": target_name,
            "description": workspace_cfg.get("description", "") or None,
            "agent_uuids": workspace_cfg.get("agent_uuids") or []
        }
        print(f"➕ Creating workspace '{target_name}'...")
        response = api.request("POST", "/v2/gen-ai/workspaces", payload=payload)
        workspace = response.get("workspace") or {}
        workspace_cfg["uuid"] = workspace.get("uuid")
        changed = True
        print(f"✅ Workspace '{target_name}' created ({workspace_cfg['uuid']}).")
    manifest["workspace"] = workspace_cfg
    return workspace_cfg, changed


def resolve_knowledge_bases(api: GradientAPI, manifest: Dict[str, Any]) -> Tuple[Dict[str, str], bool]:
    kb_entries = manifest.get("knowledge_bases") or []
    if not kb_entries:
        return {}, False

    remote_kbs = api.fetch_collection("/v2/gen-ai/knowledge_bases", "knowledge_bases")
    by_name = {kb.get("name", "").lower(): kb for kb in remote_kbs}
    ref_map: Dict[str, str] = {}
    changed = False

    for entry in kb_entries:
        ref = entry.get("ref") or entry.get("name")
        if not ref:
            raise GradientSyncError("Each knowledge base entry needs a 'ref' or 'name'.")
        uuid = entry.get("uuid")
        if uuid:
            ref_map[ref] = uuid
            continue
        kb_name = entry.get("name")
        match = by_name.get((kb_name or "").lower())
        if match:
            entry["uuid"] = match.get("uuid")
            ref_map[ref] = entry["uuid"]
            changed = True
            print(f"🔗 Linked knowledge base '{kb_name}' -> {entry['uuid']}.")
        else:
            raise GradientSyncError(f"Knowledge base '{kb_name}' (ref {ref}) does not exist yet. Please create it via the UI first.")
    return ref_map, changed


def fetch_agents(api: GradientAPI, workspace_uuid: str) -> List[Dict[str, Any]]:
    if not workspace_uuid:
        return api.fetch_collection("/v2/gen-ai/agents", "agents")
    path = f"/v2/gen-ai/workspaces/{workspace_uuid}/agents"
    response = api.request("GET", path)
    return response.get("agents") or []


def attach_knowledge_bases(api: GradientAPI, agent_uuid: str, kb_ids: List[str], *, dry_run: bool) -> None:
    if not kb_ids:
        return
    if dry_run:
        print(f"🛈 Dry-run: would attach knowledge bases {kb_ids} to '{agent_uuid}'.")
        return
    print(f"📚 Attaching {len(kb_ids)} knowledge base(s) to agent '{agent_uuid}'.")
    api.request(
        "POST",
        f"/v2/gen-ai/agents/{agent_uuid}/knowledge_bases",
        payload={"agent_uuid": agent_uuid, "knowledge_base_uuids": kb_ids}
    )


def ensure_agent(api: GradientAPI, manifest_agent: Dict[str, Any], workspace: Dict[str, Any], kb_map: Dict[str, str], *, dry_run: bool) -> Tuple[Dict[str, Any], bool]:
    workspace_uuid = workspace.get("uuid")
    if not workspace_uuid:
        raise GradientSyncError("Workspace UUID missing; ensure the workspace exists before creating agents.")

    existing_agents = fetch_agents(api, workspace_uuid)
    existing = None
    target_name = manifest_agent.get("name")
    for agent in existing_agents:
        if agent.get("name", "").lower() == (target_name or "").lower():
            existing = agent
            break

    changed = False
    kb_refs = manifest_agent.get("knowledge_base_refs") or []
    kb_ids = []
    for ref in kb_refs:
        if ref not in kb_map:
            raise GradientSyncError(f"Knowledge base ref '{ref}' is not mapped to a UUID.")
        kb_ids.append(kb_map[ref])

    if existing:
        manifest_agent["uuid"] = existing.get("uuid")
        manifest_agent["workspace_uuid"] = workspace_uuid
        current_kb_ids = {kb.get("uuid") for kb in existing.get("knowledge_bases") or [] if kb.get("uuid")}
        missing = [kb_id for kb_id in kb_ids if kb_id not in current_kb_ids]
        if missing:
            attach_knowledge_bases(api, existing["uuid"], missing, dry_run=dry_run)
        print(f"✅ Agent '{target_name}' already exists ({existing['uuid']}).")
        return manifest_agent, changed

    if dry_run:
        print(f"🛈 Dry-run: would create agent '{target_name}'.")
        return manifest_agent, changed

    payload = {
        "name": target_name,
        "description": manifest_agent.get("description"),
        "instruction": manifest_agent.get("instruction"),
        "model_uuid": manifest_agent.get("model_uuid"),
        "project_id": manifest_agent.get("project_id"),
        "region": manifest_agent.get("region"),
        "tags": manifest_agent.get("tags") or [],
        "workspace_uuid": workspace_uuid,
        "model_provider_key_uuid": manifest_agent.get("model_provider_key_uuid"),
        "open_ai_key_uuid": manifest_agent.get("openai_key_uuid"),
        "anthropic_key_uuid": manifest_agent.get("anthropic_key_uuid")
    }

    missing_required = [field for field in ("model_uuid", "project_id", "region") if not payload.get(field)]
    if missing_required:
        raise GradientSyncError(f"Agent '{target_name}' is missing required fields: {', '.join(missing_required)}")

    print(f"➕ Creating agent '{target_name}'...")
    response = api.request("POST", "/v2/gen-ai/agents", payload=payload)
    agent = response.get("agent") or {}
    manifest_agent["uuid"] = agent.get("uuid")
    manifest_agent["workspace_uuid"] = workspace_uuid
    if kb_ids:
        attach_knowledge_bases(api, manifest_agent["uuid"], kb_ids, dry_run=dry_run)
    changed = True
    print(f"✅ Agent '{target_name}' created ({manifest_agent['uuid']}).")
    return manifest_agent, changed


def ensure_agent_api_keys(api: GradientAPI, manifest_agent: Dict[str, Any], *, dry_run: bool) -> bool:
    agent_uuid = manifest_agent.get("uuid")
    if not agent_uuid:
        return False
    desired_keys = manifest_agent.get("api_keys") or []
    if not desired_keys:
        return False

    path = f"/v2/gen-ai/agents/{agent_uuid}/api_keys"
    response = api.request("GET", path)
    existing_infos = response.get("api_key_infos") or []
    by_name = {info.get("name", "").lower(): info for info in existing_infos}
    changed = False

    for entry in desired_keys:
        key_name = entry.get("name")
        if not key_name:
            raise GradientSyncError("api_keys entries need a name.")
        existing = by_name.get(key_name.lower())
        if entry.get("uuid"):
            continue
        if existing:
            entry["uuid"] = existing.get("uuid")
            print(f"🔐 Found existing API key '{key_name}' ({entry['uuid']}). Secret cannot be retrieved; rotate if needed.")
            changed = True
            continue
        if dry_run:
            print(f"🛈 Dry-run: would create API key '{key_name}' for agent {agent_uuid}.")
            continue
        payload = {"agent_uuid": agent_uuid, "name": key_name}
        print(f"🔑 Creating API key '{key_name}' for agent {agent_uuid}...")
        api_key_resp = api.request("POST", path, payload=payload)
        api_key_info = api_key_resp.get("api_key_info") or {}
        entry["uuid"] = api_key_info.get("uuid")
        secret = api_key_info.get("secret_key") or api_key_info.get("api_key")
        if secret:
            write_agent_secret(entry.get("output_file"), manifest_agent, entry, secret)
        else:
            print(f"⚠️ API did not return a secret for key '{key_name}'.")
        changed = True
    return changed


def write_agent_secret(output_file: Optional[str], agent: Dict[str, Any], api_key: Dict[str, Any], secret: str) -> None:
    if not output_file:
        print(f"⚠️ No output_file configured for key '{api_key.get('name')}', skipping secret write.")
        return
    target_path = Path(output_file)
    if not target_path.is_absolute():
        target_path = REPO_ROOT / target_path
    target = target_path
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "workspace": agent.get("workspace_slug") or agent.get("workspace_name"),
        "agent_name": agent.get("name"),
        "agent_uuid": agent.get("uuid"),
        "api_key_uuid": api_key.get("uuid"),
        "api_key_name": api_key.get("name"),
        "secret": secret,
        "written_at": int(time.time())
    }
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"📁 Stored agent key '{api_key.get('name')}' at {target}.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync Gradient workspaces/agents/api keys from a manifest.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Path to the workspace manifest (default: config/env/workspaces/the-shop.json)")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV, help="Path to the runtime .env file (default: config/env/.env)")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without mutating Gradient state or files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    env_path = (args.env_file if args.env_file.is_absolute() else REPO_ROOT / args.env_file).resolve()
    manifest_path = (args.manifest if args.manifest.is_absolute() else REPO_ROOT / args.manifest).resolve()

    env_values = load_env_file(env_path)
    token = env_values.get("DIGITALOCEAN_TOKEN") or env_values.get("DIGITAL_OCEAN_PAT")
    if not token:
        raise GradientSyncError("Set DIGITALOCEAN_TOKEN or DIGITAL_OCEAN_PAT in config/env/.env")

    base_url = env_values.get(GENAI_BASE_ENV, DEFAULT_GENAI_BASE)
    api = GradientAPI(token, base_url)

    manifest = load_manifest(manifest_path)
    manifest_changed = False

    workspace, ws_changed = ensure_workspace(api, manifest, dry_run=args.dry_run)
    manifest_changed |= ws_changed

    kb_map, kb_changed = resolve_knowledge_bases(api, manifest)
    manifest_changed |= kb_changed

    agents = manifest.get("agents") or []
    for agent in agents:
        agent.setdefault("workspace_slug", workspace.get("slug") or workspace.get("name"))
        agent["workspace_name"] = workspace.get("name")
        agent_data, agent_changed = ensure_agent(api, agent, workspace, kb_map, dry_run=args.dry_run)
        manifest_changed |= agent_changed
        key_changed = ensure_agent_api_keys(api, agent_data, dry_run=args.dry_run)
        manifest_changed |= key_changed

    if manifest_changed and not args.dry_run:
        persist_manifest(manifest_path, manifest)
        print(f"💾 Updated manifest at {manifest_path}.")
    elif args.dry_run:
        print("🛈 Dry-run complete. No files were modified.")
    else:
        print("✨ Manifest already up to date.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GradientSyncError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        raise SystemExit(1)
