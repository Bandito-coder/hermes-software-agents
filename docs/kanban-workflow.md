# Kanban Workflow — Card Lifecycle

## Creating Cards

### Backlog (parked, not dispatched)
```bash
hermes kanban create "Task title" --assignee default --body "Details..."
hermes kanban schedule <id>
```
- Assigned to `default` (your profile) → shows in "Only Mine" filter in WebUI
- `scheduled` status → dispatcher skips it
- Refine with `hermes kanban edit <id>`, `hermes kanban specify <id>`

### Ready to Dispatch
```bash
hermes kanban unblock <id>     # scheduled → ready → dispatched next tick
```

### Assign to Agent (bypass backlog)
```bash
hermes kanban create "Task title" --assignee agent --body "Details..."
# Dispatcher picks up on next tick (30s)
```

## Status Flow

```
  ┌──────────┐
  │ scheduled │ ← backlog (parked)
  └────┬─────┘
       │ unblock
       ▼
  ┌──────────┐     ┌─────────┐
  │   ready   │ ──→ │ running  │ ← agent working
  └──────────┘     └────┬────┘
                        │ review_requested
                        ▼
                   ┌─────────┐
                   │  review  │ ← reviewer checking
                   └────┬────┘
                        │
                   ┌────┴────┐
                   ▼         ▼
              ┌──────┐  ┌────────┐
              │ done  │  │ blocked │ ← needs user input
              └──────┘  └────────┘
```

## Dispatch Rules

| Assignee | Status | Dispatched? |
|---|---|---|
| `agent` | ready | ✅ Yes — spawns worker |
| `default` | ready | ✅ Yes — spawns worker |
| `brett` | any | ❌ No — non-spawnable assignee |
| any | scheduled | ❌ No — parked |
| any | blocked | ⚠️ May be promoted to ready |

## Assignment

| Assignee | Profile on Disk | Use Case |
|---|---|---|
| `default` | Yes | Your cards (shows in "Only Mine") |
| `agent` | Yes | Agent worker cards (auto-dispatched) |
| `brett` | No | Never dispatched (safe parking) |

## Useful Commands

```bash
# List your cards
hermes kanban list --mine

# List by status
hermes kanban list --status scheduled

# Show card details
hermes kanban show <id>

# Edit card
hermes kanban edit <id>

# Add comment
hermes kanban comment <id> --body "Note"

# Block on user input
hermes kanban block <id>

# Archive completed
hermes kanban archive <id>
```
