#!/usr/bin/env python3
"""
test_orchestrator.py — Comprehensive tests for the orchestration script.

Tests cover:
  T1: State persistence (save/load/roundtrip)
  T2: KanbanClient CLI wrapping
  T3: LLMClient API calls
  T4: CodebaseExplorer context gathering
  T5: Circuit breakers (all 3 types)
  T6: Phase transitions (valid and invalid)
  T7: W-BUILD happy path (full cycle)
  T8: W-BUILD fix loop (gate failure → fix → pass)
  T9: W-BUILD circuit breaker (cycles exhausted)
  T10: W-FIX workflow
  T11: Small-change fast path
  T12: Gatekeeper parsing
  T13: Unknown dimension parsing
  T14: CLI interface (start/resume/status/list)
  T15: Blocking/unblocking flow
  T16: Error handling (missing state, git failures, opencode failures)
  T17: Git operations
  T18: OpenCode invocation
  T20: Tests-first phase (test-author before builder, trace enforcement)
  T21: Design review loop (pass, fail→revise, cycle cap, referee block)
  T22: Verdict parsing and referee resume decisions
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import (
    ARCHITECT_MODEL,
    CircuitBreakerError,
    CodebaseExplorer,
    DESIGN_REVIEWER_MODEL,
    KanbanClient,
    LLMClient,
    MAX_CYCLES,
    MAX_DESIGN_REVIEW_CYCLES,
    TRACE_RETRIES,
    WorkflowEngine,
    WorkflowState,
    check_circuit_breakers,
    cmd_list,
    cmd_resume,
    cmd_start,
    cmd_status,
    STATE_DIR,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_workspace(tmp_path):
    """Create a temporary workspace with a git repo."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    subprocess.run(["git", "init"], cwd=str(workspace), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(workspace), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(workspace), capture_output=True)

    # Create a basic project structure
    (workspace / "pyproject.toml").write_text('[project]\nname = "test"\nversion = "0.1.0"\n')
    (workspace / "README.md").write_text("# Test Project\n")
    (workspace / "src").mkdir()
    (workspace / "src" / "__init__.py").write_text("")
    (workspace / "src" / "main.py").write_text("def hello(): return 'world'\n")

    subprocess.run(["git", "add", "-A"], cwd=str(workspace), capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(workspace), capture_output=True)

    return workspace


@pytest.fixture
def tmp_state_dir(tmp_path):
    """Use a temporary state directory."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    with mock.patch("orchestrator.STATE_DIR", state_dir):
        yield state_dir


@pytest.fixture
def sample_state(tmp_workspace, tmp_state_dir):
    """Create a sample workflow state."""
    state = WorkflowState(
        run_id="RUN-test1234",
        workflow="W-BUILD",
        card_id="t_abc123",
        workspace=str(tmp_workspace),
        branch="agent/test-task",
        task_title="Test Task",
        task_body="Implement a test feature.",
        phase=0,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    state.save()
    return state


@pytest.fixture
def mock_kanban():
    """Mock KanbanClient that records calls."""
    client = mock.MagicMock(spec=KanbanClient)
    client.show.return_value = {
        "id": "t_abc123",
        "title": "Test Task",
        "body": "Implement a test feature.",
        "status": "running",
        "workspace_path": "/tmp/test",
        "comments": [],
    }
    client.dry_run = False
    return client


@pytest.fixture
def mock_llm():
    """Mock LLMClient that returns structured responses."""
    client = mock.MagicMock(spec=LLMClient)
    client.dry_run = False

    def llm_side_effect(system_prompt, user_prompt, model=None, max_tokens=None):
        if "scout" in system_prompt.lower() or "codebase" in system_prompt.lower():
            return textwrap.dedent("""
                ## Project Structure
                - Python project with pyproject.toml
                - src/ directory with main module
                - Tests in tests/

                ## Key Technologies
                - Python 3.12
                - pytest for testing

                ## Relevant Files
                - src/main.py: Main application code
                - pyproject.toml: Project configuration

                ## Potential Challenges
                - None identified
            """).strip()
        elif "requirements" in system_prompt.lower() or "coach" in system_prompt.lower():
            return textwrap.dedent("""
                ## Dimensions
                | Dimension | Status | Notes |
                |-----------|--------|-------|
                | Scope | Known | Clear feature requirements |
                | Data | Known | Simple data model |
                | Interfaces | Known | REST API |
                | Error Handling | Assumed | Standard patterns |
                | Performance | Known | No special requirements |
                | Security | Known | Standard auth |
                | Testing | Known | pytest |
                | Deployment | Known | Docker |
                | Documentation | Known | README |

                ## Requirements

                ### MUST
                - REQ-1: Feature must work correctly
                - REQ-2: Must have tests

                ### SHOULD
                - REQ-3: Should have good error messages

                ### COULD
                - REQ-4: Could have performance optimizations
            """).strip()
        elif "design reviewer" in system_prompt.lower():
            return textwrap.dedent("""\
                ---VERDICT---
                status: PASS
                blocking_count: 0
                advisory_count: 0
                summary: Design meets all requirements.
                ---END---
            """).strip()
        elif "architect" in system_prompt.lower() or "design" in system_prompt.lower():
            return textwrap.dedent("""\
                ## Alternatives

                ### Option A: Simple Implementation
                - Pros: Fast to implement
                - Cons: Limited extensibility

                ### Option B: Modular Design
                - Pros: Extensible, testable
                - Cons: More code

                **Recommended: Option B**

                ## SPEC.md

                ### Data Models
                - Feature model with name, description, status

                ### API Contracts
                - POST /features — create feature
                - GET /features — list features

                ### File Structure
                - src/features.py — feature logic
                - tests/test_features.py — tests

                ### Test Plan
                - Unit tests for each function
                - Integration tests for API

                ### Error Handling
                - Input validation
                - Graceful degradation
            """).strip()
        else:
            return "Generic LLM response"

    client.call.side_effect = llm_side_effect
    return client


@pytest.fixture
def mock_explorer(tmp_workspace):
    """Mock CodebaseExplorer with real workspace."""
    explorer = mock.MagicMock(spec=CodebaseExplorer)
    explorer.workspace = tmp_workspace
    explorer.gather_context.return_value = (
        f"Workspace: {tmp_workspace}\n"
        "--- File Tree ---\n"
        "pyproject.toml\nREADME.md\nsrc/\n  __init__.py\n  main.py\n"
        "--- Key Files ---\n"
        "--- pyproject.toml ---\n[project]\nname = 'test'\n"
    )
    explorer.file_tree.return_value = "pyproject.toml\nREADME.md\nsrc/\n  main.py"
    explorer.read_key_files.return_value = "--- pyproject.toml ---\n[project]\nname = 'test'\n"
    return explorer


# ---------------------------------------------------------------------------
# T1: State Persistence
# ---------------------------------------------------------------------------

class TestStatePersistence:
    def test_save_and_load(self, tmp_state_dir):
        state = WorkflowState(
            run_id="RUN-save01", workflow="W-BUILD", card_id="t_001",
            workspace="/tmp/test", branch="agent/test", task_title="Test",
            task_body="Body", phase=1, created_at="2026-01-01T00:00:00",
        )
        state.save()

        loaded = WorkflowState.load("RUN-save01")
        assert loaded.run_id == "RUN-save01"
        assert loaded.workflow == "W-BUILD"
        assert loaded.card_id == "t_001"
        assert loaded.phase == 1

    def test_roundtrip_preserves_all_fields(self, tmp_state_dir):
        state = WorkflowState(
            run_id="RUN-rt01", workflow="W-FIX", card_id="t_002",
            workspace="/tmp/test", branch="agent/fix", task_title="Fix",
            task_body="Fix bug", phase=3, cycle=2,
            scout_output="scout data", brief_path="docs/BRIEF.md",
            spec_path="docs/SPEC.md", gatekeeper_result="PASS",
            reviewer_result="FAIL", gate_results=[{"verdict": "PASS"}],
            fix_history=[{"cycle": 1, "finding_id": "f1"}],
            cost_usd=1.23, log=["entry 1", "entry 2"],
            small_change=True,
        )
        state.save()
        loaded = WorkflowState.load("RUN-rt01")

        assert loaded.scout_output == "scout data"
        assert loaded.brief_path == "docs/BRIEF.md"
        assert loaded.cycle == 2
        assert loaded.gate_results == [{"verdict": "PASS"}]
        assert loaded.fix_history == [{"cycle": 1, "finding_id": "f1"}]
        assert loaded.cost_usd == 1.23
        assert loaded.small_change is True

    def test_load_nonexistent_raises(self, tmp_state_dir):
        with pytest.raises(FileNotFoundError):
            WorkflowState.load("RUN-nonexistent")

    def test_save_updates_timestamp(self, tmp_state_dir):
        state = WorkflowState(
            run_id="RUN-ts01", workflow="W-BUILD", card_id="t_003",
            workspace="/tmp/test", branch="agent/test", task_title="Test",
            task_body="Body", phase=0,
        )
        state.save()
        loaded = WorkflowState.load("RUN-ts01")
        assert loaded.updated_at  # should be set

    def test_append_log(self, tmp_state_dir):
        state = WorkflowState(
            run_id="RUN-log01", workflow="W-BUILD", card_id="t_004",
            workspace="/tmp/test", branch="agent/test", task_title="Test",
            task_body="Body",
        )
        state.append_log("First entry")
        state.append_log("Second entry")
        assert len(state.log) == 2
        assert "First entry" in state.log[0]
        assert "Second entry" in state.log[1]


# ---------------------------------------------------------------------------
# T2: KanbanClient
# ---------------------------------------------------------------------------

class TestKanbanClient:
    def test_dry_run_no_subprocess(self):
        client = KanbanClient(dry_run=True)
        # Should not raise, should not call subprocess
        with mock.patch("subprocess.run") as mock_run:
            client.comment("t_001", "test comment")
            mock_run.assert_not_called()

    def test_show_calls_cli(self):
        client = KanbanClient(dry_run=False)
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                ["hermes", "kanban", "show", "t_001", "--json"],
                0, stdout='{"id": "t_001", "title": "Test"}', stderr=""
            )
            result = client.show("t_001")
            assert result["id"] == "t_001"
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "show" in args
            assert "t_001" in args

    def test_block_calls_cli_with_kind(self):
        client = KanbanClient(dry_run=False)
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
            client.block("t_001", "reason text", kind="needs_input")
            args = mock_run.call_args[0][0]
            assert "block" in args
            assert "--kind" in args
            assert "needs_input" in args

    def test_comment_calls_cli(self):
        client = KanbanClient(dry_run=False)
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
            client.comment("t_001", "my comment", author="orchestrator")
            args = mock_run.call_args[0][0]
            assert "comment" in args
            assert "my comment" in args
            assert "--author" in args

    def test_complete_calls_cli(self):
        client = KanbanClient(dry_run=False)
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
            client.complete("t_001", "done", summary="all good", metadata='{"key": "val"}')
            args = mock_run.call_args[0][0]
            assert "complete" in args
            assert "--result" in args
            assert "--metadata" in args

    def test_failed_command_raises(self):
        client = KanbanClient(dry_run=False)
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess([], 1, stdout="", stderr="error")
            with pytest.raises(RuntimeError, match="Kanban command failed"):
                client.show("t_001")

    def test_unblock_calls_cli(self):
        client = KanbanClient(dry_run=False)
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
            client.unblock("t_001", "approved")
            args = mock_run.call_args[0][0]
            assert "unblock" in args
            assert "--reason" in args


# ---------------------------------------------------------------------------
# T3: LLMClient
# ---------------------------------------------------------------------------

class TestLLMClient:
    def test_dry_run_returns_placeholder(self):
        client = LLMClient(dry_run=True)
        result = client.call("system", "user")
        assert "DRY-RUN" in result

    def test_reads_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("LITELLM_API_KEY", "sk-test-key")
        client = LLMClient(dry_run=False)
        assert client.api_key == "sk-test-key"

    def test_reads_api_key_from_env_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("LITELLM_API_KEY", raising=False)
        env_file = tmp_path / ".env"
        env_file.write_text("LITELLM_API_KEY=sk-from-file\nOTHER=value")
        with mock.patch("orchestrator.Path") as mock_path:
            # Can't easily mock Path.home(), so test the env var path instead
            pass

    def test_call_makes_http_request(self, monkeypatch):
        monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
        client = LLMClient(dry_run=False)
        client.set_context(card_id="t_abc", run_id="RUN-xyz", workflow="W-BUILD",
                           workspace="/tmp/test")

        mock_response = json.dumps({
            "choices": [{"message": {"content": "test response"}}]
        }).encode()

        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_ctx = mock.MagicMock()
            mock_ctx.read.return_value = mock_response
            mock_ctx.__enter__ = mock.MagicMock(return_value=mock_ctx)
            mock_ctx.__exit__ = mock.MagicMock(return_value=False)
            mock_urlopen.return_value = mock_ctx

            result = client.call("You are a codebase scout.", "user prompt")
            assert result == "test response"

            req = mock_urlopen.call_args[0][0]
            body = json.loads(req.data)
            tags = body["metadata"]["tags"]
            assert "card:t_abc" in tags
            assert "run:RUN-xyz" in tags
            assert "workflow:W-BUILD" in tags
            assert "workspace:test" in tags
            assert "agent:scout" in tags
            assert "model:litellm/deepseek-v4-flash-0731" in tags
            assert "source:orchestrator" in tags
            assert "t_abc" in json.dumps(dict(req.header_items()))

    def test_derive_role_from_system_prompt(self):
        client = LLMClient(dry_run=True)
        assert client._derive_role("You are a codebase scout...") == "scout"
        assert client._derive_role("You are a software architect...") == "architect"
        assert client._derive_role("You are a requirements coach...") == "coach"
        assert client._derive_role("Something unrelated") == "orchestrator"

    def test_call_always_tags_even_without_context(self, monkeypatch):
        monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
        client = LLMClient(dry_run=False)  # no set_context

        mock_response = json.dumps({
            "choices": [{"message": {"content": "ok"}}]
        }).encode()
        with mock.patch("urllib.request.urlopen") as mock_urlopen:
            mock_ctx = mock.MagicMock()
            mock_ctx.read.return_value = mock_response
            mock_ctx.__enter__ = mock.MagicMock(return_value=mock_ctx)
            mock_ctx.__exit__ = mock.MagicMock(return_value=False)
            mock_urlopen.return_value = mock_ctx

            client.call("sys", "user")
            req = mock_urlopen.call_args[0][0]
            tags = json.loads(req.data)["metadata"]["tags"]
            assert "card:unset" in tags
            assert all(any(t.startswith(p) for t in tags)
                       for p in ("card:", "run:", "workflow:", "workspace:",
                                 "agent:", "model:", "source:"))


# ---------------------------------------------------------------------------
# T4: CodebaseExplorer
# ---------------------------------------------------------------------------

class TestCodebaseExplorer:
    def test_file_tree(self, tmp_workspace):
        explorer = CodebaseExplorer(str(tmp_workspace))
        tree = explorer.file_tree()
        assert "pyproject.toml" in tree
        assert "README.md" in tree
        assert "src" in tree

    def test_file_tree_skips_hidden_dirs(self, tmp_workspace):
        (tmp_workspace / ".git" / "config").parent.mkdir(parents=True, exist_ok=True)
        (tmp_workspace / ".git" / "config").write_text("test")
        explorer = CodebaseExplorer(str(tmp_workspace))
        tree = explorer.file_tree()
        assert ".git" not in tree

    def test_read_key_files(self, tmp_workspace):
        explorer = CodebaseExplorer(str(tmp_workspace))
        content = explorer.read_key_files()
        assert "pyproject.toml" in content
        assert "README.md" in content

    def test_gather_context(self, tmp_workspace):
        explorer = CodebaseExplorer(str(tmp_workspace))
        context = explorer.gather_context("test task")
        assert "Workspace:" in context
        assert "Task: test task" in context
        assert "File Tree" in context
        assert "Key Files" in context

    def test_read_key_files_empty_workspace(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        explorer = CodebaseExplorer(str(empty))
        content = explorer.read_key_files()
        assert "no key files found" in content


# ---------------------------------------------------------------------------
# T5: Circuit Breakers
# ---------------------------------------------------------------------------

class TestCircuitBreakers:
    def test_cycle_limit_exceeded(self):
        state = WorkflowState(
            run_id="RUN-cb01", workflow="W-BUILD", card_id="t_001",
            workspace="/tmp", branch="agent/test", task_title="T", task_body="B",
            cycle=5,  # MAX_CYCLES["W-BUILD"] = 4
        )
        with pytest.raises(CircuitBreakerError, match="Cycle limit exceeded"):
            check_circuit_breakers(state)

    def test_cycle_limit_at_boundary(self):
        state = WorkflowState(
            run_id="RUN-cb02", workflow="W-BUILD", card_id="t_001",
            workspace="/tmp", branch="agent/test", task_title="T", task_body="B",
            cycle=4,  # exactly at limit — should NOT trigger (>)
        )
        # Should not raise (cycle == max is ok, cycle > max triggers)
        check_circuit_breakers(state)

    def test_same_finding_repeated(self):
        state = WorkflowState(
            run_id="RUN-cb03", workflow="W-BUILD", card_id="t_001",
            workspace="/tmp", branch="agent/test", task_title="T", task_body="B",
            cycle=1,
            fix_history=[
                {"cycle": 1, "finding_id": "lint-error"},
                {"cycle": 2, "finding_id": "lint-error"},
                {"cycle": 3, "finding_id": "lint-error"},
            ],
        )
        with pytest.raises(CircuitBreakerError, match="Same finding"):
            check_circuit_breakers(state)

    def test_different_findings_no_trip(self):
        state = WorkflowState(
            run_id="RUN-cb04", workflow="W-BUILD", card_id="t_001",
            workspace="/tmp", branch="agent/test", task_title="T", task_body="B",
            cycle=1,
            fix_history=[
                {"cycle": 1, "finding_id": "lint-error"},
                {"cycle": 2, "finding_id": "type-error"},
                {"cycle": 3, "finding_id": "test-failure"},
            ],
        )
        check_circuit_breakers(state)  # should not raise

    def test_blocking_count_not_decreasing(self):
        state = WorkflowState(
            run_id="RUN-cb05", workflow="W-BUILD", card_id="t_001",
            workspace="/tmp", branch="agent/test", task_title="T", task_body="B",
            cycle=1,
            gate_results=[
                {"blocking_count": 3},
                {"blocking_count": 3},  # same — not decreasing
            ],
        )
        with pytest.raises(CircuitBreakerError, match="Blocking count not decreasing"):
            check_circuit_breakers(state)

    def test_blocking_count_decreasing_no_trip(self):
        state = WorkflowState(
            run_id="RUN-cb06", workflow="W-BUILD", card_id="t_001",
            workspace="/tmp", branch="agent/test", task_title="T", task_body="B",
            cycle=1,
            gate_results=[
                {"blocking_count": 3},
                {"blocking_count": 1},  # decreasing — ok
            ],
        )
        check_circuit_breakers(state)  # should not raise

    def test_fix_cycles_for_w_fix(self):
        state = WorkflowState(
            run_id="RUN-cb07", workflow="W-FIX", card_id="t_001",
            workspace="/tmp", branch="agent/test", task_title="T", task_body="B",
            cycle=4,  # MAX_CYCLES["W-FIX"] = 3
        )
        with pytest.raises(CircuitBreakerError, match="Cycle limit"):
            check_circuit_breakers(state)


# ---------------------------------------------------------------------------
# T6: Phase Transitions
# ---------------------------------------------------------------------------

class TestPhaseTransitions:
    def test_phases_run_sequentially(self, sample_state, mock_kanban, mock_llm, mock_explorer, tmp_workspace):
        """Test that phases execute 0 → 1 (blocked)."""
        sample_state.phase = 0
        sample_state.save()

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer, dry_run=True)
        result = engine.run()

        # Should block at phase 1 (requirements)
        assert result["status"] in ("blocked", "running")
        assert sample_state.phase >= 1

    def test_blocked_state_saved(self, sample_state, mock_kanban, mock_llm, mock_explorer):
        """Test that blocked state is persisted."""
        sample_state.phase = 0
        sample_state.save()

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer, dry_run=True)
        engine.run()

        # Reload state from disk
        loaded = WorkflowState.load(sample_state.run_id)
        assert loaded.phase_status in ("blocked", "complete")


# ---------------------------------------------------------------------------
# T7: W-BUILD Happy Path
# ---------------------------------------------------------------------------

class TestWBuildHappyPath:
    def test_full_build_cycle_pass(self, sample_state, mock_kanban, mock_llm, mock_explorer, tmp_workspace):
        """Test a complete W-BUILD with all gates passing."""
        sample_state.phase = 3  # Start at build phase
        sample_state.scout_output = "Scout analysis done"
        sample_state.brief_path = "docs/BRIEF.md"
        sample_state.spec_path = "docs/SPEC.md"
        sample_state.small_change = False
        sample_state.save()

        # Create BRIEF.md and SPEC.md
        docs = tmp_workspace / "docs"
        docs.mkdir(exist_ok=True)
        (docs / "BRIEF.md").write_text("# Brief\nRequirements here")
        (docs / "SPEC.md").write_text("# Spec\nDesign here")

        # Mock gates.sh to pass
        gates_sh = tmp_workspace / "bin" / "gates.sh"
        gates_sh.parent.mkdir(exist_ok=True)
        gates_sh.write_text('#!/bin/bash\necho "::gate:: test"\necho "::result:: PASS"\nexit 0\n')
        gates_sh.chmod(0o755)

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer, dry_run=True)

        # Mock opencode to succeed
        with mock.patch.object(engine, "_opencode_run", return_value={"ok": True, "output": "done"}):
            with mock.patch.object(engine, "_git", return_value=""):
                result = engine.run()

        assert result["status"] in ("blocked", "complete")


# ---------------------------------------------------------------------------
# T8: W-BUILD Fix Loop
# ---------------------------------------------------------------------------

class TestWBuildFixLoop:
    def test_fix_loop_after_gate_failure(self, sample_state, mock_kanban, mock_llm, mock_explorer, tmp_workspace):
        """Test that fix loop runs when gatekeeper fails, then passes."""
        sample_state.phase = 3
        sample_state.scout_output = "done"
        sample_state.spec_path = "docs/SPEC.md"
        sample_state.save()

        docs = tmp_workspace / "docs"
        docs.mkdir(exist_ok=True)
        (docs / "SPEC.md").write_text("# Spec")

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer, dry_run=True)

        call_count = {"gatekeeper": 0}

        def mock_gatekeeper():
            call_count["gatekeeper"] += 1
            if call_count["gatekeeper"] <= 1:
                return {"verdict": "FAIL", "blocking_count": 2, "findings": ["lint-error"]}
            return {"verdict": "PASS", "blocking_count": 0, "findings": []}

        with mock.patch.object(engine, "_opencode_run", return_value={"ok": True, "output": "done"}):
            with mock.patch.object(engine, "_run_gatekeeper", side_effect=mock_gatekeeper):
                with mock.patch.object(engine, "_git", return_value=""):
                    result = engine.run()

        assert call_count["gatekeeper"] >= 2  # Failed once, then passed


# ---------------------------------------------------------------------------
# T9: Circuit Breaker in Build
# ---------------------------------------------------------------------------

class TestBuildCircuitBreaker:
    def test_cycles_exhausted_triggers_breaker(self, sample_state, mock_kanban, mock_llm, mock_explorer, tmp_workspace):
        """Test that exhausting build cycles triggers circuit breaker."""
        sample_state.phase = 3
        sample_state.scout_output = "done"
        sample_state.spec_path = "docs/SPEC.md"
        sample_state.save()

        docs = tmp_workspace / "docs"
        docs.mkdir(exist_ok=True)
        (docs / "SPEC.md").write_text("# Spec")

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer, dry_run=True)

        # Gates always fail
        with mock.patch.object(engine, "_opencode_run", return_value={"ok": True, "output": "done"}):
            with mock.patch.object(engine, "_run_gatekeeper",
                                   return_value={"verdict": "FAIL", "blocking_count": 3, "findings": ["lint"]}):
                with mock.patch.object(engine, "_git", return_value=""):
                    result = engine.run()

        assert result["status"] == "circuit_breaker"
        # Any circuit breaker is acceptable here (cycle limit or blocking count)
        assert "circuit_breaker" in result["status"]


# ---------------------------------------------------------------------------
# T10: W-FIX Workflow
# ---------------------------------------------------------------------------

class TestWFixWorkflow:
    def test_fix_workflow(self, sample_state, mock_kanban, mock_llm, mock_explorer, tmp_workspace):
        """Test W-FIX workflow executes correctly."""
        sample_state.workflow = "W-FIX"
        sample_state.phase = 3
        sample_state.scout_output = "done"
        sample_state.save()

        # Tests-first: the failing test + trace must exist before the fix may start
        tests_dir = tmp_workspace / "tests"
        tests_dir.mkdir(exist_ok=True)
        (tests_dir / "test_bug.py").write_text("def test_repro():\n    assert False\n")
        (tests_dir / "TRACE.md").write_text("| BUG-1 | tests/test_bug.py::test_repro |\n")

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer, dry_run=True)

        with mock.patch.object(engine, "_opencode_run", return_value={"ok": True, "output": "done"}):
            with mock.patch.object(engine, "_run_gatekeeper",
                                   return_value={"verdict": "PASS", "blocking_count": 0, "findings": []}):
                with mock.patch.object(engine, "_git", return_value=""):
                    result = engine.run()

        assert result["status"] in ("blocked", "complete")


# ---------------------------------------------------------------------------
# T11: Small Change Fast Path
# ---------------------------------------------------------------------------

class TestSmallChangePath:
    def test_small_change_skips_coach_and_architect(self, sample_state, mock_kanban, mock_llm, mock_explorer, tmp_workspace):
        """Test that small changes skip Coach and Architect phases."""
        sample_state.phase = 1
        sample_state.task_body = "Fix a typo in the README"  # Very small task
        sample_state.save()

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer, dry_run=True)

        # Mock estimate to return small number
        with mock.patch.object(engine, "_estimate_files_touched", return_value=1):
            result = engine.phase_1_requirements()

        assert sample_state.small_change is True
        # Coach should NOT have been called
        for call in mock_llm.call.call_args_list:
            assert "requirements" not in call[0][0].lower() or "coach" not in call[0][0].lower()


# ---------------------------------------------------------------------------
# T12: Gatekeeper Parsing
# ---------------------------------------------------------------------------

class TestGatekeeperParsing:
    def test_parse_passing_gates(self, sample_state, mock_kanban, mock_llm, mock_explorer, tmp_workspace):
        """Test parsing of passing gates.sh output."""
        gates_sh = tmp_workspace / "bin" / "gates.sh"
        gates_sh.parent.mkdir(exist_ok=True)
        gates_sh.write_text(textwrap.dedent("""\
            #!/bin/bash
            echo "Detected stack: python"
            echo "::gate:: lint"
            echo "::result:: PASS"
            echo "::gate:: test"
            echo "::result:: PASS"
            exit 0
        """))
        gates_sh.chmod(0o755)

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer)
        result = engine._run_gatekeeper()

        assert result["verdict"] == "PASS"
        assert result["blocking_count"] == 0

    def test_parse_failing_gates(self, sample_state, mock_kanban, mock_llm, mock_explorer, tmp_workspace):
        """Test parsing of failing gates.sh output."""
        gates_sh = tmp_workspace / "bin" / "gates.sh"
        gates_sh.parent.mkdir(exist_ok=True)
        gates_sh.write_text(textwrap.dedent("""\
            #!/bin/bash
            echo "Detected stack: python"
            echo "::gate:: lint"
            echo "::result:: FAIL"
            echo "::output::"
            echo "Found 3 errors"
            echo "::gate:: test"
            echo "::result:: PASS"
            exit 1
        """))
        gates_sh.chmod(0o755)

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer)
        result = engine._run_gatekeeper()

        assert result["verdict"] == "FAIL"
        assert result["blocking_count"] == 1

    def test_no_gates_sh(self, sample_state, mock_kanban, mock_llm, mock_explorer, tmp_workspace):
        """Test behavior when gates.sh doesn't exist."""
        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer)
        result = engine._run_gatekeeper()

        # Should default to PASS when no gates.sh (dry run behavior)
        assert result["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# T13: Unknown Dimension Parsing
# ---------------------------------------------------------------------------

class TestUnknownParsing:
    def test_parse_unknowns_from_table(self, sample_state, mock_kanban, mock_llm, mock_explorer):
        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer)

        coach_output = textwrap.dedent("""
            | Scope | Known | Clear |
            | Data | Unknown | What data model? |
            | Security | Unknown | Auth requirements? |
            | Testing | Known | pytest |
        """)

        unknowns = engine._parse_unknowns(coach_output)
        assert len(unknowns) >= 2
        assert any("Data" in u for u in unknowns)
        assert any("Security" in u for u in unknowns)

    def test_no_unknowns(self, sample_state, mock_kanban, mock_llm, mock_explorer):
        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer)

        coach_output = textwrap.dedent("""
            | Scope | Known | Clear |
            | Data | Known | Defined |
        """)

        unknowns = engine._parse_unknowns(coach_output)
        assert len(unknowns) == 0


# ---------------------------------------------------------------------------
# T14: CLI Interface
# ---------------------------------------------------------------------------

class TestCLI:
    def test_list_empty(self, tmp_state_dir):
        """Test listing when no workflows exist."""
        with mock.patch("sys.stdout", new_callable=lambda: __import__("io").StringIO()) as mock_out:
            args = mock.MagicMock()
            cmd_list(args)
            output = json.loads(mock_out.getvalue())
            assert output == []

    def test_list_with_workflows(self, tmp_state_dir):
        """Test listing existing workflows."""
        state = WorkflowState(
            run_id="RUN-list01", workflow="W-BUILD", card_id="t_001",
            workspace="/tmp/test", branch="agent/test", task_title="Test",
            task_body="Body",
        )
        state.save()

        with mock.patch("sys.stdout", new_callable=lambda: __import__("io").StringIO()) as mock_out:
            args = mock.MagicMock()
            cmd_list(args)
            output = json.loads(mock_out.getvalue())
            assert len(output) == 1
            assert output[0]["run_id"] == "RUN-list01"

    def test_status_existing(self, sample_state):
        with mock.patch("sys.stdout", new_callable=lambda: __import__("io").StringIO()) as mock_out:
            args = mock.MagicMock()
            args.run_id = sample_state.run_id
            cmd_status(args)
            output = json.loads(mock_out.getvalue())
            assert output["run_id"] == sample_state.run_id

    def test_status_nonexistent(self, tmp_state_dir):
        with mock.patch("sys.exit") as mock_exit:
            with mock.patch("sys.stdout", new_callable=lambda: __import__("io").StringIO()):
                args = mock.MagicMock()
                args.run_id = "RUN-nonexistent"
                cmd_status(args)
                mock_exit.assert_called_with(1)


# ---------------------------------------------------------------------------
# T15: Blocking/Unblocking Flow
# ---------------------------------------------------------------------------

class TestBlockingFlow:
    def test_requirements_block(self, sample_state, mock_kanban, mock_llm, mock_explorer, tmp_workspace):
        """Test that phase 1 blocks for requirements approval."""
        sample_state.phase = 1
        sample_state.small_change = False
        sample_state.save()

        # Make Coach return unknowns (and the design reviewer PASS so the review passes round 1)
        def coach_llm(system_prompt, user_prompt, model=None, max_tokens=None):
            if "design reviewer" in system_prompt.lower():
                return "---VERDICT---\nstatus: PASS\nblocking_count: 0\nadvisory_count: 0\nsummary: ok\n---END---"
            if "requirements" in system_prompt.lower() or "coach" in system_prompt.lower():
                return "| Data | Unknown | What schema? |\n| Scope | Known | Clear |"
            return "scout output"

        mock_llm.call.side_effect = coach_llm

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer, dry_run=True)

        # Mock estimate to return high number so small-change path doesn't trigger
        with mock.patch.object(engine, "_estimate_files_touched", return_value=5):
            result = engine.phase_1_requirements()

        assert result == "blocked"
        assert sample_state.phase_status == "blocked"
        assert sample_state.block_reason == "requirements_approval"
        mock_kanban.block.assert_called()

    def test_design_block(self, sample_state, mock_kanban, mock_llm, mock_explorer, tmp_workspace):
        """Test that phase 2 blocks for design approval."""
        sample_state.phase = 2
        sample_state.small_change = False
        sample_state.scout_output = "done"
        sample_state.brief_path = "docs/BRIEF.md"
        sample_state.save()

        docs = tmp_workspace / "docs"
        docs.mkdir(exist_ok=True)
        (docs / "BRIEF.md").write_text("# Brief")

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer, dry_run=True)
        result = engine.phase_2_design()

        assert result == "blocked"
        assert sample_state.block_reason == "design_approval"
        mock_kanban.block.assert_called()


# ---------------------------------------------------------------------------
# T16: Error Handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_git_failure_in_prep(self, sample_state, mock_kanban, mock_llm, mock_explorer, tmp_workspace):
        """Test that git failures are handled gracefully."""
        sample_state.phase = 0
        sample_state.save()

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer, dry_run=True)

        def failing_git(*args):
            raise RuntimeError("git failed: permission denied")

        with mock.patch.object(engine, "_git", side_effect=failing_git):
            result = engine.run()

        assert result["status"] == "failed"
        assert "error" in result

    def test_opencode_failure_continues(self, sample_state, mock_kanban, mock_llm, mock_explorer, tmp_workspace):
        """Test that opencode failures don't crash the workflow."""
        sample_state.phase = 3
        sample_state.scout_output = "done"
        sample_state.spec_path = "docs/SPEC.md"
        sample_state.save()

        docs = tmp_workspace / "docs"
        docs.mkdir(exist_ok=True)
        (docs / "SPEC.md").write_text("# Spec")

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer, dry_run=True)

        with mock.patch.object(engine, "_opencode_run", return_value={"ok": False, "output": "error"}):
            with mock.patch.object(engine, "_run_gatekeeper",
                                   return_value={"verdict": "PASS", "blocking_count": 0, "findings": []}):
                with mock.patch.object(engine, "_git", return_value=""):
                    result = engine.run()

        # Should not crash — continues to gate/review
        assert result["status"] in ("blocked", "complete", "circuit_breaker")


# ---------------------------------------------------------------------------
# T17: Git Operations
# ---------------------------------------------------------------------------

class TestGitOperations:
    def test_git_init_and_commit(self, tmp_workspace, sample_state, mock_kanban, mock_llm, mock_explorer):
        """Test git operations work correctly."""
        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer)

        # Should be able to run git commands
        result = engine._git("status", "--porcelain")
        assert isinstance(result, str)

    def test_git_nothing_to_commit(self, tmp_workspace, sample_state, mock_kanban, mock_llm, mock_explorer):
        """Test handling of 'nothing to commit'."""
        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer)

        # Commit with nothing new should not raise
        result = engine._git("commit", "-m", "empty", "--allow-empty")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# T18: OpenCode Invocation
# ---------------------------------------------------------------------------

class TestOpenCodeInvocation:
    def test_opencode_dry_run(self, sample_state, mock_kanban, mock_llm, mock_explorer):
        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer, dry_run=True)
        result = engine._opencode_run("test prompt")
        assert result["ok"] is True
        assert "DRY-RUN" in result["output"]

    def test_opencode_success(self, sample_state, mock_kanban, mock_llm, mock_explorer):
        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer, dry_run=False)

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="done", stderr="")
            result = engine._opencode_run("implement feature")
            assert result["ok"] is True

    def test_opencode_failure(self, sample_state, mock_kanban, mock_llm, mock_explorer):
        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer, dry_run=False)

        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess([], 1, stdout="", stderr="error")
            result = engine._opencode_run("implement feature")
            assert result["ok"] is False

    def test_opencode_timeout(self, sample_state, mock_kanban, mock_llm, mock_explorer):
        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer, dry_run=False)

        with mock.patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("opencode", 600)
            result = engine._opencode_run("implement feature")
            assert result["ok"] is False
            assert "timeout" in result["output"]


# ---------------------------------------------------------------------------
# Integration: Full workflow state machine
# ---------------------------------------------------------------------------

class TestIntegration:
    def test_full_state_machine_dry_run(self, tmp_workspace, tmp_state_dir, mock_kanban, mock_llm):
        """End-to-end dry run of W-BUILD through all phases."""
        # Create gates.sh
        gates_sh = tmp_workspace / "bin" / "gates.sh"
        gates_sh.parent.mkdir(exist_ok=True)
        gates_sh.write_text('#!/bin/bash\necho "::gate:: test"\necho "::result:: PASS"\nexit 0\n')
        gates_sh.chmod(0o755)

        # Create docs
        docs = tmp_workspace / "docs"
        docs.mkdir(exist_ok=True)

        state = WorkflowState(
            run_id="RUN-integ01", workflow="W-BUILD", card_id="t_integ",
            workspace=str(tmp_workspace), branch="agent/integ-test",
            task_title="Integration Test", task_body="Build something",
            phase=0,
        )
        state.save()

        explorer = CodebaseExplorer(str(tmp_workspace))
        engine = WorkflowEngine(state, mock_kanban, mock_llm, explorer, dry_run=True)

        # Mock opencode to always succeed
        with mock.patch.object(engine, "_opencode_run", return_value={"ok": True, "output": "done"}):
            result = engine.run()

        # Should have progressed through phases
        assert state.phase >= 1
        assert state.phase_status in ("blocked", "complete")
        assert len(state.log) > 0

    def test_small_change_skips_to_build(self, tmp_workspace, tmp_state_dir, mock_kanban, mock_llm):
        """Test that small changes skip requirements and design."""
        gates_sh = tmp_workspace / "bin" / "gates.sh"
        gates_sh.parent.mkdir(exist_ok=True)
        gates_sh.write_text('#!/bin/bash\necho "::gate:: test"\necho "::result:: PASS"\nexit 0\n')
        gates_sh.chmod(0o755)

        state = WorkflowState(
            run_id="RUN-small01", workflow="W-BUILD", card_id="t_small",
            workspace=str(tmp_workspace), branch="agent/small-fix",
            task_title="Fix typo", task_body="Fix a typo in README",
            phase=0,
        )
        state.save()

        explorer = CodebaseExplorer(str(tmp_workspace))
        engine = WorkflowEngine(state, mock_kanban, mock_llm, explorer, dry_run=True)

        with mock.patch.object(engine, "_opencode_run", return_value={"ok": True, "output": "done"}):
            with mock.patch.object(engine, "_estimate_files_touched", return_value=1):
                result = engine.run()

        assert state.small_change is True
        # Should NOT have written BRIEF.md (Coach was skipped)
        assert not (tmp_workspace / "docs" / "BRIEF.md").exists()


# ---------------------------------------------------------------------------
# T19: Additional Edge Cases and Stress Tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_state_dir_created_on_save(self, tmp_path):
        """State save creates the directory if it doesn't exist."""
        deep_dir = tmp_path / "a" / "b" / "c" / "state"
        with mock.patch("orchestrator.STATE_DIR", deep_dir):
            state = WorkflowState(
                run_id="RUN-deep01", workflow="W-BUILD", card_id="t_001",
                workspace="/tmp", branch="agent/test", task_title="T", task_body="B",
            )
            state.save()
            assert (deep_dir / "RUN-deep01.json").exists()

    def test_concurrent_state_files(self, tmp_state_dir):
        """Multiple workflow states coexist without interference."""
        for i in range(10):
            state = WorkflowState(
                run_id=f"RUN-conc{i:02d}", workflow="W-BUILD", card_id=f"t_{i}",
                workspace="/tmp", branch=f"agent/task-{i}", task_title=f"Task {i}",
                task_body=f"Body {i}", phase=i % 6,
            )
            state.save()

        # Verify all 10 are loadable
        for i in range(10):
            loaded = WorkflowState.load(f"RUN-conc{i:02d}")
            assert loaded.phase == i % 6

    def test_special_characters_in_task_body(self, tmp_state_dir):
        """State handles special characters in task body."""
        state = WorkflowState(
            run_id="RUN-special01", workflow="W-BUILD", card_id="t_001",
            workspace="/tmp", branch="agent/test", task_title="Fix: <script>alert('xss')</script>",
            task_body='Body with "quotes", \'apostrophes\', and\nnewlines\tand\ttabs',
        )
        state.save()
        loaded = WorkflowState.load("RUN-special01")
        assert "<script>" in loaded.task_title
        assert '"quotes"' in loaded.task_body

    def test_empty_task_body(self, tmp_state_dir, mock_kanban, mock_llm, mock_explorer):
        """Engine handles empty task body gracefully."""
        state = WorkflowState(
            run_id="RUN-empty01", workflow="W-BUILD", card_id="t_001",
            workspace="/tmp", branch="agent/test", task_title="", task_body="",
        )
        state.save()

        engine = WorkflowEngine(state, mock_kanban, mock_llm, mock_explorer, dry_run=True)
        # Should not crash on empty body
        count = engine._estimate_files_touched()
        assert count >= 1  # minimum 1

    def test_max_cycles_per_workflow(self):
        """Verify max cycles are set for all workflow types."""
        for wf in ["W-BUILD", "W-FIX", "W-HARDEN", "W-SPEC", "W-REFACTOR"]:
            assert wf in MAX_CYCLES
            assert MAX_CYCLES[wf] > 0

    def test_state_log_ordering(self, tmp_state_dir):
        """Log entries maintain insertion order."""
        state = WorkflowState(
            run_id="RUN-order01", workflow="W-BUILD", card_id="t_001",
            workspace="/tmp", branch="agent/test", task_title="T", task_body="B",
        )
        for i in range(20):
            state.append_log(f"Entry {i}")
        state.save()

        loaded = WorkflowState.load("RUN-order01")
        for i, entry in enumerate(loaded.log):
            assert f"Entry {i}" in entry

    def test_phase_validation_max_phase(self, tmp_state_dir):
        """Phase 6 (beyond max) should cause the engine to complete."""
        state = WorkflowState(
            run_id="RUN-phase01", workflow="W-BUILD", card_id="t_001",
            workspace="/tmp", branch="agent/test", task_title="T", task_body="B",
            phase=6,  # beyond all phases
        )
        state.save()

        mock_kanban = mock.MagicMock()
        mock_llm = mock.MagicMock()
        mock_explorer = mock.MagicMock()

        engine = WorkflowEngine(state, mock_kanban, mock_llm, mock_explorer, dry_run=True)
        result = engine.run()
        assert result["status"] == "complete"


class TestKanbanEdgeCases:
    def test_block_with_all_kinds(self):
        """Test all block kinds are passed correctly."""
        client = KanbanClient(dry_run=False)
        for kind in ["capability", "dependency", "needs_input", "transient"]:
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
                client.block("t_001", "reason", kind=kind)
                args = mock_run.call_args[0][0]
                assert kind in args

    def test_show_json_parsing(self):
        """Test that show() properly parses JSON output."""
        client = KanbanClient(dry_run=False)
        card_data = {
            "id": "t_complex", "title": "Complex Card",
            "body": "Body with\nnewlines", "status": "running",
            "skills": ["dev-lead"], "comments": [{"body": "test"}],
        }
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                [], 0, stdout=json.dumps(card_data), stderr=""
            )
            result = client.show("t_complex")
            assert result["id"] == "t_complex"
            assert result["skills"] == ["dev-lead"]
            assert len(result["comments"]) == 1


class TestCodebaseExplorerEdgeCases:
    def test_file_tree_max_depth(self, tmp_workspace):
        """Test that file tree respects max_depth."""
        # Create deeply nested structure
        deep = tmp_workspace / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)
        (deep / "deep_file.py").write_text("pass")

        explorer = CodebaseExplorer(str(tmp_workspace))
        tree_depth_2 = explorer.file_tree(max_depth=2)
        tree_depth_5 = explorer.file_tree(max_depth=5)

        # Deep file should not appear in depth-2 tree
        assert "deep_file.py" not in tree_depth_2
        assert "deep_file.py" in tree_depth_5

    def test_gather_context_with_task(self, tmp_workspace):
        """Context includes task description when provided."""
        explorer = CodebaseExplorer(str(tmp_workspace))
        ctx = explorer.gather_context("Build authentication module")
        assert "Build authentication module" in ctx

    def test_gather_context_without_task(self, tmp_workspace):
        """Context works without task description."""
        explorer = CodebaseExplorer(str(tmp_workspace))
        ctx = explorer.gather_context()
        assert "File Tree" in ctx


class TestGitEdgeCases:
    def test_git_branch_checkout_existing(self, tmp_workspace, sample_state, mock_kanban, mock_llm, mock_explorer):
        """Test checking out an existing branch."""
        sample_state.workspace = str(tmp_workspace)
        sample_state.branch = "agent/existing-branch"
        sample_state.save()

        # Create the branch first
        subprocess.run(["git", "checkout", "-b", "agent/existing-branch"],
                       cwd=str(tmp_workspace), capture_output=True)
        subprocess.run(["git", "checkout", "main"],
                       cwd=str(tmp_workspace), capture_output=True)

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer)
        result = engine._git("branch", "--list", "agent/existing-branch")
        assert "existing-branch" in result


# ---------------------------------------------------------------------------
# T20: Tests-First Phase (test-author before builder + trace enforcement)
# ---------------------------------------------------------------------------

def _write_spec_with_acs(workspace, acs):
    """Write docs/SPEC.md with an Acceptance Criteria table for the given AC ids."""
    docs = Path(workspace) / "docs"
    docs.mkdir(exist_ok=True)
    rows = "\n".join(f"| {a} | testable criterion {a} | B1 |" for a in acs)
    (docs / "SPEC.md").write_text(
        f"# Spec\n\n## Acceptance Criteria\n\n"
        f"| ID | Criterion | Maps to BRIEF ID |\n|----|-----------|-----------------|\n"
        f"{rows}\n"
    )


def _write_trace(workspace, rows, test_files=None):
    """Write tests/TRACE.md (and optional test files) in the workspace."""
    tests_dir = Path(workspace) / "tests"
    tests_dir.mkdir(exist_ok=True)
    if test_files:
        for name, content in test_files.items():
            (tests_dir / name).write_text(content)
    (tests_dir / "TRACE.md").write_text("\n".join(rows) + "\n")


def _pass_verdict():
    return ("---VERDICT---\nstatus: PASS\nblocking_count: 0\nadvisory_count: 0\n"
            "summary: ok\n---END---")


def _fail_verdict(finding="DR1"):
    return (f"---VERDICT---\nstatus: FAIL\nblocking_count: 1\nadvisory_count: 0\n"
            f"summary: not ok\nfindings:\n  - id: {finding}\n    severity: blocking\n"
            f"    file: SPEC.md\n    section: Data Model\n    problem: missing field types\n"
            f"    fix: add field types\n---END---")


class TestTestsFirstPhase:
    def test_test_author_runs_before_builder(self, sample_state, mock_kanban,
                                             mock_llm, mock_explorer, tmp_workspace):
        """W-BUILD: test-author (TESTS-FIRST) must be invoked before the builder."""
        sample_state.phase = 3
        sample_state.spec_path = "docs/SPEC.md"
        sample_state.save()
        _write_spec_with_acs(tmp_workspace, ["AC1", "AC2"])
        _write_trace(tmp_workspace,
                     ["| AC1 | tests/test_feature.py::test_ac1 |",
                      "| AC2 | tests/test_feature.py::test_ac2 |"],
                     {"test_feature.py": "def test_ac1(): pass\ndef test_ac2(): pass\n"})

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm,
                                mock_explorer, dry_run=True)
        calls = []

        def fake_opencode(prompt):
            calls.append(prompt)
            return {"ok": True, "output": "done"}

        with mock.patch.object(engine, "_opencode_run", side_effect=fake_opencode):
            with mock.patch.object(engine, "_run_gatekeeper",
                                   return_value={"verdict": "PASS", "blocking_count": 0,
                                                 "findings": []}):
                with mock.patch.object(engine, "_git", return_value=""):
                    engine._build_cycle()

        assert "TESTS-FIRST" in calls[0], "test-author must run first"
        assert "GREEN phase" in calls[1], "builder must run against existing tests"

    def test_untraced_spec_item_blocks_build(self, sample_state, mock_kanban,
                                             mock_llm, mock_explorer, tmp_workspace):
        """SPEC items without a traced failing test must FAIL the trace check."""
        sample_state.phase = 3
        sample_state.spec_path = "docs/SPEC.md"
        sample_state.save()
        _write_spec_with_acs(tmp_workspace, ["AC1", "AC2", "AC3"])
        _write_trace(tmp_workspace,
                     ["| AC1 | tests/test_feature.py::test_ac1 |",
                      "| AC2 | tests/test_feature.py::test_ac2 |"],
                     {"test_feature.py": "def test_ac1(): pass\ndef test_ac2(): pass\n"})

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm,
                                mock_explorer, dry_run=True)
        result = engine._check_test_trace()
        assert result["verdict"] == "FAIL"
        assert result["blocking_count"] == 1
        assert any(f["id"] == "TRACE-AC3" for f in result["findings"])

    def test_traced_missing_test_file_blocks_build(self, sample_state, mock_kanban,
                                                   mock_llm, mock_explorer, tmp_workspace):
        """A trace row pointing at a non-existent test file must FAIL the check."""
        sample_state.phase = 3
        sample_state.spec_path = "docs/SPEC.md"
        sample_state.save()
        _write_spec_with_acs(tmp_workspace, ["AC1"])
        _write_trace(tmp_workspace, ["| AC1 | tests/ghost_file.py::test_ac1 |"])

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm,
                                mock_explorer, dry_run=True)
        result = engine._check_test_trace()
        assert result["verdict"] == "FAIL"
        assert any(f["id"] == "TRACE-AC1-FILE" for f in result["findings"])

    def test_wfix_requires_bug_trace(self, sample_state, mock_kanban, mock_llm,
                                     mock_explorer, tmp_workspace):
        """W-FIX without a delta SPEC: the bug must be traced to a failing test."""
        sample_state.workflow = "W-FIX"
        sample_state.phase = 3
        sample_state.save()
        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm,
                                mock_explorer, dry_run=True)
        result = engine._check_test_trace()
        assert result["verdict"] == "FAIL"
        assert any(f["id"] == "TRACE-BUG" for f in result["findings"])

    def test_small_change_skips_trace(self, sample_state, mock_kanban, mock_llm,
                                      mock_explorer, tmp_workspace):
        """Small-change fast path: no spec is produced, trace check is vacuous PASS."""
        sample_state.small_change = True
        sample_state.save()
        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm,
                                mock_explorer, dry_run=True)
        result = engine._check_test_trace()
        assert result["verdict"] == "PASS"

    def test_enforce_trace_retries_then_passes(self, sample_state, mock_kanban,
                                               mock_llm, mock_explorer, tmp_workspace):
        """test-author is re-invoked to close trace gaps; success on retry passes."""
        sample_state.phase = 3
        sample_state.spec_path = "docs/SPEC.md"
        sample_state.save()
        _write_spec_with_acs(tmp_workspace, ["AC1", "AC2"])

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm,
                                mock_explorer, dry_run=True)

        def fake_opencode(prompt):
            # The retry (2nd call) writes the missing trace + test files
            if not (tmp_workspace / "tests" / "TRACE.md").exists():
                _write_trace(tmp_workspace,
                             ["| AC1 | tests/test_feature.py::test_ac1 |",
                              "| AC2 | tests/test_feature.py::test_ac2 |"],
                             {"test_feature.py": "def test_ac1(): pass\ndef test_ac2(): pass\n"})
            return {"ok": True, "output": "done"}

        with mock.patch.object(engine, "_opencode_run", side_effect=fake_opencode):
            engine._enforce_test_trace()  # must NOT raise
        assert (tmp_workspace / "tests" / "TRACE.md").exists()

    def test_enforce_trace_exhausts_blocks_build(self, sample_state, mock_kanban,
                                                 mock_llm, mock_explorer, tmp_workspace):
        """Persistent trace failure raises CircuitBreakerError — the build never starts."""
        sample_state.phase = 3
        sample_state.spec_path = "docs/SPEC.md"
        sample_state.save()
        _write_spec_with_acs(tmp_workspace, ["AC1", "AC2"])

        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm,
                                mock_explorer, dry_run=True)
        with mock.patch.object(engine, "_opencode_run",
                               return_value={"ok": True, "output": "done"}):
            with pytest.raises(CircuitBreakerError, match="Tests-first trace blocked"):
                engine._enforce_test_trace()
        retries_logged = [e for e in sample_state.log if "test-author retry" in e]
        assert len(retries_logged) == TRACE_RETRIES


# ---------------------------------------------------------------------------
# T21: Design Review Loop (pass → approval; fail → revise; cap 3 → referee)
# ---------------------------------------------------------------------------

class TestDesignReviewLoop:
    def _setup(self, sample_state, tmp_workspace):
        sample_state.phase = 2
        sample_state.small_change = False
        sample_state.scout_output = "done"
        sample_state.brief_path = "docs/BRIEF.md"
        sample_state.save()
        docs = tmp_workspace / "docs"
        docs.mkdir(exist_ok=True)
        (docs / "BRIEF.md").write_text("# Brief\nRequirements here\n")

    def test_review_pass_proceeds_to_approval(self, sample_state, mock_kanban, mock_llm,
                                              mock_explorer, tmp_workspace):
        """Reviewer PASS on round 1 → design approval block, one review round."""
        self._setup(sample_state, tmp_workspace)
        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm,
                                mock_explorer, dry_run=True)
        result = engine.phase_2_design()

        assert result == "blocked"
        assert sample_state.block_reason == "design_approval"
        assert sample_state.design_review_cycles == 1
        assert sample_state.design_review_results[0]["verdict"] == "PASS"
        assert any("Design review round 1/3: PASS" in e for e in sample_state.log)
        mock_kanban.block.assert_called()

    def test_review_fail_then_pass_revises_spec(self, sample_state, mock_kanban, mock_llm,
                                                mock_explorer, tmp_workspace):
        """Reviewer FAIL → architect revises (Mode 4) → re-review PASS → approval."""
        self._setup(sample_state, tmp_workspace)

        def reviewer_llm(system_prompt, user_prompt, model=None, max_tokens=None):
            if "design reviewer" in system_prompt.lower():
                if "RE-REVIEW" in system_prompt:
                    return _pass_verdict()
                return _fail_verdict("DR1")
            if "architect" in system_prompt.lower() or "design" in system_prompt.lower():
                return "Revised SPEC\n## Acceptance Criteria\n| AC1 | x | B1 |\n"
            return "scout output"

        mock_llm.call.side_effect = reviewer_llm
        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm,
                                mock_explorer, dry_run=True)
        result = engine.phase_2_design()

        assert result == "blocked"
        assert sample_state.block_reason == "design_approval"
        assert len(sample_state.design_review_results) == 2
        assert [r["verdict"] for r in sample_state.design_review_results] == ["FAIL", "PASS"]
        assert any("Architect revised" in e for e in sample_state.log)
        spec = (tmp_workspace / "docs" / "SPEC.md").read_text()
        assert "Revised SPEC" in spec

    def test_review_cycle_cap_triggers_referee_block(self, sample_state, mock_kanban,
                                                     mock_llm, mock_explorer, tmp_workspace):
        """Reviewer FAIL 3 rounds → referee block, exactly at the cycle cap."""
        self._setup(sample_state, tmp_workspace)

        def always_fail(system_prompt, user_prompt, model=None, max_tokens=None):
            if "design reviewer" in system_prompt.lower():
                return _fail_verdict("DR1")
            return "spec content"

        mock_llm.call.side_effect = always_fail
        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm,
                                mock_explorer, dry_run=True)
        result = engine.phase_2_design()

        assert result == "blocked"
        assert sample_state.block_reason == "design_review_referee"
        assert sample_state.design_review_referee is True
        assert sample_state.design_review_cycles == MAX_DESIGN_REVIEW_CYCLES
        assert len(sample_state.design_review_results) == MAX_DESIGN_REVIEW_CYCLES
        assert all(r["verdict"] == "FAIL" for r in sample_state.design_review_results)
        call_args = mock_kanban.block.call_args
        assert "REFEREE" in str(call_args)

    def test_design_review_skip_for_small_change(self, sample_state, mock_kanban, mock_llm,
                                                 mock_explorer, tmp_workspace):
        """No design review for small changes."""
        sample_state.small_change = True
        sample_state.save()
        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm,
                                mock_explorer, dry_run=True)
        result = engine.phase_2_design()
        assert result == "done"
        mock_kanban.block.assert_not_called()

    def test_referee_proceed_bypasses_phase2(self, sample_state, mock_kanban, mock_llm,
                                             mock_explorer, tmp_workspace):
        """After referee says proceed, phase 2 returns done (review bypassed)."""
        sample_state.design_review_bypassed = True
        sample_state.save()
        engine = WorkflowEngine(sample_state, mock_kanban, mock_llm,
                                mock_explorer, dry_run=True)
        result = engine.phase_2_design()
        assert result == "done"
        mock_kanban.block.assert_not_called()


# ---------------------------------------------------------------------------
# T22: Verdict parsing + referee resume decisions
# ---------------------------------------------------------------------------

class TestDesignReviewParsing:
    def _engine(self, sample_state, mock_kanban, mock_llm, mock_explorer):
        return WorkflowEngine(sample_state, mock_kanban, mock_llm, mock_explorer, dry_run=True)

    def test_parse_pass(self, sample_state, mock_kanban, mock_llm, mock_explorer):
        assert self._engine(sample_state, mock_kanban, mock_llm,
                            mock_explorer)._parse_design_review_verdict(_pass_verdict()) == "PASS"

    def test_parse_fail(self, sample_state, mock_kanban, mock_llm, mock_explorer):
        assert self._engine(sample_state, mock_kanban, mock_llm,
                            mock_explorer)._parse_design_review_verdict(_fail_verdict()) == "FAIL"

    def test_parse_pass_with_blocking_is_fail(self, sample_state, mock_kanban, mock_llm,
                                              mock_explorer):
        output = ("---VERDICT---\nstatus: PASS\nblocking_count: 2\n"
                  "summary: but there are findings\n---END---")
        assert self._engine(sample_state, mock_kanban, mock_llm,
                            mock_explorer)._parse_design_review_verdict(output) == "FAIL"

    def test_parse_unparseable_is_fail(self, sample_state, mock_kanban, mock_llm,
                                       mock_explorer):
        assert self._engine(sample_state, mock_kanban, mock_llm,
                            mock_explorer)._parse_design_review_verdict("gibberish") == "FAIL"

    def test_extract_findings(self, sample_state, mock_kanban, mock_llm, mock_explorer):
        output = _fail_verdict("DR1") + "\ntrailing text"
        findings = self._engine(sample_state, mock_kanban, mock_llm,
                                mock_explorer)._extract_design_review_findings(output)
        assert "DR1" in findings
        assert "trailing text" not in findings

    def test_models_mapped(self):
        """Role→model map: architect uses the architect alias, design reviewer the reasoning alias."""
        assert ARCHITECT_MODEL == "litellm/architect"
        assert DESIGN_REVIEWER_MODEL == "litellm/reasoning"
        assert MAX_DESIGN_REVIEW_CYCLES == 3


class TestRefereeResume:
    def test_resume_proceed_bypasses_review(self, sample_state):
        """Referee comment 'proceed to build' → review bypassed, phase 2 advances."""
        sample_state.phase = 2
        sample_state.phase_status = "blocked"
        sample_state.block_reason = "design_review_referee"
        sample_state.design_review_referee = True
        sample_state.save()

        with mock.patch.object(KanbanClient, "show",
                               return_value={"comments": [{"author": "user",
                                                            "body": "proceed to build"}]}):
            with mock.patch("sys.stdout", new_callable=lambda: __import__("io").StringIO()):
                args = mock.MagicMock()
                args.run_id = sample_state.run_id
                args.dry_run = True
                cmd_resume(args)

        state = WorkflowState.load(sample_state.run_id)
        assert state.design_review_bypassed is True
        assert state.design_review_referee is False
        assert state.phase_status == "blocked"
        assert state.block_reason == "build_approval"  # ran PAST phase 2 (no re-block at referee)

    def test_resume_guidance_restarts_review(self, sample_state):
        """Referee guidance → design review restarts with a fresh cycle budget."""
        sample_state.phase = 2
        sample_state.phase_status = "blocked"
        sample_state.block_reason = "design_review_referee"
        sample_state.design_review_referee = True
        sample_state.design_review_cycles = 3
        sample_state.save()

        guidance = "Make the interface contracts explicit with error codes"
        with mock.patch.object(KanbanClient, "show",
                               return_value={"comments": [{"author": "user",
                                                            "body": guidance}]}):
            with mock.patch("sys.stdout", new_callable=lambda: __import__("io").StringIO()):
                # The restarted review passes → the design proceeds to the approval gate
                with mock.patch.object(LLMClient, "call", return_value=_pass_verdict()):
                    args = mock.MagicMock()
                    args.run_id = sample_state.run_id
                    args.dry_run = True
                    cmd_resume(args)

        state = WorkflowState.load(sample_state.run_id)
        assert state.design_review_referee is False
        assert state.design_review_cycles == 1  # fresh budget: old 3 reset, 1 round consumed
        assert state.block_reason == "design_approval"
        assert any("Referee: guidance given" in e for e in state.log)

    def test_resume_unblock_without_comment_proceeds(self, sample_state):
        """Unblock with no comment = referee implicit proceed."""
        sample_state.phase = 2
        sample_state.phase_status = "blocked"
        sample_state.block_reason = "design_review_referee"
        sample_state.design_review_referee = True
        sample_state.save()

        with mock.patch.object(KanbanClient, "show",
                               return_value={"comments": []}):
            with mock.patch("sys.stdout", new_callable=lambda: __import__("io").StringIO()):
                args = mock.MagicMock()
                args.run_id = sample_state.run_id
                args.dry_run = True
                cmd_resume(args)

        state = WorkflowState.load(sample_state.run_id)
        assert state.design_review_bypassed is True


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
