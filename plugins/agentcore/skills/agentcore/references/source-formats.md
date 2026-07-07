# Source Format Detection Table

Detection rules for `scan_configs.py`. Each entry defines paths to check, file patterns, and what to extract.

## Format Registry

| # | Tool | Config paths | File patterns | Extracts |
|---|------|-------------|---------------|----------|
| 1 | **GitHub Copilot** | `.github/copilot-instructions.md`, `.github/agents/`, `.github/skills/` | `*.agent.md`, `SKILL.md` | Agents, skills, instructions |
| 2 | **Claude Code** | `.claude/`, `CLAUDE.md`, `claude.md` | `settings.json`, `mcp.json`, `SKILL.md` | Skills, MCP, settings |
| 3 | **Cursor** | `.cursor/`, `.cursorrules` | `rules`, `mcp.json`, `*.mdc` | Rules, MCP configs |
| 4 | **Cline** | `.cline/`, `.clinerules` | `mcp_settings.json` | Rules, MCP configs |
| 5 | **Codex** | `codex.md`, `CODEX.md` | — | Instructions |
| 6 | **Windsurf** | `.windsurf/` | `rules`, `SKILL.md` | Rules, skills |
| 7 | **Antigravity** | `.agent/skills/` | `SKILL.md` | Skills |
| 8 | **Gemini CLI** | `.gemini/` | `rules`, `SKILL.md`, `settings.json` | Rules, skills |
| 9 | **Deep Agents** | `.deep-agents/` | `*.yaml`, `*.json` | Agent configs |
| 10 | **Dexto** | `.dexto/` | `*.yaml`, `*.json` | Agent configs |
| 11 | **Firebender** | `.firebender/` | `*.json`, `*.yaml` | Agent configs |
| 12 | **Kimi Code CLI** | `.kimi/` | `*.yaml`, `*.json` | Agent configs |
| 13 | **OpenCode** | `.opencode/` | `skill`, `*.md` | Skills |
| 14 | **Warp** | `.warp/` | `*.yaml`, `*.json` | Workflow configs |
| 15 | **agentic-core** | `.github/agents/`, `.github/skills/`, `.agents/skills/`, `.github/hooks/`, `.github/memory/`, `.github/prompts/` | `*.agent.md`, `SKILL.md`, `hooks.json` | Full ecosystem |

## Parsing Rules Per Format

### GitHub Copilot / agentic-core (`.github/`)

**Agents** — located in `.github/agents/*.agent.md`:
- YAML frontmatter: `description`, `handoffs`, `tools`
- Body: persona block (role, identity, communication_style, principles), workflow steps
- Parse frontmatter with YAML, body as markdown sections

**Skills** — located in `.github/skills/<name>/SKILL.md`:
- YAML frontmatter: `name`, `description`
- Body: instructions, workflow
- Sub-directories: `scripts/`, `references/`, `assets/`

**Hooks** — located in `.github/hooks/hooks.json`:
- JSON array of event → script mappings
- Events: `sessionStart`, `sessionEnd`, `errorOccurred`
- Scripts in `.github/hooks/scripts/`

**Memory** — located in `.github/memory/`:
- `constitution.md` — governance rules
- `agents/<name>.md` — per-agent memory
- `features/<name>/` — feature tracking (tasks, progress, phase)

**Prompts** — located in `.github/prompts/`:
- `*.prompt.md` files with reusable prompt templates

### Claude Code (`.claude/`)

**Skills** — located in `.claude/skills/<name>/`:
- Same `SKILL.md` format as GitHub Copilot
- May include `scripts/`, `references/`

**MCP servers** — located in `.claude/mcp.json` or project `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "@org/mcp-server"],
      "env": { "API_KEY": "..." }
    }
  }
}
```

**Settings** — `.claude/settings.json`:
- `allowedTools`, `customInstructions`, model preferences

### Cursor (`.cursor/`)

**Rules** — `.cursor/rules` or `.cursorrules`:
- Plain text instructions (system prompt equivalent)
- May use frontmatter with `description`, `globs`

**MCP** — `.cursor/mcp.json`:
- Same structure as Claude MCP config

### Cline (`.cline/`)

**Rules** — `.clinerules`:
- Plain text instructions

**MCP** — `.cline/mcp_settings.json`:
```json
{
  "mcpServers": {
    "server-name": {
      "command": "...",
      "args": [...],
      "env": {...},
      "disabled": false
    }
  }
}
```

### Codex

**Instructions** — `codex.md` or `CODEX.md`:
- Plain markdown with instructions for OpenAI Codex agent

### Windsurf (`.windsurf/`)

**Rules** — `.windsurf/rules`:
- Plain text instructions

**Skills** — `.windsurf/skills/<name>/SKILL.md`:
- Same SKILL.md format (may be symlinks to `.claude/skills/`)

### Gemini CLI (`.gemini/`)

**Rules** — `.gemini/rules` or `.gemini/settings.json`:
- Plain text or JSON config with system instructions

**Skills** — `.gemini/skills/<name>/SKILL.md`

### Generic Formats (Deep Agents, Dexto, Firebender, Kimi, Warp)

These tools use YAML or JSON configs. Extract:
- Agent name and description
- System prompt / instructions
- Tool definitions
- Model configuration
- Environment variables
