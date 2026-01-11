#!/usr/bin/env python3
"""
load_task_defs.py - Load and manage task definitions from YAML files.

Supports multiple repositories with repo-specific task definitions.

Usage:
    from load_task_defs import load_task, list_tasks, get_task_by_id
"""

from pathlib import Path
from typing import Any

import yaml

# Paths
SCRIPT_DIR = Path(__file__).parent
HARNESS_DIR = SCRIPT_DIR.parent
REPOS_DIR = HARNESS_DIR / "repos"
PROJECT_ROOT = HARNESS_DIR.parent  # Root of the project
BENCHMARKS_ROOT = PROJECT_ROOT / "repos"  # Where target repos are cloned


# Repository registry - maps short names to actual paths
REPO_REGISTRY = {
    "fastapi-template": {
        "name": "FastAPI Full-Stack Template",
        "path": "fastapi-template",
        "backend_path": "backend",
        "test_path": "backend/tests",
        "language": "python",
        "git_url": "https://github.com/fastapi/full-stack-fastapi-template.git",
    },
    "djangopackages": {
        "name": "Django Packages - Directory of Reusable Django Apps",
        "path": "djangopackages",
        "backend_path": "",  # Root level Django project
        "test_path": "",  # Tests distributed across apps
        "language": "python",
        "git_url": "https://github.com/djangopackages/djangopackages.git",
    },
}


def get_harness_dir() -> Path:
    """Get the harness root directory."""
    return HARNESS_DIR.resolve()


def get_benchmarks_root() -> Path:
    """Get the benchmarks root directory (where repos are cloned)."""
    return BENCHMARKS_ROOT.resolve()


def get_repo_config(repo_name: str) -> dict[str, Any] | None:
    """Get configuration for a repository."""
    return REPO_REGISTRY.get(repo_name)


def list_repos() -> list[str]:
    """List available repository names."""
    return list(REPO_REGISTRY.keys())


def get_repo_root(repo_name: str) -> Path | None:
    """Get the root path for a target repository."""
    config = get_repo_config(repo_name)
    if not config:
        return None
    return get_benchmarks_root() / config["path"]


def get_repo_tasks_dir(repo_name: str) -> Path:
    """Get the tasks directory for a repository."""
    return REPOS_DIR / repo_name / "tasks"


def get_repo_tests_dir(repo_name: str) -> Path:
    """Get the tests directory for a repository."""
    return REPOS_DIR / repo_name / "tests"


def get_repo_prompts_dir(repo_name: str) -> Path:
    """Get the prompts directory for a repository."""
    return REPOS_DIR / repo_name / "prompts"


def list_task_files(repo_name: str) -> list[Path]:
    """List all YAML task definition files for a repo."""
    tasks_dir = get_repo_tasks_dir(repo_name)
    if not tasks_dir.exists():
        return []
    return sorted(tasks_dir.glob("task*.yaml"))


def load_task(file_path: Path) -> dict[str, Any]:
    """
    Load a single task definition from a YAML file.

    Args:
        file_path: Path to the YAML file

    Returns:
        Dictionary containing task definition

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If file is not valid YAML
    """
    with open(file_path, encoding="utf-8") as f:
        task = yaml.safe_load(f)

    # Add metadata
    task["_file"] = str(file_path)
    task["_filename"] = file_path.name

    return task


def list_tasks(repo_name: str) -> list[dict[str, Any]]:
    """
    Load all task definitions for a repository.

    Returns:
        List of task definition dictionaries
    """
    tasks = []
    for file_path in list_task_files(repo_name):
        try:
            task = load_task(file_path)
            tasks.append(task)
        except Exception as e:
            print(f"Warning: Failed to load {file_path}: {e}")
    return tasks


def get_task_by_id(repo_name: str, task_id: str) -> dict[str, Any] | None:
    """
    Get a task definition by its ID.

    Args:
        repo_name: The repository name
        task_id: The task ID (e.g., "refactor-auth-dependency")

    Returns:
        Task definition dict or None if not found
    """
    for task in list_tasks(repo_name):
        if task.get("id") == task_id:
            return task
    return None


def get_task_ids(repo_name: str) -> list[str]:
    """Get list of all task IDs for a repo."""
    return [task["id"] for task in list_tasks(repo_name)]


def print_task_summary(task: dict[str, Any]) -> None:
    """Print a summary of a task."""
    print(f"ID: {task.get('id')}")
    print(f"Name: {task.get('name')}")
    print(f"Difficulty: {task.get('difficulty', 'unknown')}")
    print(f"Tags: {', '.join(task.get('tags', []))}")
    print(f"Test command: {task.get('test_command')}")
    print(f"File: {task.get('_filename')}")


def main():
    """CLI: List all tasks or show details for a specific task."""
    import argparse

    parser = argparse.ArgumentParser(description="Load and display task definitions")
    parser.add_argument("--repo", "-r", help="Repository name", default="fastapi-template")
    parser.add_argument("--task-id", "-t", help="Show details for specific task ID")
    parser.add_argument("--list", "-l", action="store_true", help="List all task IDs")
    parser.add_argument("--list-repos", action="store_true", help="List all repositories")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full descriptions")

    args = parser.parse_args()

    if args.list_repos:
        print("Available repositories:")
        for repo_name in list_repos():
            config = get_repo_config(repo_name)
            print(f"  - {repo_name}: {config['name']}")
        return

    if args.repo not in REPO_REGISTRY:
        print(f"Unknown repo: {args.repo}")
        print(f"Available: {', '.join(list_repos())}")
        exit(1)

    if args.list:
        print(f"Available tasks for {args.repo}:")
        for task_id in get_task_ids(args.repo):
            print(f"  - {task_id}")
        return

    if args.task_id:
        task = get_task_by_id(args.repo, args.task_id)
        if task:
            print_task_summary(task)
            if args.verbose:
                print("\nDescription:")
                print(task.get("description", "No description"))
        else:
            print(f"Task not found: {args.task_id}")
            print(f"Available: {', '.join(get_task_ids(args.repo))}")
            exit(1)
        return

    # Default: show all tasks
    tasks = list_tasks(args.repo)
    print(f"Found {len(tasks)} tasks for {args.repo}:\n")
    for task in tasks:
        print(f"[{task.get('difficulty', '?').upper():6}] {task.get('id')}")
        print(f"         {task.get('name')}")
        print()


if __name__ == "__main__":
    main()
