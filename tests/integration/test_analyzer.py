import sys
from pathlib import Path

# Add repo root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import asyncio
import pytest
from ghostclaw.core.analyzer import CodebaseAnalyzer


@pytest.mark.asyncio
async def test_analyze_node_repo(tmp_path):
    # Setup Node repo with large files
    (tmp_path / "package.json").write_text('{"name": "test"}')
    # Create a file with 600 lines + nested logic for Lizard
    content = "function ghost() {\n"
    for i in range(10):
        content += "  " * (i + 1) + f"if (x == {i}) {{\n"
    content += "  " * 12 + "console.log('deep');\n"
    for i in range(10):
        content += "  " * (10 - i) + "}\n"
    content += "\n".join(["// padding"] * 600) + "\n}"
    (tmp_path / "index.js").write_text(content)

    analyzer = CodebaseAnalyzer()
    report_model = await analyzer.analyze(str(tmp_path))
    report = report_model.model_dump()

    assert report["stack"] == "node"
    assert report["files_analyzed"] >= 1
    assert report["vibe_score"] < 100  # Should penalize large file
    assert any("files >400 lines" in i for i in report["issues"])


@pytest.mark.asyncio
async def test_analyze_python_repo_with_circular_imports(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test'")
    (tmp_path / "a.py").write_text("from b import x\n")
    (tmp_path / "b.py").write_text("from a import y\n")

    analyzer = CodebaseAnalyzer()
    report_model = await analyzer.analyze(str(tmp_path))
    report = report_model.model_dump()

    assert report["stack"] == "python"
    assert any("Circular dependency" in i for i in report["issues"])


@pytest.mark.asyncio
async def test_analyze_unknown_stack(tmp_path):
    # Empty dir
    analyzer = CodebaseAnalyzer()
    report_model = await analyzer.analyze(str(tmp_path))
    report = report_model.model_dump()
    assert report["stack"] == "unknown"
    # The exact issue message may vary; just check that we got some issue
    assert len(report["issues"]) > 0
