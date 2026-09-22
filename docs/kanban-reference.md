# Hermes Kanban — Complete Reference

**Source:** https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban
**Date:** 2026-09-22

---

## Status Lifecycle

```
triage → todo → ready → running → review → done → archived
                ↑                    |
                └────────────────────┘ (request_changes → back to ready)
```

| Status | Meaning | Dispatcher behavior |
|---|---|---|
| `triage` | Parking column for rough ideas | Auto-decomposed if `auto_decompose: true` (DEFAULT) |
| `todo` | Waiting on parent dependencies | Promoted to `ready` when all parents are `done`/`archived` |
| `ready` | Ready to dispatch | Dispatched to assigned profile on next tick |
| `running` | Worker actively working | Claimed, heartbeat monitored |
| `review` | Awaiting reviewer | Reviewer spawned if `review_dispatch: true` |
| `done` | Completed | Terminal state |
| `archived` | Archived | Hidden by default |

---

## The Dispatcher (Gateway-Embedded)

Runs inside the gateway process. Every N seconds (default 60, we set 30):

1. **Reclaim** stale claims (TTL expired, no heartbeat, crashed PID)
2. **Promote** `todo` → `ready` when all parents complete
3. **Auto-decompose** triage tasks (if `auto_decompose: true`)
4. **Claim** ready tasks with an assignee
5. **Spawn** worker process for claimed task

### What gets dispatched

A task is dispatched when ALL of:
- Status is `ready`
- Has an assignee (explicit, or auto-filled by `default_assignee`)
- Assignee profile exists on disk (`profile_exists()` check)
- Not guarded by respawn guard (recent success, active PR, rate limit)
- Concurrency caps not exceeded (`max_in_progress`, `max_in_progress_per_profile`)

### What does NOT get dispatched

- `triage` cards (if `auto_decompose: false`)
- `todo` cards (waiting on parents)
- `blocked` cards (waiting on user)
- `done`/`archived` cards
- Cards with no assignee AND no `default_assignee` configured
- Cards assigned to non-existent profiles

---

## The Triage Column — CRITICAL

**`auto_decompose: true` (DEFAULT):** Every tick, the dispatcher runs the built-in decomposer on triage tasks (capped by `auto_decompose_per_tick`, default 3). The decomposer:
1. Uses an LLM (`auxiliary.kanban_decomposer`) to produce a task graph
2. Fans the task out into child tasks routed to specialist profiles
3. Original task becomes parent of all children
4. Original promoted to `todo` → `ready` when children complete
5. Original's assignee (or `orchestrator_profile`) judges completion

**This is why triage cards get processed automatically.**

**`auto_decompose: false`:** Triage cards stay parked. You must manually:
- `hermes kanban decompose <id>` — LLM fans out
- `hermes kanban specify <id>` — LLM fleshes out single task
- Drag to `ready` in dashboard — manual promotion

---

## Backlog Configuration

### Option 1: Disable auto-decompose (RECOMMENDED)

```yaml
kanban:
  auto_decompose: false
```

- Triage cards stay in triage until you act
- Use `hermes kanban specify <id>` to flesh out, then drag to ready
- Or `hermes kanban decompose <id>` for LLM fan-out
- Toggle in dashboard: Orchestration pill → Manual (muted gray)

### Option 2: Unassigned cards (current setup)

```yaml
kanban:
  default_assignee: brett
```

- Cards with no assignee are skipped by dispatcher
- BUT: auto-decompose still runs on triage cards (assigns + fans out)
- Only works for `ready` status unassigned cards

### Option 3: dispatch_profiles (most restrictive)

```yaml
kanban:
  dispatch_profiles:
    - agent
```

- Dispatcher ONLY claims cards assigned to `agent` profile
- Cards assigned to `default`, `brett`, or anything else are skipped
- Fail-closed: empty list = nothing dispatched

### Recommended config

```yaml
kanban:
  dispatch_in_gateway: true
  dispatch_interval_seconds: 30
  default_assignee: brett          # unassigned → skipped
  auto_decompose: false            # triage stays parked
  dispatch_profiles:
    - agent                        # only agent profile dispatched
  failure_limit: 2
  auto_promote_children: true
```

---

## Card Creation

### CLI
```bash
# Backlog (triage — stays parked if auto_decompose: false)
hermes kanban create "Task title" --triage --body "Details..."

# Ready (dispatched if assigned to agent)
hermes kanban create "Task title" --assignee agent --body "Details..."

# With skills
hermes kanban create "Fix auth" --assignee agent --skill dev-lead

# With workspace
hermes kanban create "Build feature" --assignee agent --workspace "dir:/path/to/project"

# Goal mode (keeps going until acceptance criteria met)
hermes kanban create "Translate docs" --assignee linguist --goal --goal-max-turns 15
```

### WebUI
- Click `+` on any column header
- Creating from Triage column → stays in triage
- Creating from Ready column → goes to ready
- Assignee dropdown: pick profile or leave blank

### Dashboard
- `hermes dashboard` → Kanban tab
- Drag cards between columns
- Click card → side drawer with edit, dependencies, status actions

---

## Worker Lifecycle

1. Dispatcher spawns `hermes -p <assignee>` with `HERMES_KANBAN_TASK=t_abcd`
2. Worker calls `kanban_show()` to read task
3. Worker does work in `$HERMES_KANBAN_WORKSPACE`
4. Worker calls `kanban_heartbeat()` during long operations
5. Worker completes: `kanban_complete()`, `kanban_request_review()`, or `kanban_block()`

### Worker tools (auto-injected, nothing to install)

| Tool | Purpose |
|---|---|
| `kanban_show` | Read current task |
| `kanban_complete` | Finish with summary + metadata |
| `kanban_request_review` | Hand off to reviewer |
| `kanban_request_changes` | Reviewer rejects → back to implementer |
| `kanban_block` | Stop work, needs human input |
| `kanban_heartbeat` | Signal liveness |
| `kanban_comment` | Add note to task thread |
| `kanban_create` | (Orchestrators) fan out child tasks |
| `kanban_link` | (Orchestrators) add dependency |
| `kanban_unblock` | (Orchestrators) restore blocked task |

---

## Key Config Options

| Key | Default | Purpose |
|---|---|---|
| `dispatch_in_gateway` | `true` | Dispatcher runs inside gateway |
| `dispatch_interval_seconds` | `60` | Seconds between dispatch ticks |
| `default_assignee` | `""` | Auto-assign unassigned cards to this profile |
| `auto_decompose` | `true` | Auto-run decomposer on triage tasks |
| `auto_decompose_per_tick` | `3` | Max decompositions per tick |
| `dispatch_profiles` | unset (any) | Restrict which profiles are dispatchable |
| `max_in_progress` | unset | Global concurrency cap |
| `max_in_progress_per_profile` | unset | Per-profile concurrency cap |
| `failure_limit` | `2` | Auto-block after N consecutive failures |
| `review_dispatch` | `true` | Spawn reviewer for review tasks |
| `orchestrator_profile` | `""` | Profile for root task after decomposition |
| `auto_promote_children` | `true` | Auto-promote child tasks to ready |
| `auto_subscribe_on_create` | `true` | Resume creator on task completion |

---

## Important Notes

1. **Gateway caches config at startup.** After changing `default_assignee`, `dispatch_profiles`, or `auto_decompose`, restart: `privgate systemctl-hermes root restart hermes-gateway`

2. **`triage` with `auto_decompose: true` is NOT a backlog.** It's an active processing column that auto-decomposes tasks.

3. **`dispatch_profiles` is the cleanest way to restrict dispatch.** Only listed profiles get cards dispatched.

4. **Scratch workspaces are deleted on completion.** Use `dir:<path>` or `worktree` for persistent work.

5. **Workers are fire-and-forget OS processes.** They survive gateway restarts (launched in own systemd scope).

6. **Protocol violation = worker exits without calling kanban_complete/block.** Dispatcher retries bounded times, then auto-blocks.
