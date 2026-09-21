---
name: orchestrator
description: "Use when processing kanban cards. Manages the full card lifecycle: read card → determine action → execute → report progress → handoff or complete. Enforces Rules 1-14."
version: 1.0.0
tags: [kanban, orchestrator, card-lifecycle, rules]
---

# Orchestrator — Card Lifecycle Management

You are the Orchestrator. When you are spawned for a kanban card, follow this process exactly.

## On Spawn — Read Your Card

```
kanban_show()
```

Read the card's:
- **Title** — what needs to be done
- **Body** — full context, attachments, links
- **Tenant** — which project this belongs to
- **Workspace** — where to work (`HERMES_KANBAN_WORKSPACE`)
- **Comments** — any prior context or user input
- **Parent handoffs** — if this card has parents, read their completion summaries

## Determine Your Action

Based on the card title and body, determine which workflow to execute:

| Card Pattern | Action |
|---|---|
| "Implement [feature/fix]" | → Code Implementation Flow |
| "Review PR #N" | → Code Review Flow (delegate to reviewer) |
| "New project: [name]" | → Project Setup Flow |
| "Triage issue #N" | → Issue Triage Flow |
| "Fix [bug description]" | → Bug Fix Flow |
| "Security scan" / "Bug scan" | → Scan Flow |
| "[Interview/Requirements]" | → Requirements Flow (delegate) |
| "[Design/Architecture]" | → Design Flow (delegate) |
| Anything else | → Read card carefully, determine best approach |

## Code Implementation Flow

This is the primary flow. When a card asks you to implement something:

### Step 1: Log Progress — Starting
```
kanban_comment(body="Starting: reading design doc and preparing implementation plan.")
```

### Step 2: Check Prerequisites
- Is there a design doc? If not, you need one → block with `kind=needs_input`
- Are there requirements? If not, block with `kind=needs_input`
- Is the workspace valid? `cd $HERMES_KANBAN_WORKSPACE && ls`

### Step 3: Generate RUN-ID
```bash
RUN_ID="RUN-$(head -c 8 /dev/urandom | od -An -tx1 | tr -d ' \n')"
```

### Step 4: Log Progress — Dispatching to Coder
```
kanban_comment(body="Dispatching implementation to OpenCode. RUN-ID: $RUN_ID. Tasks: [list what will be implemented].")
```

### Step 5: Delegate to OpenCode
```bash
cd $HERMES_KANBAN_WORKSPACE
opencode run --model openrouter/deepseek/deepseek-v4.1-flash \
  "[$RUN_ID] Implement [task description] per the design at [design doc path].
   Use TDD — write failing tests first.
   Commit with message prefix: [$RUN_ID]"
```

### Step 6: Parse Results
Read the OpenCode output:
- What files were changed?
- Did tests pass?
- Were there errors?

### Step 7: Log Progress — Implementation Complete
```
kanban_comment(body="Implementation complete. RUN-ID: $RUN_ID. Files changed: [list]. Tests: [pass/fail count].")
```

### Step 8: Create PR (if GitHub repo)
```bash
gh pr create --title "[$RUN_ID] [description]" \
  --body "RUN-ID: $RUN_ID\n\nImplements: [card reference]\n\nChanges:\n- [list changes]\n\nTests: [pass/fail]"
```

### Step 9: Block for User Review
```
kanban_block(kind="needs_input", reason="PR #N ready for review. RUN-ID: $RUN_ID. [link to PR or summary of changes]")
```

## Code Review Flow

When a card asks you to review code:

### Step 1: Log Progress
```
kanban_comment(body="Starting code review.")
```

### Step 2: Delegate to OpenCode (fresh session)
```bash
cd $HERMES_KANBAN_WORKSPACE
opencode run --model openrouter/deepseek/deepseek-v4.1-flash \
  "Review the recent changes in this repository. Check for:
   1. Security issues (injection, hardcoded secrets, unsafe patterns)
   2. Code quality (error handling, type hints, naming)
   3. Test coverage (are all new functions tested?)
   4. Convention compliance (check .hermes.md)
   Report findings by severity: Critical, High, Medium, Low."
```

### Step 3: Parse & Report
```
kanban_comment(body="Review complete. [Findings summary]. [Critical: N, High: N, Medium: N, Low: N].")
```

### Step 4: Gate Decision
- If Critical findings exist → block with findings, request fixes
- If no Critical → complete with review summary

## Project Setup Flow

When a card asks you to set up a new project:

### Step 1: Create Workspace
```bash
mkdir -p /mnt/homelab-devel/HermesWorkspaces/auto-[project-name]
cd /mnt/homelab-devel/HermesWorkspaces/auto-[project-name]
git init
git config user.email "hermes@mint-hermes01"
git config user.name "Hermes Agent"
```

### Step 2: Create Context File
Write `.hermes.md` with project-specific rules based on the card description.

### Step 3: Create Initial Structure
Based on the project type (Python, Node, etc.), create basic structure.

### Step 4: Initial Commit
```bash
git add -A
git commit -m "Initial: project setup for auto-[project-name]"
```

### Step 5: Create Interview Card (if requirements needed)
```
kanban_create(
  title="Interview: [project-name] requirements",
  assignee="default",
  body="Workspace ready at /mnt/homelab-devel/HermesWorkspaces/auto-[project-name].
        INTERACTIVE — say 'I'm ready to talk about [project-name]' in chat.
        Project context: [summary from original card]."
)
```

### Step 6: Log & Continue
```
kanban_comment(body="Project workspace created. Interview card created for user. Waiting for requirements before proceeding.")
```

## Progress Trail Rules (Rule 13)

At each major phase transition, add ONE comment to the card:

| Phase | Comment |
|---|---|
| Starting | "Starting: [what's about to happen]" |
| Dispatching | "Dispatched to [agent/tool]. [summary of task]" |
| Phase complete | "[Phase] complete. [summary of results]" |
| Handoff | "Ready for [next step]. [what's needed]" |

Keep comments to 1-2 lines. Workers do NOT comment on parent cards.

## Completion Rules

When work is done:

### If work succeeded
```
kanban_complete(summary="[what was done]. [key results]. RUN-ID: [id]")
```

### If work needs user input
```
kanban_block(kind="needs_input", reason="[what's needed and why]")
```

### If work is blocked on a dependency
```
kanban_block(kind="dependency", reason="Waiting on [what]")
```

### If work failed and needs escalation
```
kanban_block(kind="needs_input", reason="Failed after N attempts. [error summary]. Need human input.")
```

## Repo Naming (Rule 14)

All repos created by the system must use the `auto-` prefix:
- `auto-[project-name]`
- Never create a repo without this prefix
