# Deploy

Two supported paths:
- **Portainer + GHCR (CI/CD)** — GitHub Actions builds the image and pushes it to
  GHCR; Portainer pulls it. See the next section.
- **Caddy compose (single VM, auto-HTTPS on a domain)** — see
  "discrepancy.inventivebizsol.co.in" further down.

## Portainer via GHCR (GitHub Actions)

On every push to `main`, [`.github/workflows/build.yml`](../../.github/workflows/build.yml)
builds `app/Dockerfile` and pushes `ghcr.io/<owner>/<repo>` with tags `latest` and the
short commit sha. No secrets to configure — it uses the built-in `GITHUB_TOKEN`.

1. **Push the repo** to GitHub. The workflow runs automatically; watch it under the
   repo's **Actions** tab (first run compiles LibreDWG — a few minutes).
2. **Make the image pullable by Portainer.** The GHCR package is private by default:
   - make it public (repo → **Packages** → the package → **Package settings** →
     **Change visibility → Public**), **or**
   - in Portainer add a registry (**Registries → Add → Custom**): URL `ghcr.io`,
     username = your GitHub user, password = a PAT with `read:packages`.
3. **Create the stack** in Portainer (**Stacks → Add stack**), paste
   [`portainer-stack.yml`](portainer-stack.yml), set the image to your
   `ghcr.io/<owner>/<repo>:latest`, and deploy.
4. **Update after a code change:** push to `main` → Actions rebuilds → in Portainer
   open the stack → **Update** with **Re-pull image** enabled (or pin a sha tag).

Health check once up: `curl -fsS http://<host>:8000/health` →
`{"ok":true,"dwg2dxf":true,"master_count":909}`.

---

# discrepancy.inventivebizsol.co.in (Caddy compose)

Runs the app behind **Caddy**, which terminates TLS and auto-issues a Let's Encrypt
certificate for the domain. No manual cert handling.

```
Internet ──443──> Caddy (reverse proxy, auto-HTTPS) ──8000──> app (uvicorn/FastAPI)
```

## Prerequisites on the VM
- Docker + Docker Compose v2 (`docker compose version`).
- Ports **80 and 443** open to the internet (security group / `ufw allow 80,443/tcp`).
  Caddy needs port 80 reachable for the ACME HTTP challenge.

## 1. Point DNS at the VM
Create an **A record** (and AAAA if you have IPv6):

```
discrepancy.inventivebizsol.co.in.  A  <VM_PUBLIC_IP>
```

Verify it has propagated before deploying (cert issuance fails otherwise):

```bash
dig +short discrepancy.inventivebizsol.co.in   # must return the VM IP
```

## 2. Deploy
Copy the repo to the VM, then from this `deploy/` directory:

```bash
docker compose up -d --build
```

First boot compiles LibreDWG (a few minutes — see the root Dockerfile), then Caddy
fetches the TLS cert. Watch it:

```bash
docker compose logs -f caddy   # look for "certificate obtained successfully"
docker compose logs -f app
```

Then open **https://discrepancy.inventivebizsol.co.in**.

## 3. Health check
```bash
curl -fsS https://discrepancy.inventivebizsol.co.in/health
# {"ok":true,"dwg2dxf":true}   <- dwg2dxf:true means the converter is on PATH
```

## Updating after a code change
```bash
git pull                       # or re-copy the files
docker compose up -d --build   # rebuilds app, leaves Caddy + certs untouched
```

## Operations
- **Logs:** `docker compose logs -f app`
- **Restart:** `docker compose restart app`
- **Stop:** `docker compose down` (TLS certs survive in the `caddy_data` volume — never `down -v`)
- **Cert location:** persisted in the `caddy_data` Docker volume. Deleting that volume forces re-issuance and risks Let's Encrypt rate limits.

## Notes / hardening
- Upload size is capped at 200 MB in `Caddyfile` (`request_body max_size`). Raise it
  there if your DWGs are larger.
- CORS is currently wide-open (`allow_origins=["*"]` in `backend/app.py`). Since the UI
  is served from the same origin, you can tighten it to the domain for production.
- No auth is configured. If this should not be world-readable, put Caddy
  `basic_auth` (or your SSO proxy) in front — ask and I'll wire it in.
- Local testing without DNS/TLS: `docker build -t dwg-discrepancy .. && docker run -p 8000:8000 dwg-discrepancy` then hit http://localhost:8000.
