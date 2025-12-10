"""
Unified Markdown Report Generator for Aspect Code Benchmarks

Generates comprehensive, human-readable .md reports containing:
- Side-by-side comparison of Baseline vs Aspect Code KB
- Detailed code changes for BOTH modes
- Test results with pass/fail details
- Smart regression analysis
- Aspect Code delta analysis
- Complete file diffs for both approaches
- Winner determination with analysis
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict, List
import json


@dataclass
class ModeResult:
    """Results for a single mode (baseline or aspect)."""
    mode: str
    timestamp: datetime
    
    # LLM Response
    llm_response: str = ""
    model_name: str = ""
    tokens_used: int = 0
    response_time_seconds: float = 0.0
    
    # Code Metrics
    code_metrics: Optional[dict] = None
    
    # Test Results
    tests_passed_before: int = 0
    tests_failed_before: int = 0
    tests_passed_after: int = 0
    tests_failed_after: int = 0
    
    # Post-test details (for error reporting)
    tests_total_after: int = 0
    post_test_stderr: str = ""
    post_test_exit_code: int = 0
    
    # Smart Regression
    regression_analysis: Optional[dict] = None
    
    # Aspect Delta
    aspect_delta: Optional[dict] = None
    
    # File diffs
    file_diffs: dict = field(default_factory=dict)
    files_modified: list = field(default_factory=list)
    
    # Verdict
    task_passed: bool = False
    regression_passed: bool = False
    
    @property
    def test_delta(self) -> int:
        return self.tests_passed_after - self.tests_passed_before
    
    @property
    def true_regressions(self) -> int:
        if self.regression_analysis:
            return len(self.regression_analysis.get('true_regressions', []))
        return 0
    
    @property
    def lines_added(self) -> int:
        if self.code_metrics:
            return self.code_metrics.get('lines_added', 0)
        return 0
    
    @property
    def lines_removed(self) -> int:
        if self.code_metrics:
            return self.code_metrics.get('lines_removed', 0)
        return 0
    
    @property
    def is_code_broken(self) -> bool:
        """True if the code changes broke the test runner (e.g., import errors)."""
        return self.tests_total_after == 0 and self.post_test_exit_code != 0
    
    @property
    def broken_code_error(self) -> str:
        """Extract the key error from stderr when code is broken."""
        if not self.is_code_broken or not self.post_test_stderr:
            return ""
        # Look for common error patterns
        lines = self.post_test_stderr.strip().split('\n')
        # Find the first line with "Error:" or similar
        for line in reversed(lines):
            if 'Error:' in line or 'error:' in line or line.startswith('E '):
                return line.strip()
        # Fall back to last non-empty line
        return lines[-1].strip() if lines else ""


@dataclass
class UnifiedExperimentData:
    """All data for a unified baseline vs aspect report."""
    experiment_id: str
    task_id: str
    task_description: str
    model_name: str
    temperature: float = 0.0
    
    baseline: Optional[ModeResult] = None
    aspect: Optional[ModeResult] = None
    
    # Prompts (shared or can differ)
    baseline_prompt: str = ""
    aspect_prompt: str = ""


def _fmt_int(val, default="N/A"):
    """Format integer or return default."""
    return str(val) if val is not None and val != "N/A" else default


def _fmt_delta(val, default="N/A"):
    """Format delta value with +/- sign."""
    if val is None or val == "N/A":
        return default
    return f"{val:+d}" if isinstance(val, int) else f"{val:+.2f}"


def _fmt_float(val, default="N/A"):
    """Format float or return default."""
    if val is None or val == "N/A":
        return default
    return f"{val:.2f}"


def _winner_emoji(baseline_val, aspect_val, lower_is_better=False) -> str:
    """Determine winner and return appropriate emoji."""
    if baseline_val == aspect_val:
        return "🤝 Tie"
    if lower_is_better:
        return "🏆 Baseline" if baseline_val < aspect_val else "🏆 Aspect"
    return "🏆 Baseline" if baseline_val > aspect_val else "🏆 Aspect"


def generate_unified_report(data: UnifiedExperimentData) -> str:
    """Generate a comprehensive unified markdown report comparing baseline vs aspect."""
    
    lines = []
    b = data.baseline
    o = data.aspect
    
    # =========================================================================
    # HEADER
    # =========================================================================
    lines.extend([
        f"# 📊 Benchmark Report: {data.task_id}",
        "",
        f"> **Task:** {data.task_description}",
        "",
        "| Property | Value |",
        "|----------|-------|",
        f"| Experiment ID | `{data.experiment_id}` |",
        f"| Model | `{data.model_name}` |",
        f"| Temperature | `{data.temperature}` |",
        f"| Generated | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |",
        "",
        "---",
        "",
    ])
    
    # =========================================================================
    # EXECUTIVE SUMMARY - THE WINNER
    # =========================================================================
    lines.extend([
        "## 🏆 Executive Summary",
        "",
    ])
    
    if b and o:
        # Determine winner
        b_score = 0
        o_score = 0
        
        # Test delta (more is better)
        if b.test_delta > o.test_delta:
            b_score += 2
        elif o.test_delta > b.test_delta:
            o_score += 2
        
        # True regressions (fewer is better)
        if b.true_regressions < o.true_regressions:
            b_score += 1
        elif o.true_regressions < b.true_regressions:
            o_score += 1
        
        # Task passed
        if b.task_passed and not o.task_passed:
            b_score += 2
        elif o.task_passed and not b.task_passed:
            o_score += 2
        
        if b_score > o_score:
            winner = "🏆 **BASELINE WINS**"
            winner_reason = "Better test results"
        elif o_score > b_score:
            winner = "🏆 **Aspect WINS**"
            winner_reason = "Better test results"
        else:
            winner = "🤝 **TIE**"
            winner_reason = "Both performed equally"
        
        lines.extend([
            f"### {winner}",
            f"_{winner_reason}_",
            "",
            "| Metric | Baseline | Aspect | Winner |",
            "|--------|:--------:|:-----------:|:------:|",
            f"| Tests Fixed | **{b.test_delta:+d}** | **{o.test_delta:+d}** | {_winner_emoji(b.test_delta, o.test_delta)} |",
            f"| All Tests Pass | {'✅' if b.task_passed else '❌'} | {'✅' if o.task_passed else '❌'} | {_winner_emoji(1 if b.task_passed else 0, 1 if o.task_passed else 0)} |",
            f"| True Regressions | {b.true_regressions} | {o.true_regressions} | {_winner_emoji(b.true_regressions, o.true_regressions, lower_is_better=True)} |",
            f"| Lines Added | +{b.lines_added} | +{o.lines_added} | — |",
            f"| Lines Removed | -{b.lines_removed} | -{o.lines_removed} | — |",
            f"| Response Time | {b.response_time_seconds:.1f}s | {o.response_time_seconds:.1f}s | {_winner_emoji(b.response_time_seconds, o.response_time_seconds, lower_is_better=True)} |",
            "",
        ])
    else:
        lines.extend([
            "_Only one mode was run. No comparison available._",
            "",
        ])
    
    lines.extend([
        "---",
        "",
    ])
    
    # =========================================================================
    # DETAILED COMPARISON TABLE
    # =========================================================================
    lines.extend([
        "## 📈 Detailed Comparison",
        "",
    ])
    
    if b and o:
        # Check for broken code
        broken_warning = []
        if b.is_code_broken:
            broken_warning.append(f"> ⚠️ **BASELINE CODE BROKEN**: Tests couldn't run due to code errors")
            if b.broken_code_error:
                broken_warning.append(f"> `{b.broken_code_error}`")
            broken_warning.append("")
        if o.is_code_broken:
            broken_warning.append(f"> ⚠️ **Aspect CODE BROKEN**: Tests couldn't run due to code errors")
            if o.broken_code_error:
                broken_warning.append(f"> `{o.broken_code_error}`")
            broken_warning.append("")
        
        if broken_warning:
            lines.extend(broken_warning)
        
        lines.extend([
            "### Test Results",
            "",
            "| Metric | Baseline | Aspect |",
            "|--------|:--------:|:-----------:|",
            f"| Tests Before | {b.tests_passed_before} passed, {b.tests_failed_before} failed | {o.tests_passed_before} passed, {o.tests_failed_before} failed |",
        ])
        
        # Test After line with special handling for broken code
        b_after = f"{b.tests_passed_after} passed, {b.tests_failed_after} failed"
        o_after = f"{o.tests_passed_after} passed, {o.tests_failed_after} failed"
        if b.is_code_broken:
            b_after = "⚠️ **CODE BROKEN** (0 tests ran)"
        if o.is_code_broken:
            o_after = "⚠️ **CODE BROKEN** (0 tests ran)"
        
        lines.extend([
            f"| Tests After | {b_after} | {o_after} |",
            f"| **Delta** | **{b.test_delta:+d}** | **{o.test_delta:+d}** |",
            f"| Verdict | {'✅ PASS' if b.task_passed else '❌ FAIL'} | {'✅ PASS' if o.task_passed else '❌ FAIL'} |",
            "",
        ])
        
        # Show full error details for broken code
        if b.is_code_broken or o.is_code_broken:
            lines.extend([
                "### ⚠️ Broken Code Details",
                "",
            ])
            if b.is_code_broken and b.post_test_stderr:
                lines.extend([
                    "**Baseline Error:**",
                    "",
                    "```",
                    b.post_test_stderr[:2000],
                    "```",
                    "",
                ])
            if o.is_code_broken and o.post_test_stderr:
                lines.extend([
                    "**Aspect Error:**",
                    "",
                    "```",
                    o.post_test_stderr[:2000],
                    "```",
                    "",
                ])
        
        # Code Metrics Comparison
        lines.extend([
            "### Code Metrics",
            "",
            "| Metric | Baseline | Aspect |",
            "|--------|:--------:|:-----------:|",
        ])
        
        b_cm = b.code_metrics or {}
        o_cm = o.code_metrics or {}
        
        lines.extend([
            f"| Files Modified | {b_cm.get('files_changed', 'N/A')} | {o_cm.get('files_changed', 'N/A')} |",
            f"| Lines Added | +{b_cm.get('lines_added', 0)} | +{o_cm.get('lines_added', 0)} |",
            f"| Lines Removed | -{b_cm.get('lines_removed', 0)} | -{o_cm.get('lines_removed', 0)} |",
            f"| Net Change | {b_cm.get('lines_added', 0) - b_cm.get('lines_removed', 0):+d} | {o_cm.get('lines_added', 0) - o_cm.get('lines_removed', 0):+d} |",
            f"| Functions Δ | {_fmt_delta(b_cm.get('functions_delta'))} | {_fmt_delta(o_cm.get('functions_delta'))} |",
            f"| Classes Δ | {_fmt_delta(b_cm.get('classes_delta'))} | {_fmt_delta(o_cm.get('classes_delta'))} |",
            "",
        ])
        
        # Regression Analysis Comparison
        lines.extend([
            "### Regression Analysis",
            "",
            "| Metric | Baseline | Aspect |",
            "|--------|:--------:|:-----------:|",
            f"| True Regressions | {b.true_regressions} | {o.true_regressions} |",
        ])
        
        b_ra = b.regression_analysis or {}
        o_ra = o.regression_analysis or {}
        b_expected = len(b_ra.get('expected_failures', []))
        o_expected = len(o_ra.get('expected_failures', []))
        
        lines.extend([
            f"| Expected Failures | {b_expected} | {o_expected} |",
            f"| Clean Run | {'✅' if b_ra.get('is_clean', True) else '❌'} | {'✅' if o_ra.get('is_clean', True) else '❌'} |",
            "",
        ])
        
        # Aspect Findings
        if b.aspect_delta or o.aspect_delta:
            lines.extend([
                "### Code Quality (Aspect Findings)",
                "",
                "| Metric | Baseline | Aspect |",
                "|--------|:--------:|:-----------:|",
            ])
            
            b_od = b.aspect_delta or {}
            o_od = o.aspect_delta or {}
            
            lines.extend([
                f"| Findings Before | {b_od.get('total_before', 0)} | {o_od.get('total_before', 0)} |",
                f"| Findings After | {b_od.get('total_after', 0)} | {o_od.get('total_after', 0)} |",
                f"| Issues Introduced | {len(b_od.get('new_findings', []))} | {len(o_od.get('new_findings', []))} |",
                f"| Issues Fixed | {len(b_od.get('resolved_findings', []))} | {len(o_od.get('resolved_findings', []))} |",
                "",
            ])
    
    lines.extend([
        "---",
        "",
    ])
    
    # =========================================================================
    # BASELINE CODE CHANGES (FULL DETAIL)
    # =========================================================================
    if b:
        lines.extend([
            "## 📝 Baseline: Code Changes",
            "",
        ])
        
        # Modified files list
        if b.code_metrics and b.code_metrics.get('modified_files'):
            lines.extend([
                "### Files Modified",
                "",
            ])
            for f in b.code_metrics['modified_files']:
                lines.append(f"- `{f['path']}` (+{f.get('lines_added', 0)} / -{f.get('lines_removed', 0)})")
            lines.append("")
        
        # Full diffs
        if b.file_diffs:
            lines.extend([
                "### Full Diffs",
                "",
            ])
            for filepath, diff in b.file_diffs.items():
                lines.extend([
                    f"#### `{filepath}`",
                    "",
                    "<details>",
                    "<summary>Click to expand diff</summary>",
                    "",
                    "```diff",
                    diff,
                    "```",
                    "",
                    "</details>",
                    "",
                ])
        
        lines.extend([
            "---",
            "",
        ])
    
    # =========================================================================
    # Aspect CODE CHANGES (FULL DETAIL)
    # =========================================================================
    if o:
        lines.extend([
            "## 📝 Aspect: Code Changes",
            "",
        ])
        
        # Modified files list
        if o.code_metrics and o.code_metrics.get('modified_files'):
            lines.extend([
                "### Files Modified",
                "",
            ])
            for f in o.code_metrics['modified_files']:
                lines.append(f"- `{f['path']}` (+{f.get('lines_added', 0)} / -{f.get('lines_removed', 0)})")
            lines.append("")
        
        # Full diffs
        if o.file_diffs:
            lines.extend([
                "### Full Diffs",
                "",
            ])
            for filepath, diff in o.file_diffs.items():
                lines.extend([
                    f"#### `{filepath}`",
                    "",
                    "<details>",
                    "<summary>Click to expand diff</summary>",
                    "",
                    "```diff",
                    diff,
                    "```",
                    "",
                    "</details>",
                    "",
                ])
        
        lines.extend([
            "---",
            "",
        ])
    
    # =========================================================================
    # LLM RESPONSES
    # =========================================================================
    lines.extend([
        "## 🤖 LLM Responses",
        "",
    ])
    
    if b:
        lines.extend([
            "### Baseline Response",
            "",
            "<details>",
            "<summary>Click to expand (~{} chars)</summary>".format(len(b.llm_response)),
            "",
            "```",
            b.llm_response[:8000] if b.llm_response else "(No response)",
            "```",
            "",
            "</details>",
            "",
        ])
    
    if o:
        lines.extend([
            "### Aspect Response",
            "",
            "<details>",
            "<summary>Click to expand (~{} chars)</summary>".format(len(o.llm_response)),
            "",
            "```",
            o.llm_response[:8000] if o.llm_response else "(No response)",
            "```",
            "",
            "</details>",
            "",
        ])
    
    lines.extend([
        "---",
        "",
    ])
    
    # =========================================================================
    # PROMPTS USED
    # =========================================================================
    lines.extend([
        "## 💬 Prompts Used",
        "",
    ])
    
    if data.baseline_prompt:
        lines.extend([
            "### Baseline Prompt",
            "",
            "<details>",
            "<summary>Click to expand</summary>",
            "",
            "```",
            data.baseline_prompt[:5000],
            "```",
            "",
            "</details>",
            "",
        ])
    
    if data.aspect_prompt:
        lines.extend([
            "### Aspect Prompt",
            "",
            "<details>",
            "<summary>Click to expand</summary>",
            "",
            "```",
            data.aspect_prompt[:5000],
            "```",
            "",
            "</details>",
            "",
        ])
    
    lines.extend([
        "---",
        "",
    ])
    
    # =========================================================================
    # PERFORMANCE STATS
    # =========================================================================
    lines.extend([
        "## ⏱️ Performance",
        "",
    ])
    
    if b and o:
        lines.extend([
            "| Metric | Baseline | Aspect |",
            "|--------|:--------:|:-----------:|",
            f"| Response Time | {b.response_time_seconds:.2f}s | {o.response_time_seconds:.2f}s |",
            f"| Tokens (approx) | ~{b.tokens_used:,} | ~{o.tokens_used:,} |",
            f"| Response Length | {len(b.llm_response):,} chars | {len(o.llm_response):,} chars |",
            "",
        ])
    
    # =========================================================================
    # FOOTER
    # =========================================================================
    lines.extend([
        "---",
        "",
        f"_Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
    ])
    
    return "\n".join(lines)


def save_unified_report(data: UnifiedExperimentData, output_dir: Path) -> Path:
    """Generate and save a unified markdown report."""
    report_content = generate_unified_report(data)
    
    # Create filename - single file for both modes
    filename = f"{data.task_id}_{data.experiment_id}.md"
    output_path = output_dir / filename
    
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_content, encoding='utf-8')
    
    return output_path


# =========================================================================
# LEGACY SUPPORT - Keep old functions for backwards compatibility
# =========================================================================

@dataclass
class ExperimentData:
    """Legacy: All data needed to generate a single-mode report."""
    experiment_id: str
    task_id: str
    mode: str
    timestamp: datetime
    
    system_prompt: str = ""
    user_prompt: str = ""
    llm_response: str = ""
    model_name: str = ""
    tokens_used: int = 0
    response_time_seconds: float = 0.0
    code_metrics: Optional[dict] = None
    test_output_before: str = ""
    test_output_after: str = ""
    tests_passed_before: int = 0
    tests_failed_before: int = 0
    tests_passed_after: int = 0
    tests_failed_after: int = 0
    regression_analysis: Optional[dict] = None
    aspect_delta: Optional[dict] = None
    file_diffs: dict = field(default_factory=dict)
    task_passed: bool = False
    regression_passed: bool = False
    overall_verdict: str = "UNKNOWN"


def generate_report(data: ExperimentData) -> str:
    """Legacy: Generate a single-mode report (kept for backwards compatibility)."""
    # Convert to ModeResult and use unified generator
    mode_result = ModeResult(
        mode=data.mode,
        timestamp=data.timestamp,
        llm_response=data.llm_response,
        model_name=data.model_name,
        tokens_used=data.tokens_used,
        response_time_seconds=data.response_time_seconds,
        code_metrics=data.code_metrics,
        tests_passed_before=data.tests_passed_before,
        tests_failed_before=data.tests_failed_before,
        tests_passed_after=data.tests_passed_after,
        tests_failed_after=data.tests_failed_after,
        regression_analysis=data.regression_analysis,
        aspect_delta=data.aspect_delta,
        file_diffs=data.file_diffs,
        task_passed=data.task_passed,
        regression_passed=data.regression_passed,
    )
    
    unified = UnifiedExperimentData(
        experiment_id=data.experiment_id,
        task_id=data.task_id,
        task_description=data.task_id,
        model_name=data.model_name,
    )
    
    if data.mode == "baseline":
        unified.baseline = mode_result
        unified.baseline_prompt = data.user_prompt
    else:
        unified.aspect = mode_result
        unified.aspect_prompt = data.user_prompt
    
    return generate_unified_report(unified)


def save_report(data: ExperimentData, output_dir: Path) -> Path:
    """Legacy: Save a single-mode report."""
    report_content = generate_report(data)
    filename = f"{data.task_id}_{data.mode}_{data.timestamp.strftime('%Y%m%d_%H%M%S')}.md"
    output_path = output_dir / filename
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_content, encoding='utf-8')
    return output_path


def generate_summary_report(experiments: list, output_dir: Path) -> Path:
    """Generate a summary report for multiple experiments."""
    lines = [
        "# Aspect Code Benchmark Summary Report",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Total Experiments:** {len(experiments)}",
        "",
        "---",
        "",
    ]
    
    report_content = "\n".join(lines)
    output_path = output_dir / "SUMMARY.md"
    output_path.write_text(report_content, encoding='utf-8')
    return output_path


if __name__ == "__main__":
    # Demo with unified report
    from datetime import datetime
    
    baseline = ModeResult(
        mode="baseline",
        timestamp=datetime.now(),
        tests_passed_before=19,
        tests_failed_before=13,
        tests_passed_after=32,
        tests_failed_after=0,
        task_passed=True,
        regression_passed=True,
        response_time_seconds=45.2,
        tokens_used=5467,
        llm_response="Sample baseline response...",
        code_metrics={
            "files_changed": 4,
            "lines_added": 168,
            "lines_removed": 4,
            "functions_delta": 4,
            "classes_delta": 0,
            "modified_files": [
                {"path": "app/models.py", "lines_added": 44, "lines_removed": 2}
            ]
        },
        file_diffs={"app/models.py": "+ new code\n- old code"},
    )
    
    aspect_result = ModeResult(
        mode="aspect",
        timestamp=datetime.now(),
        tests_passed_before=19,
        tests_failed_before=13,
        tests_passed_after=29,
        tests_failed_after=3,
        task_passed=False,
        regression_passed=True,
        response_time_seconds=52.1,
        tokens_used=5443,
        llm_response="Sample aspect response...",
        code_metrics={
            "files_changed": 4,
            "lines_added": 232,
            "lines_removed": 80,
            "functions_delta": 4,
            "classes_delta": 1,
            "modified_files": [
                {"path": "app/models.py", "lines_added": 51, "lines_removed": 8}
            ]
        },
        file_diffs={"app/models.py": "+ new code\n- old code"},
    )
    
    demo_data = UnifiedExperimentData(
        experiment_id="demo_20251128",
        task_id="stronger-password-policy",
        task_description="Implement stronger password validation with 12+ chars, uppercase, lowercase, digit, and special char requirements",
        model_name="claude-sonnet-4-20250514",
        baseline=baseline,
        aspect=aspect_result,
        baseline_prompt="You are an expert...",
        aspect_prompt="You are an expert with Aspect...",
    )
    
    print(generate_unified_report(demo_data))
