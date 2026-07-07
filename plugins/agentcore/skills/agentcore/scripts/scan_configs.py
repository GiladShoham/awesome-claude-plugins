#!/usr/bin/env python3
"""Scan a repository for AI assistant configuration files across 15 known formats.

Usage:
    python3 scan_configs.py --repo-root /path/to/repo [--format json|text]

Outputs a migration-inventory.json with all discovered artifacts.
"""

import argparse
import json
import os
import sys
import re
import yaml
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Source format registry
# ---------------------------------------------------------------------------
SOURCE_FORMATS = [
    {
        "name": "GitHub Copilot",
        "id": "github-copilot",
        "paths": [".github/copilot-instructions.md", ".github/agents", ".github/skills"],
        "patterns": {"agents": "*.agent.md", "skills": "SKILL.md"},
    },
    {
        "name": "Claude Code",
        "id": "claude-code",
        "paths": [".claude", "CLAUDE.md", "claude.md"],
        "patterns": {"skills": "SKILL.md", "mcp": "mcp.json", "settings": "settings.json"},
    },
    {
        "name": "Cursor",
        "id": "cursor",
        "paths": [".cursor", ".cursorrules"],
        "patterns": {"rules": "rules", "mcp": "mcp.json"},
    },
    {
        "name": "Cline",
        "id": "cline",
        "paths": [".cline", ".clinerules"],
        "patterns": {"mcp": "mcp_settings.json"},
    },
    {
        "name": "Codex",
        "id": "codex",
        "paths": ["codex.md", "CODEX.md"],
        "patterns": {},
    },
    {
        "name": "Windsurf",
        "id": "windsurf",
        "paths": [".windsurf"],
        "patterns": {"rules": "rules", "skills": "SKILL.md"},
    },
    {
        "name": "Antigravity",
        "id": "antigravity",
        "paths": [".agent/skills"],
        "patterns": {"skills": "SKILL.md"},
    },
    {
        "name": "Gemini CLI",
        "id": "gemini-cli",
        "paths": [".gemini"],
        "patterns": {"rules": "rules", "skills": "SKILL.md", "settings": "settings.json"},
    },
    {
        "name": "Deep Agents",
        "id": "deep-agents",
        "paths": [".deep-agents"],
        "patterns": {"configs": "*.yaml"},
    },
    {
        "name": "Dexto",
        "id": "dexto",
        "paths": [".dexto"],
        "patterns": {"configs": "*.yaml"},
    },
    {
        "name": "Firebender",
        "id": "firebender",
        "paths": [".firebender"],
        "patterns": {"configs": "*.json"},
    },
    {
        "name": "Kimi Code CLI",
        "id": "kimi-code-cli",
        "paths": [".kimi"],
        "patterns": {"configs": "*.yaml"},
    },
    {
        "name": "OpenCode",
        "id": "opencode",
        "paths": [".opencode"],
        "patterns": {"skills": "skill"},
    },
    {
        "name": "Warp",
        "id": "warp",
        "paths": [".warp"],
        "patterns": {"workflows": "*.yaml"},
    },
    {
        "name": "agentic-core",
        "id": "agentic-core",
        "paths": [
            ".github/agents", ".github/skills", ".agents/skills",
            ".github/hooks", ".github/memory", ".github/prompts",
        ],
        "patterns": {
            "agents": "*.agent.md", "skills": "SKILL.md",
            "hooks": "hooks.json", "prompts": "*.prompt.md",
        },
    },
]

SECRET_PATTERNS = re.compile(
    r"(KEY|SECRET|TOKEN|PASSWORD|PASSCODE|CREDENTIAL|AUTH|USERCODE)", re.IGNORECASE
)


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_agent_md(filepath: Path) -> dict[str, Any]:
    """Parse a .agent.md file into structured data."""
    text = filepath.read_text(encoding="utf-8", errors="replace")
    result: dict[str, Any] = {
        "type": "agent",
        "source_file": str(filepath),
        "name": filepath.stem.replace(".agent", ""),
        "frontmatter": {},
        "persona": {},
        "body": "",
    }

    # Extract YAML frontmatter
    fm_match = re.match(r"^---\n(.*?)\n---\n?(.*)", text, re.DOTALL)
    if fm_match:
        try:
            result["frontmatter"] = yaml.safe_load(fm_match.group(1)) or {}
        except yaml.YAMLError:
            result["frontmatter"] = {"_raw": fm_match.group(1)}
        result["body"] = fm_match.group(2)
    else:
        result["body"] = text

    result["description"] = result["frontmatter"].get("description", "")
    result["tools"] = result["frontmatter"].get("tools", [])
    result["handoffs"] = result["frontmatter"].get("handoffs", [])

    # Extract persona block
    persona_match = re.search(
        r"##\s*Persona\s*\n(.*?)(?=\n##\s|\Z)", result["body"], re.DOTALL
    )
    if persona_match:
        persona_text = persona_match.group(1)
        for field in ["role", "identity", "communication_style"]:
            m = re.search(rf"-\s*\**{field}\**\s*:\s*(.+)", persona_text, re.IGNORECASE)
            if m:
                result["persona"][field] = m.group(1).strip()
        # Extract principles
        principles_match = re.search(
            r"-\s*\**principles\**\s*:\s*\n((?:\s+-\s+.+\n?)+)", persona_text, re.IGNORECASE
        )
        if principles_match:
            result["persona"]["principles"] = [
                line.strip().lstrip("- ")
                for line in principles_match.group(1).strip().split("\n")
                if line.strip()
            ]

    return result


def parse_skill_md(filepath: Path) -> dict[str, Any]:
    """Parse a SKILL.md file into structured data."""
    text = filepath.read_text(encoding="utf-8", errors="replace")
    result: dict[str, Any] = {
        "type": "skill",
        "source_file": str(filepath),
        "name": filepath.parent.name,
        "frontmatter": {},
        "body": "",
        "scripts": [],
        "references": [],
    }

    fm_match = re.match(r"^---\n(.*?)\n---\n?(.*)", text, re.DOTALL)
    if fm_match:
        try:
            result["frontmatter"] = yaml.safe_load(fm_match.group(1)) or {}
        except yaml.YAMLError:
            result["frontmatter"] = {"_raw": fm_match.group(1)}
        result["body"] = fm_match.group(2)
    else:
        result["body"] = text

    result["description"] = result["frontmatter"].get("description", "")
    result["name"] = result["frontmatter"].get("name", result["name"])

    # Discover scripts and references
    skill_dir = filepath.parent
    scripts_dir = skill_dir / "scripts"
    refs_dir = skill_dir / "references"
    if scripts_dir.is_dir():
        result["scripts"] = [str(p) for p in scripts_dir.rglob("*") if p.is_file()]
    if refs_dir.is_dir():
        result["references"] = [str(p) for p in refs_dir.rglob("*") if p.is_file()]

    return result


def parse_mcp_config(filepath: Path, source_id: str) -> list[dict[str, Any]]:
    """Parse MCP server configuration from JSON."""
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    servers = data.get("mcpServers", data)
    if not isinstance(servers, dict):
        return []

    results = []
    for name, config in servers.items():
        if not isinstance(config, dict):
            continue
        server: dict[str, Any] = {
            "type": "mcp_server",
            "source_file": str(filepath),
            "source_tool": source_id,
            "name": name,
            "command": config.get("command", ""),
            "args": config.get("args", []),
            "url": config.get("url", ""),
            "transport": "stdio" if config.get("command") else "sse",
            "env_vars": {},
            "disabled": config.get("disabled", False),
        }
        # Extract env vars, classify secrets
        for k, v in config.get("env", {}).items():
            server["env_vars"][k] = {
                "value": "<REDACTED>" if SECRET_PATTERNS.search(k) else str(v),
                "is_secret": bool(SECRET_PATTERNS.search(k)),
            }
        results.append(server)
    return results


def parse_hooks_json(filepath: Path) -> list[dict[str, Any]]:
    """Parse hooks.json configuration."""
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    hooks = []
    items = data if isinstance(data, list) else [data]
    for item in items:
        if not isinstance(item, dict):
            continue
        for event in ["sessionStart", "sessionEnd", "errorOccurred",
                      "SessionStart", "SessionEnd", "PostToolUseFailure"]:
            if event in item:
                hooks.append({
                    "type": "hook",
                    "source_file": str(filepath),
                    "event": event,
                    "config": item[event],
                })
    return hooks


def parse_plaintext_rules(filepath: Path, source_id: str) -> dict[str, Any]:
    """Parse plain-text rules/instructions files."""
    text = filepath.read_text(encoding="utf-8", errors="replace")
    return {
        "type": "prompt",
        "source_file": str(filepath),
        "source_tool": source_id,
        "name": filepath.stem,
        "content_length": len(text),
        "content_preview": text[:500],
    }


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------

def scan_repo(repo_root: Path) -> dict[str, Any]:
    """Scan repository for all AI assistant configurations."""
    inventory: dict[str, Any] = {
        "repo_root": str(repo_root),
        "sources_detected": [],
        "agents": [],
        "skills": [],
        "mcp_servers": [],
        "hooks": [],
        "memory": [],
        "prompts": [],
    }

    for fmt in SOURCE_FORMATS:
        detected = False

        for path_str in fmt["paths"]:
            full_path = repo_root / path_str

            if not full_path.exists():
                continue

            detected = True

            # Single file (instructions, rules, etc.)
            if full_path.is_file():
                if full_path.suffix == ".md" or full_path.name in ("rules", ".cursorrules", ".clinerules"):
                    inventory["prompts"].append(
                        parse_plaintext_rules(full_path, fmt["id"])
                    )
                elif full_path.name.endswith(".json"):
                    inventory["mcp_servers"].extend(
                        parse_mcp_config(full_path, fmt["id"])
                    )
                continue

            # Directory scanning
            if not full_path.is_dir():
                continue

            # Agents
            for agent_file in full_path.rglob("*.agent.md"):
                inventory["agents"].append(parse_agent_md(agent_file))

            # Skills
            for skill_file in full_path.rglob("SKILL.md"):
                inventory["skills"].append(parse_skill_md(skill_file))

            # MCP configs
            for mcp_name in ("mcp.json", "mcp_settings.json"):
                mcp_file = full_path / mcp_name
                if mcp_file.is_file():
                    inventory["mcp_servers"].extend(
                        parse_mcp_config(mcp_file, fmt["id"])
                    )

            # Hooks
            hooks_file = full_path / "hooks.json"
            if hooks_file.is_file():
                inventory["hooks"].extend(parse_hooks_json(hooks_file))

            # Memory directories
            if "memory" in path_str:
                for md_file in full_path.rglob("*.md"):
                    inventory["memory"].append({
                        "type": "memory",
                        "source_file": str(md_file),
                        "name": md_file.stem,
                        "memory_type": _classify_memory(md_file, repo_root),
                    })

            # Prompts
            if "prompts" in path_str:
                for prompt_file in full_path.rglob("*.prompt.md"):
                    inventory["prompts"].append(
                        parse_plaintext_rules(prompt_file, fmt["id"])
                    )

            # Plain rules files
            rules_file = full_path / "rules"
            if rules_file.is_file():
                inventory["prompts"].append(
                    parse_plaintext_rules(rules_file, fmt["id"])
                )

        if detected:
            inventory["sources_detected"].append(fmt["name"])

    # Deduplicate (same file may be found by multiple format scanners)
    inventory["agents"] = _dedup_by_key(inventory["agents"], "source_file")
    inventory["skills"] = _dedup_by_key(inventory["skills"], "source_file")
    inventory["mcp_servers"] = _dedup_by_key(inventory["mcp_servers"], "name")

    return inventory


def _classify_memory(filepath: Path, repo_root: Path) -> str:
    """Classify memory file type."""
    rel = filepath.relative_to(repo_root)
    parts = rel.parts
    if "constitution" in filepath.name:
        return "constitution"
    if "agents" in parts:
        return "agent"
    if "features" in parts:
        return "feature"
    return "general"


def _dedup_by_key(items: list[dict], key: str) -> list[dict]:
    """Remove duplicates based on a key."""
    seen: set[str] = set()
    result = []
    for item in items:
        val = item.get(key, "")
        if val not in seen:
            seen.add(val)
            result.append(item)
    return result


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def print_summary(inventory: dict[str, Any]) -> None:
    """Print discovery summary box."""
    print("╔═══════════════════════════════════════════════════╗")
    print("║          AgentCore Migration — Discovery           ║")
    print("╠═══════════════════════════════════════════════════╣")
    print(f"║  Agents found:      {len(inventory['agents']):<28}║")
    print(f"║  Skills found:      {len(inventory['skills']):<28}║")
    print(f"║  MCP servers:       {len(inventory['mcp_servers']):<28}║")
    print(f"║  Hooks:             {len(inventory['hooks']):<28}║")
    print(f"║  Prompts:           {len(inventory['prompts']):<28}║")
    print(f"║  Memory files:      {len(inventory['memory']):<28}║")
    sources = ", ".join(inventory["sources_detected"]) or "none"
    # Wrap source line
    print(f"║  Sources: {sources:<40}║")
    print("╚═══════════════════════════════════════════════════╝")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan repo for AI assistant configs")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--format", choices=["json", "text"], default="text",
                        help="Output format")
    parser.add_argument("--output", default="migration-inventory.json",
                        help="Output file path (json format only)")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not repo_root.is_dir():
        print(f"Error: {repo_root} is not a directory", file=sys.stderr)
        sys.exit(1)

    inventory = scan_repo(repo_root)

    if args.format == "json":
        output_path = Path(args.output)
        output_path.write_text(json.dumps(inventory, indent=2, default=str))
        print(f"Inventory written to: {output_path}")
    
    print_summary(inventory)


if __name__ == "__main__":
    main()
