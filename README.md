# Hermes Software Agents

A 16-agent software development team that runs on [Hermes Agent](https://hermes-agent.nousresearch.com) — an open-source AI agent framework by Nous Research.

## What This Is

An autonomous software development platform where AI agents handle the full SDLC: requirements gathering, architecture design, implementation (TDD), code review, security auditing, documentation, and cost monitoring — with human approval gates at critical decision points.

Built and tested across 4 iterations over one session. All 30 requirements from the framework design are covered.

## Agent Roster

| Agent | Model | Role | Permission |
|---|---|---|---|
| **Scout** | workhorse | Codebase explorer | read-only |
| **Gatekeeper** | workhorse | Runs quality gates (lint, test, build) | execute-only |
| **Builder** | coding | TDD implementation via OpenCode | write |
| **Test Author** | coding | Writes tests only | write |
| **Reviewer** | coding | Code review with verdict blocks | read-only |
| **Fixer** | coding | Targeted fixes from findings | write |
| **Dev Lead** | workhorse | Orchestrates all workflows | orchestrator |
| **Coach** | workhorse | Requirements interviewer | read-mostly |
| **Architect** | architect | System design with alternatives; revises SPEC.md per review findings | read-mostly |
| **Design Reviewer** | reasoning | Validates SPEC.md before user approval (max 3 cycles, then referee) | read-only |
| **Enhancer** | workhorse | Refactoring with regression detection | orchestrator |
| **SecOps** | reasoning | Security auditor (3-layer scan) | read-only |
| **Triage** | workhorse | GitHub issue classification | read + gh CLI |
| **Docs** | workhorse | Documentation sync | write (docs only) |
| **Cost Sentinel** | workhorse | Daily cost anomaly alerts | read-only |
| **Cost Analyst** | workhorse | Weekly cost reports + proposals | read-mostly |
| **Browser Tester** | workhorse | Web smoke tests via geckodriver/Firefox (DOM/API/a11y) | execute-only |
| **Visual Tester** | vision (none configured) | Visual regression / screenshot verification | execute-only |

**Model routing** via [LiteLLM](docs/LiteLLM-integration.md): `workhorse` (deepseek-v4-flash, $0.04/1M), `coding` (deepseek-v4.1-flash, $0.12/1M), `reasoning` (mimo-v2.5-pro, $0.30/1M), `architect` (gpt-5.6-luna, $0.20/1M, fallback → coding), `local` (Ollama, free). ~$1.40/month estimated.

## Workflows

| Workflow | Description | Agents |
|---|---|---|
| **W-BUILD** | Full feature build (tests-first) | Scout→Coach→Architect→Design Reviewer→Test Author (failing tests + trace)→Builder→Gatekeeper→Reviewer→Fixer |
| **W-FIX** | Quick bug fix (tests-first) | Scout→Test Author (failing repro/uplift)→Gatekeeper→Fixer→Reviewer |
| **W-SPEC** | Requirements gathering | Scout→Coach→BRIEF.md |
| **W-REFACTOR** | Refactor with regression gate | Baseline→Scout→Architect→Builder→Gatekeeper→Reviewer |
| **W-HARDEN** | Security audit | SecOps→Fixer→Gatekeeper→SecOps verify |
| **W-DOC-SYNC** | Documentation sync | Diffs code→updates docs→flags conflicts |

## Structure

```
agents/           # Agent skill definitions (SKILL.md)
  scout/          # Each agent has its own directory
  builder/
  ...
bin/              # Gate runner scripts
  gates.sh        # Stack-detecting quality gate
docs/             # Design docs, test results, integration guides
  Hermes_Agent_Software_Framework.md    # Reference design (30 requirements)
  AgentRosterAndDesign.md               # Agent roster & workflows
  LiteLLM-integration.md                # Cost tracking & model routing
  scheduled-flows.md                    # Cron jobs & webhook setup
  browser-smoke-testing.md              # Browser tester decision & usage
  iteration-*-test-results.md           # Test results per iteration
  requirements-coverage.md              # 30 requirements mapping
tests/            # Test fixtures
  fixture/        # Python text-utils project used for testing
```

## Quick Start

```bash
# Install Hermes Agent
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# Install agent skills
cp -r agents/* ~/.hermes/skills/

# Install gate runner
cp bin/gates.sh /path/to/your/project/.github/bin/

# (Optional) Set up LiteLLM for cost tracking
# See docs/LiteLLM-integration.md
```

## How It Works

1. **Card arrives** (kanban or chat) — Dev Lead reads it
2. **Scout** explores the codebase for context
3. **Coach** interviews for requirements (if needed) → BRIEF.md
4. **Architect** designs the solution → SPEC.md with alternatives; **Design Reviewer** validates it (findings → revision, max 3 cycles → user referee call)
5. **Test Author** writes the failing tests FIRST from the spec (+ tests/TRACE.md) — the build is blocked until every spec item is traced
6. **Builder** implements via TDD to make the failing tests pass (OpenCode + Superpowers)
7. **Gatekeeper** runs quality gates (deps, lint, typecheck, test) + verifies the trace
8. **Reviewer** checks against spec with verdict block
9. If FAIL → **Fixer** loop (max 4 cycles with circuit breakers)
10. Commit on branch → human approves merge

## Design Decisions

- **Agents commit but never push** — merge is the human gate
- **Gatekeeper runs before Reviewer** — linters find most defects at zero token cost
- **Orchestrators cannot invoke each other** — no unbounded delegation chains
- **Cost agents cannot edit configs** — prevents self-serving optimization
- **Verdict blocks are machine-readable** — PASS|FAIL|BLOCKED with findings

## Test Results

All tests green across 4 iterations:
- **75/75** structural tests
- **18/18** behavioral tests (live agent tests)
- **E2E chain** verified (Scout→Coach→Architect→Builder→Gatekeeper→Reviewer)
- **Dogfooding** passed (agents audit their own skills)
- **W-HARDEN** found real secrets in workspace (correct behavior)
- **30/30** framework requirements covered

See `docs/iteration-*-test-results.md` for details.

## Framework

The reference design is in `docs/Hermes_Agent_Software_Framework.md` — 30 requirements across 7 areas (Design, Implementation, Bugs/Security, GitHub, Non-coding, Scheduling, Governance). The agent roster in `docs/AgentRosterAndDesign.md` maps every requirement to an agent workflow.

## License

MIT
