# prove-it

**Stop your agent from saying "done" when it never checked.**

A Claude Code skill that captures real evidence before a change is reported as
working, and returns one of three verdicts: `PROVEN`, `NOT PROVEN`, or
`UNPROVABLE HERE`.

```
/plugin marketplace add JohnJackHouzi/prove-it
/plugin install prove-it@prove-it
```

> Type these in Claude Code (the interface you get by running `claude`), not in
> your shell. From a plain shell, the same thing is:
>
> ```
> claude plugin marketplace add JohnJackHouzi/prove-it
> claude plugin install prove-it@prove-it
> ```

**What you get.** The `prove-it` skill, which fires on its own whenever the agent
is about to claim something works, and a `/prove` command to ask for it directly.

**Requirements.** `curl` and Python 3.8+ for the HTTP and ledger tools - both
already on your machine. `capture_page.mjs` needs Node and Playwright, and falls
back to your installed Chrome or Edge if Playwright's Chromium is not downloaded.
Without any browser it reports `UNPROVABLE HERE` rather than a weaker proof.

**Without Claude Code.** The scripts are standalone and exit non-zero when an
expectation fails, so they work in CI or from any other agent:
`git clone https://github.com/JohnJackHouzi/prove-it && prove-it/skills/prove-it/scripts/capture_http.sh https://example.com --expect-text "Example Domain"`

---

## The problem

Agents report success they never checked. The type-check passed,
so the page must load. The pixel is in the HTML, so it must fire. A subagent said
it fixed six files, so six files must be fixed. Every one of those is a claim about
a running system, backed by nothing that came from the running system.

Before the agent is allowed to say "done", it captures an
artifact that would look different if the change were broken, and returns one of
three verdicts:

```
CLAIM    The Meta pixel fires a PageView on the production home page.
VERDICT  PROVEN
PROOF    .prove-it/page-home-20260905T142530Z.json
         request https://www.facebook.com/tr/?id=...&ev=PageView -> 200
```

```
CLAIM    The migration added orders.refunded_at on the production database.
VERDICT  UNPROVABLE HERE
PROOF    none - no production credentials in this session. The migration file is
         written and reviewed; nothing was run.
```

An honest `UNPROVABLE HERE` is a good outcome. A confident "done" that was never
checked is the failure this exists to prevent.

### Three capture tools

**`capture_http.sh`** - status, redirects, timing, cache headers, body assertions.
Pure `curl` and `sh`, no dependencies. Redacts credentials before writing evidence.

```console
$ capture_http.sh https://example.com --expect-text "Example Domain"
PROVEN  status=200  0.174843s  559B  cf-cache-status=HIT age=10438
evidence: .prove-it/http-example-com-20260905T180222Z.json
```

**`capture_page.mjs`** - a real browser. Every console message, every uncaught
error, every network request with its status, text assertions, screenshots. Uses
Playwright's Chromium, or falls back to your installed Chrome or Edge so nothing
has to be downloaded.

```console
$ node capture_page.mjs --url https://example.com \
    --expect-text "Example Domain" --expect-request 'example\.com' \
    --expect-no-request 'facebook\.com/tr' --screenshot
PROVEN  nav=200  requests=1  errors=0
  text  OK    "Example Domain"
  req   OK    /example\.com/  x1  https://example.com/ -> 200
  req   OK    NOT /facebook\.com/tr/  x0
  shot  .prove-it/page-example-com-20260905T180439Z.png
```

It installs its error listeners *before* page scripts run, which is the only
reliable way to catch a throw inside an event listener - the devtools console does
not always show you those:

```console
$ node capture_page.mjs --url ./repro.html --click "#b" --expect-text "Hello proof"
NOT PROVEN  nav=200  requests=1  errors=2
  text  OK    "Hello proof"
  error pageerror: silent rejection
  error pageerror: Cannot read properties of null (reading 'boom')
```

The expected text is on the page and the verdict is still NOT PROVEN - which is
the point.

**`proof_ledger.py`** - records verdicts and prints the report. It refuses to
record `PROVEN` when the evidence file does not exist on disk:

```console
$ proof_ledger.py add --claim "fake" --verdict PROVEN --evidence /nope.json
evidence file does not exist: /nope.json
A verdict of PROVEN requires an artifact on disk. Capture one, or record
NOT PROVEN / UNPROVABLE HERE instead.
```

### Usage

Once installed, the skill triggers on its own whenever the agent is about to claim
success, or you can ask for it:

```
/prove the pricing page shows the new plan on production
```

The scripts also run standalone, so they work in CI or from any other agent - they
exit non-zero when an expectation is not met.

### What it refuses to accept as proof

A type-check. A successful build. Reading the code you just wrote. `grep` finding a
string in the repo. A subagent's summary. A screenshot taken before the deploy
finished. "The logic is correct." The absence of an error you never looked for.

The reasoning for each, with the failure it hides, is in
[`fake-proofs.md`](skills/prove-it/references/fake-proofs.md).
The per-claim capture recipes and their traps - stale CDN cache, CSP-blocked
beacons, the 8192px screenshot fold, consent gating - are in
[`proof-recipes.md`](skills/prove-it/references/proof-recipes.md).

---

## En français

`prove-it` empêche un agent d'annoncer une réussite qu'il n'a jamais vérifiée. Un
`tsc` qui passe ne prouve pas qu'une page charge. Un pixel présent dans le HTML ne
prouve pas qu'il part : une CSP le bloque en silence. Le skill capture une preuve
matérielle - réponse HTTP, requête réseau réellement émise, erreurs de console,
capture d'écran - puis rend un verdict `PROVEN`, `NOT PROVEN` ou `UNPROVABLE HERE`.

Un `UNPROVABLE HERE` honnête vaut mieux qu'un « c'est bon » jamais vérifié.

Installation dans Claude Code (pas dans le terminal) :

```
/plugin marketplace add JohnJackHouzi/prove-it
/plugin install prove-it@prove-it
```

Les scripts fonctionnent aussi seuls, sans Claude, et sortent avec un code non nul
dès qu'une attente n'est pas satisfaite.

---

## More skills

One repo per skill, so you install only what you want:
[safe-worktree](https://github.com/JohnJackHouzi/safe-worktree) - run several
agents on one repository without stealing each other's work.
[typo-fr](https://github.com/JohnJackHouzi/typo-fr) - French typography
that survives an AI, with a linter that never touches your code.

---

MIT. Contributions welcome - especially new capture recipes for claims this does
not cover yet.
