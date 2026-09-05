# What goes wrong when two sessions share one repository

Six failures, each with the signal that would have caught it.

---

## 1. The commit that lands on someone else's branch

Session A is editing on `main`. Session B, in the same directory, runs
`git checkout -b hotfix/urgent`. Session A commits. Its work is now on
`hotfix/urgent`, on top of files it never read.

Nothing errors. `git status` looked normal to both of them, one command too late.

**Signal:** `session_guard.sh check` compares the current branch to the one the
session started on. Run it immediately before staging, not at the start of the task.

**Fix:** one session, one working directory. `worktree_new.sh` instead of `checkout`.

---

## 2. Two sessions editing the same untracked config

`.claude/launch.json`, `.claude/settings.local.json`, `.env.local`, `.vscode/launch.json`:
shared files that several sessions write, and that nobody thinks of as work.
One session runs `git checkout .claude/launch.json` to "clean up" and silently
discards what the other one had just configured.

**Signal:** the guard reports these paths when they appear in your staging area.

**Fix:** never `checkout`, `restore`, or `stash` a path in that list. If it is
wrong, edit it deliberately.

---

## 3. The branch that was merged, but git says it was not

```console
$ git branch --no-merged main
+ feature/pricing          <- git says: not merged. This is a lie.
```

The branch was squash-merged: its content is in `main` as a single new commit
whose ancestry has nothing to do with the branch. `--merged` and `--no-merged`
only ever answer a question about ancestry.

**Signal:** compare content, not ancestry. For each file the branch touched, ask
whether the base branch's version is already identical:

```sh
for f in $(git diff --name-only $(git merge-base main HEAD) HEAD); do
  git diff --quiet main HEAD -- "$f" || echo "still differs: $f"
done
```

No output means the base branch already has everything. `worktree_done.sh` does
exactly this before it removes anything.

---

## 4. The pull request that was merged before your last commits

You push, a PR opens, it is reviewed, and while it is open you keep committing to
the same branch. The PR is merged from the state it was reviewed at. Your later
commits are still on the branch, and nowhere else. The branch looks finished; a
part of the work is not in the base branch.

**Signal:** `worktree_done.sh` lists the files that still differ from the base
branch *and* the commits that are not upstream, then refuses to clean up.

**Fix:** open a second pull request for the remainder. Do not assume anything rode
along.

---

## 5. Force-push and hard reset

`git reset --hard` and `git push --force` are the two commands that destroy another
session's work with no recovery path through the normal interface. Recovery goes
through `git reflog`, which only exists locally, only for a while.

**Signal:** the guard notices when its baseline commit is no longer an ancestor of
HEAD, which is what a reset or a rebase under your feet looks like.

**Fix:** never run either on a shared repository without explicit agreement. Prefer
`git revert`. If you already did, `git reflog` before touching anything else.

---

## 6. A branch created while another session was mid-write

Creating a branch snapshots the index and the working tree as they are *right now* -
including another session's half-written files, which then belong to your branch
and are missing from theirs.

**Signal:** `git status` in the directory you are about to branch from, read
immediately before branching.

**Fix:** branch from a clean state, or branch in your own worktree where nobody
else is writing.
