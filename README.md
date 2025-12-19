# PromptDesign

A CLI tool with web UI for evaluating prompts in Markdown files, assessing effectiveness, and suggesting improvements.

## Features

- **Heuristic Analysis** - Scores prompts on 6 dimensions:
  - Clarity (readability, sentence structure)
  - Specificity (concrete details, avoids vague terms)
  - Structure (logical organization)
  - Completeness (context, constraints, examples)
  - Output Format (response expectations)
  - Guardrails (boundaries, safety constraints)

- **LLM Analysis** - Claude-powered deep analysis for:
  - Ambiguity detection
  - Missing context identification
  - Prompt injection risks
  - Improvement suggestions

- **Web UI** - Interactive dashboard with:
  - Drag-and-drop file upload
  - Radar chart visualization
  - Issue cards with suggestions

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm

## Installation

### 1. Clone and navigate to the project

```bash
git clone https://github.com/youruser/promptdesign.git
cd promptdesign
```

### 2. Install Python dependencies

```bash
pip install -e .
```

### 3. Install and build frontend

```bash
cd frontend
npm install
npm run build
cd ..
```

### 4. Set up environment (required for LLM features)

Copy the example environment file and add your API key:

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key
```

Or set environment variable directly:
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

## Usage

### Start the Web UI

```bash
# Start server (opens browser automatically)
prompteval serve

# Start with a specific file
prompteval serve examples/sample-prompts.md

# Specify port
prompteval serve --port 3000

# Don't auto-open browser
prompteval serve --no-browser
```

Then open http://127.0.0.1:8080 in your browser.

### CLI-Only Analysis

```bash
# Run heuristic analysis
prompteval analyze prompts.md

# Verbose output with all dimensions
prompteval analyze prompts.md -v

# Save results to JSON
prompteval analyze prompts.md -o report.json
```

### Other Commands

```bash
# Validate a prompt file format
prompteval validate prompts.md

# Create a sample prompts.md file
prompteval init
```

### Custom Analysis Rules

You can customize the heuristic analysis rules using YAML config files:

```bash
# Use a custom config file
prompteval analyze prompts.md --config config/strict_rules.yaml

# Also works with check command
prompteval check "Your prompt" --config my-rules.yaml
```

Config files let you customize:
- **Thresholds** (min word count, max sentence length)
- **Dimension weights** (importance of each scoring dimension)
- **Term lists** (vague terms, guardrail markers, etc.)

See `config/default_rules.yaml` for the full list of configurable options, or `config/strict_rules.yaml` for an example of a stricter rule set.

## Development Mode

For development with hot-reload:

**Terminal 1 - Backend:**
```bash
uvicorn backend.app:app --reload --port 8080
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 (frontend dev server proxies API calls to backend).

## Markdown Formats

PromptDesign supports two formats for defining prompts:

### Format 1: Heading-Based (Multiple Prompts)

Use for files containing multiple system/user prompts:

```markdown
# My Prompts

## System Prompt: Assistant Name
Your system prompt content here...

## User Prompt: Task Name
Your user prompt content here...
```

**Parsing Rules:**
- `## System Prompt` or `## System Prompt: <name>` → system prompt
- `## User Prompt` or `## User Prompt: <name>` → user prompt
- Content between headings = prompt text

### Format 2: YAML Frontmatter (AI Agent Skills)

Use for AI agent skills with metadata:

```markdown
---
name: my-skill
description: A helpful skill that does X
license: MIT
version: 1.0.0
author: Your Name
tags: [productivity, automation]
---

Your skill prompt instructions here...

This format is ideal for:
- AI agent skills and capabilities
- Prompts with metadata requirements
- Single-purpose prompt files
```

**Supported Frontmatter Fields:**
- `name` - Skill identifier (required)
- `description` - What the skill does (required)
- `license` - License information
- `version` - Semantic version
- `author` - Creator name
- `tags` - List of tags for categorization

## Project Structure

```
promptdesign/
├── cli/                    # CLI entry point
│   ├── main.py            # Typer commands
│   └── parser.py          # Markdown parser
├── backend/               # FastAPI server
│   ├── app.py            # Main application
│   ├── routes/           # API endpoints
│   └── services/         # Analysis engines
├── frontend/             # React application
│   ├── src/
│   └── dist/             # Built frontend (after npm run build)
├── examples/             # Sample prompt files
├── pyproject.toml
└── README.md
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | For LLM features | Claude API key for deep analysis |

## LLM Features API

The LLM-powered features require an `ANTHROPIC_API_KEY` in your `.env` file.

### LLM Analysis

Deep analysis using Claude to detect ambiguities, missing context, and injection risks:

```bash
# Start LLM analysis (async)
curl -X POST http://localhost:8080/api/analysis/llm \
  -H "Content-Type: application/json" \
  -d '{"prompt_id": "your-prompt-id"}'

# Response: {"job_id": "abc123", "status": "pending"}

# Check status
curl http://localhost:8080/api/analysis/llm/abc123/status

# Response when complete:
# {
#   "job_id": "abc123",
#   "status": "completed",
#   "result": {
#     "ambiguities": [...],
#     "missing_context": [...],
#     "injection_risks": [...],
#     "best_practice_issues": [...],
#     "suggested_revision": "...",
#     "revision_explanation": "..."
#   }
# }
```

### Generate Suggestions

Get AI-powered improvement suggestions:

```bash
curl -X POST http://localhost:8080/api/analysis/suggestions \
  -H "Content-Type: application/json" \
  -d '{"prompt_id": "your-prompt-id", "focus_areas": ["clarity", "specificity"]}'

# Response:
# {
#   "original": "...",
#   "suggested": "...",
#   "explanation": "...",
#   "changes": [
#     {"original": "...", "replacement": "...", "reason": "..."}
#   ]
# }
```

## Troubleshooting

### "Frontend not built" message

Run the frontend build:
```bash
cd frontend && npm install && npm run build
```

### 404 errors on root path

Make sure the frontend is built and restart the server:
```bash
cd frontend && npm run build
cd .. && prompteval serve
```

### TypeScript build errors

Check for any unused imports and fix them, then rebuild:
```bash
cd frontend && npm run build
```

## License

MIT
