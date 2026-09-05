---
name: prove-it
description: Capture real evidence that a change works before reporting success, and return a PROVEN / NOT PROVEN / UNPROVABLE verdict. Use before saying "done", "fixed", "it works", "deployed", or "should work", and whenever the user asks to verify, prove, double-check, or confirm something actually works - especially in production. Triggers on "is it working", "did it deploy", "prove it", "verify this", "check in prod", "is the pixel firing", "are you sure", "confirm the fix".
---

# Prove it

A passing type-check is not proof. A read of the source is not proof. An agent's
report is not proof. **Proof is an artifact captured from the running system after
the change.**

This skill turns "it should work" into either evidence or an honest admission.

## The rule

> Never claim a change works until you have captured an artifact from the running
> system that would look different if the change were broken.

The counterfactual is the whole test. If your evidence would look identical on a
broken build, it is not evidence. `tsc` passes on a page that 500s. `grep` finds a
tracking snippet that a CSP silently blocks. A subagent reports six files fixed
that were never written to disk.

## Procedure

**1. State the claim.** One sentence, falsifiable, naming the environment.
Bad: "the fix works". Good: "GET https://example.com/pricing returns 200 and the
page contains 'Pro plan' on production."

**2. Pick the evidence.** Use the table below. If two kinds are cheap, take both:
one positive (the new behaviour appears) and one negative (no console error, no
failed request).

**3. Capture it.** Run a tool, save the output to a file. Never paraphrase from
memory - quote the captured bytes.

**4. Return a verdict.** `PROVEN`, `NOT PROVEN`, or `UNPROVABLE HERE`, with the
artifact path and the decisive line. Never end a task with an unqualified
"done" when the verdict is anything other than PROVEN.

## Evidence table

| Claim | Minimum acceptable proof | Tool |
|---|---|---|
| A page loads / renders | HTTP status + a string from the new markup | `scripts/capture_http.sh` |
| A client-side feature works | Browser console clean + expected DOM text | `scripts/capture_page.mjs` |
| Analytics, pixel, or beacon fires | The outbound network request, captured, with its status | `scripts/capture_page.mjs --expect-request` |
| An API behaves | Request and response body, both saved | `scripts/capture_http.sh --data` |
| A visual change | Screenshot taken after the deploy, at a stated viewport | `scripts/capture_page.mjs --screenshot` |
| A bug is fixed | The exact reproduction from before, now producing the new result | reuse the original repro command |
| A build or deploy landed | Deployed commit SHA or build id read back from the live system | `curl` a version endpoint, or the host's CLI |
| A migration applied | A query against the real database showing the new shape | the project's DB client |
| A file was produced | Read the produced file back and quote from it | `Read` the output, not the generator |
| A test suite passes | The runner's own summary line, unedited | the test command |

Full recipes, including the traps for each row: `references/proof-recipes.md`.

## What is never proof

Reading these back to the user as evidence is the single most common failure mode.
The full list with the reasoning: `references/fake-proofs.md`.

- A type-check, a lint, or a build that compiles
- Reading the source you just wrote
- `grep` finding a string in a repo
- A subagent's summary that you did not verify on disk
- "The logic is correct, so it works"
- A screenshot or log captured **before** the deploy finished
- The absence of an error you never looked for

## Tools

All scripts are dependency-light and write their evidence to `.prove-it/` in the
project root. They exit non-zero when an expectation is not met, so they can be
chained or run in CI.

```bash
# HTTP: status, redirects, timing, headers, body assertion
scripts/capture_http.sh https://example.com/pricing --expect-text "Pro plan"

# Browser: console errors, network requests, DOM text, screenshot
node scripts/capture_page.mjs --url https://example.com \
  --expect-request 'facebook\.com/tr' --expect-text "Pro plan" --screenshot

# Ledger: record verdicts, print the report to paste back to the user
python3 scripts/proof_ledger.py add --claim "..." --verdict PROVEN --evidence .prove-it/http-....json
python3 scripts/proof_ledger.py report
```

`capture_page.mjs` needs Playwright. If it is missing, the script prints the exact
install command and exits 2 - report `UNPROVABLE HERE` rather than substituting a
weaker proof, unless another browser tool is available in the session.

## When you cannot prove it

Say so, in one line, immediately, and name what is missing:

> NOT PROVEN - no credentials for the staging database, so the migration was never
> read back. The code is written and the type-check passes; that is all I verified.

An honest `UNPROVABLE HERE` is a good outcome. A confident "done" that was never
checked is the failure this skill exists to prevent. Do not soften it, do not bury
it at the end of a paragraph, and do not let a green build stand in for it.

## Verdict format

Close every verification with the block described in `references/verdict-format.md`.
It is three lines: claim, verdict, artifact.
