#!/usr/bin/env python3
"""
orchestrator.py — Structural workflow enforcement for Hermes dev-lead.

Replaces prompt-based orchestration with code-based flow control.
The script manages phase transitions, sub-agent invocation, circuit breakers,
and kanban blocking. The calling agent's role is reduced to:
  1. Run the script
  2. Report its output
  3. Feed back user responses when cards are unblocked

Usage:
  orchestrator.py start --workflow W-BUILD --card-id <id>
  orchestrator.py resume --run-id <id>
  orchestrator.py status --run-id <id>

Architecture:
  - State is persisted to ~/.hermes/orchestrator/state/{run_id}.json
  - Kanban ops go through `hermes kanban` CLI (subprocess)
  - Coding agents go through `opencode run` (subprocess)
  - Non-coding agents go through LiteLLM API (HTTP)
  - Gatekeeper runs gates.sh directly (subprocess)
  - The script CANNOT write project code — it only orchestrates
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STATE_DIR = Path.home() / ".hermes" / "orchestrator" / "state"
MAX_CYCLES = {"W-BUILD": 4, "W-FIX": 3, "W-HARDEN": 2, "W-SPEC": 1, "W-REFACTOR": 3}
SMALL_CHANGE_THRESHOLD = 3  # files touched — skip Coach/Architect below this
LITELLM_URL = "http://localhost:4000/v1/chat/completions"
LITELLM_KEY_ENV = "LITELLM_API_KEY"
OPENCODE_TIMEOUT = 600  # seconds per opencode invocation
SUBAGENT_TIMEOUT = 300  # seconds per LiteLLM sub-agent call
MAX_SAME_FINDING_REPEAT = 3  # circuit breaker: same finding ID in N consecutive cycles

# Non-coding agent models
SCOUT_MODEL = "litellm/deepseek-v4-flash-0731"
COACH_MODEL = "litellm/deepseek-v4-flash-0731"
ARCHITECT_MODEL = "litellm/architect"
DESIGN_REVIEWER_MODEL = "litellm/reasoning"

# Design review loop
MAX_DESIGN_REVIEW_CYCLES = 3  # review rounds before the card goes to the user as referee
TRACE_RETRIES = 2  # extra test-author attempts to fix a failing tests-first trace

# ---------------------------------------------------------------------------
# Kanban CLI Client
# ---------------------------------------------------------------------------

class KanbanClient:
    """Wraps `hermes kanban` CLI operations."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def _run(self, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        cmd = ["hermes", "kanban"] + args
        if self.dry_run:
            print(f"[DRY-RUN] {' '.join(cmd)}")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if check and result.returncode != 0:
            raise RuntimeError(f"Kanban command failed: {' '.join(cmd)}\n{result.stderr}")
        return result

    def show(self, card_id: str) -> dict:
        result = self._run(["show", card_id, "--json"])
        return json.loads(result.stdout)

    def comment(self, card_id: str, text: str, author: str = "orchestrator"):
        self._run(["comment", card_id, text, "--author", author])

    def block(self, card_id: str, reason: str, kind: str = "needs_input"):
        self._run(["block", card_id, "--kind", kind, reason])

    def unblock(self, card_id: str, reason: str = ""):
        args = ["unblock", card_id]
        if reason:
            args += ["--reason", reason]
        self._run(args)

    def complete(self, card_id: str, result_text: str, summary: str = "", metadata: str = ""):
        args = ["complete", card_id, "--result", result_text]
        if summary:
            args += ["--summary", summary]
        if metadata:
            args += ["--metadata", metadata]
        self._run(args)

    def request_review(self, card_id: str, reviewer: str, reason: str = ""):
        args = ["request-review", card_id, reviewer]
        if reason:
            args += [reason]
        self._run(args)


# ---------------------------------------------------------------------------
# LLM Client (LiteLLM proxy)
# ---------------------------------------------------------------------------

class LLMClient:
    """Calls LiteLLM proxy for non-coding agent tasks.

    Every request carries LiteLLM metadata tags so spend can be attributed to the
    kanban card, workflow run, workspace, sub-agent role and model. ``set_context``
    publishes the durable workflow identity (card/run/workflow/workspace); a per-call
    ``role`` is derived from the system prompt by the same convention the tests use
    (required since scout and coach share ``SCOUT_MODEL``). If no context is set
    (e.g. bare ``LLMClient.call`` in a unit test) tags degrade to ``unset`` sentinels
    but are still always present.
    """

    #: Sub-agent role keyword -> canonical role tag, derived from the system prompt
    #: (mirrors how test_orchestrator.py classifies scout/coach/architect calls).
    ROLE_HINTS = (
        (("design reviewer",), "design-reviewer"),
        (("scout",), "scout"),
        (("architect",), "architect"),
        (("coach", "requirements"), "coach"),
    )

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._card_id = ""
        self._run_id = ""
        self._workflow = ""
        self._workspace = ""
        self.api_key = os.environ.get(LITELLM_KEY_ENV, "")
        if not self.api_key:
            # Try reading from .env
            env_file = Path.home() / ".hermes" / ".env"
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.startswith("LITELLM_API_KEY="):
                        self.api_key = line.split("=", 1)[1].strip()
                        break

    def set_context(self, *, card_id: str = "", run_id: str = "",
                    workflow: str = "", workspace: str = "") -> None:
        """Publish the durable workflow identity used to tag every LiteLLM call.

        Called by ``WorkflowEngine`` at construction so all non-coding sub-agent
        calls (scout/coach/architect) carry card, run and workflow attribution.
        """
        self._card_id = card_id
        self._run_id = run_id
        self._workflow = workflow
        self._workspace = workspace

    def _derive_role(self, system_prompt: str) -> str:
        lowered = system_prompt.lower()
        for keywords, role in self.ROLE_HINTS:
            if any(k in lowered for k in keywords):
                return role
        return "orchestrator"

    def _tags(self, model: str, system_prompt: str) -> list[str]:
        """LiteLLM metadata tags for cost attribution."""
        ws = Path(self._workspace).name if self._workspace else "unset"
        return [
            f"card:{self._card_id or 'unset'}",
            f"run:{self._run_id or 'unset'}",
            f"workflow:{self._workflow or 'unset'}",
            f"workspace:{ws}",
            f"agent:{self._derive_role(system_prompt)}",
            f"model:{model}",
            "source:orchestrator",
        ]

    def call(self, system_prompt: str, user_prompt: str, model: str = SCOUT_MODEL,
             max_tokens: int = 4096) -> str:
        tags = self._tags(model, system_prompt)
        if self.dry_run:
            print(f"[DRY-RUN] LLM call: model={model}, prompt_len={len(user_prompt)}, "
                  f"tags={tags}")
            return f"[DRY-RUN] LLM response for model {model}"

        try:
            import urllib.request
            import urllib.error

            payload = json.dumps({
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                # LiteLLM OpenAI-compatible endpoint records metadata.tags in spend logs
                "metadata": {"tags": tags},
            }).encode()

            req = urllib.request.Request(
                LITELLM_URL,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    # Proxy-native tag header — LiteLLM reads it as request tags
                    # (comma-separated, e.g. card:t_xyz,run:RUN-abc)
                    "x-litellm-tags": ",".join(tags),
                },
            )
            with urllib.request.urlopen(req, timeout=SUBAGENT_TIMEOUT) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[LLM ERROR] {e}"


# ---------------------------------------------------------------------------
# Codebase Explorer (gathers context for sub-agents)
# ---------------------------------------------------------------------------

class CodebaseExplorer:
    """Gathers workspace context for non-coding agents."""

    SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox",
                 "dist", "build", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
    MAX_FILES = 200
    MAX_FILE_READ = 2000  # chars per file

    def __init__(self, workspace: str):
        self.workspace = Path(workspace)

    def file_tree(self, max_depth: int = 4) -> str:
        """Get a file tree of the workspace."""
        lines = []
        for root, dirs, files in os.walk(self.workspace):
            dirs[:] = [d for d in dirs if d not in self.SKIP_DIRS]
            depth = Path(root).relative_to(self.workspace).parts
            if len(depth) > max_depth:
                dirs.clear()
                continue
            indent = "  " * len(depth)
            rel = Path(root).relative_to(self.workspace)
            if str(rel) != ".":
                lines.append(f"{indent}{rel.name}/")
            for f in sorted(files):
                lines.append(f"{indent}  {f}")
            if len(lines) > self.MAX_FILES:
                lines.append("  ... (truncated)")
                break
        return "\n".join(lines)

    def read_key_files(self) -> str:
        """Read key project files (README, config, etc.)."""
        key_patterns = [
            "README.md", "README.rst", "README.txt", "README",
            "pyproject.toml", "setup.py", "setup.cfg",
            "package.json", "tsconfig.json",
            "Makefile", "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
            ".hermes.md",
            "docs/BRIEF.md", "docs/SPEC.md",
        ]
        content_parts = []
        for pattern in key_patterns:
            for match in self.workspace.glob(pattern):
                if match.is_file():
                    try:
                        text = match.read_text()[:self.MAX_FILE_READ]
                        rel = match.relative_to(self.workspace)
                        content_parts.append(f"--- {rel} ---\n{text}\n")
                    except Exception:
                        pass
        return "\n".join(content_parts) if content_parts else "(no key files found)"

    def gather_context(self, task_description: str = "") -> str:
        """Gather full context for a sub-agent."""
        parts = [f"Workspace: {self.workspace}"]
        if task_description:
            parts.append(f"Task: {task_description}")
        parts.append(f"\n--- File Tree ---\n{self.file_tree()}")
        parts.append(f"\n--- Key Files ---\n{self.read_key_files()}")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Workflow State
# ---------------------------------------------------------------------------

@dataclass
class WorkflowState:
    """Persistent workflow state."""
    run_id: str
    workflow: str
    card_id: str
    workspace: str
    branch: str
    task_title: str
    task_body: str
    phase: int = 0
    phase_status: str = "running"  # running | blocked | complete | failed
    block_reason: str = ""
    cycle: int = 0
    scout_output: str = ""
    brief_path: str = ""
    spec_path: str = ""
    gatekeeper_result: str = ""
    reviewer_result: str = ""
    gate_results: list = field(default_factory=list)
    fix_history: list = field(default_factory=list)
    cost_usd: float = 0.0
    created_at: str = ""
    updated_at: str = ""
    log: list = field(default_factory=list)
    small_change: bool = False
    # Design review loop (phase 2)
    design_review_cycles: int = 0
    design_review_results: list = field(default_factory=list)
    design_review_findings: str = ""
    design_review_referee: bool = False
    design_review_bypassed: bool = False
    design_review_guidance: str = ""

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "workflow": self.workflow,
            "card_id": self.card_id,
            "workspace": self.workspace,
            "branch": self.branch,
            "task_title": self.task_title,
            "task_body": self.task_body,
            "phase": self.phase,
            "phase_status": self.phase_status,
            "block_reason": self.block_reason,
            "cycle": self.cycle,
            "scout_output": self.scout_output,
            "brief_path": self.brief_path,
            "spec_path": self.spec_path,
            "gatekeeper_result": self.gatekeeper_result,
            "reviewer_result": self.reviewer_result,
            "gate_results": self.gate_results,
            "fix_history": self.fix_history,
            "cost_usd": self.cost_usd,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "log": self.log,
            "small_change": self.small_change,
            "design_review_cycles": self.design_review_cycles,
            "design_review_results": self.design_review_results,
            "design_review_findings": self.design_review_findings,
            "design_review_referee": self.design_review_referee,
            "design_review_bypassed": self.design_review_bypassed,
            "design_review_guidance": self.design_review_guidance,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowState":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def save(self):
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        path = STATE_DIR / f"{self.run_id}.json"
        self.updated_at = datetime.now(timezone.utc).isoformat()
        path.write_text(json.dumps(self.to_dict(), indent=2, default=str))

    @classmethod
    def load(cls, run_id: str) -> "WorkflowState":
        path = STATE_DIR / f"{run_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"State file not found: {path}")
        return cls.from_dict(json.loads(path.read_text()))

    def append_log(self, entry: str):
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self.log.append(f"[{ts}] {entry}")


# ---------------------------------------------------------------------------
# Circuit Breakers
# ---------------------------------------------------------------------------

class CircuitBreakerError(Exception):
    """Raised when a circuit breaker trips."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def check_circuit_breakers(state: WorkflowState):
    """Check all circuit breakers. Raises CircuitBreakerError if tripped."""
    max_cyc = MAX_CYCLES.get(state.workflow, 4)

    # Breaker 1: cycle limit
    if state.cycle > max_cyc:
        raise CircuitBreakerError(
            f"Cycle limit exceeded: {state.cycle}/{max_cyc}"
        )

    # Breaker 2: same finding in N consecutive cycles
    if len(state.fix_history) >= MAX_SAME_FINDING_REPEAT:
        recent = state.fix_history[-MAX_SAME_FINDING_REPEAT:]
        finding_ids = [h.get("finding_id", "") for h in recent]
        if len(set(finding_ids)) == 1 and finding_ids[0]:
            raise CircuitBreakerError(
                f"Same finding '{finding_ids[0]}' in {MAX_SAME_FINDING_REPEAT} consecutive cycles"
            )

    # Breaker 3: blocking count not decreasing across 2 cycles
    if len(state.gate_results) >= 2:
        last_two = state.gate_results[-2:]
        if all(r.get("blocking_count", 0) > 0 for r in last_two):
            if last_two[0].get("blocking_count", 0) <= last_two[1].get("blocking_count", 0):
                raise CircuitBreakerError(
                    f"Blocking count not decreasing: {last_two[1].get('blocking_count')} → "
                    f"{last_two[0].get('blocking_count')}"
                )


# ---------------------------------------------------------------------------
# Phase Executors
# ---------------------------------------------------------------------------

class WorkflowEngine:
    """Executes workflow phases with structural enforcement."""

    def __init__(self, state: WorkflowState, kanban: KanbanClient,
                 llm: LLMClient, explorer: CodebaseExplorer,
                 dry_run: bool = False):
        self.state = state
        self.kanban = kanban
        self.llm = llm
        self.explorer = explorer
        self.dry_run = dry_run
        # Publish durable workflow identity so every LiteLLM call is tagged with
        # card / run / workflow / workspace for cost attribution.
        llm.set_context(
            card_id=state.card_id, run_id=state.run_id,
            workflow=state.workflow, workspace=state.workspace,
        )

    def run(self) -> dict:
        """Run the workflow from its current phase. Returns a result dict."""
        try:
            self._run_phases()
            return {
                "status": self.state.phase_status,
                "phase": self.state.phase,
                "log": self.state.log[-10:],
                "run_id": self.state.run_id,
            }
        except CircuitBreakerError as e:
            self.state.append_log(f"CIRCUIT BREAKER: {e}")
            self.state.phase_status = "blocked"
            self.state.block_reason = f"circuit_breaker: {e}"
            self.state.save()
            self.kanban.block(
                self.state.card_id,
                f"Circuit breaker tripped: {e}. Fix history: {json.dumps(self.state.fix_history[-5:])}",
                kind="needs_input",
            )
            return {
                "status": "circuit_breaker",
                "reason": str(e),
                "log": self.state.log[-10:],
                "run_id": self.state.run_id,
            }
        except Exception as e:
            self.state.append_log(f"FATAL: {e}")
            self.state.phase_status = "failed"
            self.state.save()
            return {
                "status": "failed",
                "error": str(e),
                "log": self.state.log[-10:],
                "run_id": self.state.run_id,
            }

    def _run_phases(self):
        """Execute phases sequentially from current state."""
        phase_handlers = {
            0: self.phase_0_prep,
            1: self.phase_1_requirements,
            2: self.phase_2_design,
            3: self.phase_3_build,
            4: self.phase_4_approval,
            5: self.phase_5_finalize,
        }

        while self.state.phase <= 5:
            handler = phase_handlers.get(self.state.phase)
            if handler is None:
                break
            result = handler()
            if result == "blocked":
                # State is saved by the phase handler
                return
            # Phase completed, advance
            self.state.phase += 1
            self.state.phase_status = "running"
            self.state.save()

        self.state.phase_status = "complete"
        self.state.save()

    # ------------------------------------------------------------------
    # Phase 0: Project Prep
    # ------------------------------------------------------------------
    def phase_0_prep(self) -> str:
        self.state.append_log("Phase 0: Project Prep — starting")
        workspace = Path(self.state.workspace)

        # Create workspace if needed
        if not workspace.exists():
            workspace.mkdir(parents=True, exist_ok=True)
            self._git("init")
            self._git("add", "-A")
            self._git("commit", "-m", "Initial commit", "--allow-empty")
            self.state.append_log(f"Created workspace: {workspace}")

        # Create branch
        os.chdir(workspace)
        current_branch = self._git("branch", "--show-current").strip()
        if current_branch != self.state.branch:
            # Check if branch already exists
            branches = self._git("branch", "--list", self.state.branch).strip()
            if branches:
                self._git("checkout", self.state.branch)
            else:
                self._git("checkout", "-b", self.state.branch)
            self.state.append_log(f"On branch: {self.state.branch}")

        # Comment on card
        self.kanban.comment(
            self.state.card_id,
            f"[orchestrator] Workspace ready. RUN-ID: {self.state.run_id}. "
            f"Branch: {self.state.branch}. Starting requirements gathering."
        )

        self.state.append_log("Phase 0: complete")
        return "done"

    # ------------------------------------------------------------------
    # Phase 1: Requirements (Scout → Coach → BLOCK)
    # ------------------------------------------------------------------
    def phase_1_requirements(self) -> str:
        self.state.append_log("Phase 1: Requirements — starting")

        # Scout: gather codebase context
        context = self.explorer.gather_context(self.state.task_body)
        scout_prompt = (
            f"Explore this codebase and summarize: structure, patterns, technologies, "
            f"existing code relevant to the task.\n\nTask: {self.state.task_title}\n"
            f"{self.state.task_body}\n\nCodebase context:\n{context}"
        )
        scout_system = (
            "You are a codebase scout. Analyze the provided codebase context and return: "
            "1) Project structure summary 2) Key technologies and patterns 3) Files/modules "
            "relevant to the task 4) Potential challenges or dependencies. Be concise and factual."
        )
        self.state.scout_output = self.llm.call(scout_system, scout_prompt, SCOUT_MODEL)
        self.state.append_log(f"Scout complete: {len(self.state.scout_output)} chars")

        # Small-change fast path
        touched_files = self._estimate_files_touched()
        if touched_files < SMALL_CHANGE_THRESHOLD:
            self.state.small_change = True
            self.state.append_log(
                f"Small change ({touched_files} files) — skipping Coach and Architect"
            )
            return "done"

        # Coach: requirements assessment
        coach_system = (
            "You are a requirements coach. Assess the task across 9 dimensions: "
            "scope, data, interfaces, error handling, performance, security, testing, "
            "deployment, documentation. For each dimension, rate as Known/Assumed/Unknown. "
            "For Unknown dimensions, provide specific clarifying questions. "
            "Then produce a BRIEF.md with prioritized requirements (MUST/SHOULD/COULD). "
            "Format: ## Dimensions\\n| Dimension | Status | Notes |\\n## Requirements\\n..."
        )
        coach_prompt = (
            f"Task: {self.state.task_title}\n{self.state.task_body}\n\n"
            f"Scout analysis:\n{self.state.scout_output}"
        )
        coach_output = self.llm.call(coach_system, coach_prompt, COACH_MODEL, max_tokens=6000)

        # Write BRIEF.md
        workspace = Path(self.state.workspace)
        docs_dir = workspace / "docs"
        docs_dir.mkdir(exist_ok=True)
        brief_path = docs_dir / "BRIEF.md"
        brief_path.write_text(coach_output)
        self.state.brief_path = str(brief_path.relative_to(workspace))
        self.state.append_log(f"Coach complete: BRIEF.md written at {self.state.brief_path}")

        # Check for Unknown dimensions — if any, include questions in block reason
        unknowns = self._parse_unknowns(coach_output)
        block_reason = "Requirements ready. Review docs/BRIEF.md."
        if unknowns:
            block_reason += f" Unknowns: {'; '.join(unknowns[:5])}"

        # BLOCK — requirements approval
        self.kanban.comment(
            self.state.card_id,
            f"[orchestrator] Requirements complete. BRIEF.md at {self.state.brief_path}. "
            f"Review and approve."
        )
        self.kanban.block(self.state.card_id, block_reason, kind="needs_input")
        self.state.phase_status = "blocked"
        self.state.block_reason = "requirements_approval"
        self.state.save()

        self.state.append_log("Phase 1: BLOCKED — awaiting requirements approval")
        return "blocked"

    # ------------------------------------------------------------------
    # Phase 2: Design (Architect → Design Reviewer loop → BLOCK)
    # ------------------------------------------------------------------
    def phase_2_design(self) -> str:
        # Skip if small change
        if self.state.small_change:
            self.state.append_log("Phase 2: skipped (small change)")
            return "done"

        # Referee chose (a): proceed to build — design review bypassed for this card
        if self.state.design_review_bypassed:
            self.state.append_log("Phase 2: design review bypassed (referee 'proceed to build')")
            return "done"

        self.state.append_log("Phase 2: Design — starting")

        # Read BRIEF.md
        workspace = Path(self.state.workspace)
        brief_content = ""
        if self.state.brief_path:
            bp = workspace / self.state.brief_path
            if bp.exists():
                brief_content = bp.read_text()

        # Referee gave guidance — architect revision incorporates it; review restarts
        guidance = self.state.design_review_guidance
        if guidance:
            self.state.append_log(
                f"Phase 2: referee guidance applied — design review restarts with a fresh "
                f"{MAX_DESIGN_REVIEW_CYCLES}-cycle budget"
            )

        spec_content = ""
        spec_path = workspace / "docs" / "SPEC.md"
        if spec_path.exists():
            spec_content = spec_path.read_text()

        # Design review loop: architect (produce/revise) → design reviewer → ...
        review_round = 0
        while True:
            review_round += 1

            # 1) Architect produces SPEC.md (round 1) or revises it (rounds 2+, Mode 4)
            first_round = review_round == 1 and not self.state.design_review_findings and not guidance
            if first_round:
                architect_system = (
                    "You are a software architect. Design an implementation plan for the task. "
                    "Provide: 1) 2-3 alternative approaches with trade-offs 2) Recommended approach "
                    "with justification 3) Detailed SPEC.md with: data models, API contracts, "
                    "file structure, test plan, error handling strategy. "
                    "Format as markdown suitable for SPEC.md."
                )
                architect_prompt = (
                    f"Task: {self.state.task_title}\n{self.state.task_body}\n\n"
                    f"BRIEF.md:\n{brief_content}\n\n"
                    f"Scout analysis:\n{self.state.scout_output}"
                )
            else:
                architect_system = (
                    "You are a software architect revising SPEC.md per design-review findings (Mode 4). "
                    "Revise the EXISTING SPEC.md in place — edit only the areas the findings touch. "
                    "Return the COMPLETE updated SPEC.md (the whole document). "
                    "Do not redesign, do not add scope, do not restructure. "
                    "Address every finding; if referee guidance was given, incorporate it."
                )
                architect_prompt = (
                    f"Task: {self.state.task_title}\n{self.state.task_body}\n\n"
                    f"BRIEF.md:\n{brief_content}\n\n"
                    f"Design review findings to address:\n{self.state.design_review_findings or '(none yet)'}\n"
                    f"Referee guidance:\n{guidance or '(none)'}\n\n"
                    f"Current SPEC.md:\n{spec_content}"
                )
            architect_output = self.llm.call(
                architect_system, architect_prompt, ARCHITECT_MODEL, max_tokens=8000
            )

            # Write SPEC.md
            docs_dir = workspace / "docs"
            docs_dir.mkdir(exist_ok=True)
            spec_path = docs_dir / "SPEC.md"
            spec_path.write_text(architect_output)
            self.state.spec_path = str(spec_path.relative_to(workspace))
            spec_content = architect_output
            self.state.append_log(
                f"Architect {'revised' if review_round > 1 else 'complete'}: "
                f"SPEC.md written at docs/SPEC.md"
            )

            # 2) Design Reviewer validates SPEC.md (Mode 2 detailed design only)
            if review_round == 1:
                review_system = (
                    "You are a design reviewer. Validate the DETAILED design (SPEC.md, Mode 2) "
                    "BEFORE user approval. Do NOT review Mode 1 architecture alternatives. "
                    "Check: 1) every MUST/SHOULD requirement in BRIEF.md maps to a testable acceptance "
                    "criterion (AC) in SPEC.md; 2) data model is explicit (fields, types, relationships); "
                    "3) interface contracts complete (params, returns, errors, preconditions); "
                    "4) edge cases and error handling present and consistent; 5) test plan covers every AC; "
                    "6) internal consistency (no contradictions, ACs match the interfaces). "
                    "Format: verdict block with status: PASS | FAIL, blocking_count, advisory_count, "
                    "summary, and findings (id DR1.., severity: blocking | advisory, file: SPEC.md, "
                    "section, problem, fix)."
                )
            else:
                # Re-review: constrained to the changes made for the previous findings
                review_system = (
                    "You are a design reviewer performing a RE-REVIEW. The designer revised SPEC.md to "
                    "address your previous findings. Review ONLY the changes made for those findings: "
                    "(1) verify each finding is effectively resolved; (2) verify no adverse impact on any "
                    "other area of the document; (3) verify no conflict with the rest of the design. "
                    "Do NOT invent new problems outside the scope of the changes. If the designer ignored "
                    "a finding, re-raise it once. "
                    "Format: verdict block with status: PASS | FAIL, blocking_count, advisory_count, "
                    "summary, and findings (id DR1.., severity: blocking | advisory, file: SPEC.md, "
                    "section, problem, fix)."
                )
            review_prompt = (
                f"Task: {self.state.task_title}\n\nBRIEF.md:\n{brief_content}\n\n"
                f"SPEC.md to review:\n{spec_content}\n\n"
                + (f"Previous review findings (re-review scope):\n{self.state.design_review_findings}\n"
                   if review_round > 1 else "")
            )
            review_output = self.llm.call(
                review_system, review_prompt, DESIGN_REVIEWER_MODEL, max_tokens=4000
            )
            verdict = self._parse_design_review_verdict(review_output)
            findings_text = self._extract_design_review_findings(review_output)
            self.state.design_review_cycles = review_round
            self.state.design_review_results.append({
                "round": review_round,
                "verdict": verdict,
                "findings": findings_text[:500],
            })
            self.state.append_log(
                f"Design review round {review_round}/{MAX_DESIGN_REVIEW_CYCLES}: {verdict}"
            )

            if verdict == "PASS":
                self.state.design_review_findings = ""
                break

            # FAIL — pass the findings to the architect and re-loop
            self.state.design_review_findings = findings_text
            if review_round >= MAX_DESIGN_REVIEW_CYCLES:
                # Review exhausted — referee call (block the card)
                self.kanban.comment(
                    self.state.card_id,
                    "[orchestrator] Design review failed after 3 cycles. Referee decision needed: "
                    "(a) proceed to build (review bypassed for this card), or "
                    "(b) guidance to resolve the review issues and restart the cycle.",
                )
                self.kanban.block(
                    self.state.card_id,
                    "DESIGN REVIEW REFEREE: comment (a) 'proceed to build' to bypass the design review "
                    "for this card, or (b) your guidance for resolving the review issues — the review "
                    "restarts with up to 3 more cycles. Then unblock.",
                    kind="needs_input",
                )
                self.state.phase_status = "blocked"
                self.state.block_reason = "design_review_referee"
                self.state.design_review_referee = True
                self.state.save()
                self.state.append_log("Phase 2: BLOCKED — awaiting referee decision (design review)")
                return "blocked"

        # Design review passed — clear loop state and BLOCK for design approval
        self.state.design_review_findings = ""
        self.state.design_review_guidance = ""
        self.state.design_review_referee = False
        self.state.design_review_bypassed = False

        self.kanban.comment(
            self.state.card_id,
            f"[orchestrator] Design complete. SPEC.md at {self.state.spec_path}. "
            f"Design review: PASS. Review and approve.",
        )
        self.kanban.block(
            self.state.card_id,
            f"Design ready. Review docs/SPEC.md. To approve: unblock. "
            f"To request changes: comment with changes, then unblock.",
            kind="needs_input",
        )
        self.state.phase_status = "blocked"
        self.state.block_reason = "design_approval"
        self.state.save()

        self.state.append_log("Phase 2: BLOCKED — awaiting design approval")
        return "blocked"

    # ------------------------------------------------------------------
    # Phase 3: Build (Builder → Test Author → Gatekeeper → Reviewer)
    # ------------------------------------------------------------------
    def phase_3_build(self) -> str:
        self.state.append_log("Phase 3: Build — starting")
        workflow = self.state.workflow

        if workflow == "W-BUILD":
            return self._build_cycle()
        elif workflow == "W-FIX":
            return self._fix_cycle()
        elif workflow == "W-HARDEN":
            return self._harden_cycle()
        elif workflow == "W-SPEC":
            # Spec-only workflow — nothing to build
            self.state.append_log("W-SPEC: no build phase")
            return "done"
        elif workflow == "W-REFACTOR":
            return self._refactor_cycle()
        else:
            self.state.append_log(f"Unknown workflow: {workflow}")
            return "done"

    def _build_cycle(self) -> str:
        """Execute the tests-first → build → gate → review cycle."""
        workspace = Path(self.state.workspace)
        max_cyc = MAX_CYCLES.get("W-BUILD", 4)

        while self.state.cycle < max_cyc:
            check_circuit_breakers(self.state)
            self.state.cycle += 1
            self.state.append_log(f"Build cycle {self.state.cycle}/{max_cyc}")

            spec_path = self.state.spec_path or "docs/SPEC.md"

            # 1. TESTS-FIRST: Test Author writes the failing tests + trace BEFORE any production code
            test_prompt = (
                f"[{self.state.run_id}] TESTS-FIRST for: {self.state.task_title}. "
                f"{self.state.task_body}. "
                f"Read ONLY the spec/design (SPEC.md at {spec_path} and/or BRIEF.md) — never write "
                f"tests to suit code. Write the failing tests for every spec/design item (AC1, AC2, ...): "
                f"uplift existing tests to fail until the feature is done, or create new failing ones. "
                f"Verify they FAIL against current code. Write tests/TRACE.md mapping each spec item to "
                f"its test case ('| AC1 | tests/test_x.py::test_name |') — the orchestrator blocks the "
                f"build on any item without a traced failing test. Tests only — NEVER production code. "
                f"Commit prefix: [{self.state.run_id}]"
            )
            test_result = self._opencode_run(test_prompt)
            self.state.append_log(
                f"Test Author (tests-first): {'success' if test_result['ok'] else 'failed'}"
            )

            # 2. Structural trace check — any untraced spec/design item blocks the build
            self._enforce_test_trace()

            # 3. Builder via OpenCode — the failing tests already exist; make them pass
            builder_prompt = (
                f"[{self.state.run_id}] Implement: {self.state.task_title}. "
                f"{self.state.task_body}. TDD: the failing tests already exist in tests/ (written from "
                f"the spec) — make them pass (GREEN phase). Do not delete or weaken them. "
                f"Spec: {spec_path}. Commit prefix: [{self.state.run_id}]"
            )
            build_result = self._opencode_run(builder_prompt)
            self.state.append_log(f"Builder: {'success' if build_result['ok'] else 'failed'}")

            # Gatekeeper: run gates.sh
            gate_result = self._run_gatekeeper()
            self.state.gatekeeper_result = gate_result["verdict"]
            self.state.gate_results.append(gate_result)
            self.state.append_log(
                f"Gatekeeper: {gate_result['verdict']} "
                f"(blocking: {gate_result['blocking_count']})"
            )

            if gate_result["verdict"] == "PASS":
                # Reviewer via OpenCode
                review_prompt = (
                    f"[{self.state.run_id}] Review this implementation for: "
                    f"{self.state.task_title}. Check spec compliance against {spec_path}. "
                    f"Report any issues. Verdict: PASS or FAIL with details."
                )
                review_result = self._opencode_run(review_prompt)
                self.state.reviewer_result = "PASS" if review_result["ok"] else "FAIL"
                self.state.append_log(f"Reviewer: {self.state.reviewer_result}")

                if review_result["ok"]:
                    # All pass — commit and move on
                    self._git("add", "-A")
                    self._git("commit", "-m", f"[{self.state.run_id}] {self.state.task_title}")
                    self.state.append_log("Build committed")
                    return "done"

            # Something failed — run fix loop
            fix_prompt = (
                f"[{self.state.run_id}] Fix these findings from the gate/review: "
                f"{json.dumps(gate_result.get('findings', []))}. "
                f"Stay in scope. Commit prefix: [{self.state.run_id}]"
            )
            fix_result = self._opencode_run(fix_prompt)
            self.state.fix_history.append({
                "cycle": self.state.cycle,
                "finding_id": gate_result.get("findings", ["unknown"])[0] if gate_result.get("findings") else "unknown",
                "gate_result": gate_result["verdict"],
            })
            self.state.append_log(f"Fixer (cycle {self.state.cycle}): applied fix")

        # Exhausted cycles
        raise CircuitBreakerError(f"Build cycles exhausted: {self.state.cycle}/{max_cyc}")

    def _fix_cycle(self) -> str:
        """Execute the W-FIX workflow: scout → reproduce → fix → gate → review."""
        workspace = Path(self.state.workspace)

        # Scout: locate relevant code
        context = self.explorer.gather_context(self.state.task_body)
        scout_system = (
            "You are a codebase scout. Locate the code involved in the bug described. "
            "Identify: files, functions, relevant patterns. Be specific."
        )
        scout_prompt = (
            f"Bug: {self.state.task_title}\n{self.state.task_body}\n\n"
            f"Codebase context:\n{context}"
        )
        self.state.scout_output = self.llm.call(scout_system, scout_prompt, SCOUT_MODEL)
        self.state.append_log("Scout complete (fix)")

        # TESTS-FIRST: Test Author writes the failing test for the bug BEFORE any fix code
        test_prompt = (
            f"[{self.state.run_id}] TESTS-FIRST for bug: {self.state.task_title}. "
            f"{self.state.task_body}. "
            f"If a test already covers the buggy function: UPLIFT it so it FAILS until the bug is fixed "
            f"(fail-until-fixed). If no test covers it: create one that reproduces the bug and fails now. "
            f"NEVER modify production code. Write tests/TRACE.md mapping the bug to its test case "
            f"('| BUG-1 | tests/test_x.py::test_name |'). Commit prefix: [{self.state.run_id}]"
        )
        self._opencode_run(test_prompt)
        self.state.append_log("Test Author (tests-first): failing test requested for bug")

        # Structural trace check — the bug must be traced to a failing test before any fix
        self._enforce_test_trace()

        # Fix loop
        max_cyc = MAX_CYCLES.get("W-FIX", 3)
        while self.state.cycle < max_cyc:
            check_circuit_breakers(self.state)
            self.state.cycle += 1
            self.state.append_log(f"Fix cycle {self.state.cycle}/{max_cyc}")

            # Gatekeeper: reproduce the failure
            gate_result = self._run_gatekeeper()
            self.state.gate_results.append(gate_result)
            self.state.append_log(f"Gatekeeper (reproduction): {gate_result['verdict']}")

            # Fixer via OpenCode
            fix_prompt = (
                f"[{self.state.run_id}] Fix: {self.state.task_title}. "
                f"{self.state.task_body}\n\nScout context:\n{self.state.scout_output}\n\n"
                f"Gate findings: {json.dumps(gate_result.get('findings', []))}\n\n"
                f"Iron Law: root cause first. Commit prefix: [{self.state.run_id}]"
            )
            fix_result = self._opencode_run(fix_prompt)
            self.state.fix_history.append({
                "cycle": self.state.cycle,
                "finding_id": gate_result.get("findings", ["unknown"])[0] if gate_result.get("findings") else "unknown",
                "gate_result": gate_result["verdict"],
            })
            self.state.append_log(f"Fixer: {'success' if fix_result['ok'] else 'failed'}")

            # Re-run gates
            gate_result = self._run_gatekeeper()
            self.state.gatekeeper_result = gate_result["verdict"]
            self.state.gate_results.append(gate_result)
            self.state.append_log(f"Gatekeeper (verify): {gate_result['verdict']}")

            if gate_result["verdict"] == "PASS":
                # Reviewer
                review_prompt = (
                    f"[{self.state.run_id}] Review this fix for: {self.state.task_title}. "
                    f"Verify the bug is fixed and no regressions were introduced."
                )
                review_result = self._opencode_run(review_prompt)
                self.state.reviewer_result = "PASS" if review_result["ok"] else "FAIL"
                self.state.append_log(f"Reviewer: {self.state.reviewer_result}")

                if review_result["ok"]:
                    self._git("add", "-A")
                    self._git("commit", "-m", f"[{self.state.run_id}] Fix: {self.state.task_title}")
                    return "done"

        raise CircuitBreakerError(f"Fix cycles exhausted: {self.state.cycle}/{max_cyc}")

    def _harden_cycle(self) -> str:
        """Execute W-HARDEN: security audit → fix → verify."""
        self.state.append_log("W-HARDEN: running security gates")
        # Simplified: run gates + security checks
        gate_result = self._run_gatekeeper()
        self.state.gatekeeper_result = gate_result["verdict"]
        if gate_result["verdict"] == "PASS":
            self._git("add", "-A")
            self._git("commit", "-m", f"[{self.state.run_id}] Security hardening")
            return "done"
        return "done"

    def _refactor_cycle(self) -> str:
        """Execute W-REFACTOR: baseline → refactor → verify."""
        self.state.append_log("W-REFACTOR: running baseline gates")
        gate_result = self._run_gatekeeper()
        self.state.gatekeeper_result = gate_result["verdict"]
        if gate_result["verdict"] == "PASS":
            return "done"
        return "done"

    # ------------------------------------------------------------------
    # Phase 4: Build Approval (BLOCK)
    # ------------------------------------------------------------------
    def phase_4_approval(self) -> str:
        self.state.append_log("Phase 4: Build Approval — starting")

        # Commit if not already committed
        workspace = Path(self.state.workspace)
        os.chdir(workspace)
        status = self._git("status", "--porcelain").strip()
        if status:
            self._git("add", "-A")
            self._git("commit", "-m", f"[{self.state.run_id}] Build complete")

        self.kanban.comment(
            self.state.card_id,
            f"[orchestrator] Build complete. Gates: {self.state.gatekeeper_result}. "
            f"Review: {self.state.reviewer_result}. Cost: ${self.state.cost_usd:.4f}"
        )
        self.kanban.block(
            self.state.card_id,
            "Build ready for testing. To approve: unblock. "
            "To request fixes: comment with fixes needed, then unblock.",
            kind="needs_input",
        )
        self.state.phase_status = "blocked"
        self.state.block_reason = "build_approval"
        self.state.save()

        self.state.append_log("Phase 4: BLOCKED — awaiting build approval")
        return "blocked"

    # ------------------------------------------------------------------
    # Phase 5: Finalize
    # ------------------------------------------------------------------
    def phase_5_finalize(self) -> str:
        self.state.append_log("Phase 5: Finalize — starting")
        workspace = Path(self.state.workspace)
        os.chdir(workspace)

        # Push to GitHub
        try:
            self._git("push", "origin", self.state.branch)
            self.state.append_log(f"Pushed to origin/{self.state.branch}")
        except RuntimeError as e:
            self.state.append_log(f"Push failed (non-fatal): {e}")

        # Complete the card
        self.kanban.complete(
            self.state.card_id,
            f"Build complete. Branch {self.state.branch}. "
            f"RUN-ID: {self.state.run_id}. Cost: ${self.state.cost_usd:.4f}",
            metadata=json.dumps({
                "run_id": self.state.run_id,
                "branch": self.state.branch,
                "cycles": self.state.cycle,
                "cost_usd": self.state.cost_usd,
            }),
        )

        self.state.phase_status = "complete"
        self.state.append_log("Phase 5: COMPLETE — card finished")
        return "done"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _git(self, *args: str) -> str:
        if self.dry_run:
            print(f"[DRY-RUN] git {' '.join(args)}")
            return ""
        result = subprocess.run(
            ["git"] + list(args),
            capture_output=True, text=True, timeout=30,
            cwd=self.state.workspace,
        )
        if result.returncode != 0:
            # Some git commands return non-zero for non-errors (e.g., commit with nothing)
            if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
                return result.stdout
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
        return result.stdout

    def _opencode_run(self, prompt: str) -> dict:
        """Run opencode with a prompt. Returns {"ok": bool, "output": str}."""
        if self.dry_run:
            print(f"[DRY-RUN] opencode run: {prompt[:100]}...")
            return {"ok": True, "output": "[DRY-RUN]"}

        try:
            result = subprocess.run(
                ["opencode", "run", "--model", "litellm/coding", "--format", "json", prompt],
                capture_output=True, text=True,
                timeout=OPENCODE_TIMEOUT,
                cwd=self.state.workspace,
            )
            # Parse JSON output for status
            output = result.stdout + result.stderr
            ok = result.returncode == 0
            if not ok:
                self.state.append_log(f"OpenCode exit code: {result.returncode}")
            return {"ok": ok, "output": output}
        except subprocess.TimeoutExpired:
            self.state.append_log("OpenCode timed out")
            return {"ok": False, "output": "timeout"}
        except Exception as e:
            self.state.append_log(f"OpenCode error: {e}")
            return {"ok": False, "output": str(e)}

    def _run_gatekeeper(self) -> dict:
        """Run gates.sh and parse results."""
        workspace = Path(self.state.workspace)

        # Find gates.sh
        gates_path = workspace / "bin" / "gates.sh"
        if not gates_path.exists():
            # Try parent workspace
            gates_path = Path(self.state.workspace).parent / "bin" / "gates.sh"

        if not gates_path.exists() or self.dry_run:
            if self.dry_run:
                print("[DRY-RUN] gates.sh")
            return {"verdict": "PASS", "blocking_count": 0, "findings": [],
                    "output": "[DRY-RUN or no gates.sh]"}

        try:
            result = subprocess.run(
                ["bash", str(gates_path)],
                capture_output=True, text=True,
                timeout=120, cwd=str(workspace),
            )
            output = result.stdout + result.stderr

            # Parse gate results
            findings = []
            blocking_count = 0
            for line in output.splitlines():
                if "::result:: FAIL" in line:
                    blocking_count += 1
                if "::gate::" in line:
                    gate_name = line.split("::gate::")[1].strip()
                    # Check if next line is FAIL
                    findings.append(gate_name)

            verdict = "PASS" if result.returncode == 0 else "FAIL"
            return {
                "verdict": verdict,
                "blocking_count": blocking_count,
                "findings": findings,
                "output": output,
            }
        except subprocess.TimeoutExpired:
            return {"verdict": "FAIL", "blocking_count": 1,
                    "findings": ["timeout"], "output": "gates.sh timed out"}
        except Exception as e:
            return {"verdict": "FAIL", "blocking_count": 1,
                    "findings": ["error"], "output": str(e)}

    def _estimate_files_touched(self) -> int:
        """Estimate how many files this task will touch based on task body."""
        # Simple heuristic: count file mentions or keywords
        body = self.state.task_body.lower()
        indicators = ["file", "module", "component", "endpoint", "model", "schema"]
        count = sum(1 for i in indicators if i in body)
        # If the task mentions specific files, count them
        file_mentions = re.findall(r'\b\w+\.\w+\b', self.state.task_body)
        count += len(set(file_mentions))
        return max(count, 1)

    def _parse_unknowns(self, coach_output: str) -> list[str]:
        """Parse Unknown dimensions from coach output."""
        unknowns = []
        for line in coach_output.splitlines():
            lower = line.lower()
            if "unknown" in lower and ("|" in lower or ":" in lower):
                # Extract the question or dimension
                parts = line.split("|")
                if len(parts) >= 3:
                    dim = parts[1].strip() if len(parts) > 1 else ""
                    note = parts[-1].strip() if len(parts) > 2 else ""
                    unknowns.append(f"{dim}: {note}" if dim else note)
                elif "?" in line:
                    unknowns.append(line.strip())
        return unknowns

    # ------------------------------------------------------------------
    # Design review helpers
    # ------------------------------------------------------------------
    def _parse_design_review_verdict(self, output: str) -> str:
        """Parse the design reviewer's verdict block. Conservative: anything
        unparseable, or a PASS with blocking findings, counts as FAIL."""
        m = re.search(
            r"---VERDICT---\s*status:\s*(PASS|FAIL|BLOCKED)", output, re.IGNORECASE | re.DOTALL
        )
        if not m:
            return "FAIL"
        status = m.group(1).upper()
        bm = re.search(r"blocking_count:\s*(\d+)", output, re.IGNORECASE)
        blocking = int(bm.group(1)) if bm else 0
        if status == "PASS" and blocking == 0:
            return "PASS"
        return "FAIL"

    def _extract_design_review_findings(self, output: str) -> str:
        """Extract the findings portion of a design review verdict for the architect."""
        m = re.search(r"findings:\s*(.*?)(?:---END---|$)", output, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
        return output.strip()[:2000]

    # ------------------------------------------------------------------
    # Tests-first trace helpers
    # ------------------------------------------------------------------
    def _check_test_trace(self) -> dict:
        """Validate tests-first traceability.

        Spec/design items (AC ids from docs/SPEC.md) must each map to a traced
        failing test in tests/TRACE.md (rows: '| AC1 | tests/test_x.py::test_y |').
        W-FIX without a delta SPEC requires at least one traced test for the bug.
        Returns a gate-style dict: {'verdict', 'blocking_count', 'findings', 'output'}.
        """
        workspace = Path(self.state.workspace)

        # Small-change fast path skips the trace requirement (no spec is produced)
        if self.state.small_change:
            return {"verdict": "PASS", "blocking_count": 0, "findings": [],
                    "output": "trace skipped (small change fast path)"}

        # 1. Collect spec/design items: AC ids from SPEC.md
        spec_items: list = []
        spec_path = workspace / (self.state.spec_path or "docs/SPEC.md")
        if spec_path.exists():
            for line in spec_path.read_text().splitlines():
                m = re.match(r"\s*\|?\s*(AC\d+)\s*[|:]", line, re.IGNORECASE)
                if m:
                    item = m.group(1).upper()
                    if item not in spec_items:
                        spec_items.append(item)

        # 2. Read the trace file
        trace_candidates = [workspace / "tests" / "TRACE.md", workspace / "docs" / "TRACE.md"]
        trace_path = next((p for p in trace_candidates if p.exists()), None)
        traced: dict = {}
        if trace_path is not None:
            for line in trace_path.read_text().splitlines():
                m = re.match(r"\s*\|?\s*([A-Za-z0-9_-]+)\s*\|\s*([^|]+?)\s*::\s*([^|]+?)\s*\|?", line)
                if m:
                    traced[m.group(1).upper()] = f"{m.group(2).strip()}::{m.group(3).strip()}"

        # 3. Verify: every spec item traced, and traced test files exist
        findings = []
        for item in spec_items:
            if item not in traced:
                findings.append({
                    "id": f"TRACE-{item}",
                    "severity": "blocking",
                    "file": "tests/TRACE.md",
                    "problem": f"No failing test traced for {item}",
                    "fix": "test-author must add the test and the TRACE.md row",
                })
        for item, ref in traced.items():
            test_file = ref.split("::")[0]
            if not (workspace / test_file).exists():
                findings.append({
                    "id": f"TRACE-{item}-FILE",
                    "severity": "blocking",
                    "file": "tests/TRACE.md",
                    "problem": f"Traced test file does not exist: {test_file}",
                    "fix": "test-author must create the traced test file",
                })

        # 4. W-FIX without a delta SPEC: the bug report is the spec item — trace must exist
        if not spec_items and self.state.workflow == "W-FIX" and not traced:
            findings.append({
                "id": "TRACE-BUG",
                "severity": "blocking",
                "file": "tests/TRACE.md",
                "problem": "No test traced for the bug report",
                "fix": "test-author must write a failing test reproducing the bug and trace it in TRACE.md",
            })

        if findings:
            return {"verdict": "FAIL", "blocking_count": len(findings), "findings": findings,
                    "output": f"tests-first trace FAIL: {len(findings)} blocking"}
        return {"verdict": "PASS", "blocking_count": 0, "findings": [], "output": "trace ok"}

    def _enforce_test_trace(self) -> None:
        """Structurally enforce the tests-first trace before the build may start.

        Re-invokes test-author up to TRACE_RETRIES times to close gaps; if the trace
        still fails, raises CircuitBreakerError — the card blocks (build never starts).
        """
        trace_result = self._check_test_trace()
        if trace_result["verdict"] == "PASS":
            self.state.append_log("Tests-first trace: PASS")
            return

        retries = 0
        while retries < TRACE_RETRIES:
            retries += 1
            self.state.append_log(
                f"Tests-first trace FAIL ({trace_result['blocking_count']} blocking) — "
                f"test-author retry {retries}/{TRACE_RETRIES}"
            )
            retry_prompt = (
                f"[{self.state.run_id}] Your tests-first TRACE check failed: "
                f"{json.dumps(trace_result['findings'])}. "
                f"Write the missing failing tests and update tests/TRACE.md. "
                f"Commit prefix: [{self.state.run_id}]"
            )
            self._opencode_run(retry_prompt)
            trace_result = self._check_test_trace()
            if trace_result["verdict"] == "PASS":
                self.state.append_log("Tests-first trace: PASS (after retry)")
                return

        self.state.append_log(f"Tests-first trace BLOCKED: {trace_result['output']}")
        raise CircuitBreakerError(f"Tests-first trace blocked the build: {trace_result['output']}")


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------

def cmd_start(args):
    """Start a new workflow."""
    # Read the kanban card
    kanban = KanbanClient(dry_run=args.dry_run)
    card = kanban.show(args.card_id)

    title = card.get("title", "Untitled")
    body = card.get("body", "")
    workspace = card.get("workspace_path", args.workspace or "")

    if not workspace:
        print(json.dumps({"error": "No workspace specified. Use --workspace or set on card."}))
        sys.exit(1)

    # Generate RUN-ID
    run_id = f"RUN-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()

    # Generate branch name
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower())[:40].strip('-')
    branch = f"agent/{slug}"

    state = WorkflowState(
        run_id=run_id,
        workflow=args.workflow,
        card_id=args.card_id,
        workspace=workspace,
        branch=branch,
        task_title=title,
        task_body=body,
        phase=0,
        created_at=now,
    )
    state.append_log(f"Workflow started: {args.workflow} for card {args.card_id}")
    state.save()

    # Run the engine
    explorer = CodebaseExplorer(workspace)
    llm = LLMClient(dry_run=args.dry_run)
    engine = WorkflowEngine(state, kanban, llm, explorer, dry_run=args.dry_run)
    result = engine.run()

    print(json.dumps(result, indent=2, default=str))


def cmd_resume(args):
    """Resume a blocked workflow."""
    state = WorkflowState.load(args.run_id)

    if state.phase_status not in ("blocked", "running"):
        print(json.dumps({
            "error": f"Cannot resume: status is '{state.phase_status}'",
            "run_id": args.run_id,
        }))
        sys.exit(1)

    # Read kanban comments for user feedback
    kanban = KanbanClient(dry_run=args.dry_run)
    recent_comments = []
    try:
        card = kanban.show(state.card_id)
        # Extract comments (hermes kanban show --json includes comments)
        comments = card.get("comments", [])
        # Find comments since last block
        for c in comments:
            if c.get("author") != "orchestrator":
                recent_comments.append(c.get("body", ""))
        if recent_comments:
            state.append_log(f"User feedback: {recent_comments[-1][:200]}")
    except Exception as e:
        state.append_log(f"Could not read comments: {e}")

    previous_block = state.block_reason

    # Clear blocked state
    state.phase_status = "running"
    state.block_reason = ""

    # Referee decision (design review failed 3 cycles)
    if state.design_review_referee:
        user_text = " ".join(recent_comments).strip()
        if not user_text or re.search(
            r"\b(proceed|approve|bypass|continue|go ahead|overrule)\b", user_text, re.IGNORECASE
        ):
            # (a) proceed to build — design review bypassed for this card
            state.design_review_bypassed = True
            state.append_log("Referee: proceed to build — design review bypassed for this card")
        else:
            # (b) guidance — architect revises per guidance; review restarts
            state.design_review_guidance = user_text
            state.design_review_cycles = 0
            state.append_log("Referee: guidance given — design review restarts (fresh 3-cycle budget)")
        state.design_review_referee = False
        state.design_review_findings = ""

    # If we were blocked at requirements or design, the user approved
    if state.phase == 1 and previous_block == "requirements_approval":
        state.append_log("Requirements approved by user")
    elif state.phase == 2 and previous_block == "design_approval":
        state.append_log("Design approved by user")
    elif state.phase == 2 and previous_block == "design_review_referee":
        state.append_log("Referee decision applied (design review)")
    elif state.phase == 4:
        state.append_log("Build approved by user")

    state.save()

    # Continue execution
    explorer = CodebaseExplorer(state.workspace)
    llm = LLMClient(dry_run=args.dry_run)
    engine = WorkflowEngine(state, kanban, llm, explorer, dry_run=args.dry_run)

    # Skip to the phase after the one that blocked
    result = engine.run()
    print(json.dumps(result, indent=2, default=str))


def cmd_status(args):
    """Show workflow status."""
    try:
        state = WorkflowState.load(args.run_id)
        print(json.dumps(state.to_dict(), indent=2, default=str))
    except FileNotFoundError:
        print(json.dumps({"error": f"Run not found: {args.run_id}"}))
        sys.exit(1)


def cmd_list(args):
    """List all active workflows."""
    if not STATE_DIR.exists():
        print(json.dumps([]))
        return

    workflows = []
    for f in sorted(STATE_DIR.glob("*.json")):
        try:
            state = WorkflowState.from_dict(json.loads(f.read_text()))
            workflows.append({
                "run_id": state.run_id,
                "workflow": state.workflow,
                "card_id": state.card_id,
                "phase": state.phase,
                "status": state.phase_status,
                "created_at": state.created_at,
            })
        except Exception:
            pass
    print(json.dumps(workflows, indent=2, default=str))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Structural workflow enforcement for Hermes dev-lead"
    )
    parser.add_argument("--dry-run", action="store_true", help="Dry run (no side effects)")
    sub = parser.add_subparsers(dest="command", required=True)

    # start
    p_start = sub.add_parser("start", help="Start a new workflow")
    p_start.add_argument("--workflow", required=True,
                         choices=["W-BUILD", "W-FIX", "W-SPEC", "W-REFACTOR", "W-HARDEN"])
    p_start.add_argument("--card-id", required=True, help="Kanban card ID")
    p_start.add_argument("--workspace", help="Workspace path (overrides card)")

    # resume
    p_resume = sub.add_parser("resume", help="Resume a blocked workflow")
    p_resume.add_argument("--run-id", required=True)

    # status
    p_status = sub.add_parser("status", help="Show workflow status")
    p_status.add_argument("--run-id", required=True)

    # list
    sub.add_parser("list", help="List active workflows")

    args = parser.parse_args()

    if args.command == "start":
        cmd_start(args)
    elif args.command == "resume":
        cmd_resume(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "list":
        cmd_list(args)


if __name__ == "__main__":
    main()
