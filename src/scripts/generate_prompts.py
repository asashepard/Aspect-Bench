#!/usr/bin/env python3
"""
generate_prompts.py - Generate prompts with knowledge base context.

Reads the baseline prompts and creates new aspect_kb3 prompts by prepending
the AGENTS.md content and respective kb_*.txt content from example_kb folder.

Usage:
    python generate_prompts.py
"""

import os
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
HARNESS_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = HARNESS_DIR.parent  # aspect-code-bench root

# KB content files from example_kb folder
EXAMPLE_KB_DIR = PROJECT_ROOT / "example_kb"
AGENTS_MD_PATH = EXAMPLE_KB_DIR / "AGENTS.md"
KB_FASTAPI_PATH = EXAMPLE_KB_DIR / "kb_fastapi.txt"
KB_DJANGOPACKAGES_PATH = EXAMPLE_KB_DIR / "kb_djangopackages.txt"

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


def create_aspect_prompt(baseline_path: Path, kb_header: str, output_dir: Path):
    """Create a new aspect prompt from a baseline prompt."""
    # Get the task name from the baseline filename
    task_name = baseline_path.stem.replace("_baseline", "")
    output_filename = f"{task_name}_aspect.txt"
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


def main():
    """Generate aspect prompts for all repos."""
    print("=" * 60)
    print("Generating Aspect Code prompts (from example_kb/)")
    print("=" * 60)
    
    # Verify source files exist
    print("\nChecking source files...")
    for path in [AGENTS_MD_PATH, KB_FASTAPI_PATH, KB_DJANGOPACKAGES_PATH]:
        if not path.exists():
            print(f"ERROR: Missing file: {path}")
            return
        print(f"  ✓ {path.name}")
    
    # Read source files
    print("\nReading source files...")
    agents_md = read_file(AGENTS_MD_PATH)
    kb_fastapi = read_file(KB_FASTAPI_PATH)
    kb_djangopackages = read_file(KB_DJANGOPACKAGES_PATH)
    
    # Extract AGENTS.md content
    agents_content = extract_agents_md_content(agents_md)
    print(f"  - AGENTS.md content extracted ({len(agents_content)} chars)")
    
    # Generate KB headers
    fastapi_header = generate_kb_header(agents_content, kb_fastapi)
    djangopackages_header = generate_kb_header(agents_content, kb_djangopackages)
    
    print(f"  - FastAPI KB header: {len(fastapi_header)} chars")
    print(f"  - DjangoPackages KB header: {len(djangopackages_header)} chars")
    
    # Generate FastAPI prompts
    print(f"\n{'=' * 60}")
    print("Generating FastAPI template prompts (*_aspect.txt)...")
    print("=" * 60)
    
    fastapi_baselines = get_baseline_prompts(FASTAPI_PROMPTS_DIR)
    print(f"Found {len(fastapi_baselines)} baseline prompts")
    
    for baseline_path in fastapi_baselines:
        create_aspect_prompt(baseline_path, fastapi_header, FASTAPI_PROMPTS_DIR)
    
    # Generate DjangoPackages prompts
    print(f"\n{'=' * 60}")
    print("Generating DjangoPackages prompts (*_aspect.txt)...")
    print("=" * 60)
    
    djangopackages_baselines = get_baseline_prompts(DJANGOPACKAGES_PROMPTS_DIR)
    print(f"Found {len(djangopackages_baselines)} baseline prompts")
    
    for baseline_path in djangopackages_baselines:
        create_aspect_prompt(baseline_path, djangopackages_header, DJANGOPACKAGES_PROMPTS_DIR)
    
    print(f"\n{'=' * 60}")
    print("Done! Generated prompts:")
    print(f"  - FastAPI: {len(fastapi_baselines)} prompts (*_aspect.txt)")
    print(f"  - DjangoPackages: {len(djangopackages_baselines)} prompts (*_aspect.txt)")
    print(f"  - Total: {len(fastapi_baselines) + len(djangopackages_baselines)} prompts")
    print("=" * 60)


if __name__ == "__main__":
    main()
