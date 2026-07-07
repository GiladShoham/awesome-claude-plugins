#!/usr/bin/env python3
"""Self-check for prompt→harness promotion in generate_project.py.

Run: python3 test_prompt_promotion.py  (no framework needed)
"""
import tempfile
from pathlib import Path

from generate_project import promote_prompts_to_agents, prompt_to_agent


def test_full_content_read_beats_preview():
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / ".cursorrules"
        full = "You are a reviewer.\n" + "x" * 1000  # > scanner's 500-char preview
        f.write_text(full)
        agent = prompt_to_agent(
            {"name": ".cursorrules", "source_file": str(f), "content_preview": full[:500]}
        )
        assert agent["body"] == full, "should read full file, not the 500-char preview"


def test_preview_fallback_when_file_gone():
    agent = prompt_to_agent(
        {"name": "gone", "source_file": "/nonexistent/x.md", "content_preview": "ambient"}
    )
    assert agent["body"] == "ambient"


def test_promotion_and_collision():
    inv = {
        "agents": [{"name": "reviewer"}],  # real agent already present
        "prompts": [
            {"name": "copilot-instructions", "source_file": "/nope", "content_preview": "a"},
            {"name": "reviewer", "source_file": "/nope", "content_preview": "b"},  # collides
        ],
    }
    n = promote_prompts_to_agents(inv)
    names = [a["name"] for a in inv["agents"]]
    assert n == 1, f"only the non-colliding prompt promotes, got {n}"
    assert names == ["reviewer", "copilot-instructions"], names
    assert inv["prompts"] == [], "prompts consumed after promotion"


if __name__ == "__main__":
    test_full_content_read_beats_preview()
    test_preview_fallback_when_file_gone()
    test_promotion_and_collision()
    print("OK — prompt promotion self-check passed")
