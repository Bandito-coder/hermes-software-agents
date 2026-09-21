# Scheduled Flows & Webhook Setup — Phase 3

## Cron Jobs

These are the scheduled automation flows for the agent team. Create via `hermes cron add` or the `cronjob` tool.

### 1. Nightly Gate Check (B1, S2)

**Schedule:** Daily at 2am AEST
**Purpose:** Run gates.sh on each workspace; FAIL creates a W-FIX card

```bash
hermes cron add \
  --name "nightly-gate-check" \
  --schedule "0 2 * * *" \
  --prompt "Run gates.sh in the AgentBuilder workspace. If any gate FAILs, create a kanban card for Dev Lead: 'Fix: gate failure detected by nightly check. Run logs: <paste gate output>.' If all PASS, report nothing (silent)." \
  --skills "gatekeeper" \
  --deliver local
```

### 2. Weekly Security Scan (B2, S2)

**Schedule:** Monday 10am AEST
**Purpose:** Dev Lead → W-HARDEN security audit

```bash
hermes cron add \
  --name "weekly-security-scan" \
  --schedule "0 10 * * 1" \
  --prompt "Run a full W-HARDEN security audit on the AgentBuilder workspace. Invoke SecOps for three-layer scan (secrets, deps/CVE, SAST). If Critical/High findings, invoke Fixer for remediation. Report findings summary." \
  --skills "dev-lead,secops,fixer,gatekeeper" \
  --deliver all
```

### 3. Daily Cost Check (Gv2, Gv4)

**Schedule:** Daily at 8am AEST
**Purpose:** Cost Sentinel reads telemetry, alerts only on breach

```bash
hermes cron add \
  --name "daily-cost-check" \
  --schedule "0 8 * * *" \
  --prompt "Run a daily cost anomaly check. Read session logs and token usage. Check for: single run > $0.10, daily total > $0.50, model mix shifts, runaway loops. If anomalies found, alert with details. If clean, report nothing (silent)." \
  --skills "cost-sentinel" \
  --deliver local
```

### 4. Weekly Cost Review (Gv2)

**Schedule:** Friday 4pm AEST
**Purpose:** Cost Analyst produces weekly report + proposals

```bash
hermes cron add \
  --name "weekly-cost-review" \
  --schedule "0 16 * * 5" \
  --prompt "Produce a weekly cost report. Analyze the week's agent usage by agent, model, and workflow. Write report to reports/costs/weekly-YYYY-WW.md. Include efficiency proposals as unified diffs in reports/costs/proposals/. Estimate costs using OpenRouter pricing." \
  --skills "cost-analyst" \
  --deliver all
```

### 5. Blocked Card Reminder (existing)

**Schedule:** Daily at 9am AEST
**Purpose:** Remind about blocked kanban cards

Already configured from Phase 1. No changes needed.

---

## Webhook Setup (Documented — Do Not Create)

### GitHub Issue Pipeline (G2, G3, S3)

When ready to activate the issue→PR pipeline:

```bash
# Enable webhook platform (if not already)
hermes gateway setup

# Subscribe to GitHub issues
hermes webhook subscribe github-issues \
  --events "issues" \
  --prompt "New GitHub issue #{issue.number}: {issue.title}
Action: {action}
Author: {issue.user.login}
Body:
{issue.body}

Triage this issue. If actionable, create a W-FIX or W-BUILD card for Dev Lead." \
  --skills "triage" \
  --deliver discord

# Subscribe to PR reviews
hermes webhook subscribe github-prs \
  --events "pull_request" \
  --prompt "PR #{pull_request.number} {action}: {pull_request.title}
Author: {pull_request.user.login}
Body:
{pull_request.body}

Review this PR. If review requested, run Reviewer agent and emit verdict block." \
  --skills "reviewer" \
  --deliver discord
```

**Note:** Webhooks require the gateway to be running. Verify with `hermes gateway status`. HMAC secrets are auto-generated per subscription.

### GitHub Issue Pipeline Flow

```
Issue arrives (webhook)
  → Triage: classify (bug/feature/question/duplicate/invalid), assign P0-P3
  → Auto-label clear-cut cases
  → Ambiguous: escalate to human
  → Bug (P0-P2): create W-FIX card for Dev Lead
  → Feature (P3): create W-BUILD card for Dev Lead
  → Duplicate: comment + close
  → Invalid: close with reason
```

---

## LiteLLM Health Check

**Schedule:** Every 5 minutes
**Purpose:** Ensure LiteLLM proxy is running; auto-restart if down; alert all channels if restart fails

**Status:** ✅ Active (cron job `litellm-health-check`)
**Location:** `/apps/hermes-docker/litellm/`
**Dashboard:** http://localhost:4000/ui

---

## Cost Agent Data Sources

Cost Sentinel and Cost Analyst now query the **LiteLLM proxy API** for actual cost data:

```bash
# LiteLLM spend logs (actual $ per request)
LITELLM_KEY=$(grep LITELLM_API_KEY /apps/hermes/.hermes/.env | cut -d= -f2)
curl -sf "http://localhost:4000/spend/logs" -H "Authorization: Bearer $LITELLM_KEY"

# LiteLLM spend report (aggregated)
curl -sf "http://localhost:4000/global/spend/report?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD" \
  -H "Authorization: Bearer $LITELLM_KEY"
```

Cost agents:
- **Cannot edit** `config.yaml`, `.env`, or any agent config
- **Cannot apply** their own proposals
- **Write to** `reports/costs/` only
- Proposals are suggestions for the operator to review and apply manually
