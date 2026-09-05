# Proof recipes

One recipe per claim. Each names the trap that makes the naive version worthless.

---

## A page loads on production

```bash
scripts/capture_http.sh https://example.com/pricing --expect-text "Pro plan"
```

**Trap: the CDN served you the old build.** A 200 proves the origin answered, not
that it answered with your change. Assert on a string that only exists *after* the
change, and check the `age` / `x-vercel-cache` / `cf-cache-status` headers the
script records. On a `HIT`, re-request with a cache-buster query string before
concluding anything.

**Trap: the deploy was still building.** Read the deployed commit back (a version
endpoint, `/api/health`, a build id in the HTML) rather than trusting elapsed time.

---

## A client-side feature works

```bash
node scripts/capture_page.mjs --url https://example.com --expect-text "Pro plan"
```

The script records every console message, every page error, and every failed
request. Read them - an empty `errors` array is half the proof.

**Trap: the browser console hides errors thrown inside event listeners.** A
listener that throws will not always surface where you are looking. The script
installs `window.addEventListener('error')` and `'unhandledrejection'` before the
page runs, which is the only reliable capture.

**Trap: `dispatchEvent` proves nothing.** Synthesising an event in the console
exercises your handler, not the user's path to it. Drive the real control.

---

## An analytics pixel, tag, or beacon fires

```bash
node scripts/capture_page.mjs --url https://example.com \
  --expect-request 'facebook\.com/tr' --expect-request 'google-analytics\.com|/g/collect'
```

This is the row where reading code is most tempting and most wrong.

**Trap: the tag is in the HTML and blocked anyway.** A Content-Security-Policy
`script-src` or `connect-src` omission kills the request with only a console
warning. The captured request list is the only proof.

**Trap: the consent banner gates it.** If loading is conditional on consent, the
first page view legitimately fires nothing. Use `--click` to accept, or capture
with consent already stored, and say which case you proved.

**Trap: a 200 on the beacon is not an event in the dashboard.** Report what you
captured ("the request left the browser and returned 200"), not what you did not
("the event is in Meta Events Manager") - unless you actually opened the dashboard.

---

## An API behaves

```bash
scripts/capture_http.sh https://api.example.com/v1/orders \
  --method POST --header 'Content-Type: application/json' \
  --data '{"sku":"ABC"}' --expect-status 201
```

Save the request too, not just the response. A response that looks right for the
wrong request has proven nothing. The script writes both.

**Trap: authenticated routes.** Pass the token via `--header`, never in the URL.
Nothing secret is written to the evidence file - the script redacts
`authorization`, `cookie`, `set-cookie`, and any header matching `token|key|secret`.

---

## A visual change

```bash
node scripts/capture_page.mjs --url https://example.com --screenshot --viewport 1280x800
```

**Trap: full-page screenshots fold past ~8192 px.** Chromium silently caps the
capture and can repeat the top of the page in the overflow. For a long page,
either state the viewport-only capture, or capture in sections. The script warns
in its evidence file when a full-page shot hits the cap.

**Trap: fonts and images still loading.** The script waits for `networkidle`
before shooting. Do not lower that to `load` to make a flake go away.

---

## A bug is fixed

Re-run **the original reproduction**, unchanged. A new script that exercises the
happy path is not the same test. If the repro was manual, drive the same clicks
with `capture_page.mjs --click` and quote the resulting state.

---

## A build or deploy landed

Read the deployed identity back from the live system:

```bash
scripts/capture_http.sh https://example.com/api/health --expect-text "$(git rev-parse --short HEAD)"
```

**Trap: "the push succeeded" is not "the deploy landed".** Hosts skip builds,
queue them, or serve a stale build for hours. Ask the live system what it is
running.

---

## A database migration applied

Query the real database for the new shape - a column, a constraint, a row count -
and paste the result. The migration file's existence proves only that a file exists.

**Trap: you queried the wrong database.** Print the host or project ref alongside
the result so the evidence identifies its own source.

---

## A file was produced (PDF, image, export, report)

Read the produced file back and quote from it. For a PDF, extract its text and
check a string you expect on a specific page; for an image, check its dimensions.
The generator's exit code says the process ended, not that the output is right.

**Trap: the generator silently drops overflowing content.** Layout engines
frequently discard text that does not fit rather than erroring. Assert on content
you expect near the *end* of the document, not the beginning.

---

## A test suite passes

Paste the runner's own summary line, unedited, including the counts. If tests were
skipped or filtered, say which filter you used. A subset that passes is a subset
that passes.
