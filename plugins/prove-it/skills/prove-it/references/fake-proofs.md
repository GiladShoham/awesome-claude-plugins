# Things that are not proof

Each entry: the claim, why it feels like proof, and what it would look like on a
broken system. If your evidence would be identical when broken, it is not evidence.

## "The type-check passes"

Feels like: the compiler validated my work.
On a broken system: identical. Types describe shapes, not behaviour. A page that
throws at runtime, a query against a missing column, a null at the wrong moment -
all type-check cleanly.

## "The build succeeded"

Feels like: everything compiled, so everything runs.
On a broken system: identical. Build success proves the bundler finished. It says
nothing about a 500 on the route, a blocked third-party script, or a wrong env var
read at runtime.

## "I read the code and the logic is correct"

Feels like: I traced it end to end.
On a broken system: identical, because the bug is where you did not look - the
config, the CSP, the cache, the wrong deployed commit, an env var, a race.

## "grep found the snippet in the repo"

Feels like: the feature is there.
On a broken system: identical. The string exists in a file. Nothing established
that the file ships, that the code path runs, or that the browser was allowed to
execute it.

## "The subagent reported it fixed six files"

Feels like: work was done.
On a broken system: identical. A report is a narrative. Check the disk: `git diff
--stat`, or read the files. Reports have described edits that were never written.

## "It worked before, and I only changed one thing"

Feels like: low risk.
On a broken system: identical, and this is the most common cause of a broken
system.

## "No errors appeared"

Feels like: clean run.
On a broken system: identical, if you never opened the console, never installed an
error listener, or looked at a console buffer that was cleared by navigation.
Absence of evidence needs a capture too.

## "The screenshot looks right"

Feels like: I saw it with my own eyes.
On a broken system: identical, if the screenshot predates the deploy, came from a
cached page, or came from localhost while the claim was about production. A
screenshot's value is entirely in its timestamp and its URL - record both.

## "The API returned 200"

Feels like: the request worked.
On a broken system: not always identical, but frequently. Many APIs return 200
with an error body. Assert on the body.

## "The user said it was broken and now I changed it"

Feels like: closure.
On a broken system: identical. You have not reproduced the original failure, so
you cannot know you addressed it. Reproduce first, then fix, then re-run the repro.
