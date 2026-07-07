#!/usr/bin/env python3
"""Invoke an AgentCore harness via boto3 — fallback for `agentcore invoke --harness`.

Use when the CLI fails with `fetch failed` (Node fetch only tries the first
DNS record of the data-plane endpoint; boto3 falls back across all records).

Requires boto3 with the InvokeHarness operation (>= ~1.43):
    uv run --with 'boto3>=1.43' scripts/invoke_harness.py --arn <harness-arn> --prompt "hi"
"""

import argparse
import json
import sys
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import EventStreamError


def main() -> None:
    parser = argparse.ArgumentParser(description="Invoke an AgentCore harness")
    parser.add_argument("--arn", required=True, help="Harness ARN")
    parser.add_argument("--prompt", required=True, help="User prompt")
    parser.add_argument("--region", default=None, help="AWS region (default: from ARN)")
    parser.add_argument("--session-id", default=None, help="Session ID for continuity (min 33 chars)")
    args = parser.parse_args()

    region = args.region or args.arn.split(":")[3]
    session_id = args.session_id or str(uuid.uuid4())

    # Long read timeout: harness cold-start (microVM spin-up + first token) can exceed the 60s default.
    client = boto3.client(
        "bedrock-agentcore",
        region_name=region,
        config=Config(read_timeout=300, connect_timeout=15, retries={"max_attempts": 2}),
    )
    resp = client.invoke_harness(
        harnessArn=args.arn,
        runtimeSessionId=session_id,
        messages=[{"role": "user", "content": [{"text": args.prompt}]}],
    )

    print(f"session: {session_id}", file=sys.stderr)
    # Converse-style event stream: messageStart, contentBlockDelta, messageStop, metadata.
    # Service-side errors (e.g. model not accessible) surface as EventStreamError on iteration.
    try:
        for event in resp["stream"]:
            if "contentBlockDelta" in event:
                sys.stdout.write(event["contentBlockDelta"].get("delta", {}).get("text", ""))
                sys.stdout.flush()
            elif "messageStop" in event:
                print(f"\n[stop: {event['messageStop'].get('stopReason')}]", file=sys.stderr)
            elif "metadata" in event:
                print(f"[usage: {json.dumps(event['metadata'].get('usage'), default=str)}]", file=sys.stderr)
    except EventStreamError as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
