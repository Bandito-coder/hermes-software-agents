# Orchestrator — Structural Workflow Enforcement for Hermes Dev-Lead

## Problem

The dev-lead agent (Hermes + skill) repeatedly ignores prompt-based instructions like "NEVER write code yourself" and "DO NOT SKIP this step." No amount of bold caps in a SKILL.md can structurally prevent an LLM with access to `write_file`, `patch`, and `terminal` from using them directly.

## Solution

Replace prompt-based orchestration with **code-based flow control**. A Python script manages:

- **Phase transitions** — enforced in code, not prompts
- **Sub-agent invocation** — coding agents via `opencode run`, non-coding agents via LiteLLM API
- **Circuit breakers** — cycle limits, repeated findings, blocking count stagnation
- **Kanban blocking** — approval gates via `hermes kanban` CLI
- **State persistence** — survives process restarts, resumable after unblocking

The LLM's role is reduced to: run the script, report its output. It physically cannot skip phases or write code because the script controls the flow.

## Architecture

```
┌─────────────────────────────────────────────┐
│           Orchestrator Script               │
│  (Python, runs via terminal subprocess)     │
│                                             │
│  ┌─────────┐  ┌─────────┐  ┌────────────┐  │
│  │  State   │  │  Kanban │  │  Circuit   │  │
│  │ Manager  │  │  Client │  │  Breakers  │  │
│  └────┬────┘  └────┬────┘  └─────┬──────┘  │
│       │            │              │          │
│  ┌────▼────────────▼──────────────▼──────┐  │
│  │         Workflow Engine               │  │
│  │  Phase 0 → 1 → 2 → 3 → 4 → 5        │  │
│  └────┬──────────────┬──────────────┬────┘  │
│       │              │              │        │
│  ┌────▼────┐  ┌──────▼──────┐  ┌───▼───┐   │
│  │ LiteLLM │  │   OpenCode  │  │  Git  │   │
│  │   API   │  │     CLI     │  │  CLI  │   │
│  └─────────┘  └─────────────┘  └───────┘   │
└─────────────────────────────────────────────┘
```

## Workflows

| Workflow | Phases | Max Cycles | Description |
|----------|--------|------------|-------------|
| W-BUILD  | 0→1→2→3→4→5 | 4 | Full feature build |
| W-FIX    | 0→3→4→5 | 3 | Bug fix |
| W-SPEC   | 0→1 | 1 | Requirements only |
| W-REFACTOR | 0→3→4→5 | 3 | Code improvement |
| W-HARDEN | 0→3→4→5 | 2 | Security audit |

## Usage

```bash
# Start a new workflow
python3 orchestrator.py start --workflow W-BUILD --card-id t_abc123

# Resume after user unblocks the card
python3 orchestrator.py resume --run-id RUN-abc12345

# Check status
python3 orchestrator.py status --run-id RUN-abc12345

# List all active workflows
python3 orchestrator.py list

# Dry run (no side effects)
python3 orchestrator.py --dry-run start --workflow W-BUILD --card-id t_abc123
```

## State

State is persisted to `~/.hermes/orchestrator/state/{run_id}.json`. Contains:
- Current phase and status
- Sub-agent outputs (scout, coach, architect)
- Gate/review results
- Fix history (for circuit breakers)
- Execution log

## Circuit Breakers

1. **Cycle limit** — build: 4, fix: 3, harden: 2
2. **Same finding repeated** — same finding ID in 3 consecutive cycles
3. **Blocking count stagnation** — gate failures not decreasing across 2 cycles

On trigger: card is blocked with detailed reason and fix history.

## Blocking Points

| Phase | Block Reason | Trigger |
|-------|-------------|---------|
| 1 | Requirements approval | BRIEF.md written by Coach |
| 2 | Design approval | SPEC.md written by Architect |
| 4 | Build approval | Gates PASS, Review PASS |

## Dependencies

- Python 3.10+ (stdlib only — no pip packages)
- `hermes kanban` CLI
- `opencode` CLI (for coding agents)
- `git` CLI
- LiteLLM proxy at `localhost:4000` (for non-coding agents)

## Tests

```bash
python3 -m pytest test_orchestrator.py -v
```

69 tests covering:
- State persistence (save/load/roundtrip/concurrent)
- KanbanClient CLI wrapping (all commands, error handling)
- LLMClient API calls (dry run, HTTP)
- CodebaseExplorer (file tree, key files, context gathering)
- Circuit breakers (all 3 types, boundary conditions)
- Phase transitions (sequential, blocked state persistence)
- W-BUILD happy path (full cycle with all gates passing)
- W-BUILD fix loop (gate failure → fix → pass)
- W-BUILD circuit breaker (cycles exhausted)
- W-FIX workflow
- Small-change fast path (skips Coach/Architect)
- Gatekeeper parsing (pass/fail/no gates.sh)
- Unknown dimension parsing
- CLI interface (start/resume/status/list)
- Blocking/unblocking flow
- Error handling (git failures, opencode failures)
- Edge cases (special chars, empty body, concurrent states, deep nesting)

## Integration Plan (Not Yet Implemented)

When ready to deploy:

1. Create a new skill `orchestrated-dev-lead` that runs this script
2. Update kanban card dispatch to use the new skill
3. The skill's instructions become: "Run `python3 orchestrator.py start/resume` and report output"
4. Monitor for edge cases in production before removing the old dev-lead skill

## Files

- `orchestrator.py` — Main script (46KB)
- `test_orchestrator.py` — Test suite (43KB, 69 tests)
- `README.md` — This file
