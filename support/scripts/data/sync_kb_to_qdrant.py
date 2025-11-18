#!/usr/bin/env python3
"""Sync DigitalOcean Gradient knowledge base exports into Qdrant."""
from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib import error, request

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_ENV = REPO_ROOT / "config" / "env" / ".env"
DEFAULT_MANIFEST = REPO_ROOT / "config" / "env" / "workspaces" / "the-shop.json"
DEFAULT_DOWNLOAD_DIR = REPO_ROOT / "tmp" / "kb-sync"
GENAI_BASE_ENV = "GRADIENT_GENAI_BASE_URL"
DEFAULT_GENAI_BASE = "https://api.digitalocean.com"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from gradient_workspace_sync import GradientAPI, GradientSyncError, load_env_file  # type: ignore  # noqa: E402

COMPLETED_STATUSES = {"INDEX_JOB_STATUS_COMPLETED", "INDEX_JOB_STATUS_NO_CHANGES", "INDEX_JOB_STATUS_PARTIAL"}
FAILED_STATUSES = {"INDEX_JOB_STATUS_FAILED", "INDEX_JOB_STATUS_CANCELLED"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a DigitalOcean knowledge base indexing job into Qdrant.")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV, help="Path to runtime env file (default: config/env/.env)")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Workspace manifest for resolving KB refs")
    parser.add_argument("--kb-uuid", help="Knowledge base UUID. Overrides manifest/env values.")
    parser.add_argument("--kb-ref", default=os.getenv("DIGITALOCEAN_KB_REF", "the-shop"), help="Knowledge base ref to look up inside the manifest")
    parser.add_argument("--collection", help="Target Qdrant collection (defaults to QDRANT_COLLECTION env)")
    parser.add_argument("--job-uuid", help="Existing indexing job UUID to download")
    parser.add_argument("--start-job", action="store_true", help="Trigger a fresh indexing job before downloading the report")
    parser.add_argument("--poll-interval", type=int, default=30, help="Seconds between job status checks")
    parser.add_argument("--timeout", type=int, default=1800, help="Max seconds to wait for indexing job completion")
    parser.add_argument("--batch-size", type=int, default=64, help="Qdrant upsert batch size")
    parser.add_argument("--download-dir", type=Path, default=DEFAULT_DOWNLOAD_DIR, help="Directory to persist raw job exports")
    parser.add_argument("--dry-run", action="store_true", help="Download and decode the report without writing to Qdrant")
    return parser.parse_args()


def load_manifest(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise GradientSyncError(f"Manifest not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_kb_uuid(args: argparse.Namespace, env_values: Dict[str, str], manifest: Dict[str, Any]) -> str:
    if args.kb_uuid:
        return args.kb_uuid
    if env_values.get("DIGITALOCEAN_KB_UUID"):
        return env_values["DIGITALOCEAN_KB_UUID"]
    for entry in manifest.get("knowledge_bases", []):
        if entry.get("ref") == args.kb_ref or entry.get("name") == args.kb_ref:
            if entry.get("uuid"):
                return entry["uuid"]
    raise GradientSyncError("Unable to resolve knowledge base UUID. Provide --kb-uuid or update manifest/env values.")


def resolve_collection(args: argparse.Namespace, env_values: Dict[str, str]) -> str:
    if args.collection:
        return args.collection
    if env_values.get("QDRANT_COLLECTION"):
        return env_values["QDRANT_COLLECTION"]
    raise GradientSyncError("Set QDRANT_COLLECTION in the env file or pass --collection.")


def init_qdrant(env_values: Dict[str, str]) -> QdrantClient:
    url = env_values.get("QDRANT_URL")
    api_key = env_values.get("QDRANT_API_KEY")
    host = env_values.get("QDRANT_HOST", "qdrant")
    port = int(env_values.get("QDRANT_PORT", "6333"))
    if url:
        return QdrantClient(url=url, api_key=api_key)
    return QdrantClient(host=host, port=port, api_key=api_key)


def ensure_collection(client: QdrantClient, collection: str, env_values: Dict[str, str]) -> None:
    vector_size = int(env_values.get("QDRANT_VECTOR_SIZE", "1536"))
    distance_value = env_values.get("QDRANT_DISTANCE", "cosine").upper()
    distance = {
        "COSINE": Distance.COSINE,
        "EUCLID": Distance.EUCLID,
        "DOT": Distance.DOT,
        "MANHATTAN": Distance.MANHATTAN,
    }.get(distance_value, Distance.COSINE)
    try:
        client.get_collection(collection)
    except Exception:
        client.create_collection(collection_name=collection, vectors_config=VectorParams(size=vector_size, distance=distance))
        print(f"🆕 Created Qdrant collection '{collection}' ({vector_size} dims, {distance_value})")


def trigger_indexing_job(api: GradientAPI, kb_uuid: str) -> str:
    print(f"🚀 Starting indexing job for KB {kb_uuid}...")
    response = api.request("POST", f"/v2/gen-ai/knowledge_bases/{kb_uuid}/indexing_jobs", payload={"knowledge_base_uuid": kb_uuid})
    job = response.get("job") or {}
    job_uuid = job.get("uuid")
    if not job_uuid:
        raise GradientSyncError("Indexing job response missing uuid")
    print(f"🆔 Started job {job_uuid}")
    return job_uuid


def get_latest_job(api: GradientAPI, kb_uuid: str) -> str:
    response = api.request("GET", f"/v2/gen-ai/knowledge_bases/{kb_uuid}/indexing_jobs", query={"per_page": 1})
    jobs = response.get("jobs") or response.get("data") or []
    if not jobs:
        raise GradientSyncError("No indexing jobs found for the knowledge base")
    return jobs[0].get("uuid")


def wait_for_job(api: GradientAPI, kb_uuid: str, job_uuid: str, poll_interval: int, timeout: int) -> Dict[str, Any]:
    print(f"⏳ Waiting for job {job_uuid} to finish...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        response = api.request("GET", f"/v2/gen-ai/knowledge_bases/{kb_uuid}/indexing_jobs/{job_uuid}")
        job = response.get("job") or {}
        status = job.get("status")
        phase = job.get("phase")
        print(f"   • status={status} phase={phase}")
        if status in COMPLETED_STATUSES:
            return job
        if status in FAILED_STATUSES:
            raise GradientSyncError(f"Indexing job {job_uuid} failed with status {status}")
        time.sleep(poll_interval)
    raise GradientSyncError(f"Timed out waiting for job {job_uuid}")


def fetch_signed_url(api: GradientAPI, job_uuid: str) -> str:
    response = api.request("GET", f"/v2/gen-ai/indexing_jobs/{job_uuid}/details:signed_url")
    signed_url = response.get("signed_url")
    if not signed_url:
        raise GradientSyncError("Signed URL missing from response")
    return signed_url


def download_report(url: str) -> bytes:
    try:
        with request.urlopen(url, timeout=120) as resp:
            return resp.read()
    except error.URLError as exc:
        raise GradientSyncError(f"Failed to download signed URL payload: {exc.reason}") from exc


def decode_payload(blob: bytes) -> Any:
    if blob.startswith(b"\x1f\x8b"):
        with gzip.GzipFile(fileobj=io.BytesIO(blob)) as gz:
            blob = gz.read()
    text = blob.decode("utf-8", errors="ignore")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        chunks = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                chunks.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if not chunks:
            raise GradientSyncError("Unable to parse job report payload")
        return chunks


def iter_chunks(payload: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(payload, list):
        for item in payload:
            yield from iter_chunks(item)
    elif isinstance(payload, dict):
        if "chunks" in payload and isinstance(payload["chunks"], list):
            for chunk in payload["chunks"]:
                if isinstance(chunk, dict):
                    yield chunk
        for key in ("data_source_jobs", "items", "records"):
            if isinstance(payload.get(key), list):
                for item in payload[key]:
                    yield from iter_chunks(item)
        # Some exports are already flat dicts with embedding/text fields
        if any(field in payload for field in ("embedding", "vector")):
            yield payload


def chunk_to_point(chunk: Dict[str, Any], kb_uuid: str) -> Optional[PointStruct]:
    vector = chunk.get("embedding") or chunk.get("vector") or chunk.get("values")
    if not vector:
        return None
    if not isinstance(vector, list):
        return None
    chunk_id = (
        chunk.get("chunk_uuid")
        or chunk.get("uuid")
        or chunk.get("id")
        or chunk.get("source_id")
    )
    if chunk_id is None:
        chunk_id = str(int(time.time() * 1000))
    payload = dict(chunk.get("metadata") or {})
    payload.setdefault("content", chunk.get("content") or chunk.get("text") or chunk.get("body") or "")
    payload.setdefault("data_source_uuid", chunk.get("data_source_uuid"))
    payload.setdefault("file_name", chunk.get("source_name") or chunk.get("file_name"))
    payload.setdefault("knowledge_base_uuid", kb_uuid)
    payload.setdefault("chunk_origin", "digitalocean-kb")
    return PointStruct(id=str(chunk_id), vector=vector, payload=payload)


def upsert_points(client: QdrantClient, collection: str, points: List[PointStruct], batch_size: int, dry_run: bool) -> None:
    if dry_run:
        print(f"🛈 Dry-run: would upsert {len(points)} points into '{collection}'")
        return
    for idx in range(0, len(points), batch_size):
        batch = points[idx: idx + batch_size]
        client.upsert(collection_name=collection, points=batch)
        print(f"   • upserted {idx + len(batch)}/{len(points)} points")


def persist_blob(path: Path, blob: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)
    print(f"💾 Saved raw export to {path}")


def main() -> int:
    args = parse_args()
    env_path = args.env_file if args.env_file.is_absolute() else REPO_ROOT / args.env_file
    manifest_path = args.manifest if args.manifest.is_absolute() else REPO_ROOT / args.manifest
    env_values = load_env_file(env_path)
    manifest = load_manifest(manifest_path)

    token = env_values.get("DIGITALOCEAN_TOKEN") or env_values.get("DIGITAL_OCEAN_PAT")
    if not token:
        raise GradientSyncError("Set DIGITALOCEAN_TOKEN or DIGITAL_OCEAN_PAT in the env file")
    base_url = env_values.get(GENAI_BASE_ENV, DEFAULT_GENAI_BASE)
    api = GradientAPI(token, base_url)

    kb_uuid = resolve_kb_uuid(args, env_values, manifest)
    collection = resolve_collection(args, env_values)

    job_uuid = args.job_uuid
    if args.start_job:
        job_uuid = trigger_indexing_job(api, kb_uuid)
    if not job_uuid:
        job_uuid = get_latest_job(api, kb_uuid)

    job = wait_for_job(api, kb_uuid, job_uuid, args.poll_interval, args.timeout)
    if not job.get("is_report_available", True):
        raise GradientSyncError("Indexing job report is not available yet")

    signed_url = fetch_signed_url(api, job_uuid)
    blob = download_report(signed_url)
    download_dir = args.download_dir if args.download_dir.is_absolute() else REPO_ROOT / args.download_dir
    persist_blob(download_dir / f"{job_uuid}.json", blob)

    payload = decode_payload(blob)
    points: List[PointStruct] = []
    for chunk in iter_chunks(payload):
        point = chunk_to_point(chunk, kb_uuid)
        if point:
            points.append(point)
    if not points:
        raise GradientSyncError("No chunks with embeddings found in the export")

    client = init_qdrant(env_values)
    ensure_collection(client, collection, env_values)
    upsert_points(client, collection, points, args.batch_size, args.dry_run)
    print(f"✅ Synced {len(points)} chunks from job {job_uuid} into collection '{collection}'.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except GradientSyncError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        raise SystemExit(1)