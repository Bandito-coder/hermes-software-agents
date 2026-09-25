# Project Workflow Guide

How to use the Dev Lead agent to build projects from start to finish.

**Front door:** use the **PM** skill (`/pm`) in chat for "new project", "approve t_xxx", "kick off the design phase", "status". PM creates and manages the cards — instructions and guardrails in `agents/pm/SKILL.md`. Everything below is what happens on the card after PM hands it to Dev Lead.

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
Phase 2: DESIGN ────────→ design review loop → BLOCK (you approve design)
Phase 3: BUILD ─────────→ automatic (tests first, then Builder, gates, review)
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
> Card blocked: "Interview questions ready. Say 'Interview me for \<project\>' in chat to answer interactively with tappable buttons."

**Your options:**
1. **Interactive interview (recommended)** → say "Interview me for \<project\>" in chat. The `dev-interview` skill reads questions from the card, presents them as tappable buttons (Telegram) or numbered choices (WebUI/Discord), posts your answers back, and unblocks the card automatically.
2. **Comment answers directly** → on the kanban board, comment your answers in the expected format (Q1: A, Q2: B), then unblock
3. **Skip the interview** → comment "Skip interview" and unblock. Coach writes BRIEF.md with assumptions from the card body.

**Interview format:** Coach posts questions with A/B/C options and a recommendation. Up to 5 questions per round, 3 rounds max. Each round, Coach reads your answers and either asks follow-ups or writes BRIEF.md.

## Phase 2: Design

The Architect produces SPEC.md with 2-3 alternatives. **Before you see it**, the Design Reviewer validates the detailed design (Mode 2) — traceability of requirements → acceptance criteria, data model, interface contracts, edge cases, error handling, test plan.

**The design review loop:**
- Review **PASS** → the card blocks for your approval
- Review **FAIL** → the findings go back to the Architect, who revises SPEC.md; the reviewer re-checks ONLY the changes (no new invented problems)
- Max **3 review cycles**. If the reviewer is still not satisfied after 3 rounds, you get a **referee call**:

> Card blocked: "DESIGN REVIEW REFEREE: comment (a) 'proceed to build' to bypass the design review for this card, or (b) your guidance for resolving the review issues — the review restarts with up to 3 more cycles. Then unblock."

**Your options (after a failed review):**
1. **Proceed anyway** → comment "proceed to build" (+ unblock) → the design review is bypassed *for this card*; the design goes to the normal approval gate
2. **Give guidance** → comment your direction for resolving the issues (+ unblock) → the Architect revises per your guidance and the review restarts with a fresh 3-cycle budget
3. **Unblock without comment** → treated as "proceed"

**What you see on a passing design:**
> Card blocked: "Design ready. Review docs/SPEC.md. To approve: unblock. To request changes: comment with changes, then unblock. To discuss alternatives: say 'Discuss design for <project>' in chat."

**Your options:**
1. **Review SPEC.md** → unblock to approve the recommended approach
2. **Choose a different alternative** → comment which one, unblock
3. **Request changes** → comment what to change, unblock
4. **Discuss** → say "Discuss design for <project>" in chat

## Phase 3: Build (automatic, tests-first)

The agent builds without blocking — **tests are written BEFORE any production code**:
- **Test Author writes the failing tests first** — from SPEC.md/BRIEF.md only (never to suit code), with a trace (`tests/TRACE.md`) mapping every acceptance criterion to its test case. The build is structurally blocked until every spec item has a traced failing test.
- Builder implements via OpenCode + Superpowers (TDD) — makes the failing tests pass
- Browser Tester verifies web UI
- Gatekeeper runs quality gates + verifies the tests-first trace
- Reviewer checks spec compliance

If issues are found, the agent fixes them automatically (up to 4 cycles).

For bug fixes (W-FIX), the same rule applies: the failing test comes first (uplifted if one already exists, "fail until it's fixed"), then the fix.

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
