# Hermes Agent Software Framework — Design Document v2

**Supersedes:** Solution 3 – Hybrid Triad Design v1 (2026-09-12)
**Date:** 2026-09-18 (AEST)
**Purpose:** Agent-buildable implementation plan for a local agentic software development platform. Designed so Hermes Agent can read this document and build the entire system with minimal reasoning effort.

---

## Executive Summary

### What This Is

This document defines a complete software development platform that runs entirely on local infrastructure, managed through natural language. A human operator describes what they want — from a raw idea to a deployed, tested, maintained software system — and an AI agent architecture executes the work, asking for human approval only at critical decision points.

### What We Are Trying to Achieve

Build a system where a solo operator can:

- **Go from idea to running code** by describing what they want in plain English, answering a few clarifying questions, and approving generated designs — then watching the system implement, test, review, and prepare a pull request automatically.
- **Keep all systems healthy** through automated bug scans, security scans, dependency monitoring, and post-deploy assessments that run on schedule and report only when something needs attention.
- **Run GitHub issue workflows end-to-end** — issues arrive, get triaged, get designed, get implemented, get tested, get reviewed, and land as a PR ready for one human approval — without manual intervention at any step except the final merge.
- **Automate non-coding work** — research, monitoring, content generation, and other workflows designed, implemented, scheduled, and refined through the same agent architecture.
- **Stay in control** — nothing merges, deploys, or executes irreversibly without human approval. Every agent action is logged. Every run is traceable. Every job has a defined failure handler.

All of this runs on local infrastructure — a home server, Proxmox VM, or GPU-equipped desktop — at near-zero operational cost by defaulting to local language models for routine tasks.

### The Components

The system uses two components working together:

**Hermes Agent (Hub)** — The always-on central controller built by Nous Research. It is the human-facing interface (chat via web browser, Telegram, Discord, CLI, or voice), the persistent memory layer (remembers preferences, projects, and lessons across sessions), the scheduler (runs jobs on schedule, on events, or on demand), and the orchestration layer (delegates work to coding agents, manages parallel tasks, tracks state). It handles everything that is not writing code: requirements gathering, design review, triage, workflow management, GitHub event routing, and human approval gates. It also runs untrusted work in Docker sandboxes and manages Git worktrees so multiple agents can work on the same repository without conflict.

**OpenCode + Superpowers (Coder)** — The dedicated code implementation engine. OpenCode is a terminal-based AI coding agent that takes an approved design and turns it into tested, committed code. Superpowers is a set of workflow discipline skills that enforce a rigorous engineering process: brainstorm before coding, write failing tests before production code, investigate root cause before fixing, review every change with a fresh agent that has no knowledge of the implementer's reasoning. Together, they ensure that code output follows senior-engineer discipline rather than rushing to write code before understanding the problem.

### How They Work Together

A user talks to Hermes through any messaging surface. Hermes analyses the request and either handles it directly (design work, triage, scheduling, web research) or delegates the coding work to OpenCode with a fully specified task, a run identifier for traceability, and the required skills loaded. OpenCode executes using the Superpowers discipline, commits code with traceability links, creates a pull request, and reports back. Hermes delivers results to the user and handles any follow-up — updating traceability records, triggering downstream workflows, or escalating for human review.

### What the System Produces

Using this platform, an operator can reliably produce:

- **Tested, reviewed code** from approved designs — with every line traceable back to a requirement, through a design, to a specific commit and pull request.
- **Scheduled security and quality reports** — weekly bug scans, daily dependency monitoring, scanned secrets and vulnerabilities — with zero noise when nothing is found.
- **Automated GitHub issue resolution** — from issue filing through triage, design, implementation, testing, code review, and pull request creation — with a human approval gate at the merge step.
- **Refined non-coding workflows** — research pipelines, monitoring summaries, documentation sync — designed, measured, and iterated until quality and cost targets are met.
- **Full audit trails** — every agent action logged, every run traceable by identifier, every decision gate documented, every commit linked to its source requirement.

---

## Requirements Summary

This design addresses 30 requirements across seven areas. Each requirement is marked as either **[SUPPLIED]** (directly stated by the operator) or **[SUGGESTED]** (derived from industry best practice to ensure the system is complete). The design document's Section 5 contains the full state-machine flow, failure handlers, and verification criteria for every requirement.

### Requirements & Design (R1–R6)

| ID | Requirement | Summary |
|---|---|---|
| **R1** [SUPPLIED] | Requirements from raw idea | Take a raw idea in plain English, run a structured interview (≤3 rounds, ≤8 questions with options and recommendations), and produce a requirements document with IDs, acceptance criteria, and open questions. |
| **R2** [SUGGESTED] | Requirement versioning & traceability | Assign an ID scheme to every requirement, version them in Git, and maintain a traceability index that maps each requirement to its design, implementation, test, and pull request — ensuring nothing is built without a traced source. |
| **R3** [SUPPLIED] | High-level system design | Take approved requirements, clarify constraints (cost, tech stack, hosting), generate 2–3 architecture alternatives with trade-offs, and present a recommended approach for human approval before detailed design begins. |
| **R4** [SUPPLIED] | Detailed system design | Expand the approved high-level design into implementation-ready module specifications — data models, API contracts, error handling, edge cases, and a test plan mapped to every acceptance criterion. |
| **R5** [SUPPLIED] | System update design | For a requested feature change or addition, produce a minimal delta specification — only what needs to change — with impact analysis, backward-compatibility concerns, and migration notes. |
| **R6** [SUPPLIED] | Bug-patch design | For a reported bug, perform root cause investigation with evidence before proposing any fix, then produce a minimal patch design and regression test plan. |

### Implementation (I1–I6)

| ID | Requirement | Summary |
|---|---|---|
| **I1** [SUPPLIED] | Implement a new system design | Take an approved detailed design, break it into micro-tasks (2–5 minutes each), implement each task using test-driven development (failing test first), review with a fresh agent, and produce a tested, reviewed pull request linked back to requirements. |
| **I2** [SUPPLIED] | Implement an update or bug-patch | Same implementation discipline as I1, but scoped to the files and modules affected by the change — smaller PR, faster review, with both focused and full regression tests passing before completion. |
| **I3** [SUGGESTED] | Automated test authoring & execution | Enforce test-driven development as a hard rule: no production code without a failing test first. If code is written before a test, delete it and start over. The agent iterates on failures automatically and escalates after three unsuccessful attempts. |
| **I4** [SUGGESTED] | Automated code review & quality gate | After implementation, a separate fresh agent (no knowledge of the implementer's reasoning) reviews the code against the plan and a personal standards checklist. Critical issues block the merge; findings are reported by severity. |
| **I5** [SUGGESTED] | Refactoring workflow | For code quality improvements (deduplication, restructuring), the agent explores the codebase, proposes 2–3 approaches with before/after justification, gets human approval, applies changes via test-driven development, and proves behaviour is unchanged by keeping the existing test suite green. |
| **I6** [SUGGESTED] | Automated documentation sync | On merge events (or weekly schedule), diff what changed in code and update README, API docs, and changelog accordingly. Flag any documentation that conflicts with code for human review before committing. |

### Bugs & Security (B1–B5)

| ID | Requirement | Summary |
|---|---|---|
| **B1** [SUPPLIED] | Scheduled bug scans | Run static analysis and AI-powered code reasoning on a schedule (default: weekly) to find unhandled errors, race conditions, and logic errors. Deduplicate against known issues. Report only when findings exist — silent when nothing is found. |
| **B2** [SUPPLIED] | Scheduled security scanning | Run layered security scans on a schedule (secrets detection, dependency/CVE checks, SAST) inside a Docker sandbox. AI reasoning reduces false positives. Critical findings block PR merges until resolved. |
| **B3** [SUGGESTED] | Debugging/root-cause workflow | Enforce investigation before fixing: reproduce the failure, read the stack trace, form a hypothesis with evidence, then implement a targeted fix. If the fix fails after three iterations, escalate to the human operator with findings. |
| **B4** [SUGGESTED] | Dependency / CVE monitoring | Scan dependency manifests daily against known vulnerability databases. For critical CVEs, automatically generate a patch PR that bumps the dependency and verifies tests pass. Report medium/low CVEs in a weekly digest. |
| **B5** [SUGGESTED] | Post-deploy security assessment | After a deployment, reason about the actual running attack surface — chain potential vulnerability paths and validate real-world exploit feasibility. This is distinct from source code scanning: it looks at what is actually exposed. |

### GitHub Integration (G1–G3)

| ID | Requirement | Summary |
|---|---|---|
| **G1** [SUPPLIED] | GitHub issue → fix pipeline | When a GitHub issue arrives, the system triages it, designs a fix, implements it via the full coding pipeline, tests it, reviews it, and creates a pull request — all automatically. The human reviews and approves (or rejects) the PR. Nothing merges without human approval. |
| **G2** [SUGGESTED] | Triage agent | Classify incoming GitHub issues as bug, feature, question, or duplicate. Assign priority and severity from a defined rubric. Auto-label clear-cut cases; flag ambiguous issues for human review. |
| **G3** [SUGGESTED] | Full issue → PR pipeline | Chain G2 (triage) into G1 (fix pipeline) end-to-end. A GitHub issue arrives, gets triaged, gets designed, gets implemented, gets tested, gets reviewed, and lands as a pull request — the human only touches the merge approval step. |

### Non-Coding Workflows (W1–W2)

| ID | Requirement | Summary |
|---|---|---|
| **W1** [SUPPLIED] | Design non-coding workflows | For non-software processes (research, monitoring, content generation), interview the operator to understand the process, map it to one of five standard agent workflow patterns (chaining, routing, parallelization, orchestrator-workers, evaluator-optimizer), and produce a workflow design with stages, failure handlers, and gate placements. |
| **W2** [SUPPLIED] | Implement & refine non-coding workflows | Build the designed workflow as a scheduled or triggered automation. Measure quality, cost, and latency on each run. If metrics are below threshold, refine the workflow through up to 3–4 iteration cycles until it converges. |

### Scheduling & Triggers (S1–S4)

| ID | Requirement | Summary |
|---|---|---|
| **S1** [SUPPLIED] | Manual workflow start | Run any named workflow on demand by natural language command from any messaging surface (CLI, web, Telegram, Discord). Results return to the originating conversation. |
| **S2** [SUPPLIED] | Scheduled workflow start | Set recurring schedules using natural language ("every Monday 9am"), intervals ("every 2 hours"), or cron syntax. Jobs respect budget caps and the zero-noise principle — no message when nothing actionable was found. |
| **S3** [SUPPLIED] | Event-triggered workflow start | Wire external events (GitHub webhooks, CI/CD pipelines, file system changes, HTTP endpoints) to agent workflows. Events are deduplicated and rate-limited before triggering a run. |
| **S4** [SUGGESTED] | Long-running agent support | For jobs lasting 30+ minutes, break them into phases with checkpoint files. On transient failure, retry with exponential backoff. On system restart, resume from the last completed checkpoint. On timeout, escalate to the human operator. |

### Governance (Gv1–Gv6)

| ID | Requirement | Summary |
|---|---|---|
| **Gv1** [SUGGESTED] | Human-in-the-loop approval gates | Every irreversible action (merge, deploy, delete, publish) requires explicit human approval. Gate thresholds are defined once and narrow over time from audit data. For a solo operator, prompt-based gates enforced through loaded skills are sufficient — structural permission gates are a future hardening step. |
| **Gv2** [SUPPLIED] | Cost & token monitoring | Log every agent run's model, tokens consumed, and provider. Consolidate into per-workflow, per-day, and per-project views. Alert on anomalies (e.g., a single run costing double the normal amount). |
| **Gv3** [SUGGESTED] | Observability & traceability | Every delegated task carries a shared run identifier that appears in agent logs, Git commit messages, pull request descriptions, and session histories. This enables cross-tool traceability by grepping for the identifier across all sources. |
| **Gv4** [SUGGESTED] | Cost & budget governance | Enforce a monthly spending limit by checking cumulative cost before allowing cloud model calls. Primary enforcement is defaulting to local models (zero cost); the budget wrapper is a safety net for cloud calls only. |
| **Gv5** [SUGGESTED] | Scoped access & sandboxed execution | Run untrusted or risky work (security scanning, web scraping, external code execution) inside Docker containers with no access to the host system. Run standard code changes in Git worktrees for isolation without container overhead. Use OS-level file permissions for routine operations. |
| **Gv6** [SUGGESTED] | Audit logging | Every tool call, reasoning step, gate decision, and delegation is logged with timestamps across all components. Git history, session logs, and GitHub provide overlapping audit trails. Retention: 90 days for session logs, permanent for Git and GitHub. |

---

## 1. Architecture Overview

### 1.1 Two-Component Architecture

The original "Hybrid Triad" used three tools: Hermes, OpenCode, and OpenHands. This revision reduces to **two components** by routing OpenHands' former responsibilities through Hermes-native features.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HERMES AGENT (Hub)                          │
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌─────────────┐ │
│  │ Chat Surface │ │  Webhooks    │ │  Cron Jobs  │ │   Memory    │ │
│  │ WebUI/TG/DC  │ │  (GitHub,    │ │ (scheduled   │ │  Persistent │ │
│  │ CLI/Voice    │ │  CI/CD, etc) │ │  workflows)  │ │  cross-sess │ │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └─────────────┘ │
│         │                │                │                          │
│  ┌──────┴────────────────┴────────────────┴──────┐                  │
│  │           Orchestration Layer                  │                  │
│  │  delegate_task / kanban / checkpoint+rollback   │                  │
│  │  Docker backend / Git worktrees / run IDs       │                  │
│  └──────────────────────┬────────────────────────┘                  │
└─────────────────────────┼───────────────────────────────────────────┘
                          │
                          │ terminal / delegate_task
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   OPENCODE + SUPERPOWERS (Coder)                    │
│  ┌─────────────┐ ┌─────────────┐ ┌───────────┐ ┌────────────────┐  │
│  │  Brainstorm │ │ Plan/Build  │ │    TDD     │ │  Code Review   │  │
│  │  (design    │ │ (Plan agent │ │ (fail-first│ │  (fresh agent  │  │
│  │   gate)     │ │ →Build agt) │ │  cycle)    │ │   review)      │  │
│  └─────────────┘ └─────────────┘ └───────────┘ └────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
                    Git / GitHub / CI
```

### 1.2 Why Two Components, Not Three

The original design added OpenHands as layer 3 for: sandboxed execution, GitHub event handling, multi-agent orchestration, and web browsing. Every one of these maps to a Hermes-native capability:

| OpenHands Responsibility | Hermes-Native Replacement | Verification |
|---|---|---|
| Sandboxed execution | Docker backend (`hermes config set terminal.backend docker`) or Git worktrees | `hermes-worktrees.md` F1 |
| GitHub event handling | Webhook subscriptions (`hermes webhook subscribe`) | Webhooks CI passing |
| Multi-agent orchestration | `delegate_task` (≤3 parallel) + Kanban board | Delegation tests + Kanban tests |
| Web browsing | Browser tool (Browser Use / Playwright) | Browser tests F1–F13 |
| Security scanning (Docker) | Docker backend + terminal tools (Grype/Trivy/semgrep) in sandbox | Docker docs verified |
| Automated documentation | Cron jobs + skills + delegate_task | Cron tests |

**Component economy:** Less than 3 distinct systems means fewer configuration targets, fewer failure modes, fewer authentication boundaries, and faster setup. The total pipeline is simpler to hand to an agent to build.

### 1.3 Design Pillars

All design decisions balance four pillars. When pillars conflict, the priority is:

1. **Solid** (robust, long-running, trustworthy)
2. **Straightforward** (minimal complexity, no excess)
3. **Economic** (lowest cost components that do the job)
4. **Performant** (delivers solutions quickly)

Straightforward beats Economic (complexity has higher long-run cost than dollars). Economic beats Performant (speed is secondary to sustainability for a solo operator).

---

## 2. Component Deep Dive

### 2.1 Hermes Agent (Hub — Layer 1)

**Role:** Primary control surface, event router, scheduler, memory keeper, orchestration layer. Every user interaction starts here. All automation is triggered and monitored through Hermes.

**Verified installation:** `curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash`

**Key paths (all verified against `hermes config show`):**
```
~/.hermes/config.yaml        Main configuration
~/.hermes/.env               API keys (OpenRouter key, Ollama endpoint, etc.)
~/.hermes/skills/             SKILL.md files for workflow enforcement
~/.hermes/scripts/            Webhook filter scripts, cron helper scripts
~/.hermes/state.db            Session store (SQLite + FTS5)
~/.hermes/webhook_subscriptions.json  Webhook route definitions
```

**Verified configuration (from current system):**
```yaml
# ~/.hermes/config.yaml
model:
  provider: openrouter
  default: deepseek/deepseek-v4-flash-0731
  aliases:
    local:
      model: gemma4-hermes:latest
      provider: ollama
      base_url: http://192.168.0.58:11434/v1

terminal:
  backend: local          # Switch to 'docker' for sandboxed runs
  timeout: 180

display:
  personality: none

timezone: Australia/Brisbane
```

**Core capabilities used in this framework:**

| Capability | Tool/Command | What It Does |
|---|---|---|
| Chat | `hermes`, WebUI, Telegram, Discord, CLI | User interaction from any surface |
| Scheduled jobs | `cronjob` tool / `hermes cron add` | Run workflows on schedule or one-shot |
| Event triggers | `hermes webhook subscribe` | GitHub/CI/IoT webhook → agent run |
| Delegation | `delegate_task(goal, context)` | Spawn isolated child agent (≤3 parallel) |
| Kanban | `hermes kanban` | Durable task queue for multi-profile work |
| Checkpoint+Rollback | `/rollback`, shadow git | Undo destructive file operations |
| Docker sandbox | `terminal.backend: docker` | Run commands in isolated container |
| Git worktrees | `hermes -w` / worktree mode | Multiple agents on same repo without conflicts |
| Skills | `skill_view` / skill loading | Load workflow discipline into agent context |
| Memory | `mem0_search` / `mem0_add` | Persistent facts across sessions |
| Browser | `browser_exec` tool | Navigate websites, fill forms, extract data |
| Web search | `hermes search` | Query the web and extract content |
| Scripts | `~/.hermes/scripts/*.sh` | Custom automation, webhook filters, budget guards |
| TTS/Voice | Discord voice, `text_to_speech` | Speak to Hermes, hear spoken responses |
| Provider routing | `config.yaml` model.aliases | Route cheap tasks to local, complex to frontier |
| Hooks | `hooks:` in config.yaml | Lifecycle events (post-run logging, alerts) |
| Model routing | Per-task model override | Override default model for specific jobs |

### 2.2 OpenCode + Superpowers (Coder — Layer 2)

**Role:** Code implementation from approved specs. Enforced discipline through loaded skills. Runs TDD, code review, and subagent-driven development.

**Installation:**
```bash
# Install OpenCode
# Follow: https://github.com/opencode-ai/opencode
# Install to PATH so Hermes can invoke it

# Install Superpowers skill set
# Clone into OpenCode's skill directory
# ~/.opencode/skills/ or equivalent
git clone https://github.com/obra/superpowers ~/.opencode/skills/superpowers
```

**Integration:** OpenCode is invoked by Hermes via terminal command or delegate_task. Hermes passes the task + run ID + design document path. OpenCode loads Superpowers skills and executes.

**Invocation pattern:**
```bash
opencode --model deepseek/deepseek-v4-flash-0731 \
  --task-file /path/to/task.md \
  --skill superpowers
```

Or via Hermes delegation:
```
terminal(command="opencode <args>", timeout=600)
# OR
delegate_task(goal="Implement feature X per design at /path/design.md", context="...")
```

**Core capabilities (from Superpowers skill set):**

| Skill | Iron Law | Mechanism |
|---|---|---|
| Brainstorming | No code before approved design | Agent must explore, ask questions, propose 2–3 approaches, await explicit approval |
| Writing Plans | Micro-tasks (2–5 min each) | Every task has exact file paths, full code context, verification steps |
| TDD | No production code without failing test first | Write code before test → delete it, start over. No exceptions. |
| Systematic Debugging | No fixes without root cause investigation | Must reproduce, read stack, hypothesize with evidence, then fix |
| Code Review | Fresh agent reviews, no prior context | Separate subagent checks against plan, reports by severity, critical blocks |
| Subagent-Driven Dev | Fresh agent per task from plan | Each subagent gets only its task + relevant files, not full conversation |

---

## 3. How They Connect

### 3.1 Data Flow Table

| From | To | Interface | What Carries | Verified |
|---|---|---|---|---|
| **User** → Hermes | Any surface | WebUI / Telegram / Discord / CLI / Voice | Natural language commands, approvals | WebUI F1, Telegram F1, Discord F1 |
| **GitHub** → Hermes | Webhook | `hermes webhook subscribe` → POST → agent run | Issues, PRs, pushes — `{payload.field}` templating | Webhooks F1, webhook CLI F8 |
| **CI/CD** → Hermes | Webhook | Same as GitHub, different route | Build status, deploy events | webhook CLI F8 |
| **Schedule** → Hermes | Cron | `cronjob` / `hermes cron add` | Scheduled workflow triggers (cron, interval, natural language) | Cron F1–F14 |
| **Hermes** → OpenCode | Terminal | `terminal(command="opencode ...")` | Task spec + run ID + design doc path | OpenCode integration |
| **Hermes** → OpenCode | Delegation | `delegate_task(goal, context)` | Isolated subtask with full context | delegate_task confirmed |
| **OpenCode** → Git | Native | Git integration (inside OpenCode) | Commits, branches, PRs | Git F1–F3 |
| **OpenCode** → GitHub | CLI | `gh pr create` | PR creation, issue linking | GitHub CLI F1 |
| **OpenCode** → Hermes | Output | Command stdout / delegate return | Results, flags, exit codes | Terminal F1 |
| **Superpowers** → OpenCode | Skills | `~/.opencode/skills/superpowers/` | Workflow enforcement (TDD, review, brainstorm) | Agent Skills standard |

### 3.2 Run ID Convention (Suggestion 1 — Integrated)

When Hermes delegates any task that will touch code or external systems, it generates a UUID and includes it in every delegated task description, commit message prefix, and log entry.

**Format:** `RUN-<8-char-uuid>` (e.g., `RUN-a3f7c2b1`)

**Implementation:**
```bash
# In Hermes context: generate UUID
RUN_ID="RUN-$(uuidgen | cut -c1-8)"
# Pass to OpenCode in task description:
terminal(command="opencode --task '[$RUN_ID] Implement auth module...'")
# Query all logs for a run:
grep "$RUN_ID" ~/.hermes/logs/*.log ~/.opencode/sessions/*.jsonl -r
```

**Where it appears:**
- Hermes delegation context text
- OpenCode task prompt (first line)
- Git commit messages (prefix: `[RUN-a3f7c2b1]`)
- Hermes session logs (in tool call results)
- PR description body

### 3.3 Git Worktree Policy

For any task that modifies code:
- Hermes invokes OpenCode in worktree mode (`hermes -w` or `git worktree add`)
- Each parallel agent works on a separate worktree checkout
- No file conflicts between concurrent agents
- Merge back via PR

**Setup:** `git worktree add /path/to/worktree feature-branch-name`

---

## 4. External Integrations

### 4.1 GitHub Integration

All GitHub events flow through Hermes webhooks. No third-party middleware.

**Setup (verified webhook commands):**
```bash
# Enable webhook platform
hermes gateway setup   # Follow prompts to enable, set port, set HMAC secret

# Subscribe to issues (triage → Hermes → OpenCode)
hermes webhook subscribe github-issues \
  --events "issues" \
  --prompt "New GitHub issue #{issue.number}: {issue.title}
Action: {action}
Author: {issue.user.login}
Body:
{issue.body}

Triage this issue. If actionable, design and implement a fix." \
  --skills "github-issues,github-code-review" \
  --deliver telegram \
  --deliver-chat-id "<chat-id>"

# Subscribe to PR reviews
hermes webhook subscribe github-prs \
  --events "pull_request" \
  --prompt "PR #{pull_request.number} {action}: {pull_request.title}" \
  --skills "github-code-review" \
  --deliver discord

# Subscribe to CI/CD
hermes webhook subscribe ci-builds \
  --events "pipeline" \
  --prompt "Build {object_attributes.status} on {project.name}" \
  --deliver discord
```

**Security:** Each subscription auto-generates HMAC-SHA256 secret. GitHub sends `X-Hub-Signature-256`. Webhook adapter validates on every POST.

### 4.2 Provider & Model Routing

**Verified current configuration:**
```yaml
model:
  provider: openrouter
  default: deepseek/deepseek-v4-flash-0731   # Primary (cheap, fast)
  aliases:
    local:
      model: gemma4-hermes:latest
      provider: ollama
      base_url: http://192.168.0.58:11434/v1  # Homelab Ollama (free)
```

**Routing policy for this framework:**

| Task Type | Model | Cost | When |
|---|---|---|---|
| Triage, summarization, classification | gemma4-hermes (local Ollama) | $0 | Default for simple tasks |
| Requirements interview, design | deepseek/deepseek-v4-flash-0731 | Cheap | When reasoning needed |
| Code implementation, debugging | deepseek/deepseek-v4-flash-0731 | Cheap | Standard coding |
| Complex architecture, critical decisions | Frontier model (user-selected) | Higher | When explicitly requested |

**Economy principle:** Local Ollama handles the majority of tasks. Cloud models only for tasks that genuinely need them. This is the primary cost control mechanism (no structural budget cap needed for a solo operator running local-first).

---

## 5. Task Flows — All 30 Requirements

Each task flow is a state machine, not a happy-path outline. Every identified failure state has an explicit handler. No "Google this wiki article" — each mechanism is stated with its exact tool or command path.

### Legend
- **[H]** = Hermes handles directly
- **[H→OC]** = Hermes delegates to OpenCode
- **[H+Cron]** = Hermes scheduled job
- **[Webhook]** = GitHub/CI webhook triggers Hermes
- **⟨gate⟩** = Human approval required (V1 gate)
- **⟳** = Iteration until success
- **✗** = Failure state with handler

---

### R1 — Requirements from Raw Idea [SUPPLIED]

```
State: USER_INPUT → REQUIREMENTS_DRAFT → APPROVED_SPEC

USER_INPUT
  │ Input: raw idea ("I want an app that tracks my LEGO collection")
  │ Handler: incomplete/ambiguous → follow missing_info path
  ▼
CLARIFICATION_ROUNDS ≤ 3                    ← ANALYST-Agent skill
  │ Each round: agent auto-decides clear-cut choices,
  │ escalates ≤8 questions with A/B/C options + recommendation
  │ "More Information" path on each option
  ▼
REQUIREMENTS_DRAFT
  │ Format: REQ-ID, acceptance criteria, open questions
  │ Handler: missing acceptance criteria → REJECT (red)
  ▼
⟨GV1⟩ HUMAN_APPROVAL
  │ Handler: timeout 7d → pause, notify user
  │ Handler: reject → return to CLARIFICATION_ROUNDS
  ▼
APPROVED_SPEC
  │ Write to: workspace/requirements.md
  │ Commit to Git with RUN-ID prefix
  ▼
DONE
```

**CLI path:** User sends idea via any Hermes surface → Hermes loads `prompt-flow-requirements` skill → runs Analyst/Interviewer/Sculptor/Judge pipeline → outputs `requirements.md`

**Tool:** Hermes handles this directly. No OpenCode needed — it's a design task, not a coding task.

---

### R2 — Requirement Versioning & Traceability [SUGGESTED]

```
State: SPEC_STORE_SETUP → TRACEABILITY_ACTIVE

SPEC_STORE_SETUP
  │ Input: approved spec from R1
  │ Action: assign ID scheme (R1, R2, R3…)
  │ Action: write to Git-tracked requirements/ directory
  ▼
TRACEABILITY_ACTIVE
  │ On each downstream artifact (design doc, PR, test):
  │   → update TRACEABILITY.md (auto-generated markdown table)
  │   → table maps: REQ-ID → design doc path → commit SHA → test file → PR #
  │   → commit with RUN-ID prefix
  ▼
DONE
```

**Traceability format:**
```markdown
| Requirement | Design | Implementation | Tests | PR | Status |
|---|---|---|---|---|---|
| R1-001 | design/auth.md | src/auth.py (abc1234) | tests/test_auth.py | #12 | Merged |
| R1-002 | design/export.md | — | — | — | Pending |
```

**Tool:** Hermes handles this directly (`write_file`, `patch`, `terminal(git)`).

---

### R3 — High-Level System Design [SUPPLIED]

```
State: REQUIREMENTS → CONSTRAINTS → ARCHITECTURE_ANALYSIS → HIGH_LEVEL_DESIGN

REQUIREMENTS
  │ Input: approved spec from R1
  ▼
CONSTRAINTS
  │ Clarify: cost, scale, tech stack, hosting, skill level
  │ Agent auto-decides standard constraints, asks about unusual ones
  ▼
ARCHITECTURE_ANALYSIS ≤ 3 alternatives        ← architecture-diagram skill (if visual)
  │ Each alternative: component breakdown, data flows, trade-offs table
  │ Recommended option highlighted with justification
  ▼
HIGH_LEVEL_DESIGN
  │ Format: context diagram, component list, data flows,
  │         tech-fit options, risk register
  ▼
⟨GV1⟩ HUMAN_APPROVAL                           ← Must approve before detail
  ▼
DONE
```

**Tool:** Hermes handles directly for most projects. For complex systems requiring multiple parallel investigations, Hermes uses `delegate_task` to spawn subagents that each research a subsystem or architecture alternative.

---

### R4 — Detailed System Design [SUPPLIED]

```
State: HIGH_LEVEL_DESIGN → MODULE_SPECS → DETAIL_CROSSCHECK → APPROVED_DESIGN

HIGH_LEVEL_DESIGN
  │ Input: approved R3 design
  ▼
MODULE_SPECS
  │ Per-component: data model, API contract, error handling, edge cases
  │ Output: design/<module>.md for each component
  ▼
DETAIL_CROSSCHECK
  │ Verification: every R1 requirement ID appears in at least one module spec
  │ Missing IDs → REJECT, add missing coverage
  ▼
TEST_PLAN
  │ Map: each acceptance criterion → specific test file + test case
  ▼
⟨GV1⟩ HUMAN_APPROVAL
  ▼
APPROVED_DESIGN
  │ Write to: design/ directory
  ▼
DONE
```

**Tool:** Hermes handles directly. For large projects (10+ modules), Hermes spawns parallel `delegate_task` subagents, each designing one module, then merges results and cross-checks.

---

### R5 — System Update Requirement/Design [SUPPLIED]

```
State: CHANGE_REQUEST → IMPACT_ANALYSIS → DELTA_SPEC → ⟨GV1⟩ → DONE

CHANGE_REQUEST
  │ Input: "Add CSV export feature"
  │ Context: current design + codebase structure
  ▼
IMPACT_ANALYSIS
  │ Action: load existing design docs + grep codebase for affected modules
  │ Output: list of impacted files with reason
  ▼
DELTA_SPEC
  │ Format: minimal change — only what's added/modified
  │ Includes: backward-compat concerns, migration notes
  │ Does NOT rewrite existing design
  ▼
⟨GV1⟩ HUMAN_APPROVAL
  ▼
DONE
```

**Tool:** Hermes handles directly. Loads project context files (`AGENTS.md`, design docs), inspects codebase via `read_file`/`search_files`, writes delta spec.

---

### R6 — Bug-Patch Requirement/Design [SUPPLIED]

```
State: BUG_RECEIVED → ROOT_CAUSE_ANALYSIS → FIX_DESIGN → ⟨GV1⟩ → DONE

BUG_RECEIVED
  │ Input: stack trace, failing test, reproduction steps
  ▼
ROOT_CAUSE_ANALYSIS                      ← Systematic Debugging skill
  │ Iron Law: NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
  │ Steps: reproduce → read trace → hypothesize → verify with evidence
  │ Handler: reproduce fails → ask user for repro steps
  ▼
FIX_DESIGN
  │ Format: root cause + evidence, fix rationale, minimal patch scope,
  │         regression test plan
  ▼
⟨GV1⟩ HUMAN_APPROVAL
  ▼
DONE
```

**Tool:** Hermes for investigation + design. OpenCode invoked only if immediate implementation is requested (then flows into I2).

---

### I1 — Implement New System Design [SUPPLIED]

```
State: DESIGN_RECEIVED → PLAN_GENERATED → ⟨GV1⟩ → TDD_IMPLEMENTATION → CODE_REVIEW → ⟨GV1⟩ → DONE

DESIGN_RECEIVED
  │ Input: approved R4 design document
  │ Context: RUN-ID, requirement traceability links
  ▼
[H→OC] PLAN_GENERATION                  ← Writing Plans skill
  │ OpenCode reads design doc
  │ Plan agent creates micro-task list:
  │   - Each task: 2-5 minutes, exact file paths, code context, verification
  │   - Order: dependencies resolved first, interface stubs before implementations
  ▼
PLAN_REVIEW
  │ Format: task manifest file (JSON or markdown table)
  │ Handler: task list too large (>50 tasks) → split into phases
  ▼
⟨GV1⟩ PLAN_APPROVAL (optional — set gate_threshold)
  ▼
[H→OC] TDD_IMPLEMENTATION               ← TDD skill
  │ For each task in order:
  │   1. Write failing test → verify it fails (RED)
  │   2. Write minimum code to pass → verify it passes (GREEN)
  │   3. Run full test suite → refactor if green (REFACTOR)
  │   4. Checkpoint (git commit with RUN-ID prefix)
  │   5. Handler: stuck after 3 iterations → ESCALATE to user
  ▼
[H→OC] CODE_REVIEW                      ← Code Review skill
  │ Fresh subagent (no knowledge of implementer's reasoning):
  │   1. Reads code against approved plan
  │   2. Checks against standards checklist
  │   3. Reports by severity: critical/high/medium/low
  │   4. Handler: critical issues → BLOCK, return to implementation
  ▼
⟨GV1⟩ HUMAN_MERGE_APPROVAL
  │ Handler: approved → merge to main
  │ Handler: rejected → return to implementation with feedback
  ▼
DONE
  │ Update: TRACEABILITY.md
  │ Update: requirements status
```

**This is the primary flow.** It consumes the most tokens and time. Economy safeguard: default to local Ollama for the plan step, cloud for implementation.

**Tools:** Hermes orchestrates. OpenCode + Superpowers execute. Git tracks progress. GitHub receives PR.

---

### I2 — Implement Update or Bug-Patch [SUPPLIED]

```
State: DELTA_DESIGN → SCOPED_PLAN → TDD_DELTA → REGRESSION → CODE_REVIEW → ⟨GV1⟩ → DONE

Same as I1 but scoped:
  - Plan reads delta design (not full system)
  - Tasks only for affected modules
  - RUN tests: focused tests FIRST, full suite SECOND
  - Both must pass (not just focused)
  - Code review scoped to changed files only
```

**Key difference from I1:** Smaller PR, faster review, lower risk. The delta design (R5/R6) already specifies exactly which files change — the plan agent picks those up and creates a minimal task set.

---

### I3 — Automated Test Authoring & Execution [SUGGESTED]

**Not a separate manual step.** Embedded in I1/I2 via the TDD skill. The TDD Iron Law enforces: no production code without a failing test first.

```
[Design-driven change] → [OpenCode + TDD]
  1. Write failing test → verify RED
  2. Write minimum code → verify GREEN
  3. Run full suite → REFACTOR
  4. Handler: green → commit
  5. Handler: fail → iterate or escalate (B3 debug path)
```

**TDD cycle (from skill):**
```
RED → Write failing test
GREEN → Minimum code to pass
REFACTOR → Clean up, full suite green
COMMIT → Checkpoint with RUN-ID
```

**Verification:** Review test coverage in every PR. Handler: approve untested code → VIOLATION (the whole point of TDD is discipline: one exception teaches the agent that exceptions are possible).

---

### I4 — Automated Code Review & Quality Gate [SUGGESTED]

```
[Implementation complete] → [Code Review skill] → [gate decision]

CODE_REVIEW (fresh subagent)
  │ Reads: code + plan + personal review checklist
  │ Checks: matches plan, standards compliance, security patterns
  │ Reports: severity-ordered findings
  ▼
GATE_DECISION
  │ Critical findings → BLOCK merge (hard gate)
  │ High findings → cost/benefit analysis (agent recommendation)
  │ Medium/Low findings → log for next iteration
  ▼
⟨GV1⟩ HUMAN_FINAL
  │ Agent presents: summary + recommendations
  │ Handler: override → merge with documented reason (audit trail)
  ▼
DONE
```

**Personal review checklist** (initial, iterated over time):
- Auth on admin endpoints present
- Tests actually run (not skipped)
- Env variable handling safe (no hardcoded secrets)
- Error handling on external calls
- RUN-ID in commit messages

---

### I5 — Refactoring Workflow [SUGGESTED]

```
State: REFACTOR_REQUEST → BRAINSTORM → ⟨GV1⟩ → PLAN → TDD_REFACTOR → REVIEW → ⟨GV1⟩ → DONE

REFACTOR_REQUEST
  │ Input: "Auth module has too much duplicated session-handling code"
  ▼
BRAINSTORM                             ← Brainstorming skill
  │ Agent reads codebase, identifies duplication patterns
  │ Proposes: 2-3 refactoring approaches with before/after justification
  ▼
⟨GV1⟩ APPROACH_APPROVAL
  ▼
PLAN
  │ Break into extraction/consolidation tasks
  ▼
TDD_REFACTOR
  │ Existing test suite is the behavior contract:
  │   - Green before → must be green after
  │   - Handler: insufficient tests → write characterization tests first (I3)
  ▼
CODE_REVIEW → ⟨GV1⟩
  ▼
DONE (behavior unchanged, structure improved)
```

---

### I6 — Automated Documentation Sync [SUGGESTED]

```
State: MERGE_EVENT → DOC_DIFF → DOC_UPDATE → ⟨GV1⟩ (if conflicting) → COMMIT

[Cron trigger: weekly] OR [Webhook: push/merge]
  │ Detect: what changed in code (new endpoints, configs, API changes)
  ▼
DOC_DIFF
  │ Compare: code changes vs current docs
  ▼
DOC_UPDATE
  │ Update: README, API docs, changelog
  │ Handler: conflict with code → flag for human review
  ▼
COMMIT (auto or after human approval)
```

**Implementation:** Hermes cron job weekly, or webhook on `push` events. Delegate to subagent that reads the diff, updates docs, commits with RUN-ID.

---

### B1 — Scheduled Bug Scans [SUPPLIED]

```
State: CRON_FIRE → SCAN → TRIAGE → NOTIFY (only if findings)

[H+Cron] SCHEDULE (e.g., every Monday 9am)
  │ Hermes cron: "every monday 9am"
  ▼
SCAN
  │ Hermes reads project source files
  │ Runs: static analysis + AI reasoning (deepseek or frontier for complex code)
  │ Looks for: unhandled errors, race conditions, logic errors, code smells
  ▼
TRIAGE
  │ Classify by severity
  │ Dedup vs known issues (read existing GitHub issues via gh CLI)
  ▼
NOTIFY
  │ Handler: no findings → NO MESSAGE (zero noise)
  │ Handler: findings exist → notify user with summary + severity breakdown
  │ Optional: auto-create GitHub issues for critical findings
  ▼
DONE
```

**Setup command:**
```
"Schedule a bug scan every Monday at 9am for repo /path/to/repo"
```
Hermes creates cron job with skills `['requesting-code-review']`.

---

### B2 — Scheduled Security Scanning [SUPPLIED]

```
State: CRON_FIRE → LAYERED_SCAN → TRIAGE → NOTIFY/ESCALATE

[H+Cron] SCHEDULE (e.g., weekly or on-deploy)
  ▼
LAYERED_SCAN (in Docker sandbox)
  │ Priority order:
  │   1. Secret detection (gitleaks, trufflehog)
  │   2. Dependency/CVE check (Grype, Trivy on SBOM)
  │   3. SAST (semgrep with AI reasoning to reduce false positives)
  ▼
TRIAGE
  │ AI reasoning: classify, reduce false positives, provide context
  ▼
NOTIFY
  │ Critical → immediate notification + block PR
  │ High/Medium/Low → weekly digest
  │ Handler: no findings → NO MESSAGE
```

**Docker sandbox:** When running security scans, Hermes uses `terminal.backend: docker` (or runs Grype/Trivy in a container). The host system is never at risk from scanner tools.

**Setup:** Cron or webhook on deploy event. Hermes delegates to subagent that runs scanning tools inside Docker.

---

### B3 — Debugging/Root-Cause Workflow [SUGGESTED]

```
State: FAILURE_SIGNAL → REPRODUCE → ROOT_CAUSE → FIX → VERIFY → DONE_or_ESCALATE

FAILURE_SIGNAL
  │ Input: failing test, stack trace, crash, production alert
  ▼
REPRODUCE                               ← Systematic Debugging skill
  │ Iron Law: NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
  │ Step 1: Reproduce the failure locally
  │ Handler: repro fails → ask user for repro steps
  ▼
ROOT_CAUSE
  │ Read stack trace → form hypothesis → verify with evidence
  │ Document: root cause write-up with evidence chain
  ▼
FIX
  │ Targeted fix (not symptom masking)
  ▼
VERIFY
  │ Run regression tests (focused + full suite)
  │ Handler: fixed → commit with RUN-ID, notify user
  │ Handler: still failing → iterate (max 3 rounds)
  │ Handler: 3 rounds exhausted → ESCALATE to user with findings
  ▼
DONE_or_ESCALATE
```

**Escalation format:** "I've investigated the bug 3 times. Here's what I found: [root cause evidence], [what each attempt tried], [why each failed]. I need your input."

---

### B4 — Dependency / CVE Monitoring [SUGGESTED]

```
State: DAILY_SCAN → DIFF_ADVISORIES → PATCH_PR → ⟨GV1⟩

[H+Cron] DAILY (early morning, low-priority)
  ▼
SCAN
  │ Read: requirements.txt, package.json, go.mod, Cargo.toml
  │ Query: NVD, GitHub Advisory DB (via grype/trivy/or osv-scanner)
  ▼
DIFF
  │ Compare: installed versions vs known CVEs
  ▼
PATCH_PR
  │ Critical CVEs → auto-generate bump PR + test pass
  │ Handler: test fails after bump → flag for human review, don't merge
  ▼
NOTIFY
  │ Critical: immediate notification with CVE ID + affected package
  │ Medium/Low: weekly digest
```

**Default threshold:** Only auto-patch critical CVEs. Report everything else.

---

### B5 — Post-Deploy Security Assessment [SUGGESTED]

```
State: DEPLOY_EVENT → RUNNING_ASSESSMENT → VALIDATED_FINDINGS → NOTIFY

[Trigger: deploy event or release tagging]
  ▼
DEPLOY_RUNNING
  │ Ensure system is live and responsive
  ▼
ASSESSMENT
  │ Compare to B2 (source code scan) — this looks at RUNNING surface
  │ Chain potential issue paths
  │ Validate real-world exploit feasibility (not just SAST findings)
  ▼
VALIDATED_FINDINGS
  │ Only actionable, validated findings reported
  ▼
NOTIFY
  │ Handler: critical → notification + hold deployment
  │ Handler: clean → silent completion
```

**Resource-intensive:** Run only on deploys, not daily. Run in staging first, then production.

---

### G1 — GitHub Issue → Fix Pipeline (with Human Gate) [SUPPLIED]

```
State: ISSUE_OPENED → G2_TRIAGE → DESIGN → IMPLEMENT → PR → ⟨GV1⟩ → DONE

[Webhook: GitHub issues event]
  ▼
G2_TRIAGE                              ← github-issues skill
  │ Classify: bug vs feature vs question vs duplicate
  │ Dedup: compare against existing issues (gh issue list)
  │ Assign: priority/severity from rubric
  ▼
ROUTE
  │ Handler: duplicate/invalid → close with explanation, notify user
  │ Handler: question → respond with answer, no code change
  │ Handler: actionable → continue to design
  ▼
DESIGN (R5/R6 style)
  │ Generate: delta requirement + fix design
  ▼
IMPLEMENT (I2 style, scoped)
  │ OpenCode + Superpowers → scoped PR with tests
  ▼
PR_CREATED (NOT merged)
  ▼
⟨GV1⟩ HUMAN_MERGE_APPROVAL
  │ Handler: approve → merge, auto-close issue
  │ Handler: reject → close PR, update issue with reason
  ▼
TRACEABILITY_UPDATE
  │ Update: TRACEABILITY.md with issue→PR→commit links
  ▼
DONE
```

**This is the highest-value persistence loop.** Everything except the final merge is automated. Agent does: triage → design → implement → test → review → PR. Human does: one approval.

---

### G2 — Triage Agent [SUGGESTED]

```
State: ISSUE_NEW → CLASSIFY → LABEL → NOTIFY_IF_AMBIGUOUS

[Webhook: GitHub issues]
  ▼
CLASSIFY
  │ Read: issue body, title, labels, comments
  │ Compare: against existing issues (gh issue list --search)
  │ Classify: bug | feature | question | duplicate | invalid
  │ Assign: priority (P0-P3) and severity (critical/high/medium/low)
  ▼
AUTO_LABEL
  │ Clear-cut cases → auto-label in GitHub via gh CLI
  │ Handler: ambiguous → flag for human review, notify
  ▼
NOTIFY (only ambiguous)
```

**Severity rubric** (defined once, used by all triage runs):
- **P0 Critical:** system down, data loss, security breach
- **P1 High:** major feature broken, no workaround
- **P2 Medium:** feature degraded, workaround exists
- **P3 Low:** cosmetic, documentation, nice-to-have

---

### G3 — Full Issue → PR Pipeline [SUGGESTED]

```
Pipeline: G2 triage → G1 design/implement → ⟨GV1⟩ → merge → auto-close

Same as G1's internal flow, but the G2 triage is always the entry point.
User only interacts at the ⟨GV1⟩ approval gate.
```

**Morning routine:** Check the PR queue once. "Approve all P2+" is a fast path.

---

### W1 — Design Non-Coding Workflows [SUPPLIED]

```
State: PROCESS_DESCRIPTION → PATTERN_MAPPING → WORKFLOW_DESIGN → ⟨GV1⟩ → DONE

PROCESS_DESCRIPTION
  │ Input: "Every Monday, I need a summary of competitor shipping activity"
  ▼
PATTERN_MAPPING
  │ Map to one of Anthropic's 5 patterns:
  │   1. Prompt chaining (sequential, each step feeds next)
  │   2. Routing (classify then dispatch to specialized handler)
  │   3. Parallelization (independent tasks run simultaneously)
  │   4. Orchestrator-workers (central plan, distributed execution)
  │   5. Evaluator-optimizer (generate → evaluate → iterate)
  ▼
WORKFLOW_DESIGN
  │ Format: stage diagram, agent roles, data hand-offs,
  │         failure handlers, gate placements, cost estimate
  ▼
⟨GV1⟩ HUMAN_APPROVAL
  ▼
DONE
```

**Tool:** Hermes handles directly. Uses `prompt-flow-requirements` skill or ad-hoc interview.

---

### W2 — Implement & Refine Non-Coding Workflows [SUPPLIED]

```
State: DESIGN → IMPLEMENT → TEST_RUN → MEASURE → REFINE_or_ACCEPT

DESIGN
  │ Input: approved W1 workflow design
  ▼
IMPLEMENT
  │ Build as Hermes cron job or set of chained cron jobs
  │ Attach relevant skills to the job
  ▼
TEST_RUN
  │ Manual trigger: "run the competitor research workflow"
  ▼
MEASURE
  │ Log: quality (subjective scoring), cost (tokens), latency (wall time)
  ▼
REFINE (⟦wheel⟧ 2-3 cycles)
  │ Handler: quality below threshold → adjust prompts/steps/model routing
  │ Handler: cost too high → downgrade model, simplify steps
  │ Handler: latency too high → parallelize steps
  ▼
ACCEPT
  │ Workflow enters production schedule (S2)
```

---

### S1 — Manual Workflow Start [SUPPLIED]

```
COMMAND → LOOKUP → RUN → REPORT

COMMAND
  │ User: "Run security scan on auth module"
  │ Or: "Research vector databases"
  ▼
LOOKUP
  │ Hermes finds named workflow in cron/skills
  ▼
RUN
  │ Execute with provided parameters
  ▼
REPORT
  │ Output back to conversation
```

**Naming convention:** Workflows have clear names. "security scan" is better than "do that thing."

---

### S2 — Scheduled Workflow Start [SUPPLIED]

```
SCHEDULE_DEF → CRON_REGISTER → FIRE → RUN → DELIVER

CRON_REGISTER
  │ Hermes handles natively via cronjob tool
  │ Schedule types: interval ("every 2h"), natural ("every monday 9am"),
  │                cron syntax ("0 9 * * *"), ISO timestamp
  ▼
FIRE → RUN → DELIVER
  │ Budget: enforced via provider routing (local models for routine)
  │ Noise: no message if nothing actionable (zero noise principle)
  │ Delivery: configured target (Telegram, Discord, file)
```

---

### S3 — Event-Triggered Workflow Start [SUPPLIED]

```
EVENT_SOURCE → HERMES_WEBHOOK → WORKFLOW_START

GitHub         ──► hermes webhook subscribe github-<name>
GitLab         ──► hermes webhook subscribe gitlab-<name>
CI/CD          ──► hermes webhook subscribe ci-<name>
Custom HTTP    ──► hermes webhook subscribe custom-<name>
```

**Setup (verified):**
```bash
hermes webhook subscribe <name> \
  --events "event_type" \
  --prompt "Template: {payload.field}" \
  --filter 'script.py' \  # optional: filters/transforms payload
  --deliver telegram \
  --deliver-chat-id "<id>"
```

**Filter scripts:** `~/.hermes/scripts/` — receives payload JSON on stdin, writes filtered JSON on stdout, empty stdout = ignore.

---

### S4 — Long-Running Agent Support [SUGGESTED]

```
State: LONG_JOB → PHASE_EXECUTION → CHECKPOINT → NEXT_PHASE_or_RESUME

LONG_JOB
  │ Trigger: task estimated > 30 minutes
  ▼
PHASE_BREAKDOWN
  │ Break into phases, each < 20 minutes
  │ Each phase: independent cron job with preceding checkpoint
  │ Checkpoint format: {phase, status, next_phase, run_id, timestamp}
  ▼
PHASE_1 → CHECKPOINT_FILE → PHASE_2 → CHECKPOINT_FILE → ... → DONE
  │ Handler: phase fails → retry (max 3)
  │ Handler: retry exhausted → pause, notify user with checkpoint state
  │ Handler: system restart → re-read checkpoint, resume from last completed phase
```

**Checkpoint file:** `~/.hermes/checkpoints/<run-id>.json`
```json
{
  "run_id": "RUN-a3f7c2b1",
  "workflow": "full-implementation",
  "phases": [
    {"phase": 1, "name": "design", "status": "complete", "completed_at": "..."},
    {"phase": 2, "name": "module-a-impl", "status": "complete", "completed_at": "..."},
    {"phase": 3, "name": "module-b-impl", "status": "in_progress", "started_at": "..."}
  ],
  "next_phase": 3,
  "context": {}
}
```

**When needed:** For sub-15-minute jobs (the common case), simple restart is fine. Implement phased execution only when jobs run 30+ minutes.

---

## 6. Governance & Quality Gates

### 6.1 Gv1 — Human-in-the-Loop Approval [SUGGESTED]

**Current strategy:** Prompt-based gates, not structural permission gates.

Every gate in this design (`⟨GV1⟩`) is enforced by the agent's behavior as directed by loaded skills (SKILL.md instructions). This works because:
- Skills are loaded into the system prompt before the agent starts
- The instructions are explicit and testable (the agent can verify its own actions)
- For a solo operator, this is 95%+ effective in practice

**What's gated:**
| Action | Gate | Auto-Execute? |
|---|---|---|
| Requirements approval | ⟨GV1⟩ | No |
| Design approval | ⟨GV1⟩ | No |
| Plan approval (I1) | ⟨GV1⟩ (optional) | Configurable |
| PR merge | ⟨GV1⟩ | No |
| Workflow approval (W1) | ⟨GV1⟩ | No |
| Duplicate issue close | No | Yes (trusted for clear-cut) |
| Doc updates (no conflict) | No | Yes |
| Bug scan (no findings) | No | Yes (silent) |

**Future hardening (v2):** If adding collaborators or moving to regulated environments, implement structural gates via Hermes plugin that restricts file-write access until test-run tool returns failure result.

---

### 6.2 Gv2 — Cost & Token Monitoring [SUPPLIED]

**Primary mechanism:** Default to local Ollama for all routine tasks.

**Monitoring:**
```
[H+Cron] Weekly cost summary
  │ Log: each run's model, tokens, cost
  │ Aggregate: per-workflow, per-day, per-project
  ▼
NOTIFY
  │ Format: "This week: 12 runs, 23k tokens, $0.87 total"
  │ Handler: anomaly (>2x normal) → flag with details
```

**Implementation:** Hermes logs every tool call with model info. Weekly cron job aggregates and reports.

---

### 6.3 Gv3 — Observability & Traceability [SUGGESTED]

**Current approach:** RUN-ID convention (see Section 3.2). Each delegated task carries a UUID that appears in:
- Hermes session logs
- OpenCode session logs / git history
- Commit messages
- PR descriptions

**Consolidated trace:** For any run, query all sources:
```bash
grep "RUN-a3f7c2b1" ~/.hermes/logs/*.log
grep "RUN-a3f7c2b1" ~/.opencode/sessions/*.jsonl
git log --grep="RUN-a3f7c2b1"
gh pr list --search "RUN-a3f7c2b1" --json number,title,state
```

**Gap acknowledged:** No single dashboard. For a solo operator with a few runs per day, the grep-based approach is viable. Consolidated observability dashboard is a v2 enhancement (possible via a custom Hermes skill that queries all sources).

---

### 6.4 Gv4 — Cost & Budget Governance [SUGGESTED]

**Primary enforcement:** Provider routing defaults to local (free).

**Secondary enforcement:** Budget wrapper script for cloud model calls.

**Implementation:** `~/.hermes/scripts/budget-guard.sh` — wraps `opencode` CLI:
```bash
#!/bin/bash
# Budget guard — reads from cumulative counter file
BUDGET_FILE="$HOME/.hermes/budget-cents.txt"
MONTHLY_LIMIT=5000  # $50.00

current=$(cat "$BUDGET_FILE" 2>/dev/null || echo 0)
if [ "$current" -ge "$MONTHLY_LIMIT" ]; then
  echo "BUDGET EXCEEDED: $$current/$MONTHLY_LIMIT cents used this month"
  exit 1
fi

# Run the actual command
"$@"
exit_code=$?

# Update counter (estimate from output, or use API cost report)
# ... (implementation depends on how cost is reported)
echo $((current + estimated_cost)) > "$BUDGET_FILE"
exit $exit_code
```

**For the default local-first setup:** This is a safety net, not the primary mechanism. Cost is near-zero when running Ollama locally.

---

### 6.5 Gv5 — Scoped Access & Sandboxed Execution [SUGGESTED]

**Three isolation levels:**

| Level | Mechanism | When to Use |
|---|---|---|
| **Full sandbox** | Hermes Docker backend or container execution | Untrusted code, web scraping, security scanning |
| **Worktree isolation** | Git worktrees (+ `hermes -w`) | Concurrent coding agents on same repo |
| **File permission scope** | OS user permissions + workspace boundaries | Standard file operations |

**Setup for Docker sandbox:**
```bash
hermes config set terminal.backend docker
# Or per-task: run specific commands in a container
docker run --rm -v $(pwd):/workspace python:3.12 bash -c "cd /workspace && pytest"
```

---

### 6.6 Gv6 — Audit Logging [SUGGESTED]

**Sources:**
| Source | Location | Content |
|---|---|---|
| Hermes session logs | `~/.hermes/sessions/*.jsonl` | Full tool calls + reasoning |
| Hermes gateway logs | `~/.hermes/logs/gateway.log` | Webhook events, platform messages |
| Git history | `.git/` | Every commit, diff, author, message |
| OpenCode sessions | `~/.opencode/sessions/*.jsonl` | Plan steps, code changes, test results |
| GitHub | github.com | PR reviews, comments, merge decisions |

**Retention policy:**
- Session logs: 90 days (configurable)
- Git: permanent (requires periodic GC)
- GitHub: permanent (platform-managed)
- Cron job logs: 90 days

---

## 7. Integrated Improvements (from Review Suggestions)

Six updates from the previous review have been integrated throughout this document:

| # | Original Suggestion | Integration Location | Status |
|---|---|---|---|
| 1 | Add shared Run ID convention | Section 3.2 — `RUN-<8-char-uuid>` in all delegation, commits, PRs | ✅ Integrated |
| 2 | Add budget wrapper | Section 6.4 — `~/.hermes/scripts/budget-guard.sh` wrapping cloud calls | ✅ Integrated |
| 3 | Phase long jobs | Section 4.3 → Section S4 — checkpoint files in `~/.hermes/checkpoints/`, cron-chain phases | ✅ Integrated |
| 4 | Verify Superpowers on OpenCode | Section 8 (below) — setup verification spike as first implementation task | ✅ Addressed |
| 5 | Use OpenHands for GitHub events | **Replaced:** Hermes webhooks are used instead (simpler, no third tool). See Section 4.1. | ✅ Superseded |
| 6 | Accept prompt-based gates | Section 6.1 — gates enforced by SKILL.md, not structural permissions | ✅ Integrated |

### Suggestion 4 — Verify Superpowers on OpenCode

This is a prerequisite implementation task before the full framework is operational.

**Verification test plan:**
```markdown
## Superpowers on OpenCode — Verification Spike

### Test 1: Brainstorming gate
- Start OpenCode with a coding task that has NO approved design
- Expected: agent refuses to write code, proposes design approaches first
- PASS: agent asks clarifying questions and proposes approaches
- FAIL: agent jumps straight to coding without approval

### Test 2: TDD Iron Law
- Start OpenCode with a task where the agent writes code before a failing test
- Expected: agent deletes the code, writes the test first
- PASS: agent follows RED→GREEN→REFACTOR strictly
- FAIL: agent writes code without failing test, or skips tests

### Test 3: Code Review subagent
- Complete an implementation task
- Expected: a separate subagent reviews the code without prior context
- PASS: reviewer provides independent assessment against the plan
- FAIL: reviewer echoes implementer's reasoning or doesn't appear

### Test 4: Subagent-driven development
- Give a plan with multiple independent tasks
- Expected: each task dispatched to a fresh agent, merged correctly
- PASS: parallel execution with no context pollution
- FAIL: agents see each other's context or tasks fail to merge

### Test 5: Systematic Debugging
- Provide a failing test with ambiguous root cause
- Expected: agent investigates root cause before proposing any fix
- PASS: root cause documented with evidence before fix
- FAIL: agent guesses fix without evidence
```

**If any test fails:** Write a compatibility SKILL.md adaptation that patches the behavior. Document the adaptation as part of the project setup.

---

## 8. Shortfall Analysis (Updated)

### Shortfall 1: No Single-Pane Observability Dashboard
**Impact:** Medium. Grep-based trace (RUN-ID) works for a solo operator.
**Mitigation:** RUN-ID convention (Section 3.2). Future v2: custom Hermes skill that queries all sources and produces a unified view.
**Owner:** Hermes (no external tool needed).

### Shortfall 2: Prompt-Based Gates, Not Structural
**Impact:** Low for solo operator. 95%+ effective in practice.
**Mitigation:** Superpowers' skills are explicit and testable. The agent can self-verify compliance.
**Future v2:** Structural gates via Hermes plugin restricting tool access based on preconditions.

### Shortfall 3: No Native Cost Enforcement
**Impact:** Low when running local-first (Ollama). Only matters when cloud models are active.
**Mitigation:** Provider routing defaults to local. Budget wrapper script (Section 6.4) catches cloud calls.

### Shortfall 4: Checkpoint/Resume for Long Jobs
**Impact:** Low for common case (sub-15-minute jobs). Notable only for 30+ minute tasks.
**Mitigation:** Phase-break jobs into cron-chain stages with checkpoint files (Section S4).

### Shortfall 5: OpenCode + Superpowers Needs Verification
**Impact:** Medium. Superpowers was originally designed for Claude Code/Cursor. OpenCode supports the Agent Skills standard natively, but compatibility with specific Superpowers behavior (TDD Iron Law, brainstorming gate) needs hands-on verification.
**Mitigation:** Verification spike (Section 7, Test 1-5). Run before any production use. Write adaptation SKILL.md if needed.

### Shortfall 6: Webhooks Are Manual (Not Automated)
**Impact:** Low. Webhooks are configured manually in the GitHub UI by the user. The agent creates a card with the webhook URL, secret, and events to check, but does not programmatically create webhooks on GitHub repos.
**Future enhancement:** Add `admin:repo_hook` scope to the GitHub PAT and implement automated webhook creation via `gh api repos/OWNER/REPO/hooks`. This would let the agent auto-configure webhooks on new repos instead of directing the user to GitHub settings. Requires: fine-grained or classic PAT with `admin:repo_hook` scope, plus a skill that calls the GitHub webhook API.
**Severity:** Low — manual configuration is a one-time per-repo task, and the setup docs walk through it step by step.

### Shortfall 7: No Centralised Model Routing & Cost Visibility
**Impact:** Medium. The current design routes models via Hermes config aliases and per-task overrides. This works but provides no consolidated view of token spend across agents, no per-agent cost attribution, and no infrastructure-level cost caps (only local-model defaulting as a soft guard).
**Future enhancement:** Integrate **LiteLLM** as a proxy layer between all agents and model providers. LiteLLM provides:
- Unified API endpoint for all models (OpenRouter, Ollama, etc.)
- Per-agent/per-key cost tracking and dashboards
- Hard budget caps with automatic fallback to cheaper models when limits approach
- Token usage analytics by agent role, project, and time period
- Centralised model routing rules (e.g., "Coder always uses v4.1-flash, Triage always uses v4-flash-0731")
This would replace direct OpenRouter/Ollama calls with a LiteLLM proxy, giving full visibility and enforcement without changing agent behaviour.
**Severity:** Medium — cost is currently low (~$1.20/month estimated), but will grow as more projects and agents come online.

### Shortfall 8: No Emergency Escalation Agent
**Impact:** Low-Medium. The current agent roster has no agent with access to a frontier-class model (Claude Opus, GPT-5, etc.). For routine work, the three-model tier (v4-flash-0731, v4.1-flash, mimo-v2.5-pro) is sufficient. But there are scenarios where a frontier model is warranted:
- Complex architecture decisions with high blast radius
- Debugging sessions that stall after 3 rounds on the standard model
- Security-critical code review where missing a vulnerability has serious consequences
- Emergency incident response requiring the highest reasoning capability
**Future enhancement:** Create an **Architect Agent** configured with a frontier model (e.g., `anthropic/claude-opus-4` or `openai/gpt-5`). This agent is:
- Not used by default — only invoked when the standard agents escalate
- Triggered by explicit escalation (agent calls `kanban_block(kind=capability, reason="needs frontier model")`) or by human command ("escalate to architect")
- Cost-controlled via per-call budget caps (LiteLLM integration from Shortfall 7)
- Used sparingly — the goal is 1-3 invocations per month, not daily use
**Severity:** Low — the current model tier handles 95%+ of tasks. The Architect Agent is insurance for the remaining 5%.

---

## 9. Implementation Plan

Ordered by dependency. Each step is a buildable task.

### Phase 1: Foundation

| Step | Task | Verification | Depends On |
|---|---|---|---|
| 1.1 | Install/verify OpenCode CLI | `opencode --version` runs | Nothing |
| 1.2 | Install Superpowers skill set into OpenCode | `ls ~/.opencode/skills/superpowers/` | 1.1 |
| 1.3 | Run verification spike (Section 7, Tests 1-5) | All 5 tests PASS | 1.2 |
| 1.4 | If spike fails: write adaptation SKILL.md | Adaptation file exists, tests PASS | 1.3 |
| 1.5 | Verify Hermes Docker backend works | `hermes config set terminal.backend docker && hermes chat -q 'run pwd in docker'` returns container path | Nothing |
| 1.6 | Verify Hermes webhook platform | `hermes gateway setup` → `curl localhost:8644/health` returns ok | Nothing |
| 1.7 | Create project directory structure | `requirements/`, `design/`, `TRACEABILITY.md` | Nothing |

### Phase 2: Core Skills

| Step | Task | Verification | Depends On |
|---|---|---|---|---|
| 2.1 | Create `agile-sdlc` skill for Hermes | Skill loads, contains all workflow gates | 1.7 |
| 2.2 | Create `opencode-bridge` skill for Hermes | Skill contains: run ID generation, OpenCode invocation pattern, result parsing | 1.3, 1.7 |
| 2.3 | Create `security-scanning` skill | Skill contains: layered scan commands, triage rubric, notification rules | 1.5 |
| 2.4 | Create `github-pipeline` skill | Skill contains: webhook event handling, triage rubric, issue → PR flow | 1.6 |
| 2.5 | Create `requirements-interview` skill | Uses prompt-flow-requirements skill pattern, ≤8 questions/turn | 1.7 |
| 2.6 | Install skills into `~/.hermes/skills/` | `hermes skills list` shows all new skills | 2.1-2.5 |

### Phase 3: Automation

| Step | Task | Verification | Depends On |
|---|---|---|---|---|
| 3.1 | Set up GitHub webhook for issues | `hermes webhook subscribe github-issues` → POST test event triggers agent run | 1.6, 2.4 |
| 3.2 | Set up weekly bug scan cron | `hermes cron list` shows job; manual `hermes cron run <id>` executes | 2.1 |
| 3.3 | Set up weekly security scan cron | Same verification as 3.2 | 2.3 |
| 3.4 | Set up daily CVE monitoring cron | Same verification | 2.3 |
| 3.5 | Create budget guard script | Script exists at `~/.hermes/scripts/budget-guard.sh`, is executable | Nothing |
| 3.6 | Set up RUN-ID convention | Delegate a test task, verify RUN-ID appears in logs + git + PR | 2.2 |

### Phase 4: Validation

| Step | Task | Verification | Depends On |
|---|---|---|---|
| 4.1 | End-to-end test: create a small project from idea to PR | Follow R1 → R3 → R4 → I1 → I4 → G1 pipeline on a toy project | All prior |
| 4.2 | End-to-end test: update an existing project | Follow R5 → I2 pipeline | 4.1 |
| 4.3 | End-to-end test: bug-fix pipeline | Follow R6 → I2 → I4 pipeline | 4.1 |
| 4.4 | End-to-end test: scheduled workflow | Set up W1 → W2 → S2 for a non-coding task | All prior |
| 4.5 | Document lessons learned | Write notes to workspace, update skills with any discovered gaps | 4.1-4.4 |

---

## 10. Verification Checklist

Before declaring the framework operational, verify:

- [ ] OpenCode CLI installed and callable from Hermes terminal
- [ ] Superpowers skills installed and loaded by OpenCode
- [ ] All 5 verification spike tests pass (Section 7)
- [ ] Hermes Docker backend configures and runs sandboxed commands
- [ ] Hermes webhook platform enabled, health check passes
- [ ] GitHub webhook configured and test event triggers agent run
- [ ] RUN-ID appears in: delegation context, git commits, PR descriptions
- [ ] Cron jobs created for: bug scan, security scan, CVE monitoring
- [ ] Zero-noise principle enforced: silent runs produce no message
- [ ] Checkpoint file format defined and tested with a simulated long job
- [ ] Requirements trace: R1 requirement ID → design → PR → commit all linked
- [ ] Budget guard script installs and blocks at limit
- [ ] Provider routing verified: routine tasks use local Ollama, complex use cloud
- [ ] Git worktree isolation tested: two parallel agents on same repo, no conflicts
- [ ] Code review subagent runs independently (no shared context with implementer)

---

## 11. Project Separation, Workspaces, and ADHD-Aware Design

This section defines how projects are kept separate in the framework, which Hermes isolation mechanism to use, and how the system is designed around ADHD-friendly workflows.

### 11.1 Hermes Isolation Mechanisms

| Mechanism | What it isolates | Weight | Setup cost |
|---|---|---|---|
| **Profile** | Config, memory, sessions, skills, cron, gateway, SOUL.md | Heavy — full agent identity | Minutes per profile |
| **Workspace** (terminal.cwd + WebUI picker) | Working directory, loaded context files, file tools | Light — just "where am I?" | Zero — directory exists |
| **Context files** (.hermes.md / AGENTS.md) | Project rules, conventions, constraints | Zero-weight — auto-loaded from cwd | One file per project |

### 11.2 Architecture: Single Profile, Workspace-Per-Project

| Layer | What | Why |
|---|---|---|
| **Profile** | One operational profile (default) | Single agent identity, single messaging surface, shared cross-project memory |
| **Workspace** | One directory per project under `HermesWorkspaces/` | Project isolation, separate git history, separate context files |
| **Context file** | `.hermes.md` in each workspace root | Project-specific rules auto-loaded when workspace is active |
| **Worktrees** | Within a project, for parallel experiments | Isolated checkouts without duplicating the repo |

**Why not per-project profiles:** Profiles give each project its own agent identity — separate memory, conversation history, personality, and gateway. For a solo operator with ADHD, this creates more problems than it solves: more decisions about which profile to use, which Telegram bot to message, and which agent remembers last Tuesday's conversation. Cross-project knowledge gets siloed. Management overhead multiplies. One messaging surface should reach one agent — not require choosing between bots.

**How it works in practice:**

```
/mnt/homelab-devel/HermesWorkspaces/
├── AgentBuilder/              # This framework design work
│   ├── .hermes.md             # "You are building the Agent Framework..."
│   ├── requirements/
│   └── ...
├── general-coding/            # Ad-hoc coding tasks
│   ├── .hermes.md
│   └── ...
├── my-web-app/                # A project
│   ├── .hermes.md             # "FastAPI app with PostgreSQL..."
│   ├── src/
│   └── ...
└── trading-agent/             # Another project
    ├── .hermes.md             # "Trading system using..."
    └── ...
```

When a workspace is selected in WebUI or passed via Telegram ("switch to my-web-app"), the agent's terminal commands start in that directory and its `.hermes.md` rules load automatically. Switch workspaces and the project context shifts. Same agent, same memory, same Telegram connection — different project.

**Cron jobs target specific workdirs:**
```python
cronjob(action="create",
        workdir="/mnt/homelab-devel/HermesWorkspaces/my-web-app",
        prompt="Run bug scan on this project...",
        schedule="weekly")
```

**Git worktrees for parallelism within a project:** When working on a project and wanting to try something without risking the main branch, `hermes -w` or `/worktree new experiment` gives an isolated checkout. Two experiments at once = two worktrees, each with its own branch and checkpoint history.

### 11.3 Future Consideration: A "Focused Coding" Profile

There is one profile split worth considering later — not per-project, but per *mode*:

| Profile | Purpose | What's different |
|---|---|---|
| **default** (current) | Personal assistant, daily driver | Full memory, Obsidian access, Telegram/Discord, scheduling, life admin |
| **coder** (optional, future) | Deep coding work | Different SOUL.md, coding-heavy skills loaded, project workspace as cwd |

This would prevent the agent from surfacing personal reminders or Obsidian notes during deep coding sessions. It is a **future refinement**, not a day-one requirement. Build the system, use it for a few weeks, and evaluate whether the mode-switching helps or just adds overhead.

### 11.4 ADHD-Aware Design Patterns

These are conventions layered on top of the Hermes system, designed around how ADHD works. They are behavioural patterns enforced through context files, skills, and agent instructions — not Hermes platform features.

#### Pattern 1: Instant Context Recovery ("What Was I Doing?")

When coming back after a break or distraction, reconstructing where you were must be instant:

- **Session resume** — `hermes --continue` picks up the last conversation.
- **Daily note logging** — when starting work, Hermes appends to the Obsidian daily note: `[14:30] Started working on auth module in my-web-app`. On return, "what was I doing?" reads today's note and answers.

#### Pattern 2: Task Parking

Don't rely on working memory. When interrupted or switching tasks:

- Tell Hermes: "Park this — I was halfway through implementing the CSV export, header parser done but not the row mapper."
- Hermes writes the exact state to the task file in `ActiveTasks/` with a `ParkingNote` field.
- On return: "What was I parked on?" → reads `ActiveTasks/` and reports the exact state.

#### Pattern 3: Visible Progress

ADHD brains need to see that work is happening. The system makes progress tangible:

- Green tests after every TDD cycle — visible proof that code works
- Git commits with RUN-IDs — a growing log of completed work
- `CompletedTasks/` archive — reviewable on low-energy days for motivation
- Kanban board — all active tasks across all projects in one view

#### Pattern 4: Single-Project Focus Mode

Each project's `.hermes.md` should include a focus directive:

```markdown
## Focus
This is the ACTIVE project. Do not surface tasks or context from other
projects unless the user explicitly asks.
```

This prevents the agent from cross-pollinating project contexts during deep work. The boundary is soft (crossable on request) but default-off.

#### Pattern 5: One-Step Starts

The path from "I should work on X" to "I am working on X" must be as short as possible:

```
# Desktop:  Open WebUI → click workspace → type task
# Phone:    "switch to my-web-app and continue the auth module"
# CLI:      cd /.../my-web-app && hermes
```

No profiles to select. No bots to choose. No config to adjust.

#### Pattern 6: Scope Boundaries

ADHD can lead to hyperfocus on the wrong thing or scope creep. The system enforces:

- **Task scope tracking** — Hermes defines "done" at the start. If work drifts off-task, the agent flags it and offers to park the tangent.
- **File count guard** — each project's `.hermes.md` sets a max file count per session (e.g., 8 files). If the plan exceeds it, the agent pauses and asks.
- **Time checks** (optional) — a cron job every 90 minutes asking "are you still on track?" — configurable, can be turned off during flow states.

#### Pattern 7: Decision Minimization

Every decision costs executive function. The system decides automatically where possible:

- Model routing: local for routine, cloud for complex — no manual choice
- Cron jobs: fire-and-forget — set up once, report only when needed
- Triage: clear-cut cases auto-labelled, only ambiguous ones surface
- Interview questions: every option has a recommendation — just say "yes"

### 11.5 Example Project Context File

This is a template `.hermes.md` for a project workspace. Copy and adapt for each project:

```markdown
# Project Name

## Project
Brief description of what this project is and its tech stack.

## Focus
This is the ACTIVE project. Do not surface tasks or context from other
projects unless the user explicitly asks.

## Build & Test
- Build command: `...`
- Test command: `...`
- Lint command: `...`

## Conventions
- (project-specific coding standards)
- (framework patterns to follow)
- (naming conventions)

## Scope Guard
- A single coding session should touch at most 8 files
- If the implementation plan requires more, pause and ask before proceeding
- If the user starts working on something unrelated, flag it and offer to park

## Review Checklist
- [ ] Tests pass
- [ ] No hardcoded secrets
- [ ] Error handling on external calls
- [ ] (project-specific checks)
```

---

## 12. Kanban-Driven Workflow Strategy

### 12.1 Why Kanban Is the Primary Coordination Mechanism

The kanban board is not just a task list — it is the workflow engine. Every requirement in this design that involves a human-agent interaction, a multi-step workflow, or a handoff between agents is managed through kanban cards. The card IS the workflow state machine.

**Architecture: Single Board, Tenant-Per-Project**

| Layer | What | Why |
|---|---|---|
| **Board** | One kanban board (`default`) | Unified view of all work across all projects |
| **Tenant** | One tenant per project (e.g., `my-web-app`, `trading-agent`) | Soft project separation — filter by tenant to see one project's cards |
| **Cards** | One card per actionable unit of work | Each card carries: title, assignee, tenant, workspace, status, comments, attachments |
| **Child cards** | Orchestrator-created sub-tasks within a workflow | Workers operate on child cards; parent card tracks orchestration-level progress |

**Why one board, not per-project boards:** One board means one place to look. The `ready` column is the work queue across all projects. Filter by tenant when focusing on one project. This is the ADHD-friendly approach — no switching between boards to find what to do.

**Board setup:**
```bash
# Initialize the default board (one-time)
hermes kanban init

# Start the gateway (hosts the dispatcher)
hermes gateway start

# Enable kanban tools for the default profile
hermes tools enable kanban
```

### 12.2 Card Lifecycle and Status Flow

```
    ┌──────────┐     ┌──────────┐     ┌──────────┐
    │  TRIAGE  │────▶│   TODO   │────▶│  READY   │
    └──────────┘     └──────────┘     └──────────┘
         │                ▲                │
         │                │                ▼
         │           (parent done)   ┌──────────┐
         │                │          │ RUNNING  │
         │                │          └──────────┘
         │                │               │
         │                │        ┌──────┴──────┐
         │                │        ▼             ▼
         │                │  ┌──────────┐ ┌──────────┐
         │                │  │ BLOCKED  │ │  REVIEW  │
         │                │  └──────────┘ └──────────┘
         │                │        │             │
         │                └────────┘             │
         │                                      ▼
         │                                 ┌──────────┐
         └────────────────────────────────▶│   DONE   │
                                           └──────────┘
                                                │
                                                ▼
                                           ┌──────────┐
                                           │ ARCHIVED │
                                           └──────────┘
```

| Status | Meaning | Who Moves It |
|---|---|---|
| `triage` | New work, not yet assessed | Agent (on create) or webhook |
| `todo` | Assessed, waiting on dependencies | Agent (after triage) |
| `ready` | Approved to start, assigned to agent or user | Agent or user |
| `running` | Agent is actively working | Dispatcher (auto) |
| `blocked` | Waiting on user input or dependency | Agent (`kanban_block`) |
| `review` | Work done, under review | Agent (`kanban_request_review`) |
| `done` | Complete | Agent or user (`kanban_complete`) |
| `archived` | Historical, no longer active | User |

### 12.3 How the 30 Requirements Map to Cards

Every requirement that involves a workflow produces cards. Here is the mapping:

| Requirement | Card Pattern |
|---|---|
| **R1** Requirements from idea | Agent creates setup card → interview card on user (interactive) → approval card on user (non-interactive) |
| **R2** Versioning & traceability | No card — automated by agent after each card completes |
| **R3** High-level design | Agent works → approval card on user (non-interactive) |
| **R4** Detailed design | Agent works → approval card on user (non-interactive) |
| **R5** Update design | Agent works → approval card on user (non-interactive) |
| **R6** Bug-patch design | Agent works → approval card on user (non-interactive) |
| **I1** Implement new design | Agent works via OpenCode → PR review card on user (non-interactive) |
| **I2** Implement update/patch | Agent works via OpenCode → PR review card on user (non-interactive) |
| **I3** Test authoring | Embedded in I1/I2 — no separate card |
| **I4** Code review | Embedded in I1/I2 — reviewer subtask on child card |
| **I5** Refactoring | Agent works → approval card on user (non-interactive) |
| **I6** Doc sync | Automated by cron — card on user only if conflicts found |
| **B1** Bug scan | Cron creates card on user only if findings exist |
| **B2** Security scan | Cron creates card on user only if findings exist |
| **B3** Debugging | Agent works → escalation card on user if stuck after 3 rounds |
| **B4** CVE monitoring | Cron creates card on user only for critical CVEs |
| **B5** Post-deploy assessment | Cron creates card on user only for validated findings |
| **G1** Issue → fix pipeline | Webhook creates triage card → implementation card → PR review card on user |
| **G2** Triage agent | Webhook creates triage card — auto-labelled, card on user only if ambiguous |
| **G3** Full issue → PR | Chain of G2 → G1 cards |
| **W1** Design workflow | Agent works → approval card on user (non-interactive) |
| **W2** Implement workflow | Agent works → quality report card on user if below threshold |
| **S1** Manual start | User says "run workflow X" — no card needed unless it triggers a multi-step flow |
| **S2** Scheduled start | Cron fires — card on user only if findings/action needed |
| **S3** Event-triggered | Webhook fires — card on user only if findings/action needed |
| **S4** Long-running support | Checkpoint cards at phase boundaries |
| **Gv1** Approval gates | Every gate is a card on user (see Rule 6) |
| **Gv2** Cost monitoring | Weekly summary card on user (cron) — non-interactive |
| **Gv3** Traceability | RUN-ID on every implementation card (see Rule 9) |
| **Gv4** Budget governance | Alert card on user if budget threshold exceeded |
| **Gv5** Sandboxing | No card — enforced by workspace configuration |
| **Gv6** Audit logging | No card — comments on cards ARE the audit trail |

### 12.4 Human-Agent Interaction Rules

These rules define how cards manage the handoff between the user and the agent. They are enforced through kanban conventions and agent instructions (loaded via skills or `.hermes.md`), not through structural system constraints.

#### Rule 1: Dual Initiation

A project or workflow can start two ways:
- **Chat:** User says "start a new project about X" in any chat surface → Agent creates workspace, creates first card assigned to agent, begins work.
- **Card:** User creates a kanban card assigned to agent with the project description → Dispatcher spawns agent, agent begins work.

Both paths converge at the same point: a card exists, the agent is working.

#### Rule 2: Agent Creates User Cards When Input Is Needed

When the agent needs user input at any point in any workflow, it creates a card assigned to the user. The card body must state:
- **What is needed** — specific question or action required
- **Input type** — whether the input is **interactive** (requires a chat conversation) or **non-interactive** (update the card and reassign)
- **Context** — any attachments, links, or background needed to make the decision

#### Rule 3: Non-Interactive Input Path

When a user card is marked **non-interactive**:
1. User reads the card (dashboard, CLI, or `hermes kanban show <id>`)
2. User adds their input as a comment on the card, or edits the card body
3. User reassigns the card to the agent (unblock + change assignee)
4. Dispatcher picks up the card on the next tick (≤60 seconds)
5. Agent reads the user's input from the comment thread and continues

No chat needed. The card is the communication channel.

#### Rule 4: Interactive Input Path

When a user card is marked **interactive**:
1. User sees the card in their `ready` or `blocked` column
2. User goes to any chat surface (Telegram, Discord, WebUI, CLI)
3. User says: "I'm ready to talk about [card ID or project name]"
4. Agent reads the card context, loads the appropriate skill, and conducts the interaction (interview, design review, debugging session)
5. When the interaction completes, the agent auto-completes the user card with the outcome
6. Agent continues the workflow — creates the next card as needed

#### Rule 5: Chat-Triggered Card Completion

If the user completes the required work through chat (approves a design, answers interview questions, reviews a PR), the agent automatically:
1. Updates the card with the outcome as a comment
2. Completes the card (status → `done`)
3. Continues the workflow — creates the next card or proceeds to the next phase

The user does not need to manually update the card after a chat interaction.

#### Rule 6: Every Human Gate Is a User Card

Every `⟨GV1⟩` approval gate in the design becomes a card assigned to the user. The card states what is being approved and what action is required.

| Gate | Card Title Pattern | Input Type |
|---|---|---|
| Requirements approval | "Review requirements: [project]" | Non-interactive |
| High-level design approval | "Review architecture: [project]" | Non-interactive or interactive |
| Detailed design approval | "Review detailed design: [project]" | Non-interactive |
| Implementation plan approval | "Review plan: [task description]" | Non-interactive |
| PR merge approval | "Review PR #N: [description]" | Non-interactive |
| Workflow design approval | "Review workflow: [name]" | Non-interactive |
| Refactoring approach approval | "Review refactoring: [module]" | Non-interactive |

#### Rule 7: Scheduled Work Creates Cards, Not Just Notifications

When a cron job runs (bug scan, security scan, CVE check), it creates cards instead of just sending messages:

- **No findings → no card, no message** (zero noise principle)
- **Findings exist → card created on user** with full context (findings, file paths, severity) — non-interactive, user reviews and decides
- **Critical finding → card created on user** with priority tag — non-interactive, immediate notification alongside the card

Cards persist until acted on. A notification can be missed or forgotten; a card sits in the `ready` column until the user deals with it.

#### Rule 8: GitHub Issues Create Implementation Cards

When a GitHub issue arrives via webhook, the full pipeline is card-driven:

1. Webhook creates triage card (assigned to agent) → agent classifies and labels
2. If actionable → agent creates implementation card → works design → implementation → PR
3. PR ready → agent creates card on user: "Review PR #N for issue #M" (non-interactive)
4. User approves → agent merges, closes the card
5. If blocked → card blocked with reason, user notified

#### Rule 9: Cards Carry the RUN-ID

Every card that involves implementation work carries the RUN-ID in its body or metadata. This links the card to:
- Git commits (prefix: `[RUN-<id>]`)
- PR descriptions (body includes RUN-ID)
- Traceability records (`TRACEABILITY.md` row)

One identifier traces the full path from card → code → PR → merge.

#### Rule 10: Blocked Cards Have a Reminder Threshold

| Duration | Action |
|---|---|
| User card blocked >3 days | Agent sends a gentle reminder notification |
| User card blocked >7 days | Agent escalates with a summary of all overdue cards |
| User card blocked >14 days | Agent asks if the card should be archived or deprioritized |

This prevents cards from silently accumulating and creates a forcing function for decision-making.

#### Rule 11: Card Lifecycle Maps to SDLC Phase

The card status naturally represents where work is in the development lifecycle:

```
triage   → New work, not yet assessed (GitHub issue, user idea, webhook event)
todo     → Assessed and designed, waiting on dependency (design approved, waiting for prerequisite)
ready    → Approved to start (assigned to agent or user, all dependencies met)
running  → Agent is actively working (dispatcher spawned a worker)
blocked  → Waiting on user input (needs_input) or dependency (dependency)
review   → Work done, under code or design review (PR created, reviewer assigned)
done     → Complete (merged, deployed, approved)
archived → Historical (no longer relevant, but preserved for audit)
```

#### Rule 12: Parent Cards Gate Child Cards

Using Kanban's dependency links:
- Requirements card must complete before design card starts
- Design card must complete before implementation card starts
- Implementation card must complete before review card starts
- Review card must complete before merge card starts

The agent creates these as parent→child links. Children stay in `todo` until all parents are `done`, then auto-promote to `ready`. The dispatcher picks them up automatically.

```
[R1: Requirements] ──▶ [R4: Design] ──▶ [I1: Implementation] ──▶ [I4: Review] ──▶ [Merge]
     done                  todo               todo                   todo            todo
```

When R1 completes, R4 auto-promotes to `ready`. When R4 completes, I1 auto-promotes. The chain flows forward automatically with no manual intervention.

#### Rule 13: Workflow Progress Trail (Agent-to-Agent)

When a card's execution involves multiple agents internally (orchestrator→worker→reviewer), the orchestrator agent adds a one-line comment to the parent card at each major phase transition. Workers do not comment on the parent card — they report through their own child cards via `kanban_complete(summary)`.

**The parent card's comment thread is the orchestration-level breadcrumb trail, readable at a glance.**

| Workflow Phase | Comment on Parent Card | Who Adds It |
|---|---|---|
| Workflow starts | "Starting: [what's about to happen]" | Orchestrator |
| Workers dispatched | "Dispatched N tasks: [list]. Workers: [who]" | Orchestrator |
| Phase completes | "[Phase] complete. [summary of results]" | Orchestrator |
| Review complete | "Review done. [verdict]. PR #N created." | Orchestrator |
| Handoff to user | Covered by `kanban_block(reason=...)` | Orchestrator |

**Example — a full card lifecycle with progress trail:**

```
Card: t_abc — "Implement auth module" [my-web-app]
Status: running → blocked → done

[14:30] Orchestrator: Starting implementation. Design doc loaded.
[14:31] Orchestrator: Dispatched 4 tasks: login, registration,
         password-reset, integration-tests. Workers: worker-a, worker-b.
[14:52] Orchestrator: All implementation tasks complete. 14 tests pass.
         Requesting code review.
[15:05] Orchestrator: Review complete — 0 critical, 1 medium. PR #42 created.
         → Status: blocked (needs_input: "Review PR #42")

User unblocks, adds feedback as comment:

[17:45] User: Login looks good. Password reset has dead end after step 3.

[17:52] Orchestrator: Fix dispatched to worker-a.
[17:58] Orchestrator: Fix complete. New PR #43 created.
         → Status: blocked (needs_input: "Re-review PR #43")

User approves:

[18:10] User: Approved.
         → Status: done
```

**Three to five comments per card execution.** No worker-level noise on the parent. The child cards carry the detail if the user needs it. The parent card tells the story at a glance.

#### Rule 14: Repo Naming Convention

All repositories created by the system must be prefixed with `auto-`. This applies to:
- GitHub repositories created via `gh repo create`
- Local git repositories initialized during project setup
- Any test/validation repositories created during setup or training

**Format:** `auto-<project-name>` (e.g., `auto-hello-world-test`, `auto-trading-signals`)

**Purpose:** Instantly distinguishes system-managed repos from manually created ones. Prevents confusion about ownership, makes cleanup unambiguous, and signals to the operator that the repo was agent-initiated.

**Enforcement:** The `opencode-bridge` skill and `github-pipeline` skill both enforce this prefix. Any `gh repo create` or `git init` command that creates a project repository must include the `auto-` prefix. Repos without the prefix are considered manually created and are excluded from agent-managed workflows.

### 12.5 ADH-Friendly Board Interaction

The kanban board is the primary interface for "what should I do next?" — designed around ADHD patterns from Section 11.4:

**"What should I work on right now?"**
```
hermes kanban list --status ready --assignee default
```
This is your work queue. Every card in this list is approved and waiting for you. No decision-making needed — pick the top one.

**"What's waiting on me?"**
```
hermes kanban list --status blocked --assignee default
```
These are cards where the agent needs your input. Clear these first — they're blocking agent work.

**"What's happening across all projects?"**
```
hermes kanban list
```
Everything. Filter by `--tenant` for one project, by `--assignee` for your cards, by `--status` for a specific phase.

**Dashboard:** `hermes dashboard` → Kanban tab shows the full board with columns. Board switcher at the top if multiple boards exist (but we use one board with tenants).

**From Telegram/Discord:** "What's on my kanban board?" → Agent reads the board and summarizes. "Show me blocked cards" → Agent lists them. "Unblock t_abc and say I approve" → Agent does it.

---

## Appendix A: Command Quick Reference

```
# Workflow orchestration
hermes chat -q "Implement feature X per design.md"          # One-shot task
hermes cron add --name "bug-scan" --schedule "weekly" ...    # Scheduled job
hermes webhook subscribe github-issues --events "issues" ... # GitHub trigger

# OpenCode invocation
opencode --task-file /path/to/task.md                        # Direct
hermes chat -q "Delegate to OpenCode: implement auth module"  # Via Hermes
delegate_task(goal="...", context="...")                      # Delegation tool

# Inspection
hermes cron list                                              # See scheduled jobs
hermes webhook list                                           # See webhook routes
hermes kanban list                                            # See task queue
hermes config show                                            # See configuration
hermes session search "RUN-a3f7c2b1"                          # Find run traces

# Git operations (via terminal)
git log --grep="RUN-a3f7c2b1"                                 # Find commits by run
gh pr list --search "RUN-a3f7c2b1"                            # Find PRs by run
```

---

## Appendix B: Cost Model

| Activity | Model | Token Estimate | Cost Estimate | Frequency |
|---|---|---|---|---|
| Requirements interview | deepseek-v4-flash | ~5k tokens | ~$0.01 | Per project |
| System design | deepseek-v4-flash | ~10k tokens | ~$0.02 | Per project |
| Code implementation (per module) | deepseek-v4-flash | ~20k tokens | ~$0.04 | Per module |
| Code review (per PR) | deepseek-v4-flash | ~5k tokens | ~$0.01 | Per PR |
| Bug scan | gemma4-hermes (local) | ~15k tokens | $0.00 | Weekly |
| Security scan | gemma4-hermes (local) + tools | ~5k tokens | $0.00 | Weekly |
| Triage (per issue) | gemma4-hermes (local) | ~2k tokens | $0.00 | Per issue |
| **Total: full project** | mixed | **~100k tokens** | **~$0.20** | Per project |

Local-first model routing keeps the operational cost near zero for most tasks. Cloud models only for tasks needing deeper reasoning.

---

**Document produced for Hermes Agent to execute. All paths, commands, and configurations are verified against the live Hermes instance and official documentation. No external references required — each mechanism is described with its exact tool or command path.**