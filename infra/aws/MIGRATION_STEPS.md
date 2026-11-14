# Hybrid migration: AWS EC2 compute + GCP Cloud Tasks
#
# Repos involved
#   1. Catalyst-main  (this repo) — Django API → ECR catalyst-main
#   2. catalyst-services          — FastAPI /embed → ECR catalyst-embed
#      Path on your machine: /Users/abhinavrana/catalyst-services
#
# Out of scope for this phase
#   - Celery worker/beat (unused; Cloud Tasks does scheduling)
#   - Moving queues/auth/DB to AWS
#   - Bedrock (AISPL payment / Sales allowlist — deferred)

## Phases (do in order — stop after each)

| Phase | Scope | Status |
|-------|--------|--------|
| **A** | HTTPS on EC2 (Caddy). No DNS/Cloudflare/OAuth changes. | **in progress** |
| **B** | How Google OAuth works today + what EC2 must provide | later |
| **C** | DNS → EIP + Cloudflare SSL policies + OAuth cutover | later |

### Already done (before Phase A)

| Item | Notes |
|------|--------|
| ECR + EC2 host | `t3.xlarge`, Elastic IP `32.192.150.124`, us-east-1 |
| API + embed on compose | Always-on; S2S `http://embed:8080` + shared secret |
| Env / logs split | `/opt/catalyst/api.env`, `embed.env`, CloudWatch groups |
| GCP SA JSON on host | `/opt/catalyst/secrets/gcp-sa.json` |
| Auth smoke over HTTP | Bearer works; cookie needs HTTPS |
| `main` → `aws-migration` | Bookmarks, payments, solved-sessions |

### Phase A — TLS only (now): HTTPS on the Elastic IP

Goal: Insomnia uses `https://32.192.150.124`, TLS terminates on Caddy, login sets `jwt` cookie, later requests send it automatically. **No DNS / Cloudflare change.**

1. Open SG inbound **443**.
2. Copy `docker-compose.yml`, `deploy.sh`, `Caddyfile`, `Caddyfile.internal` to `/opt/catalyst/`.
3. In `/opt/catalyst/.env` set only `CADDYFILE=Caddyfile.internal` (keep existing `ECR_REGISTRY` / `AWS_REGION`).
4. `sudo ./deploy.sh` — public HTTPS on `:443`; API stays on loopback `:8080`.

Verify:

```bash
curl -fsSk https://32.192.150.124/health
```

Insomnia: base URL `https://32.192.150.124`, **SSL validation OFF**, enable cookie jar. Login once → `Set-Cookie: jwt=...; Secure` → later calls reuse the cookie (no Bearer).

Cert is self-signed (Let's Encrypt does not issue for bare IPs). After DNS cutover you switch to `CADDYFILE=Caddyfile` and use `https://api.catalystedutech.com`.

### Later (Phase B / C) — do not start yet

- OAuth flow walkthrough + `GOOGLE_REDIRECT_URI`
- DNS A `api` → EIP, Cloudflare SSL **Full**, switch `CADDYFILE=Caddyfile`
- Decommission Cloud Run
- Bedrock / SQS (deferred)

---

## Architecture after cutover

```
Browser / Vercel / Google OAuth redirect
    → https://api.catalystedutech.com
      → Cloudflare proxy (orange cloud, X-App-Sec)
        → A record = EC2 Elastic IP only
          → Caddy :443 (Let's Encrypt) → api:8080
                ├─ Cloud Tasks enqueue (GCP ADC via SA JSON)
                ├─ POST http://embed:8080/embed  (shared secret, docker network)
                ├─ Supabase / Upstash / Qdrant (unchanged)
                └─ Cloud Tasks callbacks → https://api.catalystedutech.com/...
EC2 (same host)
    └─ catalyst-embed  (not published publicly)
GCP (kept)
    └─ Cloud Tasks queues + OIDC SA
Google Cloud Console (P0)
    └─ OAuth redirect URI = https://api.catalystedutech.com/api/auth/google/callback
       (remove every *.run.app redirect before decommission)
```

## Auth map

| Hop | Mechanism |
|-----|-----------|
| Client → API | JWT **cookie** over HTTPS (`Secure; SameSite=None`) + Cloudflare `X-App-Sec` |
| Tooling over HTTP EIP | `Authorization: Bearer <jwt>` fallback (do not send stale `jwt` cookie) |
| Cloud Tasks → API | OIDC + `X-App-Sec` |
| API → embed (AWS) | `EMBED_AUTH_MODE=shared_secret` + `X-Embed-Secret` |
| API → Cloud Tasks | GCP SA JSON (`GOOGLE_APPLICATION_CREDENTIALS`) |

## Prerequisites

- AWS account with credits; CLI configured (`aws sts get-caller-identity`)
- Docker locally (to build/push) or GitHub Actions secrets set on **both** repos
- GCP SA JSON that can create tasks on your existing queues
- Sibling checkout: `Desktop/Catalyst-main` and `catalyst-services` (or set `CATALYST_SERVICES_DIR`)

---

## Step-by-step (execute in order)

### 0. Branches

```bash
# Catalyst-main — already on aws-migration
cd /Users/abhinavrana/Desktop/Catalyst-main

# catalyst-services
cd /Users/abhinavrana/catalyst-services
git checkout aws-migration
```

### 1. One-time AWS bootstrap (ECR + EC2 IAM)

```bash
cd /Users/abhinavrana/Desktop/Catalyst-main
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=YOUR_12_DIGIT_ID
bash infra/aws/setup-ecr-ec2.sh
```

### 2. Launch EC2

| Setting | Value |
|---------|--------|
| Size | **t3.xlarge** (current) / t3.large minimum |
| IAM | `catalyst-ec2-instance` |
| Storage | ≥ 30 GB |
| SG inbound | TCP **80** + **443** (ACME + HTTPS). Temporarily **8080** only for pre-TLS smoke. After Caddy: close public 8080. |
| Elastic IP | **required** — DNS points only here |

```bash
sudo mkdir -p /opt/catalyst/secrets
sudo chmod 700 /opt/catalyst/secrets
```

Copy onto the host:

```bash
# from laptop
scp infra/aws/ec2/docker-compose.yml infra/aws/ec2/deploy.sh \
    infra/aws/ec2/Caddyfile \
    ec2-user@EIP:/tmp/
scp path/to/gcp-tasks-sa.json ec2-user@EIP:/tmp/gcp-sa.json

# on host
sudo mv /tmp/docker-compose.yml /tmp/deploy.sh /tmp/Caddyfile /opt/catalyst/
sudo mv /tmp/gcp-sa.json /opt/catalyst/secrets/gcp-sa.json
sudo chmod 600 /opt/catalyst/secrets/gcp-sa.json
sudo chmod +x /opt/catalyst/deploy.sh
```

### 3. GCP Cloud Tasks credentials

1. Keep existing queues + `TASKS_SA_EMAIL`.
2. SA key with `cloudtasks.tasks.create` (+ `actAs` on OIDC SA if required).
3. File: `/opt/catalyst/secrets/gcp-sa.json` (**done** on current host).

### 4. Fill host env files

Three files under `/opt/catalyst/`:

| File | Purpose |
|------|---------|
| `.env` | Compose only: `AWS_REGION`, `ECR_REGISTRY`, `IMAGE_TAG`, `API_HOSTNAME`, `ACME_EMAIL` |
| `api.env` | Django: DB, Redis, LLM, OAuth, queues, `CLOUDFLARE_SHIELD_SECRET`, embed secret |
| `embed.env` | Embed-only: `EMBED_SERVICE_SECRET`, model, threads |

```bash
scp infra/aws/ec2/.env.example infra/aws/ec2/api.env.example \
    infra/aws/ec2/embed.env.example \
    ec2-user@EIP:/tmp/
# on host: copy to /opt/catalyst/{.env,api.env,embed.env} and fill values
```

Must set at least:

- `.env`: `ECR_REGISTRY`, `AWS_REGION`, `API_HOSTNAME=api.catalystedutech.com`, `ACME_EMAIL`
- `api.env`: DB/Redis/LLM/VAPID/Cloudflare/Google OAuth/queues/`PID`/`US_CENTRAL1`
- `EMBED_PROVIDER=s2s`, `EMBED_AUTH_MODE=shared_secret`, matching `EMBED_SERVICE_SECRET` in api + embed
- `ROADMAP_PROCESS_URL` / `TASK_PROCESS_URL` → `https://api.catalystedutech.com/...`
- `GOOGLE_REDIRECT_URI=https://api.catalystedutech.com/api/auth/google/callback`

### 5. Build & push both images

```bash
cd /Users/abhinavrana/Desktop/Catalyst-main
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=YOUR_ID
export CATALYST_SERVICES_DIR=/Users/abhinavrana/catalyst-services
bash infra/aws/build-and-push-both.sh
```

Or GitHub Actions on each repo (same AWS secrets on both).

### 6. Start / refresh stack on EC2 (TLS)

```bash
cd /opt/catalyst
sudo ./deploy.sh
curl -fsS http://127.0.0.1:8080/health
# After DNS → EIP:
curl -fsS https://api.catalystedutech.com/health
```

Public listeners: Caddy **80** (ACME + redirect) and **443**. API is bound to `127.0.0.1:8080` only.

Logs: CloudWatch `/catalyst/ec2/{caddy,api,embed}`.

### 7. Smoke test before / during DNS

1. Local health: `http://127.0.0.1:8080/health`
2. After DNS: `https://api.catalystedutech.com/health` with `X-APP-SEC`
3. Login over HTTPS — Insomnia should store/send `jwt` cookie (`Secure`)
4. Roadmap enqueue / embed S2S path

### 8. P0 cutover — DNS, TLS, Cloudflare, Google OAuth

#### 8a. DNS + SG

1. Cloudflare DNS **A** `api` → Elastic IP `32.192.150.124`
2. For first Let's Encrypt issue: **grey-cloud** briefly (or orange-cloud with HTTP allowed to origin). After cert exists, orange-cloud again.
3. SG: allow **80** + **443**. Close public **8080**.

#### 8b. Cloudflare SSL

| Mode | Use when |
|------|----------|
| **Full** | Origin Caddy has a real cert (current compose) — **preferred** |
| Flexible | Only if origin is plain HTTP (legacy). Do **not** use once Caddy is up |

Confirm `X-App-Sec` worker still runs. Bypass cache for `/api/*`, `/roadmap/*`, `/events/*`.

#### 8c. Google OAuth — moves login off Cloud Run cold starts

1. Google Cloud Console → OAuth client → Authorized redirect URIs:

   `https://api.catalystedutech.com/api/auth/google/callback`

2. **Delete** every `*.run.app` redirect URI.
3. On host:

   ```bash
   grep GOOGLE_REDIRECT_URI /opt/catalyst/api.env
   # GOOGLE_REDIRECT_URI=https://api.catalystedutech.com/api/auth/google/callback
   ```

4. Smoke: frontend Google login → callback on `api.catalystedutech.com` → `FRONTEND_HOME` with `jwt` cookie. No `*.run.app` bounce.

#### 8d. Confirm callbacks

1. Cloud Tasks URLs in `api.env` use `https://api.catalystedutech.com/...`
2. One roadmap generation → callback in EC2 CloudWatch, not Cloud Run
3. Cookie login works in Insomnia against `https://api.catalystedutech.com` (no Bearer required)

### 9. Decommission GCP compute (after soak)

Do **not** scale Cloud Run to 0 until **8c** Google login succeeds on EC2.

1. Scale Cloud Run `catalyst-main` to 0 / delete
2. Scale Cloud Run `embed-api` to 0 / delete
3. Keep Cloud Tasks until a later SQS migration
4. Leave Supabase, Upstash, Qdrant, Vercel alone

---

## Why EIP HTTP broke cookies

Login sets `Set-Cookie: jwt=...; Secure; SameSite=None; HttpOnly`.
Clients only persist/send that cookie on **HTTPS**. GCP Cloud Run was HTTPS; bare `http://EIP` is not. Bearer was only a tooling fallback. Caddy + `api.catalystedutech.com` restores cookie auth.

---

## Local dev (optional)

```bash
# servers/catalyst/.env
EMBED_PROVIDER=hf
HF_TOKEN=...
```

Production / EC2:

```bash
EMBED_PROVIDER=s2s
EMBED_AUTH_MODE=shared_secret
```

## Files touched (summary)

### Catalyst-main (`aws-migration`)

- `infra/aws/ec2/Caddyfile` — TLS terminator
- `infra/aws/ec2/docker-compose.yml` — caddy + api + embed; API on loopback 8080
- `infra/aws/ec2/{.env,api.env,embed.env}.example`
- `infra/aws/ec2/deploy.sh` — TLS health probe
- Embed adapter / Cloud Tasks `X-App-Sec` / `EXTRA_ALLOWED_HOSTS`

### catalyst-services (`aws-migration`)

- Shared-secret embed auth, ECR deploy workflow, Dockerfile
