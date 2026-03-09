import pytest
from ghostclaw.cli.formatters import TerminalFormatter
from typing import Dict, Any

@pytest.fixture
def mock_report() -> Dict[str, Any]:
    return {
        "vibe_score": 85,
        "stack": "Python",
        "files_analyzed": 10,
        "total_lines": 500,
        "issues": ["Issue 1"],
        "architectural_ghosts": ["Ghost 1"],
        "red_flags": ["Flag 1"],
        "errors": ["Error 1"],
        "ai_synthesis": "Overall looks fine.",
        "coupling_metrics": {"avg_ccn": 2.5, "avg_nd": 1.5}
    }

def test_terminal_formatter(mock_report):
    formatter = TerminalFormatter()
    result = formatter.format(mock_report)

    assert "🟢 Vibe Score: 85/100" in result
    assert "Stack: Python" in result
    assert "Files: 10, Lines: 500" in result
    assert "Metrics: Avg CCN: 2.5, Avg Nesting: 1.5" in result
    assert "Issue 1" in result
    assert "Ghost 1" in result
    assert "Flag 1" in result
    assert "Error 1" in result
    assert "Overall looks fine." in result
    assert "💡 Tip: Run with '--patch' to generate refactor suggestions" in result

def test_terminal_print(mock_report, capsys):
    formatter = TerminalFormatter()
    formatter.print_to_terminal(mock_report)

    captured = capsys.readouterr()
    assert "🟢 Vibe Score: 85/100" in captured.out
    assert "Stack: Python" in captured.out
