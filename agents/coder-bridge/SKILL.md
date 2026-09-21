---
name: coder-bridge
description: "Use when delegating coding tasks to OpenCode. Handles RUN-ID generation, model selection, invocation, Superpowers loading, and result parsing."
version: 1.0.0
tags: [opencode, coding, delegation, run-id, superpowers]
---

# Coder Bridge — OpenCode Invocation

## Model Assignment

| Task Type | Model | Why |
|---|---|---|
| Implementation (I1, I2) | `openrouter/deepseek/deepseek-v4.1-flash` | Best coding quality for the cost |
| Code review | `openrouter/deepseek/deepseek-v4.1-flash` | Needs to find subtle bugs |
| Simple edits, fixes | `openrouter/deepseek/deepseek-v4-flash-0731` | Cheap, fast, sufficient |

## RUN-ID Convention

Every coding task gets a unique identifier:

```bash
RUN_ID="RUN-$(head -c 8 /dev/urandom | od -An -tx1 | tr -d ' \n')"
```

The RUN-ID appears in:
- Task description (first line)
- Git commit messages: `[$RUN_ID] description`
- PR descriptions
- Kanban card comments
- Traceability records

## Invocation Pattern

### Full Implementation (TDD, with Superpowers)
```bash
cd $HERMES_KANBAN_WORKSPACE
opencode run --model openrouter/deepseek/deepseek-v4.1-flash \
  "[$RUN_ID] [Task description].

   Use TDD — write failing tests first, then implement.
   Commit with message prefix: [$RUN_ID]
   Design reference: [path to design doc]"
```

### Code Review
```bash
cd $HERMES_KANBAN_WORKSPACE
opencode run --model openrouter/deepseek/deepseek-v4.1-flash \
  "Review the recent changes. Check for:
   1. Security issues
   2. Code quality
   3. Test coverage
   4. Convention compliance (.hermes.md)
   Report by severity: Critical, High, Medium, Low."
```

### Bug Fix (with root cause investigation)
```bash
cd $HERMES_KANBAN_WORKSPACE
opencode run --model openrouter/deepseek/deepseek-v4.1-flash \
  "[$RUN_ID] Debug and fix: [bug description].

   Iron Law: investigate root cause before fixing.
   Reproduce → read trace → hypothesize → fix → verify.
   Commit with message prefix: [$RUN_ID]"
```

### Simple Edit (no TDD needed)
```bash
cd $HERMES_KANBAN_WORKSPACE
opencode run --model openrouter/deepseek/deepseek-v4-flash-0731 \
  "[$RUN_ID] [Simple task description].
   Commit with message prefix: [$RUN_ID]"
```

## Superpowers Integration

Superpowers loads automatically via the OpenCode plugin (`~/.config/opencode/opencode.jsonc`). No extra flags needed. The following skills are available:

- **test-driven-development** — RED→GREEN→REFACTOR enforcement
- **systematic-debugging** — Root cause investigation
- **requesting-code-review** — Fresh agent review
- **writing-plans** — Break specs into micro-tasks
- **brainstorming** — Explore before coding

## Result Parsing

After OpenCode completes, check:

1. **Exit code** — 0 = success, non-zero = failure
2. **Test results** — look for "N passed" or "N failed" in output
3. **Changed files** — look for file paths in the diff/commit output
4. **Errors** — look for error messages, tracebacks, failures

## Git Worktree Pattern

For parallel tasks on the same repo:
```bash
cd /path/to/repo
git worktree add .worktrees/$RUN_ID -b feature/$RUN_ID
cd .worktrees/$RUN_ID
opencode run --model openrouter/deepseek/deepseek-v4.1-flash "[$RUN_ID] task"
```

## Error Handling

| Error | Action |
|---|---|
| OpenCode exits non-zero | Check output for error, retry once with clearer instructions |
| Tests fail after implementation | Delegate debugging to OpenCode with systematic-debugging skill |
| No files changed | Check if OpenCode misunderstood the task, retry with more specific instructions |
| Model not found | Fall back to `openrouter/deepseek/deepseek-v4-flash-0731` |
