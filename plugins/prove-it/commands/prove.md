---
description: Capture real evidence that the last change works, and return a PROVEN / NOT PROVEN / UNPROVABLE verdict.
argument-hint: [what you want proven, e.g. "the pricing page shows the new plan on prod"]
---

Use the `prove-it` skill to verify this claim, end to end:

**$ARGUMENTS**

If no claim is given above, derive it from the change made in this session - the
most recent edit, fix, or deploy - and state it explicitly before verifying.

Do not skip the capture step. A type-check, a build, a code read, or a subagent's
report is not evidence. Run a real capture with the skill's scripts (or another
real browser or shell tool available here), record the verdict with
`proof_ledger.py`, and end your reply with the three-line verdict block.

If the claim cannot be verified from this session, say `UNPROVABLE HERE` in the
first line of your reply and name exactly what is missing.
