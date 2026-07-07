#!/usr/bin/env python3
"""Generate an AgentCore project scaffold from a migration inventory.

Harness-first: agents that are persona + skills + standard tools become
declarative harnesses (app/<name>/harness.json + system-prompt.md). Agents
that reference bundled scripts become Strands code runtimes (app/<name>/main.py).

Usage:
    python3 generate_project.py \
        --inventory migration-inventory.json \
        --output-dir ./agentcore-project \
        --region us-west-2
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

SECRET_PATTERNS = re.compile(
    r"(KEY|SECRET|TOKEN|PASSWORD|PASSCODE|CREDENTIAL|AUTH|USERCODE)", re.IGNORECASE
)

# CLI 0.22.0 defaults (verified via `agentcore create` / `add agent` output)
HARNESS_MODEL_ID = "global.anthropic.claude-sonnet-4-6"
RUNTIME_MODEL_ID = "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
FALLBACK_MODEL_ID = "amazon.nova-lite-v1:0"  # if Anthropic model access is not enabled


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def slugify(value: str) -> str:
    """Return a CLI-safe resource name (alphanumeric + underscores, start with letter)."""
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip().lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    # Must start with a letter
    if slug and not slug[0].isalpha():
        slug = "a" + slug
    return slug[:48] or "unnamed"


def project_slugify(value: str) -> str:
    """Return a project-safe name (alphanumeric only, start with letter, max 23 chars)."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "", value.strip().lower())
    if slug and not slug[0].isalpha():
        slug = "p" + slug
    return slug[:23] or "project"


def env_vars_to_array(env_dict: dict[str, str]) -> list[dict[str, str]]:
    """Convert env vars dict to AgentCore runtime array format [{name, value}]."""
    return [{"name": k, "value": v} for k, v in env_dict.items()]


def gateway_slugify(value: str) -> str:
    """Return a gateway-safe name (alphanumeric + hyphens, max 100 chars)."""
    slug = re.sub(r"[^a-zA-Z0-9-]+", "-", value.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    if slug and not slug[0].isalpha():
        slug = "g" + slug
    return slug[:100] or "gateway"


def classify_env_var(name: str) -> str:
    """Classify an env var as secret or config."""
    return "secret" if SECRET_PATTERNS.search(name) else "config"


def flatten_persona_to_prompt(agent: dict[str, Any]) -> str:
    """Convert agent persona + body into a system prompt string."""
    parts: list[str] = []
    persona = agent.get("persona", {})

    if persona.get("role"):
        parts.append(f"You are {persona['role']}.")
    if persona.get("identity"):
        parts.append(f"Identity: {persona['identity']}.")
    if persona.get("communication_style"):
        parts.append(f"Communication style: {persona['communication_style']}.")
    if persona.get("principles"):
        principles_text = "; ".join(
            f"({i + 1}) {p}" for i, p in enumerate(persona["principles"])
        )
        parts.append(f"Principles: {principles_text}.")

    body = agent.get("body", "")
    body = re.sub(r"##\s*Persona\s*\n.*?(?=\n##\s|\Z)", "", body, flags=re.DOTALL)
    # Drop the leading H1 title (e.g. "# CVE Triage") — it's the agent name, already implied.
    body = re.sub(r"^\s*#\s+.*\n", "", body)
    body = body.strip()
    if body:
        # If the body already carries its own "## Instructions" heading, don't double it.
        if re.match(r"##\s*Instructions\b", body, re.IGNORECASE):
            parts.append(f"\n{body}")
        else:
            parts.append(f"\n## Instructions\n{body}")

    return "\n".join(parts).strip()


def map_allowed_tools(agent: dict[str, Any]) -> list[str]:
    """Map source assistant tool names to AgentCore tool categories."""
    tool_map = {
        "read": "file_operations",
        "search": "file_operations",
        "file": "file_operations",
        "execute": "shell",
        "shell": "shell",
        "bash": "shell",
        "browser": "agentcore_browser",
        "web": "agentcore_browser",
        "code_interpreter": "agentcore_code_interpreter",
        "*": "*",
    }
    tools = agent.get("tools", []) or []
    if not tools:
        return ["file_operations", "shell"]
    mapped = {
        tool_map.get(t.lower() if isinstance(t, str) else str(t), str(t))
        for t in tools
    }
    return sorted(mapped)


def collect_runtime_env(mcp_servers: list[dict]) -> dict[str, str]:
    """Collect non-secret MCP env vars for runtime configuration."""
    env_vars: dict[str, str] = {}
    for mcp in mcp_servers:
        for var_name, var_info in mcp.get("env_vars", {}).items():
            if not var_info.get("is_secret"):
                env_vars[var_name] = var_info.get("value", "")
    return env_vars


def collect_secret_names(mcp_servers: list[dict]) -> list[str]:
    """Collect secret env var names that must become AgentCore Identity credentials."""
    names: list[str] = []
    for mcp in mcp_servers:
        for var_name, var_info in mcp.get("env_vars", {}).items():
            if var_info.get("is_secret") and var_name not in names:
                names.append(var_name)
    return names


def find_agent_script_refs(agent: dict[str, Any], repo_root: Path) -> list[Path]:
    """Find .github/scripts references inside an agent body."""
    body = agent.get("body", "")
    refs = re.findall(r"(?:^|\s)(?:\./)?\.github/scripts/([^\s`'\"]+\.(?:sh|py))", body)
    paths: list[Path] = []
    for ref in refs:
        path = (repo_root / ".github" / "scripts" / ref).resolve()
        if path.is_file() and path not in paths:
            paths.append(path)
    return paths


def is_code_agent(agent: dict[str, Any], repo_root: Path) -> bool:
    """Classify an agent: code runtime iff it bundles scripts it must execute.

    Everything else (persona + skills + standard/MCP tools) becomes a harness.
    """
    return bool(find_agent_script_refs(agent, repo_root))


def declared_skills(agent: dict[str, Any], skills: list[dict]) -> list[dict]:
    """Return the skill records declared in the agent's `skills:` frontmatter."""
    wanted = agent.get("frontmatter", {}).get("skills", [])
    return [s for s in skills if s.get("name") in wanted] if wanted else []


def copy_skill_dirs(matching_skills: list[dict], skills_dir: Path) -> list[str]:
    """Copy skill source directories into skills_dir; return copied skill names."""
    copied: list[str] = []
    for skill in matching_skills:
        source_file = Path(skill.get("source_file", ""))
        skill_source_dir = source_file.parent if source_file.is_file() else None
        if skill_source_dir and skill_source_dir.is_dir():
            name = skill.get("name", skill_source_dir.name)
            copy_tree(skill_source_dir, skills_dir / name)
            copied.append(name)
    return copied


def copy_tree(src: Path, dst: Path) -> None:
    """Copy a directory tree, replacing any existing destination."""
    if dst.exists():
        shutil.rmtree(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst)


def prompt_to_agent(prompt: dict[str, Any]) -> dict[str, Any]:
    """Promote a repo-level instruction file (Copilot/Cursor/Claude rules, ...)
    to a harness agent — its content becomes the system prompt.

    Without this, prompts are silently dropped by generation: an instruction-only
    repo would migrate to an empty project. Harness-first says persona +
    instructions → harness. The scanner stores only a 500-char preview, so read
    the full file from source_file (preview fallback if it's gone).
    """
    source = Path(prompt.get("source_file", ""))
    body = (
        source.read_text(encoding="utf-8", errors="replace")
        if source.is_file()
        else prompt.get("content_preview", "")
    )
    tool = prompt.get("source_tool", "instructions")
    return {
        "name": prompt.get("name", "instructions"),
        "body": body,
        "persona": {},
        "source_file": prompt.get("source_file", ""),
        "description": f"Harness seeded from {tool} instructions",
    }


def promote_prompts_to_agents(inventory: dict[str, Any]) -> int:
    """Fold instruction-file prompts into agents[] as harnesses. Returns count.

    Existing agents (and already-promoted prompts) win on name collision, so a
    repo with real agents plus a stray .cursorrules doesn't get a shadow harness.
    """
    prompts = inventory.get("prompts", [])
    if not prompts:
        return 0
    agents = inventory.setdefault("agents", [])
    seen = {slugify(a.get("name", "")) for a in agents}
    promoted = 0
    for p in prompts:
        slug = slugify(p.get("name", ""))
        if slug in seen:
            continue
        seen.add(slug)
        agents.append(prompt_to_agent(p))
        promoted += 1
    inventory["prompts"] = []
    return promoted


# ---------------------------------------------------------------------------
# Harness generators (declarative agents)
# ---------------------------------------------------------------------------

def generate_harness_json(agent: dict[str, Any], mcp_servers: list[dict]) -> dict[str, Any]:
    """Generate app/<name>/harness.json (schema verified against CLI 0.22.0).

    Skills are attached afterwards via `agentcore add skill` (see commands script)
    so the CLI normalizes paths; remote MCP tools are pre-populated here.
    """
    tools = [
        {
            "type": "remote_mcp",
            "name": slugify(mcp.get("name", "mcp")),
            "config": {"remoteMcp": {"url": mcp.get("url", "")}},
        }
        for mcp in mcp_servers
        if not mcp.get("disabled") and mcp.get("transport") != "stdio" and mcp.get("url")
    ]
    return {
        "name": slugify(agent.get("name", "unnamed")),
        "model": {"provider": "bedrock", "modelId": HARNESS_MODEL_ID},
        "tools": tools,
        "skills": [],
        "memory": {"mode": "disabled"},
    }


# ---------------------------------------------------------------------------
# Code-runtime generators (custom-logic agents)
# ---------------------------------------------------------------------------

def generate_runtime_metadata(agent: dict[str, Any], mcp_servers: list[dict]) -> dict[str, Any]:
    """Generate reviewable metadata consumed by the migrated entrypoint."""
    return {
        "modelId": RUNTIME_MODEL_ID,
        "systemPrompt": flatten_persona_to_prompt(agent),
        "allowedTools": map_allowed_tools(agent),
        "mcpServers": [
            {
                "name": mcp.get("name", "unnamed"),
                "transport": mcp.get("transport", "unknown"),
                "url": mcp.get("url", ""),
                # Preserve stdio command/args for review (remote MCP leaves these empty).
                "command": mcp.get("command", ""),
                "args": mcp.get("args", []),
                "migrationStatus": "MANUAL" if mcp.get("transport") == "stdio" else "AUTO",
                "note": "stdio MCP must be exposed as a remote MCP endpoint or gateway target"
                if mcp.get("transport") == "stdio" else "remote endpoint can become a Gateway target",
            }
            for mcp in mcp_servers
            if not mcp.get("disabled")
        ],
        "envVars": env_vars_to_array(collect_runtime_env(mcp_servers)),
        "identityCredentials": [slugify(name) for name in collect_secret_names(mcp_servers)],
        "maxIterations": 75,
        "timeoutSeconds": 3600,
    }


def generate_main_py(agent: dict[str, Any]) -> str:
    """Generate a Strands AgentCore Runtime entrypoint (CLI 0.22.0 pattern).

    Streaming entrypoint (stream_async + yield), per-session agent cache,
    automatic skill loading from the baked skills/ directory.
    """
    system_prompt = flatten_persona_to_prompt(agent)
    agent_name = agent.get("name", "agent")
    return f'''#!/usr/bin/env python3
"""AgentCore Runtime entrypoint for the migrated `{agent_name}` agent.

This scaffold preserves the original assistant instructions in DEFAULT_SYSTEM_PROMPT.
Skills baked into the code package (skills/) are appended to the system prompt.
"""

from collections import OrderedDict
from pathlib import Path

from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from model.load import load_model

app = BedrockAgentCoreApp()
log = app.logger

DEFAULT_SYSTEM_PROMPT = {system_prompt!r}


def _discover_skills() -> str:
    """Load SKILL.md content from the baked skills/ directory."""
    skills_dir = Path(__file__).parent / "skills"
    skills_content: list[str] = []
    if skills_dir.is_dir():
        for path in sorted(skills_dir.rglob("SKILL.md")):
            name = path.parent.name
            skills_content.append(f"\\n--- SKILL: {{name}} ---\\n{{path.read_text()}}")
            log.info(f"Loaded skill: {{name}} from {{path}}")
    return "\\n".join(skills_content)


SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT + _discover_skills()

# TODO: Add migrated tools here as @tool functions or MCP clients
tools = []


# One Agent per session_id (best-effort in-process history; LRU-bounded).
def _agent_factory():
    cache: OrderedDict[str, Agent] = OrderedDict()

    def get_or_create(session_id: str) -> Agent:
        if session_id in cache:
            cache.move_to_end(session_id)
            return cache[session_id]
        if len(cache) >= 128:
            cache.popitem(last=False)
        cache[session_id] = Agent(
            model=load_model(),
            system_prompt=SYSTEM_PROMPT,
            tools=tools,
        )
        return cache[session_id]

    return get_or_create


get_or_create_agent = _agent_factory()


@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking {agent_name}...")
    session_id = getattr(context, "session_id", "default-session")
    agent = get_or_create_agent(session_id)

    async for event in agent.stream_async(payload.get("prompt", "")):
        if not isinstance(event, dict) or "event" not in event:
            continue
        yield event


if __name__ == "__main__":
    app.run()
'''


def generate_model_load_py() -> str:
    """Generate model/load.py for Bedrock model loading."""
    return f'''from strands.models.bedrock import BedrockModel


def load_model() -> BedrockModel:
    """Get Bedrock model client using IAM credentials.

    Default: Claude Sonnet (CLI 0.22.0 template default). If Anthropic model
    access is not enabled in this account (ModelNotAccessibleException),
    switch to "{FALLBACK_MODEL_ID}" — available immediately but with low
    daily token quotas (request increase via Service Quotas on ThrottlingException).
    """
    return BedrockModel(model_id="{RUNTIME_MODEL_ID}")
'''


def generate_pyproject_toml(agent_name: str) -> str:
    """Generate pyproject.toml with AgentCore dependencies (CLI 0.22.0 versions)."""
    return f'''[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{agent_name}"
version = "0.1.0"
description = "AgentCore Runtime Application — migrated"
requires-python = ">=3.10"
dependencies = [
    "aws-opentelemetry-distro",
    "bedrock-agentcore >= 1.9.1",
    "botocore[crt] >= 1.35.0",
    "strands-agents >= 1.15.0",
]

[tool.hatch.build.targets.wheel]
packages = ["."]
'''


def generate_dockerfile(has_scripts: bool, has_skills: bool) -> str:
    """Generate a container Dockerfile for BYO AgentCore runtime deployment."""
    lines = [
        "FROM public.ecr.aws/docker/library/python:3.12-slim",
        "",
        "RUN apt-get update && apt-get install -y --no-install-recommends \\",
        "    curl jq git \\",
        "    && rm -rf /var/lib/apt/lists/*",
        "",
        "WORKDIR /app",
        "COPY pyproject.toml /app/pyproject.toml",
        "RUN pip install --no-cache-dir .",
        "",
        "COPY main.py /app/main.py",
        "COPY model/ /app/model/",
        "COPY runtime-metadata.json /app/runtime-metadata.json",
    ]
    if has_scripts:
        lines.extend([
            "COPY scripts/ /app/scripts/",
            "RUN chmod +x /app/scripts/*.sh 2>/dev/null || true",
            'ENV PATH="/app/scripts:${PATH}"',
        ])
    if has_skills:
        lines.append("COPY skills/ /app/skills/")
    lines.extend([
        "",
        "CMD [\"python3\", \"/app/main.py\"]",
        "",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Project config generators
# ---------------------------------------------------------------------------

def generate_agentcore_json(inventory: dict, repo_root: Path) -> dict[str, Any]:
    """Generate agentcore.json (CLI 0.22.0 flat resource arrays).

    Harness agents → harnesses[]; code agents → runtimes[]. Credentials and
    gateways are NOT pre-populated — the commands script adds them via the CLI
    (they need secret values / live endpoints, and pre-populating them would
    make the `add` commands fail with "already exists").
    """
    agents = inventory.get("agents", [])
    env_array = env_vars_to_array(collect_runtime_env(inventory.get("mcp_servers", [])))

    runtimes = []
    harnesses = []
    for i, agent in enumerate(agents):
        name = slugify(agent.get("name", f"agent_{i}"))
        if is_code_agent(agent, repo_root):
            runtime: dict[str, Any] = {
                "name": name,
                "build": "CodeZip",
                "codeLocation": f"app/{name}/",
                "entrypoint": "main.py",
                "runtimeVersion": "PYTHON_3_12",
                "networkMode": "PUBLIC",
                "protocol": "HTTP",
            }
            if env_array:
                runtime["envVars"] = env_array
            runtimes.append(runtime)
        else:
            harnesses.append({"name": name, "path": f"app/{name}"})

    return {
        "$schema": "https://schema.agentcore.aws.dev/v1/agentcore.json",
        "name": project_slugify("migratedagents"),
        "version": 1,
        "managedBy": "CDK",
        "tags": {
            "agentcore:created-by": "agentcore-migration-skill",
        },
        "runtimes": runtimes,
        "harnesses": harnesses,
        "memories": [],
        "knowledgeBases": [],
        "credentials": [],
        "evaluators": [],
        "onlineEvalConfigs": [],
        "agentCoreGateways": [],
        "policyEngines": [],
        "configBundles": [],
        "abTests": [],
        "datasets": [],
        "payments": [],
    }


def detect_aws_account_id() -> str:
    """Auto-detect AWS account ID from configured credentials."""
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ""


def generate_aws_targets(region: str, account_id: str = "") -> list[dict[str, str]]:
    """Generate aws-targets.json — array of {name, account, region}."""
    if not account_id:
        account_id = detect_aws_account_id()
    if not account_id:
        account_id = "<AWS_ACCOUNT_ID>"
        print("⚠️  Could not detect AWS account ID. Replace <AWS_ACCOUNT_ID> in aws-targets.json.", file=sys.stderr)
    return [
        {
            "name": "default",
            "description": f"Default deployment target ({region})",
            "account": account_id,
            "region": region,
        }
    ]


def generate_registry_record(agent: dict[str, Any]) -> dict[str, Any]:
    """Generate a Registry record manifest for an agent."""
    return {
        "name": agent.get("name", "unnamed"),
        "type": "AGENT",
        "description": agent.get("description", ""),
        "metadata": {
            "source_file": agent.get("source_file", ""),
            "migrated_from": "agentic-core",
            "migration_date": "__TIMESTAMP__",
        },
    }


def generate_exec_scripts(hooks: list[dict]) -> dict[str, str]:
    """Generate pre/post exec scripts from lifecycle hooks."""
    scripts: dict[str, str] = {}
    pre_cmds: list[str] = []
    post_cmds: list[str] = []

    for hook in hooks:
        event = hook.get("event", "")
        config = hook.get("config", {})
        if isinstance(config, dict):
            cmd = config.get("command", config.get("script", ""))
        elif isinstance(config, str):
            cmd = config
        else:
            cmd = ""

        if not cmd:
            continue
        if event.lower() == "sessionstart":
            pre_cmds.extend([f"# From: {hook.get('source_file', 'unknown')}", cmd])
        elif event.lower() == "sessionend":
            post_cmds.extend([f"# From: {hook.get('source_file', 'unknown')}", cmd])

    if pre_cmds:
        scripts["pre-invoke.sh"] = "#!/bin/bash\nset -euo pipefail\n\n" + "\n".join(pre_cmds) + "\n"
    if post_cmds:
        scripts["post-invoke.sh"] = "#!/bin/bash\nset -euo pipefail\n\n" + "\n".join(post_cmds) + "\n"
    return scripts


def build_mappings(inventory: dict, repo_root: Path) -> list[dict[str, str]]:
    """Build migration status records for the report."""
    mappings: list[dict[str, str]] = []
    for agent in inventory.get("agents", []):
        name = slugify(agent.get("name", "unnamed"))
        if is_code_agent(agent, repo_root):
            target = f"runtime — app/{name}/main.py"
        else:
            target = f"harness — app/{name}/harness.json"
        mappings.append({"type": "agent", "name": name, "status": "AUTO", "target": target})
    for skill in inventory.get("skills", []):
        mappings.append({
            "type": "skill",
            "name": skill.get("name", "unknown"),
            "status": "AUTO",
            "target": f"app/<agent>/skills/{skill.get('name', 'unknown')}/",
        })
    for mcp in inventory.get("mcp_servers", []):
        status = "MANUAL" if mcp.get("transport") == "stdio" else "AUTO"
        reason = (
            "stdio transport must be published as a remote MCP endpoint or gateway target"
            if status == "MANUAL" else "remote MCP URL attached as harness remote_mcp tool / gateway target"
        )
        mappings.append({"type": "mcp_server", "name": mcp.get("name", "unknown"), "status": status, "reason": reason})
        for var_name, var_info in mcp.get("env_vars", {}).items():
            if var_info.get("is_secret"):
                mappings.append({
                    "type": "secret",
                    "name": var_name,
                    "status": "MANUAL",
                    "reason": f"Add via: agentcore add credential --type api-key --name {slugify(var_name)} --api-key \"${var_name}\"",
                })
    return mappings


def generate_agentcore_commands(inventory: dict, repo_root: Path) -> str:
    """Generate the post-generation command script (verified CLI 0.22.0 verbs).

    Harnesses and runtimes are pre-populated in agentcore.json — this script
    only initializes the project scaffold, attaches skills, and adds
    credentials/gateways (resources that need secret values or live endpoints).
    """
    project_name = project_slugify("migratedagents")
    agents = inventory.get("agents", [])
    skills = inventory.get("skills", [])

    lines = [
        "#!/bin/bash",
        "set -euo pipefail",
        "",
        "# Review placeholders before running. Generated from migration-inventory.json.",
        "# Run from the generated project directory.",
        "",
        "# ──── Initialize project scaffold ────",
        f"# `agentcore create` makes a NESTED ./{project_name}/ scaffold (CDK deps included);",
        "# copy the generated config and app files into it.",
        f"agentcore create --project-name {project_name} --no-agent --skip-git",
        f"cp agentcore/agentcore.json {project_name}/agentcore/agentcore.json",
        f"cp agentcore/aws-targets.json {project_name}/agentcore/aws-targets.json",
        f"cp -R app {project_name}/",
        f"cd {project_name}",
    ]

    # Skills → harness mounts
    skill_lines: list[str] = []
    for agent in agents:
        if is_code_agent(agent, repo_root):
            continue  # code agents get skills baked into their package
        name = slugify(agent.get("name", "unnamed"))
        for skill in declared_skills(agent, skills):
            skill_name = skill.get("name", "skill")
            skill_lines.append(
                f"agentcore add skill --harness {name} --path app/{name}/skills/{skill_name}"
            )
    if skill_lines:
        lines.extend(["", "# ──── Skills → harness mounts ────", *skill_lines])

    # Credentials
    secret_names = collect_secret_names(inventory.get("mcp_servers", []))
    if secret_names:
        lines.extend(["", "# ──── Credentials (secrets → Identity) ────"])
        for secret_name in secret_names:
            lines.append(
                f"agentcore add credential --type api-key --name {slugify(secret_name)} --api-key \"${secret_name}\""
            )

    # Gateways for MCP servers shared across agents (harness remote_mcp tools
    # are already in harness.json; gateways add auth/policy/observability)
    stdio_mcps = [
        mcp for mcp in inventory.get("mcp_servers", [])
        if not mcp.get("disabled") and mcp.get("transport") == "stdio"
    ]
    if stdio_mcps:
        lines.extend(["", "# ──── MANUAL: stdio MCP servers need a remote endpoint first ────"])
        for mcp in stdio_mcps:
            gateway_name = f"{gateway_slugify(mcp.get('name', 'mcp'))}-gateway"
            target_name = slugify(mcp.get("name", "mcp"))
            lines.extend([
                f"# {mcp.get('name', 'mcp')}: publish the stdio server as a remote MCP endpoint, then:",
                f"# agentcore add gateway --name {gateway_name}",
                f"# agentcore add gateway-target --name {target_name} --type mcp-server --endpoint <REMOTE_MCP_URL> --gateway {gateway_name}",
            ])

    # Deploy and invoke
    lines.extend([
        "",
        "# ──── Validate & Deploy ────",
        "agentcore validate",
        "agentcore deploy --yes",
    ])
    for agent in agents[:1]:
        name = slugify(agent.get("name", "unnamed"))
        flag = "--runtime" if is_code_agent(agent, repo_root) else "--harness"
        lines.append(f"agentcore invoke {flag} {name} \"test\"")
    lines.append("")
    return "\n".join(lines)


def generate_migration_report(inventory: dict, mappings: list[dict]) -> str:
    """Generate migration-report.md."""
    lines = [
        "# AgentCore Migration Report",
        "",
        f"**Source repository:** {inventory.get('repo_root', 'unknown')}",
        f"**Sources detected:** {', '.join(inventory.get('sources_detected', []))}",
    ]

    lines.extend([
        "",
        "## Summary",
        "",
        "| Artifact | Count | Auto | Manual | Skip |",
        "|----------|-------|------|--------|------|",
    ])

    type_counts: dict[str, dict[str, int]] = {}
    for mapping in mappings:
        artifact_type = mapping.get("type", "unknown")
        status = mapping.get("status", "AUTO")
        type_counts.setdefault(artifact_type, {"total": 0, "AUTO": 0, "MANUAL": 0, "SKIP": 0})
        type_counts[artifact_type]["total"] += 1
        type_counts[artifact_type][status] = type_counts[artifact_type].get(status, 0) + 1

    for artifact_type, counts in type_counts.items():
        lines.append(
            f"| {artifact_type} | {counts['total']} | {counts.get('AUTO', 0)} "
            f"| {counts.get('MANUAL', 0)} | {counts.get('SKIP', 0)} |"
        )

    agent_targets = [m for m in mappings if m.get("type") == "agent"]
    if agent_targets:
        lines.extend(["", "## Agent Targets", ""])
        for m in agent_targets:
            lines.append(f"- **{m['name']}** → {m.get('target', '')}")

    lines.extend(["", "## Manual Action Items", ""])
    manual_items = [mapping for mapping in mappings if mapping.get("status") == "MANUAL"]
    if manual_items:
        for item in manual_items:
            lines.append(f"- **{item.get('name', 'unknown')}** ({item.get('type')}): {item.get('reason', '')}")
    else:
        lines.append("- None")

    lines.extend([
        "",
        "## Deployment",
        "",
        "1. Review `agentcore/agentcore.json`, `agentcore/aws-targets.json`, harness/app files.",
        "2. Review and run `agentcore-commands.sh`, or apply the same commands manually.",
        "3. Test locally with `agentcore dev` (code agents) before cloud deployment.",
        "",
        "```bash",
        "cd agentcore-project",
        "./agentcore-commands.sh",
        "```",
        "",
    ])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate AgentCore project from inventory")
    parser.add_argument("--inventory", required=True, help="Path to migration-inventory.json")
    parser.add_argument("--output-dir", default="./agentcore-project", help="Output directory")
    parser.add_argument("--region", default="us-west-2", help="AWS region")
    args = parser.parse_args()

    inv_path = Path(args.inventory)
    if not inv_path.is_file():
        print(f"Error: inventory file not found: {inv_path}", file=sys.stderr)
        sys.exit(1)

    inventory = json.loads(inv_path.read_text())
    repo_root = Path(inventory.get("repo_root", ".")).resolve()
    # Harness-first: fold instruction files (copilot-instructions, .cursorrules,
    # CLAUDE.md, ...) into agents[] before generation, else they're dropped.
    n_promoted = promote_prompts_to_agents(inventory)
    if n_promoted:
        print(f"ℹ️  Promoted {n_promoted} instruction file(s) to harness agent(s).")
    out_dir = Path(args.output_dir)
    # Clean output dir for idempotent re-runs
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    agentcore_dir = out_dir / "agentcore"
    agentcore_dir.mkdir(parents=True, exist_ok=True)
    (agentcore_dir / "agentcore.json").write_text(
        json.dumps(generate_agentcore_json(inventory, repo_root), indent=2)
    )
    (agentcore_dir / "aws-targets.json").write_text(
        json.dumps(generate_aws_targets(args.region), indent=2)
    )

    skills = inventory.get("skills", [])
    mcp_servers = inventory.get("mcp_servers", [])
    for agent in inventory.get("agents", []):
        agent_name = slugify(agent.get("name", "unnamed"))
        agent_dir = out_dir / "app" / agent_name
        agent_dir.mkdir(parents=True, exist_ok=True)

        matching_skills = declared_skills(agent, skills)

        if is_code_agent(agent, repo_root):
            # ── Code runtime ──
            script_refs = find_agent_script_refs(agent, repo_root)
            scripts_dir = agent_dir / "scripts"
            scripts_dir.mkdir(exist_ok=True)
            for script in script_refs:
                shutil.copy2(script, scripts_dir / script.name)

            copied_skills = copy_skill_dirs(matching_skills, agent_dir / "skills")

            (agent_dir / "main.py").write_text(generate_main_py(agent))
            (agent_dir / "pyproject.toml").write_text(generate_pyproject_toml(agent_name))

            model_dir = agent_dir / "model"
            model_dir.mkdir(exist_ok=True)
            (model_dir / "__init__.py").write_text("")
            (model_dir / "load.py").write_text(generate_model_load_py())

            (agent_dir / "runtime-metadata.json").write_text(
                json.dumps(generate_runtime_metadata(agent, mcp_servers), indent=2)
            )
            (agent_dir / "Dockerfile").write_text(
                generate_dockerfile(has_scripts=bool(script_refs), has_skills=bool(copied_skills))
            )
        else:
            # ── Harness ──
            (agent_dir / "harness.json").write_text(
                json.dumps(generate_harness_json(agent, mcp_servers), indent=2)
            )
            (agent_dir / "system-prompt.md").write_text(
                flatten_persona_to_prompt(agent) or "You are a helpful assistant"
            )
            # Copy declared skills next to the harness; agentcore-commands.sh mounts them
            copy_skill_dirs(matching_skills, agent_dir / "skills")

        registry_dir = out_dir / "registry"
        registry_dir.mkdir(exist_ok=True)
        (registry_dir / f"{agent_name}.json").write_text(
            json.dumps(generate_registry_record(agent), indent=2)
        )

    exec_scripts = generate_exec_scripts(inventory.get("hooks", []))
    if exec_scripts:
        exec_dir = out_dir / "exec-scripts"
        exec_dir.mkdir(exist_ok=True)
        for name, content in exec_scripts.items():
            path = exec_dir / name
            path.write_text(content)
            path.chmod(0o755)

    command_script = out_dir / "agentcore-commands.sh"
    command_script.write_text(generate_agentcore_commands(inventory, repo_root))
    command_script.chmod(0o755)

    mappings = build_mappings(inventory, repo_root)
    (out_dir / "migration-report.md").write_text(generate_migration_report(inventory, mappings))

    auto = sum(1 for mapping in mappings if mapping["status"] == "AUTO")
    manual = sum(1 for mapping in mappings if mapping["status"] == "MANUAL")
    skip = sum(1 for mapping in mappings if mapping["status"] == "SKIP")
    n_harness = sum(1 for m in mappings if m["type"] == "agent" and m["target"].startswith("harness"))
    n_runtime = sum(1 for m in mappings if m["type"] == "agent" and m["target"].startswith("runtime"))
    print(f"\n✅ AgentCore project generated at: {out_dir}")
    print(f"   Agents: {n_harness} harness, {n_runtime} code runtime")
    print(f"   Mappings: {auto} auto, {manual} manual, {skip} skipped")
    print(f"   Commands: {command_script}")
    print(f"   Report: {out_dir / 'migration-report.md'}")


if __name__ == "__main__":
    main()
