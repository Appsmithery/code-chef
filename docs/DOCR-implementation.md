# **DOCR Implementation Plan**

**High-level approach**

1. Summarize how DOCR would streamline our current Docker Compose / DOKS deployment loop.
2. Highlight the relevant DO guidance (login, Kubernetes secrets, CI/CD).
3. Lay out an automated, stepwise rollout plan that ties into our repo and GitHub Actions.

## recommendation

- **Why DOCR helps**: Every service under docker-compose.yml currently builds locally from `containers/*`. Pushing those artifacts to DigitalOcean Container Registry (DOCR) centralizes images, avoids reprovisioning build tooling on droplets, gives DOKS clusters a fast pull target, and lets CI/CD gate deployments on signed artifacts instead of source. DO’s docs confirm we can authenticate either via `doctl registry login` (issues short-lived credentials) or a Docker `config.json`, and the control panel can fan that secret across every namespace in a DOKS cluster automatically, so runtime pulls become trivial.
- **Security & governance**: The `docker-config.json` you attached can be stored as an encrypted secret (GitHub, Actions, or Kubernetes) and lets us create `kubernetes.io/dockerconfigjson` secrets exactly as described in the DO guide. DOCR also supports read/write or read-only password scopes, so we can grant CI the minimum needed.
- **Deployment velocity**: Once images are in DOCR, GitHub Actions (or another CI) can follow DO’s push-to-deploy tutorial: build image → `doctl registry login --expiry-seconds …` → push → update manifests → `doctl kubernetes cluster kubeconfig save --expiry-seconds …` → `kubectl apply`. That removes manual SSH builds from the path to production and lines up with the “last step before deployment” goal.

Net: yes, adopt DOCR now. It reduces the gap between local Compose and cloud deploys, keeps secrets managed, and makes agent rollouts reproducible.

## stepwise implementation plan

1. **Name images & tags**

   - Pick a consistent naming scheme such as `registry.digitalocean.com/the-shop/<service>:<git-sha>` for every Dockerfile in `containers/*`.
   - Update docker-compose.yml `build` blocks to include `image:` entries that follow this naming convention; Compose will tag them automatically when building.

2. **Bootstrap registry auth for humans**

   - Install `doctl` (if not already) and run:
     ```powershell
     doctl registry login
     ```
     This writes the same credentials found in `docker-config.json` and keeps local Docker ready for pushes/pulls (per DO doc).
   - **Fallback when `doctl` fails**: DigitalOcean also supports the plain Docker login flow. Run:
     ```powershell
     docker login registry.digitalocean.com
     ```
     Supply the DO account username (e.g., `alex@appsmithery.co`) and a DO API token/PAT when prompted. Docker caches these credentials in the current user’s credential store, so subsequent `docker compose push` executions succeed even if `doctl` cannot validate the token.

3. **Create Kubernetes pull secret once**

   - Either click “Add secret to all namespaces” in the DO control panel (recommended) or run:
     ```bash
     doctl registry kubernetes-manifest | kubectl apply -f -
     ```
   - This matches the doc flow where DOKS copies the secret into every namespace and updates the default service account.

4. **Store credentials for automation**

   - Add `DIGITALOCEAN_ACCESS_TOKEN`, `REGISTRY_NAME`, `CLUSTER_NAME`, and the Base64 content of `docker-config.json` as GitHub Actions secrets.
   - Optionally keep the full `docker-config.json` in the-shop for local scripts but never commit it.

5. **Author CI workflow to build & push**

   - Create `.github/workflows/docr-build.yml` with one job that:
     1. Checks out the repo.
     2. Uses `digitalocean/action-doctl@v2` with `${{ secrets.DIGITALOCEAN_ACCESS_TOKEN }}`.
     3. Runs `docker build` for each agent (use a build matrix to parallelize).
     4. Tags as `registry.digitalocean.com/${{ secrets.REGISTRY_NAME }}/<service>:${GITHUB_SHA}`.
     5. Calls `doctl registry login --expiry-seconds 1200`.
     6. Pushes each tag.

6. **Gate deployments on pushed images**

   - Extend the workflow (or add a second) that, after a successful push on `main`, updates Kubernetes manifests (or Helm chart) to the new tag and applies them using short-lived kubeconfig credentials (`doctl kubernetes cluster kubeconfig save --expiry-seconds 600 …`).
   - For droplet-based deployments, have the remote host run `docker compose pull && docker compose up -d` so it consumes the freshly pushed DOCR images.

7. **Wire Compose/Helm to DOCR**

   - Replace local-only image references in docker-compose.yml, Helm charts, or Taskfiles with the DOCR-based name so every environment (dev, staging, prod) pulls from the registry instead of building in-place.

8. **Add image retention & GC**

   - Enable DOCR’s built-in garbage collection or schedule `doctl registry garbage-collection start` to avoid hitting registry limits, per DO documentation warning about read-only windows.

9. **Instrument pipeline status**

   - Emit build metadata (image tag, digest, workflow run) back to Langfuse/Prometheus or store in reports so the orchestrator agent knows which image is live.

10. **Document and train**
    - Update DEPLOYMENT.md with the new push workflow, credential rotation steps, and the exact GitHub Action. Include the `docker login` fallback from the docs for air-gapped builders.

Following those steps gives us a reproducible supply chain: developers build locally when needed, CI always publishes authoritative images to DOCR, and clusters (or droplets) simply pull tagged artifacts. From there we can add policy enforcement (e.g., tag signing or vulnerability scanning) without changing our deployment ergonomics.
