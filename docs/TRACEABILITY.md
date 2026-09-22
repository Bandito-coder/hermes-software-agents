# TRACEABILITY.md — Requirement to Implementation Mapping

**Date:** 2026-09-22
**Source:** Hermes_Agent_Software_Framework.md v3 + AgentRosterAndDesign.md

---

## Mapping

| Req ID | Requirement | Agent | Skill File | Status |
|--------|------------|-------|------------|--------|
| R1 | Requirements gathering | Coach | coach/SKILL.md | ✅ Implemented |
| R2 | Versioning & traceability | Coach → Architect → Builder | This file | ✅ Implemented |
| R3 | High-level design | Architect | architect/SKILL.md | ✅ Implemented |
| R4 | Detailed design | Architect | architect/SKILL.md | ✅ Implemented |
| R5 | System update design | Architect (delta mode) | architect/SKILL.md | ⚠️ Never invoked |
| R6 | Bug-patch design | Scout + Fixer | fixer/SKILL.md | ✅ Implemented |
| B1 | Scheduled bug scans | weekly-bug-scan cron | cron job | ⚠️ Generic skill, not pipeline |
| B2 | Security scanning | SecOps | secops/SKILL.md | ✅ Implemented |
| B3 | Debugging workflow | Fixer | fixer/SKILL.md | ✅ Implemented |
| B4 | Dependency/CVE | SecOps | secops/SKILL.md | ✅ Implemented |
| B5 | Post-deploy assessment | W-HARDEN workflow | dev-lead/SKILL.md | ⚠️ No deploy trigger |
| G1 | Issue→fix pipeline | Dev Lead + Kanban | dev-lead/SKILL.md | ✅ Implemented |
| G2 | Triage | Triage agent | triage/SKILL.md | ✅ Implemented |
| G3 | Issue→PR pipeline | Dev Lead + GitHub | dev-lead/SKILL.md | ✅ Implemented |
| Gv1 | HITL approval gates | Kanban blocking | kanban config | ✅ Implemented |
| Gv2 | Cost & token monitoring | Cost Sentinel | cost-sentinel/SKILL.md | ✅ Implemented |
| Gv3 | Observability | RUN-ID + ledger | dev-lead/SKILL.md | ✅ Implemented |
| Gv4 | Cost & budget governance | LiteLLM budget | litellm_config.yaml | ✅ Implemented |
| Gv5 | Scoped access/sandbox | Docker + git branches | docker-compose.yml | ✅ Implemented |
| Gv6 | Audit logging | ledger.jsonl + git | dev-lead/SKILL.md | ✅ Implemented |
| I1 | Feature implementation | Builder | builder/SKILL.md | ✅ Implemented |
| I2 | Implement update/patch | Fixer | fixer/SKILL.md | ✅ Implemented |
| I3 | Test authoring & execution | Test Author + Gatekeeper | test-author/SKILL.md | ✅ Implemented |
| I4 | Review & quality gate | Reviewer + Gatekeeper | reviewer/SKILL.md | ✅ Implemented |
| I5 | Refactoring | Enhancer | enhancer/SKILL.md | ⚠️ Never invoked end-to-end |
| I6 | Documentation sync | Docs agent | docs/SKILL.md | ✅ Implemented |
| N1 | Correctness by construction | TDD via Superpowers | builder/SKILL.md | ✅ Implemented |
| N2 | Performance | Gatekeeper | gatekeeper/SKILL.md | ✅ Implemented |
| N3 | Data locality | LiteLLM proxy | litellm_config.yaml | ✅ Implemented |
| N4 | Single board | Kanban config | config.yaml | ✅ Implemented |
| N5 | Engine framework-agnostic | Architect design | architect/SKILL.md | ✅ Implemented |
| N6 | Minimal toolchain | Hermes + OpenCode only | — | ✅ Implemented |

---

## Update History

| Date | Change |
|------|--------|
| 2026-09-22 | Initial creation from framework v3 requirements |
