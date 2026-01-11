#!/usr/bin/env python3
"""src/scripts/generate_prompts.py

Generate prompt files with knowledge base context.

By default, reads baseline prompts and creates `*_aspect.txt` prompts by
prepending agent instructions + KB content from `example_kb/`.

This script also supports generating prompts for a single repo and/or from an
alternate KB directory (e.g. a new KB edition).

Usage:
    python src/scripts/generate_prompts.py
    python src/scripts/generate_prompts.py --repo fastapi-template --kb-dir new_kb --mode-name aspect_kb_new
"""

import argparse
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
HARNESS_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = HARNESS_DIR.parent  # aspect-code-bench root

# Default KB content files from example_kb folder
DEFAULT_KB_DIR = PROJECT_ROOT / "example_kb"

# Prompt directories
FASTAPI_PROMPTS_DIR = HARNESS_DIR / "repos" / "fastapi-template" / "prompts"
DJANGOPACKAGES_PROMPTS_DIR = HARNESS_DIR / "repos" / "djangopackages" / "prompts"


def read_file(path: Path) -> str:
    """Read a file and return its content."""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def extract_agents_md_content(agents_md: str) -> str:
    """Extract the content between ASPECT_CODE_START and ASPECT_CODE_END markers."""
    start_marker = "<!-- ASPECT_CODE_START -->"
    end_marker = "<!-- ASPECT_CODE_END -->"
    
    start_idx = agents_md.find(start_marker)
    end_idx = agents_md.find(end_marker)
    
    if start_idx == -1 or end_idx == -1:
        raise ValueError("Could not find ASPECT_CODE markers in AGENTS.md")
    
    # Include the content between markers (excluding markers themselves)
    content = agents_md[start_idx + len(start_marker):end_idx].strip()
    return content


def generate_kb_header(agents_content: str, kb_content: str) -> str:
    """Generate the new KB header for prompts."""
    header = f"""# AI Coding Assistant Instructions

<!-- ASPECT_CODE_START -->
{agents_content}
<!-- ASPECT_CODE_END -->

# Aspect Code Knowledge Base

{kb_content}

"""
    return header


def get_baseline_prompts(prompts_dir: Path) -> list[Path]:
    """Get all baseline prompt files."""
    return sorted(prompts_dir.glob("*_baseline.txt"))


def extract_baseline_content(baseline_path: Path) -> str:
    """Read baseline file - this is the content after project structure."""
    content = read_file(baseline_path)
    return content


def create_aspect_prompt(baseline_path: Path, kb_header: str, output_dir: Path, mode_name: str):
    """Create a new prompt for `mode_name` from a baseline prompt."""
    # Get the task name from the baseline filename
    task_name = baseline_path.stem.replace("_baseline", "")
    output_filename = f"{task_name}_{mode_name}.txt"
    output_path = output_dir / output_filename
    
    # Read the baseline content
    baseline_content = read_file(baseline_path)
    
    # Combine KB header with baseline content
    full_content = kb_header + baseline_content
    
    # Write the new prompt
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_content)
    
    print(f"Created: {output_path.name}")
    return output_path


def _kb_paths_for_repo(kb_dir: Path, repo_name: str) -> tuple[Path, Path]:
    """Return (agents_md_path, kb_txt_path) for a repo from the given kb_dir."""
    agents_md_path = kb_dir / "AGENTS.md"
    if repo_name == "fastapi-template":
        kb_txt_path = kb_dir / "kb_fastapi.txt"
    elif repo_name == "djangopackages":
        kb_txt_path = kb_dir / "kb_djangopackages.txt"
    else:
        # Fall back to a conventional name: kb_<repo>.txt
        kb_txt_path = kb_dir / f"kb_{repo_name}.txt"
    return agents_md_path, kb_txt_path


def main():
    """Generate prompts for one or more repos."""
    parser = argparse.ArgumentParser(description="Generate prompts with KB context")
    parser.add_argument(
        "--repo",
        choices=["fastapi-template", "djangopackages"],
        help="Generate prompts for a single repo (default: both)",
    )
    parser.add_argument(
        "--kb-dir",
        default=str(DEFAULT_KB_DIR),
        help="KB directory containing AGENTS.md and kb_*.txt (default: example_kb)",
    )
    parser.add_argument(
        "--mode-name",
        default="aspect",
        help="Prompt mode suffix to generate (default: aspect)",
    )
    args = parser.parse_args()

    kb_dir = Path(args.kb_dir)
    mode_name = args.mode_name.strip()
    if not mode_name:
        raise ValueError("--mode-name cannot be empty")

    print("=" * 60)
    print(f"Generating prompts (kb_dir={kb_dir}, mode={mode_name})")
    print("=" * 60)

    repos_to_generate = [args.repo] if args.repo else ["fastapi-template", "djangopackages"]
    total_created = 0

    for repo_name in repos_to_generate:
        agents_md_path, kb_txt_path = _kb_paths_for_repo(kb_dir, repo_name)

        print("\nChecking source files...")
        for path in [agents_md_path, kb_txt_path]:
            if not path.exists():
                print(f"ERROR: Missing file: {path}")
                return
            print(f"  ✓ {path}")

        print("\nReading source files...")
        agents_md = read_file(agents_md_path)
        kb_content = read_file(kb_txt_path)

        agents_content = extract_agents_md_content(agents_md)
        print(f"  - AGENTS.md content extracted ({len(agents_content)} chars)")

        kb_header = generate_kb_header(agents_content, kb_content)
        print(f"  - KB header: {len(kb_header)} chars")

        prompts_dir = FASTAPI_PROMPTS_DIR if repo_name == "fastapi-template" else DJANGOPACKAGES_PROMPTS_DIR
        print(f"\n{'=' * 60}")
        print(f"Generating {repo_name} prompts (*_{mode_name}.txt)...")
        print("=" * 60)

        baselines = get_baseline_prompts(prompts_dir)
        print(f"Found {len(baselines)} baseline prompts")

        for baseline_path in baselines:
            create_aspect_prompt(baseline_path, kb_header, prompts_dir, mode_name=mode_name)
            total_created += 1

    print(f"\n{'=' * 60}")
    print("Done!")
    print(f"Generated: {total_created} prompts (*_{mode_name}.txt)")
    print("=" * 60)


if __name__ == "__main__":
    main()
