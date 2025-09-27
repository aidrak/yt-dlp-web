# Claude Docker Template Setup

## Using the Template

### Option 1: Command Palette (Recommended)
1. Open VSCode
2. Create/open an empty folder for your new project
3. Press `Ctrl+Shift+P` (Windows/Linux) or `Cmd+Shift+P` (Mac)
4. Type "Project: Create Project From Template"
5. Select "Claude Docker Template" from the list
6. Follow the prompts to customize:
   - Project name (slug auto-generated)

### Option 2: Manual Setup
1. Copy this template directory to your projects folder
2. Find and replace all placeholders manually:
   - `yt-dlp-web` → Your Project Name
   - `yt-dlp-web` → auto-generated from project name

## Setting Up the Template for Reuse

### Installing as VSCode Template
1. Open this template directory in VSCode
2. Press `Ctrl+Shift+P` and run "Project: Save Project As Template"
3. Name it "Claude Docker Template"
4. The template will be saved and available for future use

### Template Location
Templates are stored in:
- **Windows**: `%APPDATA%/Code/User/ProjectTemplates/`
- **macOS**: `~/Library/Application Support/Code/User/ProjectTemplates/`
- **Linux**: `~/.config/Code/User/ProjectTemplates/`

## What's Included

### Claude Code Integration
- `.claude/CLAUDE.md` - Project rules and context
- `.claude/settings.json` - Claude Code configuration
- `.claude/commands/` - Custom commands for testing, debugging, deployment
- `.claude/agents/` - Custom code review agent

### Development Environment
- `.devcontainer/` - Dev container configuration
- `.vscode/` - VSCode settings and extensions
- Docker configuration with multi-stage builds
- Python project with ruff, mypy, pytest

### CI/CD & Deployment
- GitHub Actions workflows
- Docker Compose for local development
- Unraid deployment configuration

## Next Steps
1. Update `.env.example` with your actual environment variables
2. Configure your Docker registry in `docker-compose.yml`
3. Update the GitHub workflows with your deployment targets
4. Start developing!