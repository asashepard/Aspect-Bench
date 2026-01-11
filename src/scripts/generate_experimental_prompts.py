#!/usr/bin/env python3
"""src/scripts/generate_experimental_prompts.py

Generate experimental prompt sets for KB effectiveness testing.

Generates two experimental prompt sets:
1. `no_kb` - Instructions only (no KB content), with instructions telling the
   model to use `.aspect/*.md` files IF provided in the prompt
2. `swapped` - Swapped KBs: FastAPI prompts get Django KB, Django prompts get FastAPI KB

Usage:
    python src/scripts/generate_experimental_prompts.py
    python src/scripts/generate_experimental_prompts.py --mode no_kb
    python src/scripts/generate_experimental_prompts.py --mode swapped
    python src/scripts/generate_experimental_prompts.py --mode both
"""

import argparse
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
HARNESS_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = HARNESS_DIR.parent  # aspect-code-bench root

# KB directory
KB_DIR = PROJECT_ROOT / "new_kb"

# Prompt directories
FASTAPI_PROMPTS_DIR = HARNESS_DIR / "repos" / "fastapi-template" / "prompts"
DJANGOPACKAGES_PROMPTS_DIR = HARNESS_DIR / "repos" / "djangopackages" / "prompts"


# ==============================================================================
# NO_KB MODE: Instructions only, no KB content
# ==============================================================================
NO_KB_INSTRUCTIONS = """## AI Coding Agent Instructions

### Aspect Code Knowledge Base (Optional)

If `.aspect/*.md` files are provided in this prompt, use them as a knowledge base:

| File | Purpose |
|------|---------|
| `architecture.md` | **Read first.** High-risk hubs, directory layout, entry points—the "Do Not Break" zones |
| `map.md` | Data models with signatures, symbol index, naming conventions |
| `context.md` | Module clusters (co-edited files), external integrations, data flow paths |

If these files are NOT provided, proceed using your general coding knowledge.

### Golden Rules

1. **Read before you write.** If KB files are provided, read them before multi-file edits.
2. **Think step-by-step.** Break complex tasks into smaller steps; reason through each before coding.
3. **Prefer minimal, local changes.** Small patches are safer than large refactors, especially in hub files.
4. **Never truncate code.** Don't use placeholders like `// ...rest` or `# existing code...`. Provide complete implementations.
5. **Don't touch tests, migrations, or third-party code** unless the user explicitly asks you to.
6. **Never remove referenced logic.** Check all callers before deleting a symbol.
7. **Follow existing naming patterns.** Match the project's existing naming conventions and import styles.
8. **When unsure, go small.** Propose a minimal, reversible change instead of a sweeping refactor.

### Recommended Workflow

1. **Understand the task.** Parse requirements; note which files or endpoints are involved.
2. **Check for KB files.** If `.aspect/*.md` files are provided, read them for architectural context.
3. **Make minimal edits.** Implement the smallest change that solves the task; run tests.
4. **Preserve existing code.** Read the COMPLETE file before modifying. Preserve all existing functions/exports.

### When Changing Code

- **Read the COMPLETE file** before modifying it. Preserve all existing exports/functions.
- **Add, don't reorganize.** Unless the task says "refactor", avoid moving code around.
- **Avoid renaming** widely-used symbols without updating all callers.
- **Match conventions.** Follow existing naming patterns (naming, imports, frameworks).
- **Prefer small, localized changes** in the most relevant module.

### If Things Go Wrong

1. **Use git** to see what changed: `git diff`, `git status`
2. **Restore lost code** with `git checkout -- <file>` if needed
3. **Re-read the complete file** before making more changes
4. **Run actual tests** to verify behavior before assuming something works
"""


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
    
    content = agents_md[start_idx + len(start_marker):end_idx].strip()
    return content


def get_baseline_prompts(prompts_dir: Path) -> list[Path]:
    """Get all baseline prompt files."""
    return sorted(prompts_dir.glob("*_baseline.txt"))


def generate_no_kb_header() -> str:
    """Generate instructions-only header (no KB content)."""
    return f"""# AI Coding Assistant Instructions

<!-- ASPECT_CODE_START -->
{NO_KB_INSTRUCTIONS}
<!-- ASPECT_CODE_END -->

"""


def generate_swapped_kb_header(agents_content: str, kb_content: str) -> str:
    """Generate KB header with swapped KB content."""
    header = f"""# AI Coding Assistant Instructions

<!-- ASPECT_CODE_START -->
{agents_content}
<!-- ASPECT_CODE_END -->

# Aspect Code Knowledge Base

{kb_content}

"""
    return header


def create_prompt(baseline_path: Path, header: str, output_dir: Path, mode_name: str):
    """Create a new prompt from a baseline prompt."""
    task_name = baseline_path.stem.replace("_baseline", "")
    output_filename = f"{task_name}_{mode_name}.txt"
    output_path = output_dir / output_filename
    
    baseline_content = read_file(baseline_path)
    full_content = header + baseline_content
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_content)
    
    print(f"  Created: {output_path.name}")
    return output_path


def generate_no_kb_prompts():
    """Generate no_kb prompts for both repos (instructions only, no KB content)."""
    print("\n" + "=" * 60)
    print("Generating NO_KB prompts (instructions only, no KB content)")
    print("=" * 60)
    
    header = generate_no_kb_header()
    print(f"Header size: {len(header)} chars")
    
    total_created = 0
    
    for repo_name, prompts_dir in [
        ("fastapi-template", FASTAPI_PROMPTS_DIR),
        ("djangopackages", DJANGOPACKAGES_PROMPTS_DIR),
    ]:
        print(f"\n{repo_name}:")
        baselines = get_baseline_prompts(prompts_dir)
        print(f"  Found {len(baselines)} baseline prompts")
        
        for baseline_path in baselines:
            create_prompt(baseline_path, header, prompts_dir, mode_name="no_kb")
            total_created += 1
    
    print(f"\n✓ Generated {total_created} no_kb prompts")
    return total_created


def generate_swapped_prompts():
    """Generate swapped prompts (FastAPI gets Django KB, Django gets FastAPI KB)."""
    print("\n" + "=" * 60)
    print("Generating SWAPPED prompts (cross-repo KBs)")
    print("=" * 60)
    
    # Read the shared AGENTS.md
    agents_md_path = KB_DIR / "AGENTS.md"
    if not agents_md_path.exists():
        print(f"ERROR: Missing {agents_md_path}")
        return 0
    
    agents_md = read_file(agents_md_path)
    agents_content = extract_agents_md_content(agents_md)
    print(f"AGENTS.md content: {len(agents_content)} chars")
    
    # Read both KB files
    fastapi_kb_path = KB_DIR / "kb_fastapi.txt"
    django_kb_path = KB_DIR / "kb_djangopackages.txt"
    
    for path in [fastapi_kb_path, django_kb_path]:
        if not path.exists():
            print(f"ERROR: Missing {path}")
            return 0
    
    fastapi_kb = read_file(fastapi_kb_path)
    django_kb = read_file(django_kb_path)
    print(f"FastAPI KB: {len(fastapi_kb)} chars")
    print(f"Django KB: {len(django_kb)} chars")
    
    total_created = 0
    
    # FastAPI prompts get Django KB
    print(f"\nfastapi-template (with Django KB):")
    fastapi_header = generate_swapped_kb_header(agents_content, django_kb)
    baselines = get_baseline_prompts(FASTAPI_PROMPTS_DIR)
    print(f"  Found {len(baselines)} baseline prompts")
    for baseline_path in baselines:
        create_prompt(baseline_path, fastapi_header, FASTAPI_PROMPTS_DIR, mode_name="swapped")
        total_created += 1
    
    # Django prompts get FastAPI KB
    print(f"\ndjangopackages (with FastAPI KB):")
    django_header = generate_swapped_kb_header(agents_content, fastapi_kb)
    baselines = get_baseline_prompts(DJANGOPACKAGES_PROMPTS_DIR)
    print(f"  Found {len(baselines)} baseline prompts")
    for baseline_path in baselines:
        create_prompt(baseline_path, django_header, DJANGOPACKAGES_PROMPTS_DIR, mode_name="swapped")
        total_created += 1
    
    print(f"\n✓ Generated {total_created} swapped prompts")
    return total_created


def main():
    """Generate experimental prompts."""
    parser = argparse.ArgumentParser(description="Generate experimental prompt sets")
    parser.add_argument(
        "--mode",
        choices=["no_kb", "swapped", "both"],
        default="both",
        help="Which experimental mode to generate (default: both)",
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("Generating Experimental Prompt Sets")
    print("=" * 60)
    print(f"KB directory: {KB_DIR}")
    print(f"Mode: {args.mode}")
    
    total = 0
    
    if args.mode in ("no_kb", "both"):
        total += generate_no_kb_prompts()
    
    if args.mode in ("swapped", "both"):
        total += generate_swapped_prompts()
    
    print("\n" + "=" * 60)
    print(f"DONE! Total prompts generated: {total}")
    print("=" * 60)


if __name__ == "__main__":
    main()
