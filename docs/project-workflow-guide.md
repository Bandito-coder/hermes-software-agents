# Project Workflow Guide

How to use the Dev Lead agent to build projects from start to finish.

## Starting a Project

**Option 1: Kanban card (recommended)**
```
hermes kanban create "Build: My Project" \
  --assignee agent \
  --skill dev-lead \
  --workspace "dir:/path/to/workspace" \
  --body "Description of what to build..."
```

**Option 2: Chat**
> "Start a new project: My Project. Build a web app that does X."

The Dev Lead will create the workspace, initialize git, and begin the workflow.

## The Five Phases

Every project goes through five phases with **four blocking points** where your input is required.

```
Phase 0: PROJECT PREP ──→ automatic
Phase 1: REQUIREMENTS ──→ BLOCK (you approve requirements)
Phase 2: DESIGN ────────→ BLOCK (you approve design)
Phase 3: BUILD ─────────→ automatic (Builder, tests, review)
Phase 4: BUILD APPROVAL → BLOCK (you test and approve)
Phase 5: FINALIZE ──────→ automatic (push to GitHub)
```

## How Blocking Works

When the agent needs your input, the kanban card status changes to **blocked**. You'll see a comment explaining what's needed and how to respond.

### Three Ways to Respond

| Method | How | When to use |
|--------|-----|-------------|
| **Kanban board** | Comment on the card, then click Unblock | When you want to review files first |
| **Chat command** | Say "Unblock <project>" or "I approve <project>" | Quick approval without opening the board |
| **Interactive chat** | Say "Interview me for <project>" | When you want to discuss in real-time |

### What Your Response Means

| Your action | What happens |
|-------------|-------------|
| Unblock with no comment | **Implicit approval** — agent proceeds to next phase |
| Comment "Approved" + unblock | **Explicit approval** — agent proceeds |
| Comment with changes + unblock | **Request changes** — agent updates and re-blocks |
| Say "Interview me for <project>" in chat | **Interactive mode** — questions asked in chat |

## Phase 1: Requirements

The Coach agent assesses 9 dimensions and asks questions about what's unknown.

**What you see:**
> Card blocked: "Requirements ready. Review docs/BRIEF.md. To approve: unblock. To request changes: comment with changes, then unblock. To do the interview interactively: say 'Interview me for <project>' in chat."

**Your options:**
1. **Review BRIEF.md** → unblock to approve
2. **Request changes** → comment what's missing, unblock
3. **Interactive interview** → say "Interview me for <project>" in chat. The Coach will ask questions in real-time. You answer inline. When done, the card unblocks automatically.

**Interview format:** Up to 10 questions, 3 rounds max. Each question has A/B/C options with a recommendation and a "More info" path.

## Phase 2: Design

The Architect produces SPEC.md with 2-3 alternatives.

**What you see:**
> Card blocked: "Design ready. Review docs/SPEC.md. To approve: unblock. To request changes: comment with changes, then unblock. To discuss alternatives: say 'Discuss design for <project>' in chat."

**Your options:**
1. **Review SPEC.md** → unblock to approve the recommended approach
2. **Choose a different alternative** → comment which one, unblock
3. **Request changes** → comment what to change, unblock
4. **Discuss** → say "Discuss design for <project>" in chat

## Phase 3: Build (automatic)

The agent builds without blocking:
- Builder implements via OpenCode + Superpowers (TDD)
- Browser Tester verifies web UI
- Test Author verifies spec coverage
- Gatekeeper runs quality gates
- Reviewer checks spec compliance

If issues are found, the agent fixes them automatically (up to 4 cycles).

## Phase 4: Build Approval

The agent builds a Docker container for you to test.

**What you see:**
> Card blocked: "Build ready for testing. Docker preview at http://host:port. Test the app. To approve: unblock. To request fixes: comment with fixes needed, then unblock."

**Your options:**
1. **Test the app** at the Docker preview URL
2. **Approve** → unblock (or comment "Approved" + unblock)
3. **Request fixes** → comment what's wrong, unblock → agent fixes and re-blocks

**The fix loop:** You can request fixes as many times as needed. Each cycle:
- You comment with issues → unblock
- Agent fixes via OpenCode + Superpowers
- Agent re-deploys Docker
- Agent re-blocks for your review

This continues until you approve.

## Phase 5: Finalize

After approval, the agent:
1. Pushes the branch to GitHub
2. Comments with the repo URL
3. Completes the card

## Quick Reference

| Action | Command |
|--------|---------|
| Create project card | `hermes kanban create "Build: X" --assignee agent --skill dev-lead --workspace "dir:/path"` |
| Unblock a card | `hermes kanban unblock <card-id>` |
| Unblock with note | `hermes kanban unblock <card-id> --reason "Approved"` |
| Add comment | `hermes kanban comment <card-id> "Your feedback"` |
| Check status | `hermes kanban list` |
| View card details | `hermes kanban show <card-id>` |

## Tips

- **You don't need to be thorough in the initial card.** The Coach will ask about anything that's unclear. A one-line description is fine — the interview fills in the details.
- **You can skip phases.** If you say "Skip the interview, I know what I want" in a comment, the agent will proceed with your card body as the requirements.
- **The Docker preview updates after each fix cycle.** You always test the latest version.
- **Cost is tracked per card.** The final comment includes the total cost from LiteLLM.
