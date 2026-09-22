# Hermes Agent Software Framework — As Implemented
**Date:** 2026-09-22 (AEST)
**Status:** Definitive reference — matches running system
**Supersedes:** Hermes_Agent_Software_Framework.md (v3 design — this document reflects what's actually built)

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Infrastructure](#3-infrastructure)
4. [Model Routing](#4-model-routing)
5. [Agent Roster](#5-agent-roster)
6. [Workflow Definitions](#6-workflow-definitions)
7. [Project Workflow (W-BUILD)](#7-project-workflow-w-build)
8. [OpenCode + Superpowers Integration](#8-opencode--superpowers-integration)
9. [Quality Gates](#9-quality-gates)
10. [Kanban Integration](#10-kanban-integration)
11. [Cost Tracking](#11-cost-tracking)
12. [Browser and Visual Testing](#12-browser-and-visual-testing)
13. [Docker Review Deployments](#13-docker-review-deployments)
14. [Sub-Agent Invocation Rules](#14-sub-agent-invocation-rules)
15. [Requirements Traceability](#15-requirements-traceability)
16. [Configuration Reference](#16-configuration-reference)
17. [Lessons Learned](#17-lessons-learned)

---

## 1. System Overview

The Hermes Agent Software Framework is a multi-agent software development platform built on **Hermes Agent** (Nous Research) as the central hub, with **OpenCode** as the coding engine, and **Superpowers** (obra/superpowers) providing discipline skills (TDD, systematic debugging, verification-before-completion).

### Core Design Principles

1. **Hermes is the hub** — all orchestration, kanban, scheduling, communication happens through Hermes
2. **OpenCode is the coder** — all code writing goes through `opencode run` with Superpowers loaded
3. **Kanban is the control plane** — card lifecycle (triage→todo→ready→running→blocked→done) drives all work
4. **RUN-ID tracks everything** — every build/fix gets a unique ID in commits, comments, and ledger
5. **Gates before review** — code must pass automated gates (lint, typecheck, test) before human review
6. **Docker for testing** — every build deploys a container for the user to test before approval
7. **Cost tracked per card** — LiteLLM spend logs reconciled to each kanban card via time-range queries

### What This System Does

A developer creates a kanban card describing what they want built. The system:

1. Creates a workspace and git repo
2. Gathers requirements via structured interview (Coach)
3. Designs the solution with alternatives (Architect)
4. Implements via TDD (Builder through OpenCode+Superpowers)
5. Verifies test coverage (Test Author)
6. Runs quality gates (Gatekeeper)
7. Reviews for spec compliance (Reviewer)
8. Deploys Docker preview for user testing
9. Loops on user feedback until approved
10. Pushes final code to GitHub

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User (Brett)                          │
│              WebUI / Discord / Telegram                  │
└─────────────┬───────────────────────────┬───────────────┘
              │                           │
     ┌────────▼────────┐         ┌────────▼────────┐
     │   Kanban Board   │         │   Chat Sessions  │
     │  (Gateway:30s)   │         │  (WebUI:8787)    │
     └────────┬─────────┘         └────────┬─────────┘
              │                            │
     ┌────────▼────────────────────────────▼──────────┐
     │              Hermes Agent (Hub)                 │
     │  ┌─────────┐ ┌──────────┐ ┌─────────────────┐  │
     │  │ Gateway  │ │ Profile  │ │  delegate_task   │  │
     │  │ Dispatcher│ │ Manager │ │  (sub-agents)    │  │
     │  └────┬─────┘ └──────────┘ └────────┬────────┘  │
     │       │                             │           │
     │  ┌────▼─────────────────────────────▼────────┐  │
     │  │           Dev Lead (Orchestrator)          │  │
     │  │  ┌───────┐ ┌──────────┐ ┌──────────────┐  │  │
     │  │  │ Scout │ │  Coach   │ │   Architect  │  │  │
     │  │  └───────┘ └──────────┘ └──────────────┘  │  │
     │  │  ┌──────────────────────────────────────┐  │  │
     │  │  │  OpenCode + Superpowers (Coding)     │  │  │
     │  │  │  Builder │ Test Author │ Fixer │ Reviewer │  │
     │  │  └──────────────────────────────────────┘  │  │
     │  │  ┌───────────┐ ┌──────────┐ ┌──────────┐  │  │
     │  │  │ Gatekeeper│ │ Browser  │ │  Visual  │  │  │
     │  │  │           │ │ Tester   │ │  Tester  │  │  │
     │  │  └───────────┘ └──────────┘ └──────────┘  │  │
     │  └───────────────────────────────────────────┘  │
     └─────────────────────────────────────────────────┘
              │                    │
     ┌────────▼────────┐  ┌───────▼──────────┐
     │    LiteLLM      │  │   Git / GitHub    │
     │  (localhost:4000)│  │   Docker          │
     │  Model Router    │  │   SQLite          │
     └─────────────────┘  └──────────────────┘
```

### Two Tool Invocation Patterns

| Pattern | Used For | How It Works |
|---------|----------|-------------|
| **`delegate_task`** | Non-coding agents (Scout, Coach, Architect, Browser Tester, Visual Tester) | Spawns isolated Hermes sub-agent with its own session. Returns summary to parent. |
| **`opencode run`** | Coding agents (Builder, Test Author, Fixer, Reviewer) | Invokes OpenCode CLI with Superpowers loaded. TDD, systematic-debugging, verification-before-completion enforced. |

**This distinction is critical.** The quality gap between the two patterns is significant — OpenCode+Superpowers enforces TDD discipline that plain `delegate_task` does not.

---

## 3. Infrastructure

### 3.1 Hermes Agent

- **Version:** Latest (auto-updated via `hermes update`)
- **Profiles:** `default` (Brett's chat), `agent` (kanban worker)
- **Agent profile location:** `/apps/hermes/.hermes/profiles/agent/`
- **Skills directory:** `/apps/hermes/.hermes/skills/` (default) + `/apps/hermes/.hermes/profiles/agent/skills/` (agent)

### 3.2 OpenCode

- **Version:** 1.18.30
- **Location:** `/apps/hermes/.local/bin/opencode`
- **Superpowers plugin:** Configured in `~/.config/opencode/opencode.jsonc`
- **Plugin cache:** `/apps/hermes/.cache/opencode/packages/superpowers@git+https:/github.com/obra/superpowers.git/`

### 3.3 LiteLLM Proxy

- **Location:** `/apps/hermes-docker/litellm/`
- **Port:** 4000 (accessible at `http://192.168.0.119:4000/ui`)
- **Database:** PostgreSQL (container `litellm-postgres`)
- **Budget:** $10/30 days
- **Health check:** Cron job every 5 minutes

### 3.4 Docker Containers

| Container | Port | Purpose |
|-----------|------|---------|
| `litellm` | 4000 | Model routing proxy |
| `litellm-postgres` | 5432 | LiteLLM spend tracking |
| `energy-plan-analysis` | 8100 | Review deployment (example) |
| `qdrant` | 6333 | Vector database (mem0) |

### 3.5 Kanban

- **Board:** Default (single board, `auto_decompose: false`)
- **Dispatcher:** Embedded in gateway, 30-second tick interval
- **Default assignee:** `brett` (non-spawnable — cards park until manually promoted)
- **Dispatch assignee:** `agent` (only `agent` profile gets dispatched)
- **Backlog workflow:** Create in Triage → assign to `brett` → park. When ready: promote to Ready + assign to `agent`.

### 3.6 GitHub

- **Repo:** `https://github.com/Bandito-coder/hermes-software-agents`
- **Contents:** All 18 agent skills, bin/ scripts, docs, tests

### 3.7 Geckodriver + Firefox

- **geckodriver:** v0.35.0 at `/apps/hermes/.local/bin/geckodriver`
- **Firefox:** 156.0 (headless)
- **Setup script:** `bin/setup-browser-testing.sh`

---

## 4. Model Routing

### 4.1 LiteLLM Aliases

| Alias | Model | Cost (input/output per M) | Used By |
|-------|-------|---------------------------|---------|
| `local` | ollama/gemma4-hermes:latest | Free | Fallback, mechanical tasks |
| `workhorse` | deepseek/deepseek-v4-flash-0731 | $0.04 / $0.16 | Scout, Coach, Gatekeeper, Dev Lead, Enhancer, Triage, Docs, Cost agents, Browser Tester |
| `coding` | deepseek/deepseek-v4.1-flash | $0.12 / $0.48 | Builder, Test Author, Fixer, Reviewer |
| `reasoning` | xiaomi/mimo-v2.5-pro | $0.30 / $0.61 | Architect, SecOps |
| `vision` | qwen/qwen3-vl-8b-instruct | $0.117 / $0.455 | Visual Tester |

### 4.2 Fallback Chain

```
workhorse → local
coding → workhorse
```

### 4.3 Agent Profile Config

The agent profile routes ALL requests through LiteLLM at `localhost:4000/v1`:

```yaml
model:
  provider: custom
  default: workhorse
  base_url: http://localhost:4000/v1
  aliases:
    workhorse: {model: workhorse, provider: custom, base_url: http://localhost:4000/v1}
    coding: {model: coding, provider: custom, base_url: http://localhost:4000/v1}
    reasoning: {model: reasoning, provider: custom, base_url: http://localhost:4000/v1}
```

---

## 5. Agent Roster

### 5.1 Complete Agent List (18 agents)

#### Tier 1 — Orchestrators (workhorse model)

| Agent | Version | Model | Role | Permission |
|-------|---------|-------|------|-----------|
| **dev-lead** | 3.0.0 | workhorse | Full workflow orchestrator. W-BUILD, W-FIX, W-SPEC, W-REFACTOR, W-HARDEN. 4 user-facing blocking points. | Orchestrator |
| **enhancer** | 2.0.0 | workhorse | Refactoring orchestrator with regression awareness. Baseline gate before any change. | Orchestrator |

#### Tier 2 — Research & Design (mixed models)

| Agent | Version | Model | Role | Permission |
|-------|---------|-------|------|-----------|
| **scout** | 1.0.0 | workhorse | Read-only codebase explorer. Maps structure, finds patterns. | Edit-locked |
| **coach** | 2.0.0 | workhorse | Requirements interviewer. 9-dimension assessment, ≤3 rounds, ≤5 questions. Produces BRIEF.md. | Read-mostly |
| **architect** | 2.0.0 | reasoning | Chief architect. 2-3 alternatives, detailed SPEC.md. | Read-mostly |

#### Tier 3 — Coding (via OpenCode+Superpowers, coding model)

| Agent | Version | Model | Role | Permission |
|-------|---------|-------|------|-----------|
| **builder** | 1.0.0 | coding | Implements features via TDD. Strict RED→GREEN→REFACTOR. | Write |
| **test-author** | 1.0.0 | coding | Writes tests ONLY. Never modifies production code. | Write |
| **fixer** | 1.0.0 | coding | Targeted fix applier. Iron Law: root cause before fix. | Write |
| **reviewer** | 1.0.0 | coding | Read-only code reviewer. Spec compliance + code quality. | Edit-locked |

#### Tier 4 — Quality & Verification (mixed models)

| Agent | Version | Model | Role | Permission |
|-------|---------|-------|------|-----------|
| **gatekeeper** | 1.0.0 | workhorse | Runs gates.sh. Reports PASS/FAIL verbatim. Spec compliance check. | Execute-only |
| **secops** | 3.0.0 | reasoning | Security auditor. Secrets, CVEs, SAST. | Edit-locked |
| **browser-tester** | 1.0.0 | workhorse | DOM/API/accessibility smoke tests via geckodriver/Firefox. | Execute-only |
| **visual-tester** | 0.1.0 | vision | Screenshot regression via vision model. | Execute-only |

#### Tier 5 — Operations (workhorse model)

| Agent | Version | Model | Role | Permission |
|-------|---------|-------|------|-----------|
| **triage** | 3.0.0 | workhorse | GitHub issue classifier. P0-P3 priority. | Read + gh CLI |
| **docs** | 3.0.0 | workhorse | Documentation sync. .md files only. | Write (docs only) |
| **cost-sentinel** | 3.0.0 | workhorse | Daily spend anomaly check. Silent when clean. | Read/execute |
| **cost-analyst** | 3.0.0 | workhorse | Weekly cost/efficiency review. Proposals only. | Read-mostly |

#### Tier 6 — Bridges (no model — invocation helpers)

| Agent | Version | Role |
|-------|---------|------|
| **coder-bridge-v2** | 1.0.0 | OpenCode invocation helper. RUN-ID, model selection, Superpowers loading. |

### 5.2 Permission Model

| Tier | Permission | What They Can Do |
|------|-----------|-----------------|
| Edit-locked | Read only | Scout, Reviewer, SecOps — never modify files |
| Read-mostly | Read + specific writes | Coach (BRIEF.md only), Architect (SPEC.md only), Cost Analyst (proposals only) |
| Execute-only | Read + run commands | Gatekeeper, Browser Tester, Visual Tester — run tests, never modify code |
| Write | Read + write code | Builder, Test Author, Fixer, Docs — can modify production/test code |
| Orchestrator | Full lifecycle | Dev Lead, Enhancer — delegate to sub-agents, manage kanban |

---

## 6. Workflow Definitions

### 6.1 W-BUILD (Full Build Cycle)

The primary workflow. 5 phases, 4 user-facing blocking points.

```
Phase 0: PROJECT PREP ──→ automatic
Phase 1: REQUIREMENTS ──→ BLOCK (user approves requirements)
Phase 2: DESIGN ────────→ BLOCK (user approves design)
Phase 3: BUILD ─────────→ automatic (Builder, tests, review)
Phase 4: BUILD APPROVAL → BLOCK (user tests, requests fixes or approves)
Phase 5: FINALIZE ──────→ automatic (push to GitHub)
```

**Detailed flow:**

```
Phase 0: Project Prep
  1. kanban_show() — read the card
  2. Generate RUN_ID
  3. Create workspace if needed (mkdir, git init)
  4. Create branch agent/<slug>
  5. kanban_comment("Workspace ready")

Phase 1: Requirements
  6. Invoke SCOUT — explore codebase
  7. Small-change fast path check (<3 files → skip Coach/Architect)
  8. Invoke COACH — 9-dimension assessment, structured interview
  9. BLOCK — Requirements approval
     → User can: unblock (approve), comment + unblock (changes), or say "Interview me for <project>" in chat

Phase 2: Design
  10. Invoke ARCHITECT — 2-3 alternatives, SPEC.md
  11. BLOCK — Design approval
      → User can: unblock (approve), comment + unblock (changes), or say "Discuss design for <project>" in chat

Phase 3: Build
  12. Invoke BUILDER via opencode run (TDD, 600s timeout)
  13. Invoke BROWSER TESTER (if web UI)
  14. Invoke TEST AUTHOR via opencode run
  15. Invoke GATEKEEPER — gates.sh + spec compliance
  16. If FAIL → FIX LOOP
  17. Invoke REVIEWER via opencode run — spec compliance
  18. If FAIL → FIX LOOP
  19. All PASS: commit, Docker deployment, cost tracking

Phase 4: Build Approval + Fix Loop
  20. BLOCK — Build approval with Docker preview URL
      → User can: unblock (approve), comment with fixes + unblock (fix loop)
      → Fix loop: user comments → agent fixes → Docker rebuilt → re-blocks
      → Continues until user approves

Phase 5: Finalize
  21. Push to GitHub
  22. kanban_complete
```

### 6.2 W-FIX (Quick Fix)

```
1. kanban_show() — read the card
2. Generate RUN_ID
3. Create branch (dir mode: reuse build branch)
4. Invoke SCOUT — locate code
5. Invoke GATEKEEPER — reproduce failure
6. Invoke FIXER via opencode run (systematic-debugging)
7. Invoke GATEKEEPER again
8. Invoke REVIEWER
9. All PASS: commit, Docker deployment, block on user
```

### 6.3 W-SPEC (Requirements Only)

```
1. kanban_show()
2. Generate RUN_ID
3. Invoke SCOUT
4. Invoke COACH — 9-dimension assessment
5. Coach writes BRIEF.md
6. Block on user: "Review BRIEF.md — approve to continue."
7. On approval: update TRACEABILITY.md if it exists
```

### 6.4 W-HARDEN (Security Audit)

```
1. kanban_show()
2. Generate RUN_ID
3. Create branch
4. Invoke SECOPS — 3-layer scan (secrets, CVE, SAST)
5. If PASS → skip to step 8
6. For each Critical/High: Invoke FIXER
7. Invoke GATEKEEPER
8. Invoke SECOPS (verify)
9. All PASS: commit, report findings
```

### 6.5 W-REFACTOR (Refactoring)

```
Delegate to ENHANCER:
  → Enhancer runs: baseline gate → Scout → Architect → Builder → Test Author → Gatekeeper → Reviewer loop
  → MAX_CYCLES: 3
  → Regression = always blocking
```

### 6.6 FIX LOOP (Shared by W-BUILD and W-FIX)

```
cycle = 1
while cycle <= MAX_CYCLES:
    1. Invoke FIXER via opencode run
    2. Invoke GATEKEEPER: re-run gates
    3. If FAIL → next cycle
    4. Invoke REVIEWER: re-review
    5. If PASS → exit loop
    6. Check circuit breakers
    cycle += 1
```

**Circuit Breakers:**
- `cycle > MAX_CYCLES` (build: 4, fix: 3, harden: 2)
- Same finding ID appears in 3 consecutive cycles
- Gatekeeper blocking_count does not decrease across 2 consecutive cycles
- Any sub-agent verdict contains `escalate: human`

---

## 7. Project Workflow (W-BUILD)

### 7.1 User Interaction Model

At each blocking point, the user has multiple response options:

| Method | How | When to Use |
|--------|-----|-------------|
| **Kanban board** | Comment on card, then click Unblock | Review files first |
| **Chat command** | "Unblock <project>" or "I approve <project>" | Quick approval |
| **Interactive chat** | "Interview me for <project>" | Real-time discussion |
| **Unblock without comment** | Just unblock | Implicit approval |

### 7.2 What Happens at Each Block

**Block 1 — Requirements:**
- Card blocked with reason: "Requirements ready. Review docs/BRIEF.md."
- User reviews BRIEF.md, comments with changes or approves
- If user says "Interview me for <project>" in chat → Coach runs interactively

**Block 2 — Design:**
- Card blocked with reason: "Design ready. Review docs/SPEC.md."
- User reviews SPEC.md, comments with changes or approves
- If user says "Discuss design for <project>" in chat → Architect discusses alternatives

**Block 3 — Build Approval:**
- Card blocked with reason: "Build ready. Docker preview at http://host:port."
- User tests the app in the browser
- Comment with fixes → agent fixes → re-deploys → re-blocks
- Unblock without comment or "Approved" → finalize

### 7.3 The Fix Loop

When the user comments with fixes and unblocks:
1. Agent reads ALL comments since last block
2. Agent invokes Fixer via OpenCode+Superpowers
3. Agent runs Gatekeeper + Reviewer
4. Agent redeploys Docker
5. Agent re-blocks for user testing

This loop continues until the user approves (unblock without comment or with "Approved").

---

## 8. OpenCode + Superpowers Integration

### 8.1 What Superpowers Provides

Superpowers (obra/superpowers, 89K+ GitHub stars) is an OpenCode plugin that auto-loads 15 discipline skills:

| Skill | What It Does | Used By |
|-------|-------------|---------|
| **test-driven-development** | RED→GREEN→REFACTOR cycle | Builder, Test Author |
| **systematic-debugging** | Root cause before fix | Fixer |
| **verification-before-completion** | Prove work is done before claiming success | All coding agents |
| **brainstorming** | Explore intent before coding | Builder (pre-implementation) |
| **writing-plans** | Break work into micro-tasks | Builder |
| **requesting-code-review** | Fresh agent review | Reviewer |
| **receiving-code-review** | Process review feedback | Fixer |
| **finishing-a-development-branch** | Integration decisions | Builder |
| **using-git-worktrees** | Isolated feature work | Builder |
| **executing-plans** | Inline plan execution | Builder |
| **subagent-driven-development** | Parallel task dispatch | Builder (complex tasks) |
| **dispatching-parallel-agents** | Concurrent execution | Builder (complex tasks) |
| **writing-skills** | Create/edit skill files | Meta |
| **using-superpowers** | Meta skill discovery | Meta |
| **diagnosing-superpowers** | Debug skill issues | Meta |

### 8.2 How OpenCode Is Invoked

```bash
cd $HERMES_KANBAN_WORKSPACE
timeout 600 opencode run --model openrouter/deepseek/deepseek-v4.1-flash \
  "[$RUN_ID] <task description>. Use TDD. Spec: <SPEC.md path>. Commit prefix: [$RUN_ID]"
```

Superpowers auto-loads from `~/.config/opencode/opencode.jsonc`:
```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["superpowers@git+https://github.com/obra/superpowers.git"]
}
```

### 8.3 OpenCode Timeout Handling

OpenCode tasks can take 5-15 minutes for complex implementations. The Dev Lead handles timeouts intelligently:

1. Run with 600s timeout
2. On timeout: check `git diff --stat` and `git log --oneline -3` for progress
3. If progressing: re-invoke with "Continue from where you left off"
4. If no progress after 2 attempts: fall back to `delegate_task` with explicit TDD + flag degraded mode
5. Check OpenCode logs at `~/.local/share/opencode/log/` for errors
6. NEVER silently fall back — always document what happened

### 8.4 Which Agents Use OpenCode

| Agent | Uses OpenCode? | Why |
|-------|---------------|-----|
| Builder | ✅ | TDD enforcement |
| Test Author | ✅ | Test-driven-development |
| Fixer | ✅ | Systematic-debugging |
| Reviewer | ✅ | Code review with coding model |
| Scout | ❌ | Read-only, no coding |
| Coach | ❌ | Requirements interview, no coding |
| Architect | ❌ | Design, no coding |
| Gatekeeper | ❌ | Runs scripts, no coding |
| Dev Lead | ❌ | Orchestrator, delegates |
| Others | ❌ | Research/audit, no coding |

---

## 9. Quality Gates

### 9.1 gates.sh — The Gate Runner

The gatekeeper runs `bin/gates.sh` which auto-detects the stack and runs:

1. **Dependencies** — `uv sync` or `pip install` or `npm ci`
2. **Lint** — `ruff check` (Python) or `eslint` (JS)
3. **Typecheck** — `mypy` (Python) or `tsc` (JS)
4. **Test** — `pytest` (Python) or `npm test` (JS)

All four must PASS. Any FAIL blocks the workflow.

### 9.2 Spec Compliance Check

In addition to gates.sh, the Gatekeeper verifies:
- Every MUST requirement in SPEC.md has at least one test
- Every acceptance criterion is covered
- Reports missing coverage as blocking findings

### 9.3 Reviewer Checklist

The Reviewer checks:
1. Every spec requirement is implemented
2. No spec requirement is missing
3. Code quality (error handling, security, conventions)
4. Test adequacy (coverage, edge cases)

---

## 10. Kanban Integration

### 10.1 Status Lifecycle

```
triage → todo → ready → running → blocked → done → archived
                ↑                    |
                └────────────────────┘ (request_changes → back to ready)
```

### 10.2 Dispatcher Behavior

The dispatcher runs inside the gateway every 30 seconds:

1. Reclaim stale claims (TTL expired, no heartbeat)
2. Promote `todo` → `ready` when all parents complete
3. Claim `ready` tasks with assignee `agent`
4. Spawn worker process for claimed task

### 10.3 What Gets Dispatched

A task is dispatched when ALL of:
- Status is `ready`
- Has assignee `agent`
- Agent profile exists on disk
- Not guarded by respawn guard
- Concurrency caps not exceeded

### 10.4 What Does NOT Get Dispatched

- `triage` cards (if `auto_decompose: false`)
- `todo` cards (waiting on parents)
- `blocked` cards (waiting on user)
- `done`/`archived` cards
- Cards with no assignee or assignee `brett`

### 10.5 Sub-Agent Kanban Isolation

Sub-agents spawned via `delegate_task` are fenced from kanban:
- `scrub_kanban_env()` strips all kanban env vars
- `_assert_not_delegated_child_mutation()` blocks kanban tool calls
- **But CLI access bypasses this** — sub-agents are explicitly told not to use `hermes kanban` commands

---

## 11. Cost Tracking

### 11.1 Per-Card Cost

LiteLLM tracks every request with session_id. The Dev Lead queries LiteLLM's `/spend/logs` endpoint filtered by the card's start time (from kanban_show) to completion time. Sums `spend` field.

### 11.2 LiteLLM Spend API

```bash
LITELLM_KEY=$(grep LITELLM_API_KEY /apps/hermes/.hermes/.env | cut -d= -f2)
curl -sf "http://localhost:4000/spend/logs" -H "Authorization: Bearer $LITELLM_KEY"
```

Filter by `startTime` field. Sum `spend` field for all requests in the card's time range.

### 11.3 Cost Sentinel + Cost Analyst

- **Cost Sentinel:** Daily cron job. Queries LiteLLM for anomalies (single run >2x, daily >3x, model mix shift). Silent when clean.
- **Cost Analyst:** Weekly cron job. Produces cost report and efficiency improvement proposals. Never applies changes.

---

## 12. Browser and Visual Testing

### 12.1 Browser Tester

- **Model:** workhorse
- **Tool:** geckodriver v0.35.0 + Firefox 156.0 headless
- **Scripts:** `bin/smoke_run.py`, `bin/webdriver_client.py`
- **Check sets:** page-load, dom-element, glance, form-interaction
- **Output:** PASS/FAIL verdict block with structured findings

### 12.2 Visual Tester

- **Model:** vision (qwen/qwen3-vl-8b-instruct, $0.117/M input)
- **Capabilities:** Screenshot comparison, chart verification, layout verification
- **Status:** OPERABLE (vision model configured in LiteLLM)
- **Integration:** Dev Lead invokes selectively for UI-heavy changes only

### 12.3 Environment Setup

```bash
bash bin/setup-browser-testing.sh
```
Installs: geckodriver → `/apps/hermes/.local/bin/geckodriver`, venv with selenium at `~/.hermes/browser-smoke-venv/`

---

## 13. Docker Review Deployments

### 13.1 When Docker Is Deployed

- **W-BUILD:** After all gates PASS and review PASS, before blocking on user
- **W-FIX:** After gates PASS and review PASS, before blocking on user
- **Bug fixes on existing builds:** Rebuild the container with the fix merged

### 13.2 How It Works

1. Build: `cd $HERMES_KANBAN_WORKSPACE && docker compose build`
2. Deploy: `docker compose up -d`
3. Get port from docker-compose.yml
4. kanban_comment with preview URL
5. User tests in browser before approving

### 13.3 Port Convention

| Project | Port |
|---------|------|
| energy-plan-analysis | 8100 |
| Future projects | 8101, 8102, ... |

---

## 14. Sub-Agent Invocation Rules

### 14.1 Coding Agents — MUST Use OpenCode

| Agent | Invocation | Model | Timeout |
|-------|-----------|-------|---------|
| Builder | `opencode run` | coding | 600s |
| Test Author | `opencode run` | coding | 600s |
| Fixer | `opencode run` | coding | 600s |
| Reviewer | `opencode run` | coding | 600s |

### 14.2 Non-Coding Agents — Use delegate_task

| Agent | Invocation | Model |
|-------|-----------|-------|
| Scout | `delegate_task` | workhorse |
| Coach | `delegate_task` | workhorse |
| Architect | `delegate_task` | reasoning |
| Gatekeeper | `delegate_task` | workhorse |
| Browser Tester | `delegate_task` | workhorse |
| Visual Tester | `delegate_task` | vision |

### 14.3 Sub-Agent Monitoring

After spawning a sub-agent:
1. Wait 3-5 minutes
2. Call `delegate_task(action='list')` to check status
3. If progressing (new tool calls): wait another 3-5 minutes
4. If stalled (no activity for 5+ minutes): `delegate_task(action='stop')`
5. Max wait: 15 minutes. If exceeded, stop and proceed with partial results
6. NEVER enter a sleep-poll loop

### 14.4 Kanban Isolation for Sub-Agents

All sub-agents receive this instruction:
> "You are a sub-agent. NEVER call kanban_complete, kanban_block, kanban_request_review, or any hermes kanban CLI command. Return your results as plain text output. The parent worker handles all kanban lifecycle operations."

---

## 15. Requirements Traceability

### 15.1 Framework Requirements (30 total)

From `Hermes_Agent_Software_Framework.md` v3:

| ID | Requirement | Status | Agent Coverage |
|----|------------|--------|---------------|
| R1 | Requirements gathering | ✅ Implemented | Coach |
| R2 | Traceability | ✅ Implemented | Coach → Architect → Builder |
| R3 | High-level design | ✅ Implemented | Architect |
| R4 | Detailed design | ✅ Implemented | Architect |
| R5 | Impact analysis | ✅ Implemented | Scout, Architect (delta design) |
| R6 | Codebase exploration | ✅ Implemented | Scout |
| B1 | Nightly gate runs | ⚠️ Cron exists, not created | Gatekeeper |
| B2 | Security audits | ✅ Implemented | SecOps |
| B3 | Bug investigation | ✅ Implemented | Scout, Fixer |
| B4 | Dependency scanning | ✅ Implemented | SecOps |
| B5 | SAST | ✅ Implemented | SecOps |
| G1 | Card lifecycle | ✅ Implemented | Dev Lead, Kanban |
| G2 | Issue triage | ✅ Implemented | Triage |
| Gv1 | Budget guard | ✅ Implemented | LiteLLM |
| Gv2 | Cost tracking | ✅ Implemented | Cost Sentinel, Cost Analyst |
| Gv4 | Spend reporting | ✅ Implemented | Cost Analyst |
| I1 | Feature implementation | ✅ Implemented | Builder |
| I2 | Bug fixing | ✅ Implemented | Fixer |
| I3 | Test execution | ✅ Implemented | Gatekeeper, Test Author |
| I4 | Quality gates | ✅ Implemented | Gatekeeper |
| I5 | Refactoring | ✅ Implemented | Enhancer |
| I6 | Documentation sync | ✅ Implemented | Docs |
| N1 | Correctness by construction | ✅ Implemented | TDD via Superpowers |
| N2 | Performance | ✅ Implemented | Gatekeeper |
| N3 | Data locality | ✅ Implemented | LiteLLM proxy |
| N4 | Single board | ✅ Implemented | Kanban config |
| N5 | Engine framework-agnostic | ✅ Implemented | Architect design |
| N6 | Minimal toolchain | ✅ Implemented | Hermes + OpenCode only |

---

## 16. Configuration Reference

### 16.1 File Locations

| File | Purpose |
|------|---------|
| `/apps/hermes/.hermes/config.yaml` | Main Hermes config |
| `/apps/hermes/.hermes/profiles/agent/config.yaml` | Agent profile config |
| `/apps/hermes/.hermes/skills/` | Default profile skills |
| `/apps/hermes/.hermes/profiles/agent/skills/` | Agent profile skills |
| `/apps/hermes-docker/litellm/litellm_config.yaml` | LiteLLM model routes |
| `/apps/hermes-docker/litellm/.env` | LiteLLM secrets |
| `~/.config/opencode/opencode.jsonc` | OpenCode + Superpowers config |

### 16.2 Key Config Values

```yaml
# Kanban
kanban.default_assignee: brett        # Non-spawnable — cards park
kanban.dispatch_assignee: agent       # Only agent profile gets dispatched

# Toolsets
toolsets.kanban: enabled
toolsets.kanban_decomposer: disabled
```

### 16.3 Cron Jobs (15 total)

| Job | Schedule | Purpose | Pipeline-relevant? |
|-----|----------|---------|-------------------|
| raindrop-bookmarks | every 10m | Bookmark processing | No |
| Google Tasks Watch | every 5m | Task monitoring | No |
| State of the Union | daily 5:45am | News digest | No |
| inbox-process | daily 2am | Obsidian inbox processing | No |
| vault-hygiene | daily 2:30am | Vault cleanup | No |
| orphan-sweeper | weekly Sun 2am | Orphan file cleanup | No |
| daily-rollover | daily midnight | Daily note rollover | No |
| daily-summary | daily 10pm | Daily summary | No |
| INDEX CARD — DAILY VALIDATION | daily 2:30am | Index card validation | No |
| memory-optimise | daily 3am | Memory optimization | No |
| weekly-bug-scan | Monday 9am | Bug scan | Yes |
| weekly-security-scan | Monday 10am | Security scan | Yes |
| blocked-card-reminder | daily 9am | Kanban blocked reminder | Yes |
| litellm-health-check | every 5m | LiteLLM health | Yes |

---

## 17. Lessons Learned

### 17.1 Sub-Agent Kanban Isolation

**Problem:** Scout sub-agent called `hermes kanban complete` via terminal, prematurely ending a card.

**Root cause:** The fencing mechanism blocks kanban *tools* but not CLI commands run through the terminal tool.

**Fix:** Sub-agents explicitly instructed not to use kanban CLI commands. Documented in Dev Lead skill.

### 17.2 OpenCode+Superpowers Bypass

**Problem:** Builder/Test Author/Fixer were invoked via `delegate_task` (plain Hermes sub-agents) instead of `opencode run`, bypassing TDD discipline.

**Root cause:** Dev Lead skill said "or via opencode run" but didn't enforce it. The `delegate_task` path was simpler, so agents used it.

**Fix:** Dev Lead skill rewritten to REQUIRE `opencode run` for all coding agents. `delegate_task` only for non-coding agents.

### 17.3 Incomplete Build Passing Gates

**Problem:** AER detail v3 endpoint was never called — all plans had `pricing_model: UNKNOWN`. Gates passed because tests matched the incomplete implementation.

**Root cause:** Builder didn't implement all spec requirements. Test Author wrote tests for what existed, not what the spec required. Gatekeeper only ran existing tests.

**Fix:** Added spec-compliance check to Gatekeeper (every MUST requirement must have a test). Added spec-compliance check to Reviewer (completeness against requirements).

### 17.4 OpenCode Timeout Handling

**Problem:** OpenCode timed out and the agent silently fell back to `delegate_task`, losing Superpowers enforcement.

**Root cause:** No timeout handling — just a raw `opencode run` call.

**Fix:** Intelligent timeout handling: check workspace for progress, re-invoke with "Continue" if progressing, fall back only after 2 failed attempts with degraded mode flag.

### 17.5 Dir Workspace Branch Handling

**Problem:** Bug fix card created a new branch instead of working on the existing build branch.

**Root cause:** `dir` workspace mode didn't check the current branch before creating a new one.

**Fix:** Dev Lead skill now checks `git branch --show-current` before creating branches in dir mode. For bug fixes during review, works on the existing build branch.

---

**End of document.**
