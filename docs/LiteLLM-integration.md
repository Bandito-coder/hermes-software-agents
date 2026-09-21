# LiteLLM Integration — AgentBuilder Cost Tracking & Model Routing

**Date:** 2026-09-21 (AEST)
**Status:** ✅ Active and running

---

## Overview

LiteLLM acts as a proxy between Hermes Agent and model providers (OpenRouter, local Ollama). It provides:

- **Actual cost tracking** per request (not estimated from logs)
- **Hard budget enforcement** per agent key (blocks requests when exceeded)
- **Centralized model routing** with automatic fallback chains
- **Per-RUN-ID tracking** via metadata tags
- **Built-in dashboard** at http://localhost:4000/ui
- **Spend reports** via REST API

## Current State

| Component | Status | Details |
|---|---|---|
| LiteLLM Proxy | ✅ Healthy | Port 4000, 3 OpenRouter models active |
| Postgres DB | ✅ Healthy | Port 5432 (internal), persistent volume |
| Auto-start | ✅ Configured | `restart: unless-stopped` on both containers |
| Health check | ✅ Active | Cron every 5min, auto-restart, alerts all channels |
| Cost tracking | ✅ Working | 10 entries, $0.000135 tracked so far |
| Dashboard | ✅ Available | http://localhost:4000/ui |

## Architecture

```
Hermes Agent (hub)
    │
    ▼
LiteLLM Proxy (localhost:4000)
    │
    ├──→ OpenRouter (cloud models)
    │    ├── workhorse: deepseek-v4-flash-0731 ($0.04/$0.16/1M)
    │    ├── coding: deepseek-v4.1-flash ($0.12/$0.48/1M)
    │    └── reasoning: mimo-v2.5-pro ($0.30/$0.61/1M)
    │
    └──→ Ollama (192.168.0.58:11434, local models, free)
         └── local: gemma4-hermes:latest

Postgres DB (litellm-postgres:5432)
    └── LiteLLM_SpendLogs — every request logged with actual $
```

## Files

| File | Purpose |
|---|---|
| `/apps/hermes-docker/litellm/docker-compose.yml` | Container definitions |
| `/apps/hermes-docker/litellm/litellm_config.yaml` | Model routing + budget config |
| `/apps/hermes-docker/litellm/.env` | Secrets (DB password, master key, OpenRouter key) |
| `/apps/hermes/.hermes/scripts/litellm-health.sh` | Health check script |

## Model Routing

| Alias | Model | Use Case | Cost |
|---|---|---|---|
| `local` | Ollama gemma4-hermes | Mechanical tasks, free | $0 |
| `workhorse` | deepseek-v4-flash-0731 | Default agent work | $0.04/$0.16/1M |
| `coding` | deepseek-v4.1-flash | Builder, Test Author, Fixer, Reviewer | $0.12/$0.48/1M |
| `reasoning` | mimo-v2.5-pro | Architect, SecOps | $0.30/$0.61/1M |

**Fallback chain:** workhorse → local, coding → workhorse

## Health Monitoring

**Cron job:** `litellm-health-check` (every 5 minutes)
- Silent when healthy
- Auto-restarts container if down
- Alerts via all channels (Telegram, Discord, WebUI) if restart fails

**Manual check:**
```bash
curl http://localhost:4000/health/liveness
# → "I'm alive!"
```

## Operations

### Start/Stop/Restart
```bash
cd /apps/hermes-docker/litellm
docker compose up -d      # Start
docker compose down        # Stop
docker compose restart     # Restart
docker compose logs -f     # View logs
```

### View Spend
```bash
MASTER_KEY=$(grep LITELLM_MASTER_KEY .env | cut -d= -f2)
curl -s http://localhost:4000/spend/logs -H "Authorization: Bearer $MASTER_KEY"
```

### View Dashboard
Open http://localhost:4000/ui in browser (login with master key)

## Next Steps (Optional)

1. **Update Hermes config** to route through LiteLLM (change `base_url` to `http://localhost:4000/v1`)
2. **Create virtual keys** per agent for per-agent budget caps
3. **Update Cost Sentinel/Analyst** skills to query LiteLLM API instead of scraping logs
4. **Set up per-agent budgets** once virtual keys are created
