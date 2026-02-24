"""Core analyzer — orchestrates stack detection, metrics, and stack-specific analysis."""

import datetime
from pathlib import Path
from typing import Dict
from core.detector import detect_stack, find_files
from core.validator import RuleValidator
from stacks import get_analyzer


class CodebaseAnalyzer:
    """Main analyzer class that coordinates the full analysis pipeline."""

    def __init__(self, validator: RuleValidator = None):
        """
        Initialize the analyzer with optional injected dependencies.

        Args:
            validator: Rule engine to use (Phase 4)
        """
        self.validator = validator or RuleValidator()

    def analyze(self, root: str) -> Dict:
        """
        Perform a complete architectural analysis of a codebase.

        Args:
            root: Path to repository root

        Returns:
            Complete analysis report with vibe score, issues, ghosts, etc.
        """
        # 1. Detect stack
        stack = detect_stack(root)

        # 2. Find relevant files based on stack
        analyzer = get_analyzer(stack)
        extensions = analyzer.get_extensions() if analyzer else []
        files = find_files(root, extensions) if extensions else []

        # 3. Compute base metrics
        total_lines = 0
        large_files = []
        line_counts = []
        for f in files:
            try:
                with open(f, 'r', encoding='utf-8', errors='ignore') as file:
                    count = sum(1 for _ in file)
                    total_lines += count
                    line_counts.append(count)
                    if count > (analyzer.get_large_file_threshold() if analyzer else 300):
                        large_files.append(f)
            except Exception:
                continue

        total_files = len(files)
        avg_lines = sum(line_counts) / total_files if total_files > 0 else 0
        large_count = len(large_files)

        base_metrics = {
            "total_files": total_files,
            "total_lines": total_lines,
            "large_file_count": large_count,
            "average_lines": avg_lines,
            "vibe_score": 100  # Will be computed later
        }

        # 4. Stack-specific analysis
        if analyzer:
            stack_result = analyzer.analyze(root, files, base_metrics)
            issues = stack_result.get('issues', [])
            ghosts = stack_result.get('architectural_ghosts', [])
            flags = stack_result.get('red_flags', [])
            coupling_metrics = stack_result.get('coupling_metrics', {})
        else:
            issues = ["Cannot detect tech stack; no build files found"]
            ghosts = []
            flags = []
            coupling_metrics = {}

        # 5. Merge metrics for vibe score
        combined_metrics = {**base_metrics, "coupling_metrics": coupling_metrics}

        # 6. Apply rule validation (Phase 4)
        try:
            report_with_rules = self.validator.validate(stack, {
                "issues": issues,
                "architectural_ghosts": ghosts,
                "red_flags": flags,
                "coupling_metrics": coupling_metrics,
                "files_analyzed": total_files,
                "total_lines": total_lines,
                "stack": stack,
                **base_metrics
            })
            issues = report_with_rules['issues']
            ghosts = report_with_rules['architectural_ghosts']
            flags = report_with_rules['red_flags']
        except Exception as e:
            issues.append(f"Rule validation failed: {str(e)}")

        # 7. Compute final vibe score
        vibe_score = self._compute_vibe_score(base_metrics, len(issues), len(ghosts))

        # 8. Build final report
        report = {
            "vibe_score": vibe_score,
            "stack": stack,
            "files_analyzed": total_files,
            "total_lines": total_lines,
            "issues": issues,
            "architectural_ghosts": ghosts,
            "red_flags": flags,
            "metadata": {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat() + "Z",
                "analyzer": "ghostclaw-refactored",
                "version": "0.1.3",
                "coupling_enabled": True,
                "rules_enabled": True
            }
        }

        return report

    def _compute_vibe_score(self, metrics: Dict, issue_count: int, ghost_count: int) -> int:
        """Calculate the final vibe score (0-100)."""
        score = 100

        # Penalty for large files
        large_file_penalty = min(30, metrics['large_file_count'] * 5)
        score -= large_file_penalty

        # Penalty for high average lines
        avg = metrics.get('average_lines', 0)
        if avg > 200:
            score -= 10

        # Additional penalty for explicit issues
        score -= min(20, issue_count * 3)
        score -= min(15, ghost_count * 5)

        return max(0, min(100, score))
