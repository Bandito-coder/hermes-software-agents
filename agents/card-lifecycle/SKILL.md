---
name: card-lifecycle
description: "Use when processing kanban cards autonomously. Contains the decision logic, prompts, and error handlers for each card type. This is the execution engine."
version: 1.0.0
tags: [kanban, lifecycle, autonomous, decisions]
---

# Card Lifecycle — Autonomous Execution Engine

This skill contains the decision logic for processing kanban cards. It works with the orchestrator skill to drive cards through the pipeline.

## Decision Tree

When you receive a card, follow this decision tree:

```
CARD RECEIVED
  │
  ├─ Is the card assigned to YOU (default/hermes)?
  │   ├─ YES → Continue to "Process Card"
  │   └─ NO → Do nothing (not your card)
  │
  ├─ PROCESS CARD
  │   │
  │   ├─ Read card title + body
  │   │
  │   ├─ Does it require USER INPUT first?
  │   │   ├─ YES → Block with needs_input, wait
  │   │   └─ NO → Continue
  │   │
  │   ├─ Does it require a DESIGN DOC?
  │   │   ├─ YES → Is one attached/linked?
  │   │   │   ├─ YES → Use it
  │   │   │   └─ NO → Block: "Need design doc before implementation"
  │   │   └─ NO → Continue
  │   │
  │   ├─ Is it IMPLEMENTATION work?
  │   │   ├─ YES → Delegate to OpenCode (coder-bridge skill)
  │   │   └─ NO → Continue
  │   │
  │   ├─ Is it REVIEW work?
  │   │   ├─ YES → Delegate review to OpenCode
  │   │   └─ NO → Continue
  │   │
  │   ├─ Is it SETUP work?
  │   │   ├─ YES → Execute setup steps
  │   │   └─ NO → Continue
  │   │
  │   └─ Is it UNKNOWN?
  │       └─ Read card carefully, determine best approach
  │          If unclear → Block: "Need clarification on [what]"
```

## Prompts for Each Card Type

### Implementation Card Prompt
```
You are implementing a feature or fix. Follow these steps:

1. Read the design doc (if provided)
2. Generate a RUN-ID
3. Log progress: "Starting implementation"
4. Delegate to OpenCode with TDD
5. Parse results
6. Create PR (if GitHub repo)
7. Block on user for review

Model: openrouter/deepseek/deepseek-v4.1-flash
Skill: test-driven-development (auto-loaded)
```

### Review Card Prompt
```
You are reviewing code. Follow these steps:

1. Log progress: "Starting code review"
2. Delegate to OpenCode for fresh review
3. Parse findings by severity
4. If Critical findings → block with findings
5. If no Critical → complete with summary

Model: openrouter/deepseek/deepseek-v4.1-flash
```

### Setup Card Prompt
```
You are setting up a new project. Follow these steps:

1. Create workspace directory (auto- prefix)
2. Initialize git
3. Create .hermes.md context file
4. Create initial project structure
5. Commit
6. Create interview card on user (if requirements needed)
7. Log progress and complete

Model: openrouter/deepseek/deepseek-v4-flash-0731
```

### Triage Card Prompt
```
You are triaging a GitHub issue. Follow these steps:

1. Read the issue (title, body, labels)
2. Search for duplicates: gh issue list --search
3. Classify: bug | feature | question | duplicate | invalid
4. Assign priority: P0 | P1 | P2 | P3
5. Auto-label: gh issue edit N --add-label
6. If actionable → create implementation card
7. If duplicate/invalid → close with explanation

Model: openrouter/deepseek/deepseek-v4-flash-0731
```

## Error Handlers

### Handler: Design Doc Missing
```
kanban_block(kind="needs_input", 
  reason="Cannot proceed with implementation — no design doc found.
         Please either:
         1. Attach the design doc to this card, or
         2. Create a design card first (assign to agent with 'design [feature]')")
```

### Handler: OpenCode Failed
```
If OpenCode exits non-zero:
1. Read the error output
2. If it's a model error → retry with fallback model
3. If it's a code error → delegate debugging to OpenCode
4. If it fails twice → block with error summary
```

### Handler: Tests Failed
```
If tests fail after implementation:
1. Log: "Tests failing, delegating to debug"
2. Delegate to OpenCode with systematic-debugging skill
3. If debug succeeds → continue
4. If debug fails after 3 rounds → block with findings
```

### Handler: PR Creation Failed
```
If gh pr create fails:
1. Check if gh is authenticated: gh auth status
2. Check if remote exists: git remote -v
3. If no remote → complete card without PR, note "PR not created — no remote configured"
4. If auth issue → block with auth error
```

### Handler: User Response Timeout
```
If a card has been blocked for >3 days:
- Send reminder notification (handled by blocked-card-reminder cron)

If >7 days:
- Escalate: list all overdue cards

If >14 days:
- Ask: "Should this card be archived or deprioritized?"
```

## Progress Trail Template

At each major step, add a comment:

```python
# Starting
kanban_comment(body=f"Starting: {task_summary}")

# Dispatching
kanban_comment(body=f"Dispatched to OpenCode. RUN-ID: {run_id}. Model: {model}. Tasks: {task_list}")

# Phase complete
kanban_comment(body=f"{phase_name} complete. {result_summary}")

# Handoff
kanban_comment(body=f"Ready for {next_step}. {what_is_needed}")
```

## Completion Template

```python
# Success
kanban_complete(summary=f"{what_was_done}. {key_results}. RUN-ID: {run_id}")

# Needs user input
kanban_block(kind="needs_input", reason=f"{what_is_needed}. {context}")

# Blocked on dependency
kanban_block(kind="dependency", reason=f"Waiting on {dependency}")

# Failed
kanban_block(kind="needs_input", reason=f"Failed after {n} attempts. {error_summary}. Need human input.")
```
