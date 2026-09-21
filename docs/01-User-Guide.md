# User Guide — Hermes Agentic SDLC Platform

**Audience:** You (the operator). Day-to-day usage of the system.
**Last updated:** 2026-09-21 (AEST)

---

## Getting Started

### What This System Does

You have an AI-powered software development platform running on your home server. It can:

- **Turn ideas into code** — describe what you want in plain English, answer a few questions, approve designs, and the system implements, tests, reviews, and prepares a pull request automatically.
- **Keep your projects healthy** — automated bug scans and security scans run weekly, reporting only when something needs attention.
- **Handle GitHub issues end-to-end** — issues arrive, get triaged, get designed, get implemented, get tested, get reviewed, and land as a PR ready for your approval.
- **Manage your work** — a kanban board tracks everything across all projects, showing you exactly what needs your attention.

### Your Two Interfaces

1. **Chat** — Telegram, Discord, or the WebUI. Talk to the agent naturally: "start a new project," "what's on my board?", "review PR #42."
2. **Kanban Board** — Visual task board at `hermes dashboard` → Kanban tab. Shows all cards across all projects with status columns.

### How to Access

| Surface | How |
|---|---|
| **Telegram** | Message your Hermes bot |
| **Discord** | Message in your Hermes channel or DM |
| **WebUI** | Open http://localhost:8787 in your browser |
| **Dashboard** | Open http://localhost:9119 in your browser |
| **CLI** | `hermes` in terminal |

---

## The Kanban Board — Your Work Queue

The kanban board is your primary interface for "what should I do next?"

### Columns

| Column | What It Means | What You Do |
|---|---|---|
| **Triage** | New work, not yet assessed | Nothing — the agent handles this |
| **Todo** | Assessed, waiting on dependencies | Nothing — auto-promotes when ready |
| **Ready** | Approved to start, assigned to you | **This is your to-do list** |
| **Running** | Agent is actively working | Nothing — check progress via comments |
| **Blocked** | Agent needs your input | **Respond to these first** |
| **Review** | Work done, under review | Review and approve |
| **Done** | Complete | Nothing |

### Quick Commands

```bash
# See everything on the board
hermes kanban list

# See only your cards
hermes kanban list --assignee default

# See only one project
hermes kanban list --tenant my-web-app

# See blocked cards (agent needs you)
hermes kanban list --status blocked

# See ready cards (your to-do list)
hermes kanban list --status ready

# View a specific card
hermes kanban show t_abc123

# Add a comment to a card
hermes kanban comment t_abc123 "Approved, looks good"

# Unblock a card
hermes kanban unblock t_abc123
```

### From Chat

You can also manage cards from Telegram/Discord/WebUI:
- "What's on my kanban board?"
- "Show me blocked cards"
- "Unblock t_abc123 and say I approve"
- "Create a card for implementing auth module in my-web-app"

---

## How Cards Work — The Ping-Pong Pattern

Cards bounce between you and the agent. Here's the flow:

### Non-Interactive Input (most common)

1. Agent needs your input → creates a card assigned to you (status: blocked)
2. You read the card (dashboard, CLI, or `hermes kanban show t_abc`)
3. You add your input as a comment
4. You reassign the card back to the agent (unblock)
5. Agent reads your comment and continues working

### Interactive Input (interviews, discussions)

1. Agent needs a conversation → creates a card marked "INTERACTIVE"
2. You go to any chat surface (Telegram, Discord, WebUI)
3. You say: "I'm ready to talk about [project name]"
4. Agent reads the card context and conducts the conversation
5. When done, the agent auto-completes the card and continues

### What You See on a Card

```
Card: t_abc — "Implement auth module" [my-web-app]
Status: blocked

[14:30] Agent: Starting implementation. Design doc loaded.
[14:31] Agent: Dispatched 4 tasks: login, registration, password-reset, tests.
[14:52] Agent: All implementation tasks complete. 14 tests pass.
[15:05] Agent: Review complete — 0 critical. PR #42 created.
         → Status: blocked (needs_input: "Review PR #42")

You: [add comment] "Looks good, approved"
You: [unblock card]

Agent continues, merges PR, closes card.
```

---

## Project Management

### Creating a New Project

**Via chat:**
```
"I'd like to start a new project. The idea is a trading signals dashboard.
 Get everything ready."
```

**Via kanban card:**
```bash
hermes kanban create "New project: trading signals dashboard" \
  --assignee default \
  --tenant trading-signals
```

### Switching Between Projects

**In WebUI:** Use the workspace picker at the top.
**In chat:** "Switch to my-web-app and continue the auth module"
**In CLI:** `cd /mnt/homelab-devel/HermesWorkspaces/my-web-app && hermes`

### Viewing Progress Across Projects

```bash
# All projects
hermes kanban list

# One project
hermes kanban list --tenant trading-signals

# Dashboard view
hermes dashboard  # → Kanban tab
```

---

## Workflow Walkthroughs

Each walkthrough shows: what you say, what the agent does, what you see, what you need to do, and how it completes.

### R1 — Develop Requirements from a Raw Idea

**What you say:**
"I want an app that tracks my LEGO collection"

**What the agent does:**
- Sets up a project workspace
- Runs an interview (up to 3 rounds of questions with options)
- Generates a requirements document

**What you see on kanban:**
- Card on you: "Interview: LEGO collection app requirements" (interactive)

**What you need to do:**
Go to chat and say "I'm ready to talk about LEGO collection." Answer the agent's questions (multiple choice with recommendations — just say "yes" to the default for easy ones).

**How it completes:**
- Interview card auto-completes
- New card on you: "Review requirements: LEGO collection" (non-interactive)
- You review the requirements doc, add feedback or approve
- Agent finalizes requirements

---

### R3/R4 — Generate System Design

**What you say:** (after approving requirements)
"Approve requirements, proceed to design"

**What the agent does:**
- Generates high-level architecture (2-3 alternatives with trade-offs)
- Presents recommendation for approval
- Generates detailed design (module specs, data models, API contracts)

**What you see on kanban:**
- Card on you: "Review architecture: LEGO collection" (non-interactive)
- After approval: card on you: "Review detailed design: LEGO collection" (non-interactive)

**What you need to do:**
Review the design docs. Approve or give feedback via card comments.

---

### I1 — Implement a Design

**What you say:** (after approving design)
"Approved, implement it"

**What the agent does:**
- Breaks design into micro-tasks
- Implements each task using TDD (test-driven development)
- Code review by a fresh agent
- Creates a pull request

**What you see on kanban:**
- Progress comments on the implementation card (agent-to-agent trail)
- Card on you: "Review PR #N: [description]" (non-interactive)

**What you need to do:**
Review the PR. Approve or request changes via card comment.

**How it completes:**
Agent merges PR, updates traceability, closes card.

---

### G1 — GitHub Issue → Fix Pipeline

**What happens:** (automatic via webhook)
1. GitHub issue arrives → agent triages it
2. If actionable → agent designs fix, implements via OpenCode, creates PR
3. Card on you: "Review PR #N for issue #M"
4. You approve → agent merges, issue auto-closes

**What you need to do:**
Review PRs when cards appear. Approve or request changes.

---

### B1/B2 — Scheduled Scans (Automatic)

**What happens:** (weekly, Monday morning)
- Bug scan runs at 9am
- Security scan runs at 10am
- If findings exist → card on you with severity breakdown
- If no findings → silent (no card, no message)

**What you need to do:**
Review findings cards when they appear. Reassign to agent with "fix the critical ones" if needed.

---

## Common Tasks — Quick Reference

| What You Want | What to Say/Do |
|---|---|
| See what needs my attention | "What's on my kanban board?" or `hermes kanban list --status blocked` |
| See my to-do list | `hermes kanban list --status ready` |
| Start a new project | "I'd like a new project about..." |
| Approve something | Add comment "Approved" on the card, unblock |
| Request changes | Add comment with feedback, unblock |
| Run a security scan | "Run security scan on my-web-app" |
| Check what was I doing | "What was I doing?" (reads daily note + active tasks) |
| Park current work | "Park this — I was halfway through..." |
| View all projects | `hermes kanban list` or `hermes dashboard` |

---

## ADHD Tips

### Your Ready Column Is Your To-Do List
```bash
hermes kanban list --status ready --assignee default
```
Don't think about what to work on. Pick the top card.

### Clear Blocked Cards First
```bash
hermes kanban list --status blocked --assignee default
```
These are blocking agent work. Clear them in one sitting.

### Task Parking
When interrupted, tell the agent: "Park this — I was halfway through X, done Y but not Z." It saves the exact state. When you come back: "What was I parked on?"

### One Project at a Time
Switch workspace → work → switch back. The `.hermes.md` focus directive prevents cross-project noise.

### Visible Progress
Every card has a comment trail. Every TDD cycle shows green tests. Every PR shows changed files. You can always see that work happened.

### Decision Defaults
The agent recommends, you approve. Say "yes" to the default. Save your decisions for the ones that matter.
