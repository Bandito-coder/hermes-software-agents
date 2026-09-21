# Configuration Reference — Hermes Agentic SDLC Platform

**Audience:** Reference document for the as-built system configuration.
**Last updated:** 2026-09-21 (AEST)
**Source:** Captured from live system via `hermes config show` and `config.yaml`.

---

## System Overview

| Component | Value |
|---|---|
| **Hermes Agent** | v0.20.6 (2026.8.27) |
| **OpenCode** | 1.18.30 |
| **GitHub CLI** | 2.78.0 |
| **Python** | 3.11.15 |
| **Node.js** | 18.19.1 |
| **Docker** | 29.8.1 |
| **OS** | Ubuntu 24.04, kernel 7.0 |
| **CPU** | AMD Ryzen 5 5600, 4 cores |
| **RAM** | 7.7 GB |
| **Root disk** | 31 GB |

---

## Paths

| Path | Purpose |
|---|---|
| `/apps/hermes/.hermes/config.yaml` | Main configuration |
| `/apps/hermes/.hermes/.env` | API keys and secrets |
| `/apps/hermes/hermes-agent/` | Hermes source code |
| `/apps/hermes/.hermes/skills/` | Installed skills |
| `/apps/hermes/.hermes/kanban.db` | Kanban board database |
| `/apps/hermes/.hermes/webhook_subscriptions.json` | Webhook routes |
| `/apps/hermes/.hermes/logs/` | Gateway and worker logs |
| `/apps/hermes/.hermes/sessions/` | Conversation transcripts |
| `~/.config/opencode/opencode.jsonc` | OpenCode configuration |
| `~/.local/share/opencode/auth.json` | OpenCode API keys |
| `~/bin/gh` | GitHub CLI binary |

---

## Model Configuration

**Primary model:** `deepseek/deepseek-v4-flash-0731` via OpenRouter
**Local fallback:** `gemma4-hermes:latest` via Ollama at `192.168.0.58:11434`

| Alias | Model | Provider | Base URL |
|---|---|---|---|
| (default) | deepseek/deepseek-v4-flash-0731 | openrouter | — |
| `r1` | deepseek/deepseek-r1 | openrouter | — |
| `local` | gemma4-hermes:latest | ollama | http://192.168.0.58:11434/v1 |

**Fallback chain:** OpenRouter → Ollama (gemma4-hermes) → OpenRouter (xiaomi/mimo-v2.5-pro)

**Max turns:** 150

---

## Terminal Configuration

| Setting | Value | Purpose |
|---|---|---|
| `terminal.backend` | `local` | Run commands on host (switch to `docker` for sandboxing) |
| `terminal.cwd` | `.` | Working directory (relative to session start) |
| `terminal.timeout` | `180` | Command timeout in seconds |
| `terminal.docker_image` | `nikolaik/python-nodejs:python3.11-nodejs20` | Docker image for sandboxed execution |
| `terminal.container_memory` | `4096` | Container memory limit (MB) |
| `terminal.container_cpu` | `2` | Container CPU limit (cores) |

---

## Webhook Platform

| Setting | Value |
|---|---|
| `platforms.webhook.enabled` | `true` |
| `platforms.webhook.extra.port` | `8644` |
| `platforms.webhook.extra.secret` | (set — see .env or webhook list) |

### Active Subscriptions

| Name | URL | Events | Delivery |
|---|---|---|---|
| `github-issues` | `http://localhost:8644/webhooks/github-issues` | `issues` | origin |
| `github-prs` | `http://localhost:8644/webhooks/github-prs` | `pull_request` | origin |

### GitHub Webhook Configuration

For each monitored repo, configure in GitHub → Settings → Webhooks:
- **Issues webhook:** URL `http://<server>:8644/webhooks/github-issues`, events: Issues
- **PRs webhook:** URL `http://<server>:8644/webhooks/github-prs`, events: Pull requests
- Content type: `application/json`
- Secret: from `hermes webhook list`

---

## Kanban Configuration

| Setting | Value | Purpose |
|---|---|---|
| `kanban.dispatch_in_gateway` | `true` | Dispatcher runs inside gateway |
| `kanban.dispatch_interval_seconds` | `60` | How often dispatcher checks for ready tasks |
| `kanban.failure_limit` | `2` | Auto-block after N consecutive failures |
| `kanban.default_assignee` | `default` | Default profile for new cards |

**Board:** `default` (single board, tenant-per-project)

---

## Delegation Configuration

| Setting | Value | Purpose |
|---|---|---|
| `delegation.max_concurrent_children` | `3` | Max parallel subagents |
| `delegation.max_spawn_depth` | `1` | Max nesting depth (1 = no sub-sub-agents) |
| `delegation.max_iterations` | `250` | Max turns per delegated task |
| `delegation.orchestrator_enabled` | `true` | Allow orchestrator pattern |

---

## Checkpoints

| Setting | Value | Purpose |
|---|---|---|
| `checkpoints.enabled` | `true` | Filesystem rollback safety |
| `checkpoints.max_snapshots` | `20` | Max snapshots per file |
| `checkpoints.retention_days` | `7` | Auto-prune after N days |

---

## Skills Inventory

### Custom Skills (Created During Build)

| Skill | Purpose | Loaded When |
|---|---|---|
| `agentic-sdlc` | Kanban Rules 1-14, card-driven workflow | When handling kanban cards |
| `opencode-bridge` | RUN-ID generation, OpenCode invocation | When delegating to OpenCode |
| `security-scanning` | Layered security scans | When running security scans |
| `github-pipeline` | Issue → PR pipeline | When handling GitHub events |

### Superpowers (OpenCode Plugin)

Installed as OpenCode plugin: `superpowers@git+https://github.com/obra/superpowers.git`

| Skill | Purpose |
|---|---|
| brainstorming | Explore intent before coding |
| test-driven-development | RED→GREEN→REFACTOR enforcement |
| requesting-code-review | Fresh agent review |
| systematic-debugging | Root cause investigation |
| writing-plans | Break specs into micro-tasks |
| subagent-driven-development | Parallel task execution |
| executing-plans | Execute implementation plans |
| receiving-code-review | Process review feedback |
| finishing-a-development-branch | Integration decisions |
| using-git-worktrees | Isolated feature work |
| verification-before-completion | Prove work is done |
| dispatching-parallel-agents | Concurrent task dispatch |
| writing-skills | Create/edit skill files |
| using-superpowers | Meta-skill for discovery |
| diagnosing-superpowers | Debug skill issues |

---

## Cron Jobs

### Agent-Driven Jobs (New)

| Name | Schedule | Skills | Delivery | Purpose |
|---|---|---|---|---|
| `weekly-bug-scan` | Monday 9am | requesting-code-review | origin | Bug scan across all workspaces |
| `weekly-security-scan` | Monday 10am | security-scanning | origin | Security scan across all workspaces |
| `blocked-card-reminder` | Daily 9am | — | origin | Remind about blocked cards >3 days |

### Existing Jobs

| Name | Schedule | Type | Purpose |
|---|---|---|---|
| `raindrop-bookmarks` | Every 10m | no-agent script | Process Raindrop bookmarks |
| `Google Tasks Watch` | Every 5m | script | Watch Google Tasks |
| `State of the Union` | Daily 5:45am | script | Political news summary |
| `inbox-process` | Daily 2am | script | Process Obsidian inbox |
| `vault-hygiene` | Daily 2:30am | script | Clean Obsidian vault |
| `orphan-sweeper` | Weekly Sunday 2am | script | Remove orphaned vault files |
| `daily-rollover` | Daily midnight | script | Daily task rollover |
| `daily-summary` | Daily 10pm | script | Daily summary |
| `INDEX CARD — DAILY VALIDATION` | Daily 2:30am | agent | Validate index cards |
| `memory-optimise` | Daily 3am | script + skills | Optimize memory systems |

---

## Security Configuration

| Setting | Value | Purpose |
|---|---|---|
| `approvals.mode` | `smart` | Smart approval (auto-approve safe ops) |
| `approvals.timeout` | `60` | Approval timeout in seconds |
| `approvals.cron_mode` | `deny` | Cron jobs default to deny on approval |
| `security.redact_secrets` | `true` | Redact secrets in output |
| `security.tirith_enabled` | `true` | Security scanner enabled |
| `privacy.redact_pii` | `false` | PII redaction disabled |

---

## Messaging Platforms

### Telegram

| Setting | Value |
|---|---|
| Status | Configured |
| Streaming | Enabled |
| Reactions | Disabled |

### Discord

| Setting | Value |
|---|---|
| Status | Configured |
| Streaming | Disabled |
| Require mention | Yes |
| Auto-thread | Yes |
| Voice FX | Enabled |
| Free-response channels | hermes-agent-text, HermesAgentVoice |

---

## OpenCode Configuration

**Config file:** `~/.config/opencode/opencode.jsonc`

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["superpowers@git+https://github.com/obra/superpowers.git"]
}
```

**Auth:** OpenRouter API key stored in `~/.local/share/opencode/auth.json`

**Default model:** `openrouter/deepseek/deepseek-v4-flash-0731`

---

## Dashboard

| Setting | Value |
|---|---|
| Theme | default |
| Auth | Basic auth enabled |
| Username | brett |
| Session TTL | default |

---

## Context Compression

| Setting | Value | Purpose |
|---|---|---|
| Enabled | yes | Compress long conversations |
| Threshold | 50% | Trigger at 50% context usage |
| Target ratio | 20% | Preserve 20% of threshold |
| Protect last | 20 messages | Keep last 20 messages |
| Protect first | 3 messages | Keep first 3 non-system messages |

---

## STT/TTS

| Component | Setting |
|---|---|
| STT provider | Groq |
| TTS provider | Edge TTS |
| TTS voice | en-AU-NatashaNeural (Australian female) |
| Voice recording key | Ctrl+B |
