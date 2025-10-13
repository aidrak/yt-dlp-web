# Python Development with Gitea CI/CD

Python development repository with automated code quality checks and Gitea Actions CI/CD.

## Project Structure

- `src/` - Python application source code
- `tests/` - Pytest test suite
- `tools/` - Development utilities
- `venv/` - Python virtual environment
- `.claude/` - Claude Code configuration
  - `docs/` - Detailed documentation (read on-demand)
  - `hooks/` - Automated quality check hooks
  - `commands/` - Custom slash commands
  - `agents/` - Specialized agents
  - `settings.json` - Project configuration

## Essential Commands

**Development**: `source venv/bin/activate` → `pip install -r requirements-dev.txt` → `python tools/run_tests.py`

**Code Quality**: `ruff check .` / `ruff format .` / `pytest --cov=src`

**CI/CD**: Tag push (`git tag v1.0.x && git push origin v1.0.x`) triggers Gitea Actions → Docker build on Unraid → `gitea.odieserver.com/brandon-dev/[repo-name]:latest`

**Tools**: Ruff (lint/format), Pylance/mypy (type check), Pytest (testing). See `.claude/docs/LINTING.md` and `.claude/docs/TESTING.md` for details.

## Automated Hooks

Configured in `.claude/settings.json`:

- **Pre-Tool-Use**: Environment setup and project rules reminder
- **Post-Edit**: Auto-format, lint, validate, and optionally test Python files

## CI/CD & Docker

**Registry**: `gitea.odieserver.com/brandon-dev/[repo-name]`
**Trigger**: Tag push (`v*.*.*`) → Gitea Actions runner (Ubuntu VM) → Docker build (Unraid via SSH)
**Details**: `.claude/docs/GITEA_CICD_SETUP.md`

## Core Development Rules

### Never Overcomplicate
- Fix root causes, don't add complexity layers
- Use virtual environment when available
- Address Pylance errors and warnings
- NEVER delete code as a remedy for fixing errors - refactor or fix properly

### Code Quality Standards
- **Type Hints**: Always use type annotations
- **Docstrings**: Document all public functions (Google or NumPy style)
- **Testing**: Write tests alongside code
- **Line Length**: 88 characters (Black standard)
- **Imports**: Auto-sorted by Ruff

### Error Handling
- NEVER delete code just because it has errors
- Fix the underlying issue or refactor properly
- If code must be removed, understand and document why
- Deletion is not a substitute for debugging

### Security
- Hardcoded secrets OK for development - VERIFY removal before production
- ALWAYS validate user input
- Use environment variables for production config
- Never commit real secrets to version control

## Detailed Documentation

Comprehensive guides in `.claude/docs/` (read on-demand):
- **LINTING.md** - Linting, formatting, type checking
- **TESTING.md** - Pytest, coverage, mocking, best practices
- **GITEA_CICD_SETUP.md** - CI/CD pipeline setup and troubleshooting

This streamlined setup ensures high-quality code with minimal manual intervention and efficient token usage through on-demand documentation.

---

<critical_rules>
  <rule_1>NEVER delete code to fix errors - refactor or fix properly. Deletion is not debugging.</rule_1>
  <rule_2>Always use type hints for all function signatures</rule_2>
  <rule_3>Write tests alongside new code (pytest)</rule_3>
  <rule_4>Use virtual environment when available (venv/)</rule_4>
  <rule_5>Address Pylance errors and warnings - don't ignore them</rule_5>
  <rule_6>Display these critical_rules verbatim at the END of every response</rule_6>
</critical_rules>
