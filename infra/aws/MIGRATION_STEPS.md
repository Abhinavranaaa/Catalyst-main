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

## Architecture after cutover

```
Browser / Vercel
    → Cloudflare (X-App-Sec)
      → EC2:8080  catalyst-api  (Django)
            ├─ Cloud Tasks enqueue (GCP ADC via SA JSON)
            ├─ POST http://embed:8080/embed  (shared secret, docker network)
            ├─ Supabase / Upstash / Qdrant (unchanged)
            └─ Cloud Tasks callbacks → same public API URL
EC2 (same host)
    └─ catalyst-embed  (catalyst-services main.py)  NOT published publicly
GCP (kept)
    └─ Cloud Tasks queues + OIDC SA
```

## Auth map

| Hop | Mechanism |
|-----|-----------|
| Client → API | JWT cookies + Cloudflare `X-App-Sec` |
| Cloud Tasks → API | OIDC attached + `X-App-Sec` header (publishers send it) |
| API → embed (AWS) | `EMBED_AUTH_MODE=shared_secret` + `X-Embed-Secret` |
| API → embed (still on Cloud Run) | `EMBED_AUTH_MODE=google_id_token` (no EMBED_SERVICE_SECRET on embed) |
| API → Cloud Tasks API | GCP SA JSON (`GOOGLE_APPLICATION_CREDENTIALS`) |

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
git checkout aws-migration   # created for this work
```

### 1. One-time AWS bootstrap (ECR + EC2 IAM)

```bash
cd /Users/abhinavrana/Desktop/Catalyst-main
export AWS_REGION=ap-south-1          # pick your credit region
export AWS_ACCOUNT_ID=YOUR_12_DIGIT_ID
bash infra/aws/setup-ecr-ec2.sh
```

Creates:

- ECR repos `catalyst-main`, `catalyst-embed`
- Instance profile `catalyst-ec2-instance` (ECR pull + CloudWatch logs)

### 2. Launch EC2

Console or CLI:

| Setting | Value |
|---------|--------|
| AMI | Amazon Linux 2023 or Ubuntu 22.04 |
| Size | **t3.large** minimum (embed loads MiniLM; OOM risk on t3.small) |
| IAM | instance profile `catalyst-ec2-instance` |
| Storage | ≥ 30 GB |
| SG inbound | TCP **8080** from Cloudflare IP ranges (or 0.0.0.0/0 only while testing) |
| Elastic IP | yes |

SSH in, then:

```bash
# copy bootstrap from your laptop, or curl from a gist — then:
sudo AWS_REGION=ap-south-1 bash bootstrap.sh
sudo mkdir -p /opt/catalyst/secrets
sudo chmod 700 /opt/catalyst/secrets
```

Copy onto the host:

```bash
# from laptop
scp infra/aws/ec2/docker-compose.yml infra/aws/ec2/deploy.sh \
    ec2-user@EIP:/tmp/
scp path/to/gcp-tasks-sa.json ec2-user@EIP:/tmp/gcp-sa.json

# on host
sudo mv /tmp/docker-compose.yml /tmp/deploy.sh /opt/catalyst/
sudo mv /tmp/gcp-sa.json /opt/catalyst/secrets/gcp-sa.json
sudo chmod 600 /opt/catalyst/secrets/gcp-sa.json
sudo chmod +x /opt/catalyst/deploy.sh
```

### 3. GCP Cloud Tasks credentials

1. Keep existing queues + `TASKS_SA_EMAIL` (OIDC SA used in task payloads).
2. Use a SA key that can `cloudtasks.tasks.create` (and `iam.serviceAccounts.actAs` on the OIDC SA if required).
3. File on EC2: `/opt/catalyst/secrets/gcp-sa.json`.

### 4. Fill `/opt/catalyst/.env`

```bash
# from laptop
scp infra/aws/ec2/.env.example ec2-user@EIP:/tmp/.env.example
# on host: sudo cp /tmp/.env.example /opt/catalyst/.env && sudo nano /opt/catalyst/.env
```

Must set at least:

- `ECR_REGISTRY`, `AWS_REGION`
- All current Cloud Run env vars (DB, Redis, LLM, VAPID, Cloudflare secret, Google OAuth, queues, `PID`, **`US_CENTRAL1=us-central1`**)
- `EMBED_PROVIDER=s2s`
- `EMBED_AUTH_MODE=shared_secret`
- `EMBED_SERVICE_SECRET=<long random>` (same value used by embed container)
- `ROADMAP_PROCESS_URL` / `TASK_PROCESS_URL` → your public API paths
- `EXTRA_ALLOWED_HOSTS=<ec2-public-dns>` until DNS cutover
- `GOOGLE_REDIRECT_URI` still `https://api.catalystedutech.com/...` if domain unchanged

### 5. Build & push both images

**Option A — one script (recommended locally):**

```bash
cd /Users/abhinavrana/Desktop/Catalyst-main
export AWS_REGION=ap-south-1
export AWS_ACCOUNT_ID=YOUR_ID
export CATALYST_SERVICES_DIR=/Users/abhinavrana/catalyst-services
bash infra/aws/build-and-push-both.sh
```

**Option B — GitHub Actions on each repo:**

1. Catalyst-main → workflow **Deploy main to AWS ECR**
2. catalyst-services → workflow **Deploy embed to AWS ECR**  
   (add the same AWS_* + ECR_REGISTRY secrets to **both** GitHub repos)

### 6. Start the stack on EC2

```bash
cd /opt/catalyst
sudo ./deploy.sh
curl -fsS http://127.0.0.1:8080/health
# embed is internal; from host:
sudo docker exec catalyst-api python -c "import urllib.request; print(urllib.request.urlopen('http://embed:8080/health').read())"
```

Logs: CloudWatch log groups `/catalyst/ec2/api` and `/catalyst/ec2/embed`.

### 7. Smoke test before DNS cutover

1. Hit `http://EIP:8080/health` (temporarily open SG if needed).
2. From a shell with the API container env, enqueue a test roadmap job **or** call `/roadmap/task-be` with `X-App-Sec` manually.
3. Confirm embed: any session/roadmap path that embeds text (S2S latency logs appear).

### 8. Cut traffic over

1. Cloudflare DNS for `api.catalystedutech.com` → EC2 Elastic IP (proxied).
2. Confirm Cloud Tasks callback URLs already use that hostname (update GCP / `.env` if they still point at `*.run.app`).
3. Google OAuth: redirect URI already on `api.catalystedutech.com` — no change if domain unchanged.
4. Watch CloudWatch + a live roadmap generation + login.

### 9. Decommission GCP compute (after soak)

1. Scale Cloud Run `catalyst-main` to 0 / delete when stable.
2. Scale Cloud Run `embed-api` to 0 / delete when stable.
3. **Keep** Cloud Tasks queues/project until a later SQS migration.
4. Leave Supabase, Upstash, Qdrant, Vercel alone.

---

## Local dev (optional)

Do **not** call the remote embed service if you want zero cost/latency:

```bash
# in servers/catalyst/.env
EMBED_PROVIDER=hf
HF_TOKEN=...
```

Production / EC2 always uses:

```bash
EMBED_PROVIDER=s2s
EMBED_AUTH_MODE=shared_secret   # on AWS
# or omit AUTH_MODE + SECRET and use google_id_token while embed still on Cloud Run
```

## Files touched (summary)

### Catalyst-main (`aws-migration`)

- `catalyst/adapters/embed.py` — multi-mode auth; parse `{embeddings: [...]}`
- `catalyst/ai_resources.py` — default `s2s`; `hf` local-only
- Cloud Tasks publishers — send `X-App-Sec`
- `EXTRA_ALLOWED_HOSTS` in settings
- `infra/aws/**` — ECR/EC2 bootstrap, compose, deploy, build-both script
- `servers/embed/README.md` — points at catalyst-services (no stub)

### catalyst-services (`aws-migration`)

- `main.py` — optional `EMBED_SERVICE_SECRET` / `X-Embed-Secret`
- `Dockerfile` + `requirements.embed.txt` + `.dockerignore` (excludes 2.5G `lufc/`)
- `.github/workflows/deploy-aws.yml` — push `catalyst-embed`
- `AWS.md` — short notes
- `cloudbuild.yaml` — still deploys Cloud Run `embed-api` until you tear it down
