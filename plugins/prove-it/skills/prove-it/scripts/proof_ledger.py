#!/usr/bin/env python3
"""proof_ledger.py - record verification verdicts and print the report.

The ledger is append-only JSON Lines at .prove-it/ledger.jsonl. It exists so a
claim of success is attached to an artifact that exists on disk: `add` refuses a
PROVEN verdict whose evidence file is missing.

    proof_ledger.py add --claim "..." --verdict PROVEN --evidence .prove-it/http-....json
    proof_ledger.py add --claim "..." --verdict "UNPROVABLE HERE" --note "no prod credentials"
    proof_ledger.py report          # the blocks to paste back to the user
    proof_ledger.py check           # exit 1 if anything is unproven
    proof_ledger.py clear           # start a fresh verification session

Standard library only. Python 3.8+.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

VERDICTS = ("PROVEN", "NOT PROVEN", "UNPROVABLE HERE")
LEDGER = os.path.join(".prove-it", "ledger.jsonl")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(path: str):
    if not os.path.exists(path):
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def decisive_line(evidence: str) -> str:
    """One line from the evidence file that a reader can check."""
    if not evidence or not os.path.exists(evidence):
        return ""
    try:
        with open(evidence, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return ""
    if data.get("tool") == "capture_http.sh":
        bits = [f"status {data.get('status')}"]
        if data.get("cache_headers"):
            bits.append(str(data["cache_headers"]))
        if data.get("matched"):
            bits.append("matched " + ", ".join(json.dumps(m) for m in data["matched"]))
        if data.get("missing"):
            bits.append("MISSING " + ", ".join(json.dumps(m) for m in data["missing"]))
        return ", ".join(bits)
    if data.get("tool") == "capture_page.mjs":
        bits = [f"nav {data.get('nav_status')}"]
        for c in data.get("request_checks", []):
            sample = (c.get("samples") or [{}])[0]
            hit = f" {sample.get('url')} -> {sample.get('status')}" if sample.get("url") else ""
            bits.append(f"{'OK' if c.get('ok') else 'FAIL'} /{c.get('pattern')}/ x{c.get('count')}{hit}")
        for c in data.get("text_checks", []):
            bits.append(f"{'OK' if c.get('ok') else 'MISSING'} text {json.dumps(c.get('text'))}")
        errs = len(data.get("page_errors", [])) + len(data.get("console_errors", []))
        bits.append(f"{errs} console/page errors")
        return ", ".join(bits)
    return str(data.get("verdict", ""))


def cmd_add(args) -> int:
    verdict = args.verdict.strip().upper()
    if verdict not in VERDICTS:
        print(f"verdict must be one of: {', '.join(VERDICTS)}", file=sys.stderr)
        return 2
    if verdict == "PROVEN":
        if not args.evidence:
            print("PROVEN needs --evidence pointing at a captured artifact.", file=sys.stderr)
            return 2
        if not os.path.exists(args.evidence):
            print(f"evidence file does not exist: {args.evidence}\n"
                  f"A verdict of PROVEN requires an artifact on disk. Capture one, or "
                  f"record NOT PROVEN / UNPROVABLE HERE instead.", file=sys.stderr)
            return 2
    entry = {
        "at": now(),
        "claim": args.claim,
        "verdict": verdict,
        "evidence": args.evidence or None,
        "line": decisive_line(args.evidence) if args.evidence else "",
        "note": args.note or "",
    }
    os.makedirs(os.path.dirname(args.ledger) or ".", exist_ok=True)
    with open(args.ledger, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"{verdict}  {args.claim}")
    return 0


def render(entry) -> str:
    proof = entry.get("evidence") or "none"
    line = entry.get("line") or entry.get("note") or ""
    if line:
        proof = f"{proof} - {line}"
    return (f"CLAIM    {entry.get('claim', '')}\n"
            f"VERDICT  {entry.get('verdict', '')}\n"
            f"PROOF    {proof}")


def cmd_report(args) -> int:
    entries = load(args.ledger)
    if not entries:
        print("no verdicts recorded yet - nothing has been verified.")
        return 0
    unproven = [e for e in entries if e.get("verdict") != "PROVEN"]
    for e in unproven:            # unproven first: a failure never hides at the bottom
        print(render(e) + "\n")
    for e in entries:
        if e.get("verdict") == "PROVEN":
            print(render(e) + "\n")
    print(f"{len(entries) - len(unproven)}/{len(entries)} claims proven.")
    return 0


def cmd_check(args) -> int:
    entries = load(args.ledger)
    unproven = [e for e in entries if e.get("verdict") != "PROVEN"]
    if not entries:
        print("NOTHING VERIFIED - the ledger is empty.")
        return 1
    if unproven:
        for e in unproven:
            print(f"{e.get('verdict')}  {e.get('claim')}")
        return 1
    print(f"ALL PROVEN - {len(entries)} claims, each with an artifact.")
    return 0


def cmd_clear(args) -> int:
    if os.path.exists(args.ledger):
        os.remove(args.ledger)
        print(f"cleared {args.ledger}")
    else:
        print("nothing to clear")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ledger", default=LEDGER, help=f"ledger path (default {LEDGER})")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="record one verdict")
    a.add_argument("--claim", required=True, help="one falsifiable sentence, naming the environment")
    a.add_argument("--verdict", required=True, help=" | ".join(VERDICTS))
    a.add_argument("--evidence", help="path to the captured artifact")
    a.add_argument("--note", help="why it could not be proven, when it could not")
    a.set_defaults(func=cmd_add)

    for name, fn, helptext in (
        ("report", cmd_report, "print the verdict blocks, unproven first"),
        ("check", cmd_check, "exit 1 if anything is unproven"),
        ("clear", cmd_clear, "delete the ledger"),
    ):
        s = sub.add_parser(name, help=helptext)
        s.set_defaults(func=fn)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
