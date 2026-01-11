# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by emailing the maintainers directly rather than opening a public issue.

## API Keys

**Never commit API keys to this repository.**

This project requires API keys for LLM providers (Anthropic, OpenAI). These should be:

1. Stored in a `.env` file (which is gitignored)
2. Passed via `--api-key` command line argument
3. Set as environment variables

See `.env.example` for the expected format.

## Sensitive Data

The following directories contain potentially sensitive experiment data and are gitignored:

- `src/results/` - Benchmark results
- `src/responses/` - Raw LLM responses  
- `src/reports/` - Generated reports
- `repos/` - Cloned target repositories

## Best Practices

- Never include real API keys in issues, PRs, or discussions
- Review your commits before pushing to ensure no secrets are included
- Use environment variables for all sensitive configuration
