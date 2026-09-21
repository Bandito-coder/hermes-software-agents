# Maintenance Guide — Hermes Agentic SDLC Platform

**Audience:** You (the operator). Ongoing operations, troubleshooting, and disaster recovery.
**Last updated:** 2026-09-21 (AEST)

---

## System Monitoring

### Quick Health Check

```bash
# Gateway status
privgate service-status root hermes-gateway

# Webhook platform
curl http://localhost:8644/health

# Kanban board
hermes kanban stats

# Disk usage
df -h /

# Memory
free -h

# Running processes
ps aux | grep hermes | grep -v grep
```

### Disk Space

Root partition at `/dev/sda3` (31 GB). Keep ≥5 GB free.

```bash
df -h /
```

If disk is getting full:
```bash
# Check what's using space
du -sh /apps/hermes/* 2>/dev/null | sort -rh | head -10

# Clean caches
uv cache prune
npm cache clean --force

# Clean old sessions (if needed)
hermes sessions prune
```

### RAM Usage

```bash
free -h
```

If swap is heavily used (>2 GB):
- Reduce `max_concurrent_children`: `hermes config set delegation.max_concurrent_children 2`
- Check for runaway processes: `ps aux --sort=-%mem | head -10`

---

## Troubleshooting

### Gateway Won't Start

```bash
# Check status
privgate service-status root hermes-gateway

# Check logs
tail -50 ~/.hermes/logs/gateway.log

# Common causes:
# 1. Port conflict — another process on 8644
lsof -i :8644
# 2. Config corruption — validate YAML
python3 -c "import yaml; yaml.safe_load(open('/apps/hermes/.hermes/config.yaml'))"
# 3. Restart
privgate systemctl-hermes root restart hermes-gateway
```

### Webhook Not Triggering

```bash
# Check webhook platform is healthy
curl http://localhost:8644/health

# Check webhook subscriptions exist
hermes webhook list

# Check gateway logs for webhook events
grep webhook ~/.hermes/logs/gateway.log | tail -20

# Test a webhook manually
hermes webhook test github-issues

# Common causes:
# 1. Gateway not restarted after config change
privgate systemctl-hermes root restart hermes-gateway
# 2. GitHub can't reach your server (firewall/NAT)
# 3. Signature mismatch — check secret matches GitHub webhook config
```

### Kanban Worker Not Spawning

```bash
# Check dispatcher is running (inside gateway)
hermes kanban stats

# Check for stuck tasks
hermes kanban list --status running

# Common causes:
# 1. Gateway not running
privgate systemctl-hermes root restart hermes-gateway
# 2. Profile not found — check assignee exists
hermes profile list
# 3. Memory limits — reduce max_concurrent_children
```

### Ollama Unreachable

```bash
# Test connectivity
curl http://192.168.0.58:11434/api/tags

# Common causes:
# 1. Ollama service down on the other machine
# 2. Network issue — ping 192.168.0.58
# 3. Port blocked — check firewall
```

### OpenCode Errors

```bash
# Check OpenCode works
opencode --version

# Check Superpowers plugin is loaded
opencode run --model litellm/workhorse --pure "List your skills" 2>&1 | head -20

# Check OpenCode config
cat ~/.config/opencode/opencode.jsonc

# Common causes:
# 1. Plugin not installed — check config has superpowers entry
# 2. Model doesn't support tools — use a model that does
# 3. API key expired — check ~/.local/share/opencode/auth.json
```

### Disk Full

```bash
# Emergency cleanup
uv cache prune
npm cache clean --force
docker system prune -f

# Check for large files
find /apps/hermes -type f -size +100M 2>/dev/null

# Move Docker data to NAS if needed
# (requires planning — don't do mid-task)
```

---

## Configuration Management

### Changing Settings

```bash
# View current config
hermes config show

# Change a setting
hermes config set <key> <value>

# Examples
hermes config set delegation.max_concurrent_children 3
hermes config set terminal.timeout 300
hermes config set checkpoints.retention_days 14
```

### Adding Skills

Skills live in `~/.hermes/skills/`. Each skill is a directory with a `SKILL.md` file.

```bash
# Install from hub
hermes skills install <skill-name>

# Create custom skill
mkdir -p ~/.hermes/skills/my-skill
# Write SKILL.md in that directory

# List installed skills
hermes skills list
```

### Model Routing

```bash
# View current model config
hermes config get model

# Change default model
hermes config set model.default litellm/workhorse

# Change local model alias
hermes config set model.aliases.local.model gemma4-hermes:latest
```

---

## System Continuity & Backup

### What Needs Backing Up

| Component | Location | Priority | Frequency |
|---|---|---|---|
| Hermes config | `~/.hermes/config.yaml` | Critical | After any change |
| API keys/secrets | `~/.hermes/.env` | Critical | After any change |
| Skills | `~/.hermes/skills/` | High | Weekly |
| Kanban board | `~/.hermes/kanban.db` | High | Daily |
| Cron jobs | `~/.hermes/cron/` | High | After any change |
| Sessions | `~/.hermes/sessions/` | Medium | Weekly |
| OpenCode config | `~/.config/opencode/` | Medium | After any change |
| Obsidian vault | `/apps/gitsync/obsidian-brett/` | High | Git-synced (automatic) |
| Project workspaces | `/mnt/homelab-devel/HermesWorkspaces/` | High | Git-tracked per project |

### Hermes Config Snapshot

```bash
# Full profile export (includes config, skills, memories)
hermes profile export default

# Creates: default.tar.gz in current directory
# Contains: config.yaml, .env, SOUL.md, skills, memories
# Does NOT include: sessions, state.db, kanban.db
```

### Full Backup

```bash
# 1. Export Hermes profile
hermes profile export default --output /mnt/homelab-devel/backups/

# 2. Copy kanban database
cp ~/.hermes/kanban.db /mnt/homelab-devel/backups/kanban-$(date +%Y%m%d).db

# 3. Copy cron jobs
cp -r ~/.hermes/cron/ /mnt/homelab-devel/backups/cron-$(date +%Y%m%d)/

# 4. Skills backup
tar czf /mnt/homelab-devel/backups/skills-$(date +%Y%m%d).tar.gz ~/.hermes/skills/

# 5. OpenCode config
cp ~/.config/opencode/opencode.jsonc /mnt/homelab-devel/backups/
```

### Automated Backup (Cron)

Consider adding a weekly backup cron job:
```bash
hermes cron add --name "weekly-backup" --schedule "every sunday 2am" \
  --script "backup-hermes.sh" --deliver local
```

---

## Proxmox VM Backup & Restore

### Regular Backup (Proxmox Snapshot)

1. Log into Proxmox web UI (PVE01 or PVE02)
2. Select the Hermes VM
3. Backup → Backup Now
4. Storage: your NAS backup target
5. Mode: Snapshot (fastest)
6. Compression: ZSTD

### Restore from Snapshot

1. Log into Proxmox web UI
2. Select the backup storage → find the backup
3. Restore → select target storage
4. Start the VM
5. Verify: `hermes config show`, `hermes kanban stats`

### Total VM Loss (Corruption)

If the VM is completely lost:

1. Create new VM on Proxmox (see Setup Guide, Section "Proxmox VM Setup")
2. Install Ubuntu 24.04
3. Install prerequisites (Docker, Node.js, uv, Hermes)
4. Restore from backup:
   - Copy `config.yaml`, `.env`, skills, kanban.db from backup
   - Place in `~/.hermes/`
   - Run `hermes setup` if needed
5. Restart gateway: `privgate systemctl-hermes root restart hermes-gateway`
6. Verify all components

### Hypervisor Loss

If the Proxmox host is lost:

1. Install Proxmox on new hardware
2. Restore VMs from NAS backup (if NAS survived)
3. If NAS also lost: restore from off-site backup
4. Follow "Total VM Loss" procedure above

**Recovery time estimates:**
- From Proxmox snapshot: ~10 minutes
- From scratch (with backup): ~30 minutes
- From scratch (no backup): ~2-4 hours (re-run full implementation plan)

---

## Update Procedures

### Hermes Update

```bash
hermes update
# Pulls latest code, syncs skills to all profiles
```

### OpenCode Update

```bash
opencode upgrade
```

### System Packages

```bash
# Only when needed, and only by you (requires sudo)
sudo apt update && sudo apt upgrade -y
```

### Skills Update

```bash
# Hub-installed skills
hermes skills install <skill-name> --update

# Custom skills — manual edit
# Edit the SKILL.md in ~/.hermes/skills/<name>/
```

---

## Log Management

### Log Locations

| Log | Location | Content |
|---|---|---|
| Gateway | `~/.hermes/logs/gateway.log` | Gateway events, webhook deliveries |
| Sessions | `~/.hermes/sessions/*.jsonl` | Full conversation transcripts |
| Kanban workers | `~/.hermes/logs/kanban-worker-*.log` | Worker execution logs |
| Cron | `~/.hermes/cron/` | Job execution history |

### Useful Diagnostic Commands

```bash
# Recent gateway errors
grep -i error ~/.hermes/logs/gateway.log | tail -20

# Webhook delivery attempts
grep webhook ~/.hermes/logs/gateway.log | tail -20

# Kanban worker activity
ls -lt ~/.hermes/logs/kanban-worker-*.log | head -10

# Session search
hermes session search "keyword"
```

### Log Rotation

Hermes manages its own log rotation. If logs grow too large:
```bash
# Check log sizes
du -sh ~/.hermes/logs/

# Manual cleanup (keep last 7 days)
find ~/.hermes/logs/ -name "*.log" -mtime +7 -delete
```
