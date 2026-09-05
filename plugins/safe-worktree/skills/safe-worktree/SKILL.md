---
name: safe-worktree
description: Run several agents or sessions on one repository without stealing each other's work. Use before starting feature work, before any commit or push when other sessions may be open, and when a dev server has to run from a second copy of the repo. Triggers on "work on this in parallel", "another session", "start a branch", "set up a worktree", "before I commit", "did someone else change this", "the branch changed", "clean up this branch".
---

# Safe worktree

Two agents in one directory share one HEAD. When the second one switches branch,
the first one's next commit lands somewhere it was never meant to go, on top of
files it never read. Nothing errors. The work is simply gone from where it should
have been.

This skill makes parallel work safe: a real isolated checkout, a guard that runs
before you commit, and a cleanup that knows a squash merge when it sees one.

## The four rules

1. **One session, one working directory.** Never switch branch in a directory
   another session may be using. Create a worktree instead.
2. **Look before you commit.** Re-read `git status` and `git log` immediately
   before staging. The repository may have moved since you last looked.
3. **Never rewrite shared history.** No `reset --hard`, no `push --force`, no
   `checkout` of a file another session may be editing - config files under
   `.claude/` especially.
4. **Never trust `git branch --no-merged`.** It reports a squash-merged branch as
   unmerged. Deleting on that signal alone loses nothing; *keeping* on it wastes
   hours. Compare content, not ancestry.

## Starting work

```bash
scripts/worktree_new.sh feature/pricing
```

Creates `../<repo>-pricing` as a sibling directory on the same filesystem, checks
out a new branch there, and makes it actually runnable: `node_modules` is
copy-on-write cloned rather than reinstalled, and ignored env files are carried
over. It refuses to place a worktree in `/tmp`, and it refuses a branch already
checked out somewhere else.

Why those refusals matter, and what breaks when you ignore them (symlinked
`node_modules`, cross-filesystem copies, dev servers that cannot resolve their own
dependencies): `references/dev-server-in-a-worktree.md`.

## Before every commit

```bash
scripts/session_guard.sh init     # once, when you start working
scripts/session_guard.sh check    # immediately before you stage anything
```

`check` compares the repository to where you left it and stops you when:

- the branch changed under you
- commits appeared that you did not make
- the upstream moved
- your staging area contains a file that belongs to another session
  (`.claude/launch.json`, `.claude/settings.local.json`, `.env*`)
- another worktree has this branch checked out

It exits non-zero on anything it finds, so it can gate a commit in a hook or a
script. Read what it reports before you commit anyway.

## Finishing

```bash
scripts/worktree_done.sh
```

Refuses while uncommitted or untracked work exists, then decides whether the
branch is really merged by **comparing file contents against the base branch**,
not by asking git about ancestry. A squash merge, a rebase merge, and a
fast-forward all look different to `git branch --merged`; they look identical to
the file comparison. Only then does it remove the worktree and delete the branch.

## The failure modes this exists to prevent

Each one is a real incident, with the signal you would have seen: see
`references/parallel-sessions.md`.

- A commit landing on another session's branch, silently
- Two sessions both editing `.claude/launch.json`, one reverting the other
- A branch deleted because `--no-merged` did not list it as merged - it was
  squashed
- A pull request merged while more commits were still being written to its branch
- `npm install` running for ten minutes in a worktree that only needed a clone
- A dev server in a worktree resolving the *other* checkout's dependencies

## When not to use a worktree

For a one-line read or a quick `git log`, use the directory you are in. Worktrees
are for work that holds a branch for more than a moment. What matters is the rule,
not the ceremony: do not move HEAD in a directory someone else is using.
