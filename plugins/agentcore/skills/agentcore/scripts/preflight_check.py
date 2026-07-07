#!/usr/bin/env python3
"""Preflight check for AgentCore migration prerequisites.

Verifies all required tools and libraries are installed before starting
the migration workflow. Run this before any other migration step.

Usage:
    python3 preflight_check.py
"""

import shutil
import subprocess
import sys


def check(name: str, passed: bool, fix: str) -> bool:
    """Print a check result and return True if passed."""
    icon = "✅" if passed else "❌"
    print(f"  {icon}  {name}")
    if not passed:
        print(f"      Fix: {fix}")
    return passed


def get_version(cmd: list[str]) -> str:
    """Run a command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.stdout.strip() if result.returncode == 0 else ""
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def main() -> None:
    print("\n╔═══════════════════════════════════════════════════╗")
    print("║       AgentCore Migration — Preflight Check       ║")
    print("╚═══════════════════════════════════════════════════╝\n")

    results: list[bool] = []

    # 1. Python version
    py_major, py_minor = sys.version_info[:2]
    results.append(check(
        f"Python {py_major}.{py_minor} (need ≥ 3.10)",
        py_major >= 3 and py_minor >= 10,
        "Install Python 3.10+: brew install python  OR  https://python.org",
    ))

    # 2. Node.js
    node_ver = get_version(["node", "--version"])
    node_ok = False
    if node_ver:
        # node_ver is like "v20.11.0" → parse major
        try:
            major = int(node_ver.lstrip("v").split(".")[0])
            node_ok = major >= 20
        except ValueError:
            pass
    results.append(check(
        f"Node.js {node_ver or 'not found'} (need ≥ 20)",
        node_ok,
        "Install Node.js 20+: brew install node  OR  nvm install 20",
    ))

    # 3. AWS CLI
    aws_ver = get_version(["aws", "--version"])
    results.append(check(
        f"AWS CLI {'installed' if aws_ver else 'not found'}{f' ({aws_ver.split()[0]})' if aws_ver else ''}",
        bool(aws_ver),
        "Install AWS CLI: brew install awscli  OR  pip install awscli",
    ))

    # 4. AWS credentials
    caller = get_version(["aws", "sts", "get-caller-identity", "--query", "Account", "--output", "text"])
    results.append(check(
        f"AWS credentials {'configured (account: ' + caller + ')' if caller else 'not configured'}",
        bool(caller),
        "Configure credentials: aws configure  OR  export AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY",
    ))

    # 5. uv (required by the AgentCore CLI for Python agents)
    uv_path = shutil.which("uv")
    results.append(check(
        f"uv {'installed' if uv_path else 'not found'}",
        bool(uv_path),
        "Install uv: brew install uv  OR  curl -LsSf https://astral.sh/uv/install.sh | sh",
    ))

    # 6. AgentCore CLI ≥ 0.22 (harness support: add harness/skill/tool, export harness)
    ac_path = shutil.which("agentcore")
    ac_ver = get_version(["agentcore", "--version"]) if ac_path else ""
    ac_ok = False
    if ac_ver:
        try:
            major, minor = (int(x) for x in ac_ver.split(".")[:2])
            ac_ok = (major, minor) >= (0, 22)
        except ValueError:
            pass
    results.append(check(
        f"AgentCore CLI {ac_ver or 'not found'} (need ≥ 0.22)",
        ac_ok,
        "Install/upgrade: npm install -g @aws/agentcore@latest  (or: agentcore update)",
    ))

    # 7. AWS bedrock-agentcore-control namespace
    ac_ns = get_version(["aws", "bedrock-agentcore-control", "help"])
    # help command returns content on success
    results.append(check(
        f"AWS bedrock-agentcore-control namespace {'available' if ac_ns else 'not found'}",
        bool(ac_ns),
        "Update AWS CLI: pip install --upgrade awscli  OR  brew upgrade awscli",
    ))

    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\n{'─' * 55}")
    if all(results):
        print(f"  ✅  All {total} checks passed — ready to migrate!\n")
    else:
        print(f"  ⚠️   {passed}/{total} checks passed — fix the issues above before migrating.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
