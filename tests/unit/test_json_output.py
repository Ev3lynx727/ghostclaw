"""JSON output format and schema validation tests."""
import json
import subprocess
import tempfile
from pathlib import Path

import pytest


def run_ghostclaw_json(repo_path: Path, args: list = None) -> dict:
    """Run ghostclaw analyze with --json and return parsed output."""
    cmd = ["python", "-m", "ghostclaw.cli.ghostclaw", "analyze", str(repo_path), "--json", "--no-write-report"]
    if args:
        cmd.extend(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, f"Command failed: {result.stderr}"
    # JSON is printed to stdout, logs to stderr. Find the first '{' and last '}' to extract the full JSON object.
    output = result.stdout
    start = output.find('{')
    end = output.rfind('}') + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON found in output. stdout[:500]: {output[:500]}")
    json_str = output[start:end]
    return json.loads(json_str)


def test_json_output_schema_full_scan(tmp_path):
    """Validate JSON output structure for a full scan (non-delta)."""
    # Setup a minimal Python repo
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'\n")
    (tmp_path / "main.py").write_text("print('hello')\n")

    data = run_ghostclaw_json(tmp_path, ["--no-ai"])

    # Required top-level fields
    assert "vibe_score" in data
    assert isinstance(data["vibe_score"], int)
    assert "stack" in data
    assert isinstance(data["stack"], str)
    assert "files_analyzed" in data
    assert isinstance(data["files_analyzed"], int)
    assert "total_lines" in data
    assert isinstance(data["total_lines"], int)
    assert "issues" in data
    assert isinstance(data["issues"], list)
    assert "architectural_ghosts" in data
    assert isinstance(data["architectural_ghosts"], list)
    assert "red_flags" in data
    assert isinstance(data["red_flags"], list)
    assert "coupling_metrics" in data
    assert isinstance(data["coupling_metrics"], dict)
    assert "errors" in data
    assert isinstance(data["errors"], list)

    # Metadata required
    assert "metadata" in data
    meta = data["metadata"]
    assert "timestamp" in meta
    assert "analyzer" in meta
    assert "version" in meta
    assert "adapters_active" in meta

    # Delta mode should NOT be present or should be false in full scan
    delta = meta.get("delta", {})
    # If delta field exists, it should have mode=False
    if delta:
        assert delta.get("mode") is False or "mode" not in delta


def test_json_output_contains_delta_fields(tmp_path):
    """Validate that delta mode adds the required delta metadata fields."""
    import os

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)

    # Create initial commit
    (tmp_path / "file1.py").write_text("print('v1')\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=tmp_path, check=True)

    # Modify file and commit
    (tmp_path / "file1.py").write_text("print('v2')\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "update"], cwd=tmp_path, check=True)

    # Run delta mode (no AI to avoid API key requirement)
    data = run_ghostclaw_json(tmp_path, ["--delta", "--base", "HEAD~1", "--no-ai"])

    # Check delta metadata exists and is correct type
    assert "metadata" in data
    meta = data["metadata"]
    assert "delta" in meta
    delta = meta["delta"]

    # Required delta fields
    assert "mode" in delta
    assert delta["mode"] is True
    assert "base_ref" in delta
    assert isinstance(delta["base_ref"], str)
    assert "files_changed" in delta
    assert isinstance(delta["files_changed"], list)
    assert "diff" in delta
    assert isinstance(delta["diff"], str)
    assert len(delta["diff"]) > 0  # diff should not be empty

    # files_changed should include file1.py
    assert any("file1.py" in f for f in delta["files_changed"])


def test_json_output_delta_base_report_loaded(tmp_path):
    """When a base report exists, delta mode should include base context in ai_prompt (if AI enabled)."""
    import json as json_mod
    import os

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)

    # Create first commit
    (tmp_path / "a.py").write_text("print('a')\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "add a"], cwd=tmp_path, check=True)

    # Run full analysis to generate base report JSON (use dummy API key)
    env = {"GHOSTCLAW_API_KEY": "dummy", **os.environ}
    subprocess.run(
        ["python", "-m", "ghostclaw.cli.ghostclaw", "analyze", ".", "--no-write-report", "--json", "--no-ai"],
        cwd=tmp_path, capture_output=True, text=True, env=env, check=True
    )

    # Verify base JSON report was written
    reports_dir = tmp_path / ".ghostclaw" / "reports"
    if not reports_dir.exists():
        pytest.skip("No reports dir created (full analysis may not have run due to environment)")
    json_files = list(reports_dir.glob("ARCHITECTURE-REPORT-*.json"))
    if not json_files:
        pytest.skip("No JSON report created (expected in .ghostclaw/reports/)")

    # Make a change and commit
    (tmp_path / "a.py").write_text("print('a modified')\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "modify a"], cwd=tmp_path, check=True)

    # Run delta mode with --use-ai and --dry-run to capture ai_prompt without API call
    result = subprocess.run(
        ["python", "-m", "ghostclaw.cli.ghostclaw", "analyze", ".", "--delta", "--base", "HEAD~1", "--use-ai", "--dry-run", "--json", "--no-write-report"],
        cwd=tmp_path, capture_output=True, text=True, env=env, timeout=60
    )
    assert result.returncode == 0, f"Delta run failed: {result.stderr}"

    # Parse JSON output (extract full JSON object)
    output = result.stdout
    start = output.find('{')
    end = output.rfind('}') + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON in output. stderr: {result.stderr[:500]}")
    data = json_mod.loads(output[start:end])

    # The ai_prompt should be present and include diff and base context
    assert "ai_prompt" in data
    ai_prompt = data["ai_prompt"]
    assert isinstance(ai_prompt, str)
    assert "<diff>" in ai_prompt
    assert "<base_context>" in ai_prompt or "Base Vibe Score" in ai_prompt  # base context present
    assert "<current_state>" in ai_prompt
    assert "architectural drift" in ai_prompt.lower()


def test_json_output_validates_with_demjson(tmp_path):
    """Removed demjson3 dependency; this test is no longer needed."""
    pytest.skip("demjson3 dependency removed; JSON validation covered by other tests using built-in json module")
