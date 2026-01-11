<div align="center">

# Aspect Bench

**A/B Testing Framework for LLM Code Generation with Knowledge Base Context**

[![CI](https://github.com/asashepard/aspect-bench/actions/workflows/ci.yml/badge.svg)](https://github.com/asashepard/aspect-bench/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE.md)
[![VS Code Extension](https://img.shields.io/badge/VS_Code_Extension-coming_soon-orange)](#about)

*Measure how project-specific context improves LLM code generation accuracy*

</div>

## About

**Aspect Bench** is a rigorous A/B testing framework that measures how project-specific context (knowledge bases) improves LLM code generation.

This benchmarks the [Aspect Code VS Code extension](https://marketplace.visualstudio.com/items?itemName=aspect-code.aspect-code), which generates structured `.aspect/` knowledge bases that help AI coding agents understand your project's architecture.

📊 [View benchmark results](https://www.aspectcode.com/blog/making-ai-reliable) • 🔌 [Get the extension](https://aspectcode.com)

---

## Overview

Aspect Bench compares LLM performance across two modes:

| Mode | Description |
|------|-------------|
| **Baseline** | Standard prompts without additional context |
| **Aspect KB** | Prompts enhanced with project knowledge base files from the [Aspect Code](https://marketplace.visualstudio.com/items?itemName=aspect-code.aspect-code) extension |

This A/B testing approach measures how much project-specific context improves:
- ✅ Code generation accuracy
- ✅ Test pass rates  
- ✅ Regression prevention

---

## Sample Results

Real benchmark results from Claude 4 Sonnet on 15 FastAPI tasks:

| Metric | Baseline | With KB | Δ |
|--------|----------|---------|---|
| **Tasks Passed** | 5 | 9 | +80% |
| **Tests Fixed** | 24 | 41 | +71% |
| **Regressions** | 8 | 3 | -63% |

> The KB-enhanced prompts consistently outperform baseline, especially on complex refactoring tasks where project architecture knowledge is critical.

---

## Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   ASPECT BENCH WORKFLOW (With Aspect Code)                  │
└─────────────────────────────────────────────────────────────────────────────┘

  1. SETUP                    2. GENERATE KB              3. GENERATE PROMPTS
  ┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
  │ Clone target repo│   →    │ Open in VS Code  │   →    │ Run generate_    │
  │ into repos/      │        │ with Aspect Code │        │ prompts.py       │
  │                  │        │ extension        │        │                  │
  └──────────────────┘        └──────────────────┘        └──────────────────┘
                                     │
                                     ▼
                              ┌──────────────────┐
                              │ Extension creates│
                              │ .aspect/         │
                              │ Copy to example_ │
                              │ kb/kb_<repo>.txt │
                              └──────────────────┘

  4. RUN BENCHMARK            5. GENERATE REPORT
  ┌──────────────────┐        ┌──────────────────┐
  │ run_benchmark.py │   →    │ generate_report. │   →    📊 Results!
  │ --repo <name>    │        │ py --experiment  │
  │ --provider ...   │        │ -id <id>         │
  └──────────────────┘        └──────────────────┘
```

---

## Quick Start

> **TL;DR** — Clone, install, set API key, run:
> ```bash
> git clone https://github.com/asashepard/aspect-bench.git && cd aspect-bench
> pip install -e . && cp .env.example .env  # Add your ANTHROPIC_API_KEY
> python src/scripts/run_benchmark.py --repo fastapi-template --provider anthropic
> ```

### 1. Clone the Repository

```bash
git clone https://github.com/asashepard/aspect-bench.git
cd aspect-bench
```

### 2. Install Dependencies

```bash
pip install -e .
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your API keys
```

### 4. Clone Target Repositories

Clone the target repositories into the `repos/` folder:

```bash
# Create repos folder
mkdir repos
cd repos

# Clone fastapi-template
git clone https://github.com/fastapi/full-stack-fastapi-template.git fastapi-template

# Clone djangopackages
git clone https://github.com/djangopackages/djangopackages.git djangopackages

cd ..
```

### 5. Find Available Tasks

Tasks are defined in YAML files for each repository:

```bash
# View task definitions
cat src/repos/fastapi-template/tasks/task_defs.yaml
cat src/repos/djangopackages/tasks/task_defs.yaml
```

Each task has an `id` field (e.g., `missing-item-404`, `api-package-404`) that you use when running benchmarks.

**Task file location pattern:**
```
src/repos/<repo-name>/tasks/task_defs.yaml
```

### 6. Generate Prompts (Required Before Running)

Before running benchmarks, generate the prompts from task definitions:

```bash
python src/scripts/generate_prompts.py
```

This creates both baseline and aspect prompt files in each repo's `prompts/` directory.

### 7. Run a Benchmark

```bash
# Run all tasks for a repository
python src/scripts/run_benchmark.py --repo fastapi-template --provider anthropic

# Run a specific task by ID
python src/scripts/run_benchmark.py --repo djangopackages --tasks api-package-404 --provider anthropic

# Run all repositories
python src/scripts/run_benchmark.py --all-repos --provider anthropic
```

### 8. Generate Report

```bash
python src/scripts/generate_report.py --experiment-id <experiment_id>
```

---

## Pre-Run Checklist

Before running benchmarks, ensure:

- [ ] `.env` file exists with valid `ANTHROPIC_API_KEY` (and/or `OPENAI_API_KEY`)
- [ ] Target repository is cloned in `repos/<repo-name>/`
- [ ] Knowledge base generated via Aspect Code extension and saved to `example_kb/`
- [ ] Prompts generated by running `python src/scripts/generate_prompts.py`
- [ ] Tests are configured and runnable for the target repo

---

## Generating Knowledge Base Files

The knowledge base (KB) files are **generated by the Aspect Code VS Code extension**, not by a script.

### Steps to Generate KB:

1. **Install the Aspect Code extension** from the [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=aspect-code.aspect-code)

2. **Open your target repository** in VS Code

3. **Run the Aspect Code extension** to generate the KB:
   - The extension creates a `.aspect/` folder with `kb.txt` and other analysis files

4. **Copy the generated KB** to the benchmark:
   ```bash
   cp repos/<repo-name>/.aspect/kb.txt example_kb/kb_<repo-name>.txt
   ```

5. **Copy AGENTS.md** (if not already present):
   ```bash
   cp repos/<repo-name>/.aspect/AGENTS.md example_kb/AGENTS.md
   ```

---

## Project Structure

```
aspect-bench/
├── .env.example              # Environment template
├── .gitignore
├── README.md
├── CONTRIBUTING.md
├── LICENSE.md
│
├── example_kb/               # Knowledge base files from Aspect Code extension
│   ├── AGENTS.md             # Agent instructions template
│   ├── kb_djangopackages.txt # KB for djangopackages repo
│   └── kb_fastapi.txt        # KB for fastapi-template repo
│
├── repos/                    # Cloned target repositories (gitignored)
│   ├── fastapi-template/     # ← Cloned target repo
│   │   └── backend/...
│   └── djangopackages/       # ← Cloned target repo
│       └── djangopackages/...
│
└── src/
    ├── repos/                # Benchmark harness files (prompts, tasks, tests)
    │   ├── djangopackages/
    │   │   ├── prompts/      # Generated prompts (*_baseline.txt, *_aspect.txt)
    │   │   ├── tasks/
    │   │   │   └── task_defs.yaml   # ← Task definitions with IDs
    │   │   └── tests/
    │   │
    │   └── fastapi-template/
    │       ├── prompts/
    │       ├── tasks/
    │       │   └── task_defs.yaml   # ← Task definitions with IDs
    │       └── tests/
    │
    ├── scripts/              # Main scripts
    │   ├── run_benchmark.py      # Main benchmark runner
    │   ├── generate_prompts.py   # Generate prompt files from tasks
    │   ├── generate_report.py    # Generate markdown reports
    │   ├── run_tests_for_task.py # Test runner utility
    │   └── load_task_defs.py     # Task/repo registry
    │
    ├── results/              # Benchmark results (gitignored)
    ├── responses/            # LLM responses (gitignored)
    └── reports/              # Generated reports (gitignored)
```

---

## Core Scripts

### `run_benchmark.py`

Main entry point for running benchmarks.

```bash
# Full benchmark for a repo
python src/scripts/run_benchmark.py --repo fastapi-template --provider anthropic

# Single task test (use task ID from task_defs.yaml)
python src/scripts/run_benchmark.py --repo fastapi-template --tasks missing-item-404 --provider anthropic

# Multiple specific tasks
python src/scripts/run_benchmark.py --repo fastapi-template --tasks missing-item-404 add-csv-export --provider anthropic

# All repos
python src/scripts/run_benchmark.py --all-repos --provider anthropic
```

**Arguments:**
- `--repo`: Repository name (from REPO_REGISTRY)
- `--tasks`: Space-separated task IDs (optional, defaults to all)
- `--provider`: `anthropic` or `openai`
- `--all-repos`: Run all registered repositories

### `generate_prompts.py`

Generate prompt files from task definitions. **Must run before benchmarking.**

```bash
python src/scripts/generate_prompts.py
```

### `generate_report.py`

Generate human-readable markdown reports from benchmark results.

```bash
python src/scripts/generate_report.py --experiment-id 20241201_143022
```

---

## Finding Task IDs

Task IDs are defined in the `task_defs.yaml` file for each repository:

```yaml
# Example from src/repos/fastapi-template/tasks/task_defs.yaml
tasks:
  - id: missing-item-404           # ← This is the task ID
    name: "Return 404 for missing items"
    description: |
      Modify the items endpoint to return 404 when item not found...
    
  - id: add-csv-export             # ← Another task ID
    name: "Add CSV export endpoint"
    ...
```

To list all task IDs for a repo:

```bash
# Using grep
grep "^  - id:" src/repos/fastapi-template/tasks/task_defs.yaml

# Or view the full file
cat src/repos/fastapi-template/tasks/task_defs.yaml
```

---

## Benchmark Output

### Results Structure

Each benchmark run creates:

```
results/
└── aspect_ab_experiment_<experiment_id>.json

responses/
└── <repo>_<task_id>_<mode>_<experiment_id>.txt

reports/
└── <experiment_id>/
    └── report.md
```

### Report Contents

Generated reports include:
- **Side-by-side comparison** of baseline vs aspect KB results
- **Test pass/fail counts** before and after changes
- **Regression analysis** (did existing tests break?)
- **Code diffs** for both approaches
- **Winner determination** with analysis

---

## Supported Providers

| Provider | Environment Variable | Models |
|----------|---------------------|--------|
| Anthropic | `ANTHROPIC_API_KEY` | Claude 4 Sonnet, Claude 4.5 Opus |
| OpenAI | `OPENAI_API_KEY` | GPT-4o, o1, o3 |

---

## License

MIT License - see [LICENSE.md](LICENSE.md)

---

## Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting PRs.
