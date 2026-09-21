# Kanban Workflow — Card Lifecycle

## Config

```yaml
kanban:
  default_assignee: brett       # Cards default to non-spawnable assignee
  dispatch_in_gateway: true     # Dispatcher runs inside gateway
  dispatch_interval_seconds: 30 # Dispatch tick interval
```

**Key:** `default_assignee: brett` means new cards are NOT dispatched until explicitly assigned to `agent`.

## Creating Cards

### Backlog (not dispatched)
```bash
hermes kanban create "Task title" --body "Details..."
# No assignee → defaults to brett → dispatcher skips
```
- Shows in WebUI with "Only Mine" filter OFF (unassigned)
- Refine: `hermes kanban edit <id>`, `hermes kanban specify <id>`, `hermes kanban comment <id> --body "..."`

### Ready to Dispatch
```bash
hermes kanban assign <id> agent
# Dispatcher picks up on next tick (30s)
```

### Dispatch Immediately (skip backlog)
```bash
hermes kanban create "Task title" --assignee agent --body "Details..."
```

## Status Flow

```
  ┌──────────┐
  │ (none)    │ ← backlog (unassigned, dispatcher skips)
  └────┬─────┘
       │ assign agent
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
| (none/unassigned) | any | ❌ No — skipped |
| `agent` | ready | ✅ Yes — spawns worker |
| `default` | ready | ✅ Yes — spawns worker |
| `brett` | any | ❌ No — non-spawnable |
| any | scheduled | ❌ No — parked |
| any | blocked | ❌ No — waiting on user |

## Useful Commands

```bash
# Create backlog card
hermes kanban create "Task" --body "Details..."

# Assign to agent (dispatches)
hermes kanban assign <id> agent

# List all cards
hermes kanban list

# List by assignee
hermes kanban list --assignee agent

# Show card
hermes kanban show <id>

# Edit card
hermes kanban edit <id>

# Add comment
hermes kanban comment <id> --body "Note"

# Block (needs user input)
hermes kanban block <id>

# Complete
hermes kanban complete <id> --result "Done"

# Archive
hermes kanban archive <id>
```
