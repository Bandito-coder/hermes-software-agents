# Agent Roster & Workflow Design — Supplement to Hermes_Agent_Software_Framework.md

**Date:** 2026-09-21 (AEST)
**Status:** Authoritative agent-layer design
**Relationship to the framework:** `Hermes_Agent_Software_Framework.md` defines WHAT the system must do (30 requirements, governance, platform architecture). This document defines WHO does it — the agent roster and agent workflows that implement every requirement, staying entirely within the framework's architecture (Hermes hub + OpenCode coder, kanban Rules 1-14, RUN-ID convention, single board with tenants).

**Source for the agent layer:** `02 Cards/Development Agent Framework 2608072240` (vault) — 13 proven agents, verdict contracts, circuit breakers, permission model, gate runner. Extended where the framework's 30 requirements demand coverage the vault design didn't have (Triage, docs sync).

---

## 1. Agent Roster

14 agents in 4 permission tiers. Each agent is a Hermes skill; orchestrators run as kanban workers.

### Tier 1 — Local (zero API cost, mechanical tasks)

| Agent | Model | Role | Permission | Framework Requirements |
|---|---|---|---|---|
| **Scout** | workhorse | Read-only codebase explorer. Gathers context, maps structure, finds patterns. Every workflow starts here. | edit-locked (search/read only) | R5/R6 impact analysis, B3 investigation, I5 refactor exploration |
| **Gatekeeper** | workhorse | Runs the gate runner (deps, lint, typecheck, test, build). Reports PASS/FAIL verbatim — never summarizes failures away. | execute only | I3 test execution, I4 quality gate, B1 nightly gate runs |
| **Cost Sentinel** | workhorse | Daily spend anomaly check. Reads cost telemetry, alerts only on breach. Silent when clean. | read/execute only | Gv2, Gv4 |

### Tier 2 — Mid-range (fast implementation & orchestration)

| Agent | Model | Role | Permission | Framework Requirements |
|---|---|---|---|---|
| **Builder** | coding | Implements from spec via OpenCode + Superpowers TDD. Writes production code only after failing tests. | write | I1, I2 |
| **Test Author** | coding | Writes tests only. Never writes production code. Characterization tests for untested code (I5 prerequisite). | write | I3 |
| **Fixer** | coding | Applies targeted fixes from Reviewer/Gatekeeper findings. Iron Law: root cause before fix. | write | B3, I2 (patch scope) |
| **Dev Lead** | workhorse | Build-loop orchestrator. Runs /build, /fix, /harden workflows. Creates cards, branches, commits, ledger entries. | orchestrator | I1, I2, I4 loop control, G1, B1/B2 remediation loops |
| **Enhancer** | workhorse | Feature orchestrator with regression awareness — baseline gate before any change. | orchestrator | I5, R5 (change implementation) |
| **Triage** | workhorse | GitHub issue classification: bug/feature/question/duplicate/invalid. Assigns P0-P3 per severity rubric. Auto-labels clear-cut cases. | read + gh CLI | G2 |
| **Docs** | workhorse | Documentation sync: diffs code changes, updates README/API docs/changelog, flags conflicts for human review. | write (docs only) | I6 |

### Tier 3 — Mid-high (strong reasoning)

| Agent | Model | Role | Permission | Framework Requirements |
|---|---|---|---|---|
| **Coach** | workhorse | Requirements interviewer. Gathers codebase context via Scout, assesses 9 dimensions (Outcome, Users, Data, Boundaries, Rules, Failure, Scale, Integration, Done), asks only about Unknowns. Budget: 3 rounds, 5 questions max. Writes BRIEF.md. | read-mostly (edits BRIEF only) | R1 |
| **Reviewer** | coding | Senior code reviewer, read-only. Checks against plan, conventions, personal review checklist. Emits verdict blocks. Critical findings block merges. | edit-locked | I4, I5 (no-behavior-change proof) |
| **Cost Analyst** | workhorse | Weekly cost/efficiency review. Writes proposals as unified diffs — NEVER applies them (cannot edit agent configs). | read-mostly (writes proposals only) | Gv2, Gv4 |

### Tier 4 — Premium (deep reasoning, invoked rarely)

| Agent | Model | Role | Permission | Framework Requirements |
|---|---|---|---|---|
| **Architect** | reasoning | Chief architect. Writes SPEC.md (data model, interface contracts, acceptance criteria) from BRIEF. Escalation target when Fixer hits structural changes. Produces 2-3 alternatives with trade-offs at the high level. | read-mostly (edits SPEC only) | R3, R4, R5 (delta design), Fixer escalation |
| **SecOps** | reasoning | Security auditor, read-only. Layers: secrets, dependencies/CVE, SAST with AI reasoning to cut false positives. Critical/High auto-remediated via Fixer; Medium/Low reported only. | edit-locked | B2, B4, B5 |

### Model cost summary

| Model | Agents | Est. monthly share |
|---|---|---|
| workhorse ($0.04/$0.16 per 1M) | Scout, Gatekeeper, Cost Sentinel, Coach, Dev Lead, Enhancer, Triage, Docs, Cost Analyst | ~$0.30 |
| coding ($0.12/$0.48 per 1M) | Builder, Test Author, Fixer, Reviewer | ~$0.60 |
| reasoning ($0.30/$0.61 per 1M) | Architect, SecOps | ~$0.30 |
| **Total** | 14 agents | **~$1.20/month** at moderate usage |

Local-first routing (framework Section 4.2) holds: mechanical work never touches paid APIs.

---

## 2. Permission Model

Two enforcement layers (from the vault design — proven):

1. **Hard boundary** — toolset restriction: edit-locked agents get no file-write tools; orchestrators get delegation capability.
2. **Soft boundary** — body instructions in each skill constrain how tools are used.

| Category | Agents | Capability | Rationale |
|---|---|---|---|
| **Edit-locked** | Scout, Gatekeeper, Reviewer, SecOps, Cost Sentinel | Observe/execute, never modify | Observers can't corrupt evidence or be tricked into "fixing" what they're auditing |
| **Read-mostly** | Coach, Architect, Cost Analyst | Edit only designated outputs (BRIEF.md, SPEC.md, proposals/) | Reasoning agents produce documents, not code |
| **Write** | Builder, Test Author, Fixer, Docs | Full file write in the active worktree | Implementation capability |
| **Orchestrator** | Dev Lead, Enhancer | Delegate to named sub-agents | Loop control |

**Design decisions carried forward:**
- **Agents commit but never push.** All work lands on `agent/<short-task-slug>` branches. Merge is the user's kanban gate (framework Gv1). Under unattended execution, work stops at a branch.
- **Orchestrators cannot invoke each other.** Shallow call graph; no unbounded delegation chains (framework delegation.max_spawn_depth: 1 enforces this at the platform level).
- **Sub-agents cannot invoke** any other agent or their orchestrator.
- **Cost agents cannot edit agent configs.** Cost Sentinel and Cost Analyst write to `reports/costs/` only. Given write access to quality settings, they'd find the same three cheap wins every week: downgrade Reviewer, cut MAX_CYCLES, skip Architect.
- **Gatekeeper runs before Reviewer.** Linters and test suites find most defects at zero token cost. Paying a model to find a missing import is waste.

### Delegation rules

**Dev Lead invokes (10):** Scout → Coach → Architect → Builder → Test Author → Gatekeeper → Reviewer → Fixer → SecOps → Triage

**Enhancer invokes (8):** Scout → Architect → Builder → Test Author → Gatekeeper → Reviewer → Fixer → Docs (no SecOps — security audits are on-demand)

**Small-change fast path:** Dev Lead skips Coach and Architect when a task touches <3 files, changes no data models/interfaces, and follows existing patterns. Scout → Builder → Test Author → Gatekeeper → Reviewer → Fixer loop only.

---

## 3. Verdict Block Contract

Every reporting agent (non-orchestrator) ends output with a machine-readable verdict:

```
---VERDICT---
status: PASS | FAIL | BLOCKED
blocking_count: <int>
advisory_count: <int>
escalate: none | architect | human
summary: <one line, ≤120 chars>
findings:
  - id: F1
    severity: blocking | advisory
    file: path/to/file.ext
    line: 42
    problem: <one sentence>
    fix: <one sentence, concrete>
---END---
```

Orchestrators parse this to decide next steps:
- `PASS` → proceed to next workflow step
- `FAIL` → invoke Fixer with findings attached
- `BLOCKED` → stop loop, block card on user (kanban Rule 2)
- `escalate: architect` → hand off to Architect
- `escalate: human` → block card on user with findings summary

**Variant forms:** Gatekeeper and Cost Sentinel: `PASS | FAIL` only, `escalate: none | human`.

This is the machine-checkable implementation of the framework's I4 quality gate and the B-scan severity reporting.

---

## 4. Circuit Breakers & Escalation

Orchestrators stop the fix loop when ANY of:

1. Cycle count reaches MAX_CYCLES (build: 4, fix: 3, harden: 2)
2. Same finding ID appears in 3 consecutive cycles
3. Gatekeeper `blocking_count` doesn't decrease across 2 consecutive cycles
4. Any agent emits `escalate: human`

On trigger: Dev Lead blocks the card on the user with the findings summary and cycle history.

**Escalation chain:**
```
Fixer → Architect → human
```
- **Fixer escalates to Architect** when a fix requires: migration, dependency change, interface change, or changes across >3 files
- **Architect escalates to human** when the original SPEC was wrong and needs amendment
- **Any agent** can emit `escalate: human` to stop the loop immediately

This implements the framework's failure handlers (B3's "escalate after 3 rounds", I1's "critical issues block merge") as structural, loop-level controls rather than hoping the model behaves.

---

## 5. Gate Runner

`gates.sh` — stack-detecting gate chain, run by Gatekeeper on the local model (zero API cost):

| Stack | Gates |
|---|---|
| Django | deps, lint, typecheck, django-check, migrations, test |
| Python | deps, lint, typecheck, test |
| Node | deps, lint, typecheck, test, build |

Exit codes: 0 = pass, 1 = gate failed, 2 = no stack detected.
Output format: `::gate:: <name>`, `::result:: PASS|FAIL`, `::output::` on failure (verbatim — Gatekeeper copies errors, never paraphrases).

**Baseline gate (Enhancer/regression rule):** before any feature work on existing code, Gatekeeper runs once to prove the suite is green. Any test that passed before and fails after is a regression — always blocking.

---

## 6. Agent Workflows — Mapped to All 30 Requirements

Four primary workflows (kanban-card-driven equivalents of the vault's slash commands) plus scheduled/event-triggered flows. Every requirement from the framework maps to exactly one agent workflow.

### W-BUILD — Full Build Cycle → I1, I3, I4, R2, Gv1, Gv3, Gv6

```
Card (or chat) → Dev Lead
  1. Generate RUN-ID. Create branch agent/<short-task-slug>.
  2. Scout (context) — local, edit-locked
  3. Coach (if no BRIEF) — R1 interview, writes BRIEF.md
  4. Architect (if new system/feature) — R3/R4, writes SPEC.md
     → Card on user: "Review SPEC" (non-interactive, Gv1 gate)
  5. Builder — implements via OpenCode + TDD (I1, I3)
  6. Test Author — fills test gaps (I3)
  7. Gatekeeper — gates.sh (I3 execution, I4 first pass)
  8. Reviewer — read-only review, verdict block (I4)
     ↓ FAIL → Fixer → Gatekeeper → Reviewer (loop, MAX 4 cycles)
     ↓ PASS
  9. git commit [RUN-ID] (never push) → ledger entry (R2, Gv6)
  10. Card on user: "Review branch agent/<slug> — approve to merge" (Gv1)
```

### W-FIX — Quick Fix → R6, I2, B3

```
Card (or GitHub issue webhook via G1) → Dev Lead
  1. Generate RUN-ID. Create branch.
  2. Scout (locate code)
  3. Gatekeeper (reproduce failure)
  4. Fixer — Iron Law: root cause investigation first (B3), targeted fix only (I2 scope)
     ↓ structural? → escalate to Architect (R5 delta design)
  5. Gatekeeper → Reviewer loop (MAX 3 cycles)
  6. Commit [RUN-ID] → ledger entry
  7. Card on user: merge approval (Gv1)
```
Skips Coach and Architect by design — surgical changes only.

### W-HARDEN — Security Audit → B2, B4, B5

```
Card or weekly cron → Dev Lead
  1. SecOps (audit) — reasoning, read-only, layered scan
     ↓ Critical/High findings → Fixer (remediate)
     → Gatekeeper → SecOps verify (MAX 2 cycles)
     ↓ Medium/Low findings → report only
  2. Card on user only if findings (zero-noise, framework Rule 7)
```
B4 (CVE monitoring) runs as a daily Gatekeeper/SecOps script pass — critical CVEs create a W-FIX card automatically. B5 (post-deploy assessment) is W-HARDEN invoked on a deploy webhook, scoped to the running surface.

### W-SPEC — Requirements → R1, R2

```
Card or chat → Dev Lead → Coach
  1. Scout (codebase context)
  2. Coach assesses 9 dimensions; asks only Unknowns (3 rounds, 5 questions max)
     → Interview card on user: INTERACTIVE (Rule 4)
  3. Coach writes BRIEF.md (R1 output: IDs, acceptance criteria, open questions)
  4. Card on user: "Review BRIEF" (non-interactive)
  5. On approval: Dev Lead updates TRACEABILITY.md (R2)
```

### Scheduled & Event Flows → B1, S1-S4, G1-G3, Gv2, Gv4

| Flow | Trigger | Agents | Requirements |
|---|---|---|---|
| Nightly gate check | Cron (daily) | Gatekeeper runs gates.sh on each workspace; FAIL → W-FIX card | B1, S2 |
| Weekly security scan | Cron (Mon 10am) | Dev Lead → W-HARDEN | B2, S2 |
| GitHub issue arrives | Webhook | Triage (classify, dedupe, label, P0-P3) → W-FIX or W-BUILD card | G2, G3, S3 |
| PR review request | Webhook | Reviewer verdict → card on user | G1, I4 |
| Daily cost check | Cron | Cost Sentinel — silent unless breach | Gv2, Gv4 |
| Weekly cost review | Cron | Cost Analyst — writes review + proposal diffs | Gv2 |
| Doc sync | Post-merge or weekly | Docs — diffs changes, updates docs, flags conflicts | I6 |
| Manual run | Chat ("run security scan on X") | Named workflow runs once | S1 |
| Long job | >30 min estimate | Dev Lead breaks into checkpointed phases | S4 |

**W1/W2 (non-coding workflows)** stay Hermes-native per the framework (cron + skills + delegate_task) — no roster change needed; Dev Lead is not involved.

---

## 7. Kanban Integration (Framework Rules 1-14 Apply Verbatim)

| Rule | Implementation in the agent layer |
|---|---|
| 1 (dual initiation) | Dev Lead cards created via chat or directly by user |
| 2 (user cards) | Every verdict-driven pause creates a card stating what's needed + interactive/non-interactive |
| 3 (non-interactive) | SPEC/BRIEF/PR review cards — comment + reassign |
| 4 (interactive) | Coach interview cards — "I'm ready to talk about [project]" |
| 5 (chat-triggered completion) | Dev Lead auto-completes after chat interactions |
| 6 (gates as cards) | BRIEF, SPEC, PR merge — all cards on user |
| 7 (scans create cards) | Gatekeeper/SecOps findings → cards; silent when clean |
| 8 (issue pipeline) | Triage → Dev Lead W-FIX → PR card |
| 9 (RUN-ID) | Every card, commit, branch, verdict, ledger entry |
| 10 (blocked reminders) | blocked-card-reminder cron (already live) |
| 11 (lifecycle mapping) | Card status = SDLC phase |
| 12 (parent gating) | BRIEF card → SPEC card → build card → merge card chain |
| 13 (progress trail) | Dev Lead comments on parent card at each phase: "Scout complete", "Builder dispatched", "Gatekeeper: PASS", "Review: PASS — ready for user". Sub-agents never comment on parents |
| 14 (auto- prefix) | All system-created repos `auto-<name>` |

---

## 8. Test Ledger & Run Telemetry

Every workflow run appends to `reports/runs/ledger.jsonl`:
```json
{"run_id": "RUN-a3f7c2b1", "workflow": "build", "branch": "agent/auth-module", "cycles": 2, "agents": ["scout","builder","test-author","gatekeeper","reviewer","fixer"], "verdict": "PASS", "tokens_est": 41200, "ts": "..."}
```

This is the framework's Gv3 (traceability) and Gv6 (audit) implementation: one RUN-ID greps cards, commits, ledger, and verdicts.

---

## 9. Testing Requirements (Every Iteration)

An iteration is NOT complete until all of these are green:

1. **Structural tests** — every agent skill: valid frontmatter, correct model assignment, correct permission tier, verdict template present (reporting agents), escalation clause present
2. **Behavioral tests** — run each new agent on a fixture: edit-locked agents leave `git status` clean; Builder writes failing test first; Reviewer emits parseable verdict blocks; Fixer stays in scope; Gatekeeper reports verbatim
3. **Workflow E2E tests** — each new workflow runs on a fixture project to PASS or blocked-on-user; circuit breakers trigger at MAX_CYCLES; escalation fires correctly
4. **Regression** — all previous iterations' E2E tests re-run and pass
5. **Reviewer sign-off** — the Reviewer agent reviews the iteration's own output
6. Results recorded in `iteration-N/test-results.md` with pass/fail per test and evidence

---

## 10. Build Phases

| Phase | Scope | Agents Built |
|---|---|---|
| **1** | Minimum viable build/fix loop (W-BUILD happy path + W-FIX) | Dev Lead, Scout, Builder, Test Author, Gatekeeper, Reviewer, Fixer + gates.sh |
| **2** | Requirements + design + feature loop | Coach, Architect, Enhancer + W-SPEC; refine Phase 1 from test findings |
| **3** | Security + triage + cost + docs | SecOps, Triage, Docs, Cost Sentinel, Cost Analyst + W-HARDEN, webhook flows; Reviewer passes the complete solution |
| **Future** | LiteLLM routing (framework Shortfall 7), Architect-emergency frontier agent (Shortfall 8), automated webhooks (Shortfall 6) | — |

Each phase: build → test → fix → all-green → human review → next-phase kickoff prompt written.
