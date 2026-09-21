# Documentation — Hermes Agentic SDLC Platform

**Generated:** 2026-09-21 (AEST)
**Source:** As-built system state captured during implementation.

---

## Documents

| Doc | File | Audience | Purpose |
|---|---|---|---|
| **User Guide** | [01-User-Guide.md](01-User-Guide.md) | Day-to-day use | How to use the system, kanban board, workflow walkthroughs, ADHD tips |
| **Setup Guide** | [02-Setup-Guide.md](02-Setup-Guide.md) | Initial setup / rebuild | Manual prerequisites, one-time config, from-scratch rebuild procedure |
| **Maintenance Guide** | [03-Maintenance-Guide.md](03-Maintenance-Guide.md) | Ongoing operations | Troubleshooting, backups, Proxmox restore, updates, log management |
| **Configuration Reference** | [04-Configuration-Reference.md](04-Configuration-Reference.md) | Reference | Every setting, skill, webhook, cron job, model routing — as-built |

## Reading Order

1. **New to the system?** Start with the **User Guide** — it explains what the system does and how to interact with it.
2. **Setting up from scratch?** Follow the **Setup Guide** — it lists what you need to do manually and what the agent handles.
3. **Something broken?** Check the **Maintenance Guide** — troubleshooting section, then backup/restore if needed.
4. **Need a specific setting?** Look it up in the **Configuration Reference** — every config key, skill, webhook, and cron job documented.

## Related Documents

| Doc | Location | Purpose |
|---|---|---|
| Design Document | `Hermes_Agent_Software_Framework.md` | Full technical design (architecture, 30 requirements, rules) |
| Implementation Plan | `AgentBuilder-ImplementationDesign.md` | Build plan with phases, verification steps |
| Analysis | `HermesSpecificItemsAnswer.md` | Workspace/profile/ADHD analysis |
| Superpowers Verification | `auto-hello-world-test/RESULTS.md` | Verification spike results |

## Updating These Docs

These docs were generated from the as-built system state. After Phase 7 E2E testing, any findings will be incorporated. To update:

1. Ask Hermes: "Update the docs with [what changed]"
2. Or edit directly and ask Hermes to verify
3. Re-capture as-built state: `hermes config show`, `hermes webhook list`, etc.
