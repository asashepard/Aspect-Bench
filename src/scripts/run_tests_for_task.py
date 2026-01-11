#!/usr/bin/env python3
"""
run_tests_for_task.py - Run pytest tests for a specific benchmark task.

Supports multiple repositories with the --repo parameter.

Usage:
    python src/scripts/run_tests_for_task.py --repo fastapi-template --task-id <id>
    python src/scripts/run_tests_for_task.py --repo fastapi-template --all
    python src/scripts/run_tests_for_task.py --repo fastapi-template --task-id <id> --with-regression

Modes:
    Default:           Run only the task-specific tests
    --all:             Run all benchmark tests for the repo
    --with-regression: Run task tests + regression tests (catch side effects)
    --regression-only: Run only regression tests (use to verify baseline)

Returns exit code 0 if all tests pass, non-zero if any fail.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Add scripts dir to path for imports
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from load_task_defs import (  # noqa: E402
    get_repo_config,
    get_repo_root,
    get_repo_tests_dir,
    get_task_by_id,
    get_task_ids,
    list_repos,
)


def run_pytest_command(cmd_parts: list, cwd: Path, capture: bool = False) -> int:
    """Run a pytest command and return exit code."""
    try:
        result = subprocess.run(cmd_parts, cwd=cwd, capture_output=capture, text=True)

        if capture:
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)

        return result.returncode

    except FileNotFoundError:
        print(f"Error: Command not found: {cmd_parts[0]}")
        return 127
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


def get_test_file_for_task(repo_name: str, task_id: str) -> Path | None:
    """Get the test file path for a task."""
    tests_dir = get_repo_tests_dir(repo_name)

    # Map task IDs to test files - organized by repo
    task_to_test = {
        # FastAPI Template tasks
        "refactor-auth-dependency": "test_aspect_bench_auth_refactor.py",
        "missing-item-404": "test_aspect_bench_error_schema.py",
        "consistent-error-schema": "test_aspect_bench_error_schema.py",
        "paginated-items-endpoint": "test_aspect_bench_pagination.py",
        "stronger-password-policy": "test_aspect_bench_password_policy.py",
        "soft-delete-items": "test_aspect_bench_soft_delete.py",
        "rate-limit-login": "test_aspect_bench_rate_limit.py",
        "optimize-items-query": "test_aspect_bench_query_optimization.py",
        "add-csv-export": "test_aspect_bench_csv_export.py",
        "refactor-items-service-layers": "test_aspect_bench_service_layers.py",
        "api-response-caching": "test_aspect_bench_response_caching.py",
        "external-service-retry": "test_aspect_bench_retry.py",
        "db-pool-metrics-endpoint": "test_aspect_bench_pool_metrics.py",
        "streaming-file-upload": "test_aspect_bench_file_upload.py",
        "api-timeout-configuration": "test_aspect_bench_timeout_defaults.py",
        # Django Packages tasks - one test file per task
        "package-edit-permissions": "test_aspect_bench_package_edit_permissions.py",
        "grid-lock-permissions": "test_aspect_bench_grid_lock_permissions.py",
        "api-package-404": "test_aspect_bench_api_package_404.py",
        "api-grid-404": "test_aspect_bench_api_grid_404.py",
        "api-error-schema": "test_aspect_bench_api_error_schema.py",
        "package-list-pagination": "test_aspect_bench_package_list_pagination.py",
        "grid-list-pagination": "test_aspect_bench_grid_list_pagination.py",
        "search-filtering": "test_aspect_bench_search_filtering.py",
        "homepage-caching": "test_aspect_bench_homepage_caching.py",
        "search-caching": "test_aspect_bench_search_caching.py",
        "package-csv-export": "test_aspect_bench_package_csv_export.py",
        "grid-json-export": "test_aspect_bench_grid_json_export.py",
        "pypi-fetch-retry": "test_aspect_bench_pypi_fetch_retry.py",
        "github-fetch-timeout": "test_aspect_bench_github_fetch_timeout.py",
        "api-metrics-endpoint": "test_aspect_bench_api_metrics_endpoint.py",
    }

    test_file = task_to_test.get(task_id)
    if test_file:
        return tests_dir / test_file
    return None


def run_regression_tests(repo_name: str, verbose: bool = False, capture: bool = False) -> int:
    """
    Run regression tests to verify no side effects.

    Returns:
        Exit code (0 = pass, non-zero = fail)
    """
    repo_root = get_repo_root(repo_name)
    tests_dir = get_repo_tests_dir(repo_name)
    regression_test = tests_dir / "test_aspect_bench_regression.py"
    config = get_repo_config(repo_name)
    backend_path = config.get("backend_path", "")

    if not regression_test.exists():
        print(f"Warning: No regression test file found for {repo_name}")
        return 0

    # Working directory is the backend for proper imports
    work_dir = repo_root / backend_path if backend_path else repo_root

    # Build pytest command
    cmd_parts = [
        "pytest",
        str(regression_test),
        "-m",
        "regression",
    ]

    if verbose:
        cmd_parts.append("-v")

    print("\n" + "=" * 60)
    print("REGRESSION TESTS - Checking for side effects")
    print("=" * 60)

    return run_pytest_command(cmd_parts, work_dir, capture)


def run_all_benchmark_tests(repo_name: str, verbose: bool = False, capture: bool = False) -> int:
    """
    Run all benchmark tests for a repository.

    Returns:
        Exit code (0 = pass, non-zero = fail)
    """
    repo_root = get_repo_root(repo_name)
    tests_dir = get_repo_tests_dir(repo_name)
    config = get_repo_config(repo_name)
    backend_path = config.get("backend_path", "")

    # Find all test files
    test_files = list(tests_dir.glob("test_aspect_bench_*.py"))

    if not test_files:
        print(f"No benchmark tests found for {repo_name}")
        return 1

    # Working directory is the backend for proper imports
    work_dir = repo_root / backend_path if backend_path else repo_root

    # Build pytest command - run from backend with paths relative to it
    cmd_parts = ["pytest"]
    cmd_parts.extend([str(f) for f in test_files])
    cmd_parts.extend(["-m", "aspect_bench"])

    if verbose:
        cmd_parts.append("-v")

    print("=" * 60)
    print(f"ALL BENCHMARK TESTS for {repo_name}")
    print("=" * 60)
    print(f"Running: {len(test_files)} test files")
    print(f"Working directory: {work_dir}")
    print("-" * 60)

    return run_pytest_command(cmd_parts, work_dir, capture)


def run_tests_for_task(
    repo_name: str,
    task_id: str,
    verbose: bool = False,
    capture: bool = False,
    with_regression: bool = False,
) -> int:
    """
    Run the tests for a specific task.

    Args:
        repo_name: The repository name
        task_id: The task ID
        verbose: Show verbose test output
        capture: Capture output instead of streaming
        with_regression: Also run regression tests

    Returns:
        Exit code (0 = pass, non-zero = fail)
    """
    task = get_task_by_id(repo_name, task_id)
    if not task:
        print(f"Error: Task not found: {task_id}")
        print(f"Available tasks: {', '.join(get_task_ids(repo_name))}")
        return 1

    repo_root = get_repo_root(repo_name)
    config = get_repo_config(repo_name)
    backend_path = config.get("backend_path", "")

    # Get test file
    test_file = get_test_file_for_task(repo_name, task_id)
    if not test_file or not test_file.exists():
        print(f"Error: Test file not found for task: {task_id}")
        return 1

    # Working directory is the backend for proper imports
    work_dir = repo_root / backend_path if backend_path else repo_root

    # Build pytest command
    cmd_parts = [
        "pytest",
        str(test_file),
        "-m",
        "aspect_bench",
    ]

    if verbose:
        cmd_parts.append("-v")

    print("=" * 60)
    print(f"TASK: {task.get('name')}")
    print(f"REPO: {repo_name}")
    print("=" * 60)
    print(f"Running: pytest {test_file.name}")
    print(f"Working directory: {work_dir}")
    print("-" * 60)

    # Track all results
    results = {}

    results["task"] = run_pytest_command(cmd_parts, work_dir, capture)

    # Run regression tests if requested
    if with_regression:
        results["regression"] = run_regression_tests(repo_name, verbose, capture)

    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_type, exit_code in results.items():
        status = "[PASSED]" if exit_code == 0 else "[FAILED]"
        print(f"  {test_type.upper()}: {status}")
        if exit_code != 0:
            all_passed = False

    print("-" * 60)
    if all_passed:
        print(f"All tests PASSED for task: {task_id}")
        return 0
    else:
        print(f"Some tests FAILED for task: {task_id}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Run pytest tests for a specific benchmark task",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available repos
  python run_tests_for_task.py --list-repos
  
  # List tasks for a repo
  python run_tests_for_task.py --repo fastapi-template --list
  
  # Run tests for a specific task
  python run_tests_for_task.py --repo fastapi-template --task-id refactor-auth-dependency
  
  # Run all benchmark tests for a repo
  python run_tests_for_task.py --repo fastapi-template --all
  
  # Run with regression tests
  python run_tests_for_task.py --repo fastapi-template --task-id refactor-auth-dependency --with-regression
""",
    )
    parser.add_argument(
        "--repo",
        "-r",
        default="fastapi-template",
        help="Repository name (default: fastapi-template)",
    )
    parser.add_argument("--task-id", "-t", help="Task ID (e.g., 'refactor-auth-dependency')")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose test output")
    parser.add_argument(
        "--capture", action="store_true", help="Capture output instead of streaming"
    )
    parser.add_argument(
        "--list", "-l", action="store_true", help="List available task IDs and exit"
    )
    parser.add_argument(
        "--list-repos", action="store_true", help="List available repositories and exit"
    )
    parser.add_argument(
        "--all", "-a", action="store_true", help="Run all benchmark tests for the repo"
    )
    parser.add_argument(
        "--with-regression",
        action="store_true",
        help="Also run regression tests to detect side effects",
    )
    parser.add_argument(
        "--regression-only", action="store_true", help="Run only regression tests (no task tests)"
    )

    args = parser.parse_args()

    if args.list_repos:
        print("Available repositories:")
        for repo in list_repos():
            config = get_repo_config(repo)
            print(f"  - {repo}: {config['name']}")
        sys.exit(0)

    if args.list:
        print(f"Available task IDs for {args.repo}:")
        for task_id in get_task_ids(args.repo):
            print(f"  - {task_id}")
        sys.exit(0)

    if args.regression_only:
        exit_code = run_regression_tests(args.repo, args.verbose, args.capture)
        sys.exit(exit_code)

    if args.all:
        exit_code = run_all_benchmark_tests(args.repo, args.verbose, args.capture)
        sys.exit(exit_code)

    if not args.task_id:
        parser.error(
            "--task-id is required unless using --list, --list-repos, --all, or --regression-only"
        )

    exit_code = run_tests_for_task(
        args.repo,
        args.task_id,
        verbose=args.verbose,
        capture=args.capture,
        with_regression=args.with_regression,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
