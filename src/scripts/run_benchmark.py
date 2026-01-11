#!/usr/bin/env python3
"""
run_benchmark.py - Run A/B benchmark comparing baseline vs aspect prompts.

Compares baseline (no KB) vs aspect (with knowledge base content) across all tasks.

Usage:
    python run_benchmark.py --repo fastapi-template --provider anthropic
    python run_benchmark.py --repo djangopackages --provider anthropic
    python run_benchmark.py --all-repos --provider anthropic
    python run_benchmark.py --repo fastapi-template --tasks task_001  # Single task test
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# Add scripts dir to path for imports
SCRIPT_DIR = Path(__file__).parent
HARNESS_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from load_task_defs import get_repo_prompts_dir, get_repo_root, list_tasks  # noqa: E402

# Configuration
LLM_TEMPERATURE = 0.0  # Use 0 for reproducibility
DEFAULT_MODES = ["baseline", "aspect"]  # Default A/B modes to compare

# Try to import LLM clients
try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import openai

    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


def get_results_dir() -> Path:
    """Get the results directory."""
    results_dir = HARNESS_DIR / "results"
    results_dir.mkdir(exist_ok=True)
    return results_dir


def get_responses_dir() -> Path:
    """Get the responses directory for saving LLM responses."""
    responses_dir = HARNESS_DIR / "responses"
    responses_dir.mkdir(exist_ok=True)
    return responses_dir


def reset_repo(repo_name: str) -> bool:
    """Reset repository to clean state using git checkout and clean."""
    repo_root = get_repo_root(repo_name)
    if not repo_root or not repo_root.exists():
        print(f"  ✗ Repository not found: {repo_root}")
        return False

    try:
        subprocess.run(
            ["git", "checkout", "."], cwd=repo_root, check=True, capture_output=True, text=True
        )
        subprocess.run(
            ["git", "clean", "-fd"], cwd=repo_root, check=True, capture_output=True, text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to reset repo: {e}")
        return False


def run_tests(task_id: str, repo_name: str, with_regression: bool = False) -> dict[str, Any]:
    """Run tests for a task and return structured results."""
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "run_tests_for_task.py"),
        "--repo",
        repo_name,
        "--task-id",
        task_id,
        "--capture",
    ]
    if with_regression:
        cmd.append("--with-regression")

    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start

    # Parse test counts from pytest output
    tests_passed = 0
    tests_failed = 0
    stdout = result.stdout

    # Look for pytest summary
    import re

    passed_match = re.search(r"(\d+)\s+passed", stdout)
    failed_match = re.search(r"(\d+)\s+failed", stdout)
    if passed_match:
        tests_passed = int(passed_match.group(1))
    if failed_match:
        tests_failed = int(failed_match.group(1))

    return {
        "passed": result.returncode == 0,
        "exit_code": result.returncode,
        "elapsed_seconds": round(elapsed, 2),
        "stdout": stdout[-5000:] if len(stdout) > 5000 else stdout,
        "stderr": result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr,
        "tests_passed": tests_passed,
        "tests_failed": tests_failed,
        "tests_total": tests_passed + tests_failed,
    }


def load_prompt(task_id: str, repo_name: str, mode: str = "aspect") -> str | None:
    """Load a prompt file for a task."""
    prompts_dir = get_repo_prompts_dir(repo_name)
    prompt_file = prompts_dir / f"{task_id}_{mode}.txt"

    if prompt_file.exists():
        with open(prompt_file, encoding="utf-8") as f:
            return f.read()

    print(
        f"  ✗ Missing prompt file: {prompt_file}\n"
        "    Generate prompts first:\n"
        "      python src/scripts/generate_prompts.py\n"
        "    (This repo does not commit generated prompt .txt files.)"
    )
    return None


def call_claude(prompt: str, api_key: str, model: str = "claude-sonnet-4-20250514") -> str:
    """Call Claude API and return the response text."""
    if not HAS_ANTHROPIC:
        raise ImportError("anthropic package not installed. Run: pip install anthropic")

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=model,
        max_tokens=16000,
        temperature=LLM_TEMPERATURE,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


def call_openai(prompt: str, api_key: str, model: str = "gpt-4o") -> str:
    """Call OpenAI API and return the response text."""
    if not HAS_OPENAI:
        raise ImportError("openai package not installed. Run: pip install openai")

    client = openai.OpenAI(api_key=api_key)

    response = client.chat.completions.create(
        model=model,
        max_tokens=8000,
        temperature=LLM_TEMPERATURE,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content


def count_code_lines(text: str) -> int:
    """Count non-empty, non-comment lines in code."""
    lines = text.split("\n")
    count = 0
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("//"):
            count += 1
    return count


def extract_code_blocks(response: str) -> list[dict[str, str]]:
    """Extract code blocks with filepath headers from LLM response."""
    blocks = []
    pattern = r"```(\w+)?\s*\n(.*?)```"
    matches = re.findall(pattern, response, re.DOTALL)

    for lang, content in matches:
        lang = lang or ""
        lines = content.split("\n")

        filepath = None
        code_lines = []

        for i, line in enumerate(lines):
            if i < 3:
                filepath_match = re.match(
                    r"^\s*(?:#|//|/\*)\s*filepath:\s*(.+?)\s*(?:\*/)?$", line, re.IGNORECASE
                )
                if filepath_match:
                    filepath = filepath_match.group(1).strip()
                    continue
            code_lines.append(line)

        code = "\n".join(code_lines).strip()
        if code:
            blocks.append(
                {
                    "language": lang,
                    "file": filepath,
                    "code": code,
                    "line_count": count_code_lines(code),
                }
            )

    return blocks


def apply_code_blocks(blocks: list[dict[str, str]], repo_name: str) -> list[str]:
    """Apply code blocks to repository files."""
    repo_root = get_repo_root(repo_name)
    modified_files = []

    for block in blocks:
        filepath = block.get("file")
        if not filepath:
            continue

        filepath = filepath.replace("\\", "/")
        if filepath.startswith("./"):
            filepath = filepath[2:]

        target = repo_root / filepath

        if not target.parent.exists():
            alt_target = repo_root / "backend" / filepath
            if alt_target.parent.exists() or filepath.startswith("app/"):
                target = alt_target

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(block["code"], encoding="utf-8")
            modified_files.append(str(filepath))
        except Exception as e:
            print(f"    ✗ Failed to write {filepath}: {e}")

    return modified_files


def run_single_task(
    task_id: str,
    repo_name: str,
    mode: str,
    api_key: str,
    provider: str = "anthropic",
    model: str | None = None,
    experiment_id: str | None = None,
) -> dict[str, Any]:
    """Run a single task with specified prompt mode."""
    timestamp = datetime.now()
    exp_id = experiment_id or timestamp.strftime("%Y%m%d_%H%M%S")

    result = {
        "task_id": task_id,
        "repo": repo_name,
        "mode": mode,
        "provider": provider,
        "model": model,
        "timestamp": timestamp.isoformat(),
        "experiment_id": exp_id,
        "pre_test": None,
        "llm_response": "",
        "llm_response_length": 0,
        "llm_response_code_lines": 0,
        "lines_added_to_repo": 0,
        "code_blocks_extracted": 0,
        "files_modified": [],
        "post_test": None,
        "tests_fixed": 0,
        "success": False,
        "error": None,
    }

    try:
        # Step 1: Reset repo
        print("    Resetting repository...")
        if not reset_repo(repo_name):
            result["error"] = "Failed to reset repository"
            return result

        # Step 2: Run pre-tests
        print("    Running pre-tests...")
        result["pre_test"] = run_tests(task_id, repo_name)

        # Step 3: Load prompt
        print(f"    Loading {mode} prompt...")
        prompt = load_prompt(task_id, repo_name, mode)
        if not prompt:
            result["error"] = f"Failed to load {mode} prompt"
            return result

        # Step 4: Call LLM
        print(f"    Calling {provider} API ({model})...")
        start_time = time.time()

        if provider == "anthropic":
            response = call_claude(prompt, api_key, model or "claude-sonnet-4-20250514")
        else:
            response = call_openai(prompt, api_key, model or "gpt-4o")

        elapsed = time.time() - start_time
        result["llm_response"] = response
        result["llm_response_length"] = len(response)
        result["llm_time_seconds"] = round(elapsed, 2)

        print(f"    Response received ({len(response)} chars, {elapsed:.1f}s)")

        # Save response to file
        responses_dir = get_responses_dir()
        response_file = responses_dir / f"{repo_name}_{task_id}_{mode}_{exp_id}.txt"
        response_file.write_text(response, encoding="utf-8")

        # Step 5: Extract and apply code
        print("    Extracting code blocks...")
        blocks = extract_code_blocks(response)
        result["code_blocks_extracted"] = len(blocks)

        # Calculate code line metrics
        total_code_lines = sum(b.get("line_count", 0) for b in blocks)
        result["llm_response_code_lines"] = total_code_lines

        blocks_with_files = [b for b in blocks if b.get("file")]
        lines_to_add = sum(b.get("line_count", 0) for b in blocks_with_files)
        result["lines_added_to_repo"] = lines_to_add

        print(f"    Found {len(blocks)} code blocks, {len(blocks_with_files)} with filepaths")
        print(f"    Code lines in response: {total_code_lines}, lines to add: {lines_to_add}")

        if not blocks_with_files:
            result["error"] = "No code blocks with filepath extracted"
            return result

        print(f"    Applying {len(blocks_with_files)} code blocks...")
        result["files_modified"] = apply_code_blocks(blocks_with_files, repo_name)

        # Step 6: Run post-tests
        print("    Running post-tests...")
        result["post_test"] = run_tests(task_id, repo_name)

        # Determine success
        result["success"] = result["post_test"]["passed"]

        # Print summary
        pre = result["pre_test"]
        post = result["post_test"]
        tests_fixed = post["tests_passed"] - pre["tests_passed"]
        result["tests_fixed"] = tests_fixed

        print(f"    Pre:  {pre['tests_passed']} passed, {pre['tests_failed']} failed")
        print(f"    Post: {post['tests_passed']} passed, {post['tests_failed']} failed")
        if tests_fixed > 0:
            print(f"    ✅ +{tests_fixed} tests now passing")
        elif tests_fixed < 0:
            print(f"    ❌ {tests_fixed} tests regressed")

    except Exception as e:
        result["error"] = str(e)
        print(f"    ✗ Error: {e}")
        import traceback

        traceback.print_exc()

    return result


def run_aspect_experiment(
    repos: list[str],
    api_key: str,
    provider: str = "anthropic",
    model: str | None = None,
    task_ids: list[str] | None = None,
    modes: list[str] | None = None,
) -> dict[str, Any]:
    """Run an experiment across repos for one or more prompt modes."""
    modes = modes or DEFAULT_MODES
    experiment_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = model or ("claude-sonnet-4-20250514" if provider == "anthropic" else "gpt-4o")

    results = {
        "experiment_id": experiment_id,
        "repos": repos,
        "provider": provider,
        "model": model_name,
        "temperature": LLM_TEMPERATURE,
        "modes": modes,
        "started_at": datetime.now().isoformat(),
        "tasks": [],
        "summary": {mode: {"total": 0, "passed": 0, "failed": 0, "errors": 0} for mode in modes},
        "output_stats": {mode: {"tokens": 0, "code_lines": 0, "lines_added": 0} for mode in modes},
        "test_improvements": {mode: 0 for mode in modes},
        "true_regressions": {mode: 0 for mode in modes},
    }

    print("\n" + "=" * 75)
    print("ASPECT CODE A/B BENCHMARK EXPERIMENT")
    print("=" * 75)
    print(f"Experiment ID: {experiment_id}")
    print(f"Repositories:  {', '.join(repos)}")
    print(f"Provider:      {provider}")
    print(f"Model:         {model_name}")
    print(f"Temperature:   {LLM_TEMPERATURE}")
    print(f"Modes:         {' vs '.join(modes)}")
    print("=" * 75)

    all_tasks_to_run = []
    for repo_name in repos:
        repo_tasks = list_tasks(repo_name)
        if task_ids:
            repo_tasks = [t for t in repo_tasks if t.get("id") in task_ids]
        for task in repo_tasks:
            all_tasks_to_run.append((repo_name, task))

    print(f"Total tasks:   {len(all_tasks_to_run)}")
    print("=" * 75)

    for i, (repo_name, task) in enumerate(all_tasks_to_run):
        task_id = task.get("id")
        task_name = task.get("name", task_id)

        print(f"\n{'─' * 75}")
        print(f"[{i + 1}/{len(all_tasks_to_run)}] {repo_name} / {task_name}")
        print(f"        ID: {task_id}")
        print("─" * 75)

        task_results = {"task_id": task_id, "task_name": task_name, "repo": repo_name}

        for mode in modes:
            print(f"\n  [{mode.upper()}]")

            task_result = run_single_task(
                task_id=task_id,
                repo_name=repo_name,
                mode=mode,
                api_key=api_key,
                provider=provider,
                model=model,
                experiment_id=experiment_id,
            )

            task_results[mode] = task_result

            # Update summary counts
            results["summary"][mode]["total"] += 1
            if task_result.get("error"):
                results["summary"][mode]["errors"] += 1
                status = f"ERROR: {task_result['error'][:50]}"
            elif task_result.get("success"):
                results["summary"][mode]["passed"] += 1
                status = "✅ PASSED"
            else:
                results["summary"][mode]["failed"] += 1
                status = "❌ FAILED"

            # Update output stats
            results["output_stats"][mode]["tokens"] += task_result.get("llm_response_length", 0)
            results["output_stats"][mode]["code_lines"] += task_result.get(
                "llm_response_code_lines", 0
            )
            results["output_stats"][mode]["lines_added"] += task_result.get(
                "lines_added_to_repo", 0
            )

            # Update test improvements
            tests_fixed = task_result.get("tests_fixed", 0)
            results["test_improvements"][mode] += tests_fixed
            if tests_fixed < 0:
                results["true_regressions"][mode] += 1

            # Print per-mode status
            pre_test = task_result.get("pre_test", {})
            post_test = task_result.get("post_test", {})
            pre_passed = pre_test.get("tests_passed", 0)
            pre_failed = pre_test.get("tests_failed", 0)
            post_passed = post_test.get("tests_passed", 0) if post_test else 0
            post_failed = post_test.get("tests_failed", 0) if post_test else 0

            print(f"    Pre:  {pre_passed} passed, {pre_failed} failed")
            if post_test:
                print(f"    Post: {post_passed} passed, {post_failed} failed")
                if tests_fixed > 0:
                    print(f"    ✅ +{tests_fixed} tests now passing")
                elif tests_fixed < 0:
                    print(f"    ❌ {tests_fixed} tests regressed")
            print(f"    Status: {status}")
            if task_result.get("files_modified"):
                files_list = task_result["files_modified"][:3]
                print(f"    Files:  {', '.join(files_list)}")

        results["tasks"].append(task_results)

    results["finished_at"] = datetime.now().isoformat()

    # Calculate elapsed time
    start = datetime.fromisoformat(results["started_at"])
    end = datetime.fromisoformat(results["finished_at"])
    results["total_elapsed_seconds"] = round((end - start).total_seconds(), 2)

    # Save results
    # Keep legacy name only for the default A/B run to avoid breaking existing tooling.
    if modes == DEFAULT_MODES:
        results_file = get_results_dir() / f"aspect_ab_experiment_{experiment_id}.json"
    else:
        results_file = get_results_dir() / f"benchmark_experiment_{experiment_id}.json"
    results_file.write_text(json.dumps(results, indent=2), encoding="utf-8")

    # Print summary
    print("\n" + "=" * 75)
    print("EXPERIMENT SUMMARY")
    print("=" * 75)
    print(f"Experiment ID:  {experiment_id}")
    print(f"Total tasks:    {len(all_tasks_to_run)}")
    print(f"Total time:     {results['total_elapsed_seconds']:.2f} seconds")
    print()
    print(
        f"{'Mode':<15} {'Tasks OK':<10} {'Failed':<10} {'Errors':<10} {'Tests Fixed':<12} {'True Reg.':<10}"
    )
    print("-" * 75)
    for mode in modes:
        s = results["summary"][mode]
        tests_fixed = results["test_improvements"][mode]
        true_reg = results["true_regressions"][mode]
        tests_str = f"+{tests_fixed}" if tests_fixed >= 0 else str(tests_fixed)
        print(
            f"{mode:<15} {s['passed']:<10} {s['failed']:<10} {s['errors']:<10} {tests_str:<12} {true_reg:<10}"
        )
    print("-" * 75)

    # Output stats
    print()
    print("📈 OUTPUT STATISTICS:")
    print()
    print(f"{'Mode':<20} {'Chars':>12} {'Code Lines':>12} {'Lines Added':>12}")
    print("-" * 60)
    for mode in modes:
        out = results["output_stats"][mode]
        print(f"{mode:<20} {out['tokens']:>12,} {out['code_lines']:>12,} {out['lines_added']:>12,}")
    print("-" * 60)

    # Only show a delta comparison when the default A/B modes are used.
    if modes == DEFAULT_MODES:
        baseline_tests_fixed = results["test_improvements"]["baseline"]
        aspect_tests_fixed = results["test_improvements"]["aspect"]
        baseline_true_regressions = results["true_regressions"]["baseline"]
        aspect_true_regressions = results["true_regressions"]["aspect"]

        print()
        print("📊 COMPARISON:")
        print()
        print("  Test Improvements:")
        print(f"    Baseline fixed:     {baseline_tests_fixed:+d} tests")
        print(f"    Aspect fixed:       {aspect_tests_fixed:+d} tests")
        if baseline_tests_fixed > 0:
            improvement = ((aspect_tests_fixed - baseline_tests_fixed) / baseline_tests_fixed) * 100
            print(f"    Aspect advantage:   {improvement:+.1f}%")
        elif aspect_tests_fixed > baseline_tests_fixed:
            print(
                f"    Aspect advantage:   +{aspect_tests_fixed - baseline_tests_fixed} more tests fixed"
            )

        print()
        print("  True Regressions (bugs in unmodified code):")
        print(f"    Baseline:     {baseline_true_regressions}")
        print(f"    Aspect:       {aspect_true_regressions}")
        if baseline_true_regressions > aspect_true_regressions:
            print(
                f"    ✅ Aspect caused {baseline_true_regressions - aspect_true_regressions} fewer regressions!"
            )
        elif aspect_true_regressions > baseline_true_regressions:
            print(
                f"    ⚠️ Aspect caused {aspect_true_regressions - baseline_true_regressions} more regressions"
            )
        else:
            print("    Tie - both had same regressions")

    print()
    print(f"📁 Results saved to: {results_file}")
    print("=" * 75)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Run Aspect Code benchmark experiment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--repo", "-r", help="Repository name (use --all-repos for all)")
    parser.add_argument(
        "--all-repos", action="store_true", help="Run on all registered repositories"
    )
    parser.add_argument(
        "--provider",
        "-p",
        choices=["anthropic", "openai"],
        default="anthropic",
        help="LLM provider (default: anthropic)",
    )
    parser.add_argument(
        "--model", "-m", help="Model name (default: claude-sonnet-4-20250514 for Anthropic)"
    )
    parser.add_argument(
        "--api-key", help="API key (or use ANTHROPIC_API_KEY/OPENAI_API_KEY env vars)"
    )
    parser.add_argument("--tasks", "-t", nargs="+", help="Specific task IDs to run (default: all)")
    parser.add_argument(
        "--modes",
        nargs="+",
        default=None,
        help="Prompt modes to run (suffixes like baseline, aspect, aspect_kb_new). Default: baseline aspect",
    )

    args = parser.parse_args()

    # Determine repos
    if args.all_repos:
        repos = ["fastapi-template", "djangopackages"]
    elif args.repo:
        repos = [args.repo]
    else:
        print("Error: Specify --repo or --all-repos")
        sys.exit(1)

    # Get API key
    api_key = args.api_key
    if not api_key:
        if args.provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY")
        elif args.provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        print("Error: API key required.")
        print(
            f"  Set environment variable: {'ANTHROPIC_API_KEY' if args.provider == 'anthropic' else 'OPENAI_API_KEY'}"
        )
        print("  Or use --api-key argument")
        sys.exit(1)

    # Check for required packages
    if args.provider == "anthropic" and not HAS_ANTHROPIC:
        print("Error: anthropic package not installed. Run: pip install anthropic")
        sys.exit(1)
    if args.provider == "openai" and not HAS_OPENAI:
        print("Error: openai package not installed. Run: pip install openai")
        sys.exit(1)

    # Run experiment
    run_aspect_experiment(
        repos=repos,
        api_key=api_key,
        provider=args.provider,
        model=args.model,
        task_ids=args.tasks,
        modes=args.modes,
    )


if __name__ == "__main__":
    main()
