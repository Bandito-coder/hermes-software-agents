# Setup Guide — Hermes Agentic SDLC Platform

**Audience:** You (the operator). Manual prerequisites and from-scratch rebuild procedures.
**Last updated:** 2026-09-21 (AEST)

---

## Prerequisites

### Hardware Requirements

| Resource | Minimum | Recommended | Current |
|---|---|---|---|
| CPU | 4 cores | 6+ cores | AMD Ryzen 5 5600, 4 cores |
| RAM | 4 GB | 8 GB | 7.7 GB |
| Root disk | 30 GB | 50+ GB | 31 GB |
| Network | LAN + internet | LAN + internet | Available |

### Software Requirements (Pre-installed)

All of these are already installed on the current system:

| Component | Version | Location |
|---|---|---|
| Linux | Ubuntu 24.04, kernel 7.0 | System |
| Docker | 29.8.1 | System |
| Git | 2.43.0 | System |
| Python | 3.11.15 | System |
| Node.js | 18.19.1 | System |
| uv | 0.11.24 | System |
| Hermes Agent | v0.20.6 | /apps/hermes/hermes-agent |
| OpenCode | 1.18.30 | System |
| GitHub CLI (gh) | 2.78.0 | ~/bin/gh |

---

## Manual Setup Steps (Agent Cannot Do)

These require your direct action — the agent cannot create accounts or generate tokens.

### 1. GitHub Personal Access Token

**What:** A token for the `gh` CLI to create repos, PRs, and manage issues.
**Scopes:** `repo`, `delete_repo`, `read:org`

1. Go to https://github.com/settings/tokens
2. "Generate new token (classic)"
3. Note: `hermes-agent` (or any name)
4. Check: `repo`, `delete_repo`, `read:org`
5. Expiration: 90 days (renewable)
6. Generate, copy the `ghp_...` token
7. Authenticate: `echo "ghp_..." | ~/bin/gh auth login --with-token`
8. Verify: `~/bin/gh auth status`

### 2. OpenRouter API Key

**What:** API key for cloud LLM models (DeepSeek, etc.).
**Status:** Already configured at `/apps/hermes/.hermes/.env`

If you need to regenerate:
1. Go to https://openrouter.ai/keys
2. Create a new key
3. Add to `/apps/hermes/.hermes/.env`: `OPENROUTER_API_KEY=sk-or-...`

### 3. Telegram Bot Token (if using Telegram)

**Status:** Already configured.

If you need to create a new one:
1. Message @BotFather on Telegram
2. `/newbot` → follow prompts
3. Copy the token
4. Add to `/apps/hermes/.hermes/.env`: `TELEGRAM_BOT_TOKEN=...`

### 4. Discord Bot Token (if using Discord)

**Status:** Already configured.

If you need to create a new one:
1. Go to https://discord.com/developers/applications
2. Create application → Bot → Reset Token
3. Copy the token
4. Add to `/apps/hermes/.hermes/.env`: `DISCORD_BOT_TOKEN=...`

### 5. GitHub Repository Webhooks

For each repo you want the agent to monitor:

1. Go to your repo on GitHub → Settings → Webhooks → Add webhook
2. **Payload URL:** `http://<your-server-ip>:8644/webhooks/github-issues`
3. **Content type:** `application/json`
4. **Secret:** (from `hermes webhook list` — shows the secret for each subscription)
5. **Events:** Select "Issues" (for the issues webhook) or "Pull requests" (for the PRs webhook)
6. Save

Repeat for the PRs webhook with URL `http://<your-server-ip>:8644/webhooks/github-prs`.

**Note:** Your server must be reachable from GitHub's webhook servers. If behind NAT/firewall, use a tunnel (ngrok, cloudflared) or configure port forwarding for port 8644.

### 6. Proxmox VM Setup (for from-scratch rebuild)

If rebuilding from scratch on a new VM:

1. Create VM on Proxmox (PVE01 dev or PVE02 prod)
2. Install Ubuntu 24.04 Server
3. Allocate: 4+ CPU cores, 8 GB RAM, 50 GB disk
4. Install Docker: `curl -fsSL https://get.docker.com | sh`
5. Install Node.js: `curl -fsSL https://deb.nodesource.com/setup_18.x | bash && apt install nodejs`
6. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
7. Install Hermes: `curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`
8. Run `hermes setup` to configure API keys
9. Follow this Setup Guide from Step 1

---

## One-Time Configuration (Agent-Driven)

These steps were completed during the build. Listed here for rebuild reference.

```bash
# Enable webhook platform
hermes config set platforms.webhook.enabled true
hermes config set platforms.webhook.extra.port 8644
hermes config set platforms.webhook.extra.secret "$(openssl rand -hex 32)"

# Initialize Kanban
hermes kanban init
hermes config set kanban.default_assignee default

# Enable checkpoints
hermes config set checkpoints.enabled true

# Set delegation limits
hermes config set delegation.max_concurrent_children 3

# Install Superpowers plugin for OpenCode
# (already configured in ~/.config/opencode/opencode.jsonc)
# Plugin: superpowers@git+https://github.com/obra/superpowers.git

# Install GitHub CLI
mkdir -p ~/bin
curl -sL https://github.com/cli/cli/releases/download/v2.78.0/gh_2.78.0_linux_amd64.tar.gz -o /tmp/gh.tar.gz
tar -xzf /tmp/gh.tar.gz -C /tmp/
cp /tmp/gh_2.78.0_linux_amd64/bin/gh ~/bin/gh
chmod +x ~/bin/gh
export PATH="$HOME/bin:$PATH"

# Authenticate GitHub CLI
echo "<your-token>" | gh auth login --with-token

# Restart gateway to pick up webhook config
privgate systemctl-hermes root restart hermes-gateway
```

---

## Verification Checklist

After setup, verify each component:

```bash
# Gateway running
privgate service-status root hermes-gateway

# Webhook platform healthy
curl http://localhost:8644/health

# Kanban operational
hermes kanban stats

# GitHub CLI authenticated
~/bin/gh auth status

# OpenCode + Superpowers working
opencode run --model litellm/workhorse "List your skills"

# Ollama accessible
curl http://192.168.0.58:11434/api/tags

# Cron jobs active
hermes cron list
```

---

## Quick Start (From Scratch)

Complete sequence from bare VM to operational system:

1. Create VM, install Ubuntu 24.04
2. Install Docker, Node.js, uv
3. Install Hermes (`curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`)
4. Run `hermes setup` — configure OpenRouter API key
5. Generate GitHub PAT (scopes: repo, delete_repo, read:org)
6. Authenticate gh CLI
7. Run the AgentBuilder implementation plan (Phases 0-8)
8. Configure GitHub webhooks on your repos
9. Start working — create your first project via chat or kanban card
