# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-10

### Added
- Initial public release
- A/B benchmark framework comparing baseline vs KB-enhanced prompts
- Support for Anthropic (Claude) and OpenAI models
- Two benchmark repositories: `fastapi-template` and `djangopackages`
- 30 benchmark tasks (15 per repository)
- Automated test execution and result tracking
- Report generation with pass/fail deltas
- Experimental prompt modes: `no_kb` (instructions only) and `swapped` (cross-repo KB)

### Infrastructure
- Comprehensive documentation (README, CONTRIBUTING)
- Task definition YAML schema
- Prompt generation scripts

### Repositories Benchmarked
- **fastapi-template** - Full-stack FastAPI + React template
- **djangopackages** - Django Packages community directory

---

## [Unreleased]

### Planned
- Additional benchmark repositories
- Multi-turn conversation benchmarks
- Automated KB generation from Aspect Code extension
