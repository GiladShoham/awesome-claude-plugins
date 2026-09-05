# safe-worktree

**Run several agents on one repository without stealing each other's work.**

A Claude Code skill for parallel sessions: isolated worktrees that actually run, a
guard that catches the repository moving under you, and a cleanup that knows a
squash merge when it sees one.

```
/plugin marketplace add JohnJackHouzi/safe-worktree
/plugin install safe-worktree@safe-worktree
```

> Type these in Claude Code (the interface you get by running `claude`), not in
> your shell. From a plain shell, the same thing is:
>
> ```
> claude plugin marketplace add JohnJackHouzi/safe-worktree
> claude plugin install safe-worktree@safe-worktree
> ```

**What you get.** The `safe-worktree` skill, which fires when parallel work starts
or a commit is coming, and a `/worktree` command to drive it directly.

**Requirements.** `git` and a POSIX shell. Nothing else - no Python, no Node.
Copy-on-write cloning of `node_modules` uses APFS on macOS and reflinks on
btrfs/xfs; elsewhere it falls back to a plain copy with a warning.

**Without Claude Code.** The three scripts are standalone:
`git clone https://github.com/JohnJackHouzi/safe-worktree && safe-worktree/skills/safe-worktree/scripts/worktree_new.sh feature/x`

---

## The problem

Two agents in one directory share one HEAD.

Session A is working on `main`. Session B, in the same directory, runs
`git checkout -b hotfix/urgent`. Session A commits. Its work is now on
`hotfix/urgent`, on top of files it never read. Nothing errors, no command fails,
and `git status` looked perfectly normal to both of them - one command too late.

That is the cheap version. The expensive ones are a `reset --hard` that erases an
hour of another session's commits, and a branch deleted because git said it was
not merged.

---

## Three tools

### `worktree_new.sh` - an isolated checkout that actually runs

```console
$ worktree_new.sh feature/pricing
repository : /Users/john/code/demo-app
worktree   : /Users/john/code/demo-app-pricing
branch     : feature/pricing
Preparing worktree (new branch 'feature/pricing')

cloning node_modules (copy-on-write, no reinstall)
  never symlink node_modules into a worktree: bundlers resolve through the
  link and load the other checkout's code.

copied ignored env files: .env.local
```

`node_modules` is cloned copy-on-write - instant, no extra disk space, no
`npm install`. Ignored `.env*` files are carried over, because a worktree without
them boots into a broken config that looks like a code bug.

It refuses the placements that quietly break things:

```console
$ worktree_new.sh feature/x /tmp/scratch
STOP - refusing to create a worktree under a temp directory.
     Temp dirs are wiped without warning and are usually on another filesystem,
     which defeats the copy-on-write clone of node_modules and breaks dev servers.
```

It also refuses a branch already checked out somewhere else, a target inside the
repository, and a branch name that already exists.

### `session_guard.sh` - run it right before you commit

```console
$ session_guard.sh init
baseline: feature/pricing at a8ecd078

$ session_guard.sh check

[1] COMMITS APPEARED THAT YOU DID NOT MAKE (1 since you started)
    90de526  Other Session  autre session: ajoute pricing
    If none of these are yours, another session is committing here.

STOP  1 finding(s) - read them before you commit.
```

It catches the branch changing under you, commits you did not make, a rewritten
history (`reset --hard`, a rebase, a force fetch), an upstream that moved, and
files in your staging area that belong to another session:

```console
[1] THE BRANCH CHANGED UNDER YOU
    started on : main
    now on     : hotfix/urgent
    Anything you commit now lands on hotfix/urgent.

[2] STAGED FILES THAT OTHER SESSIONS WRITE
    .claude/launch.json
    Never `git checkout` these either - that discards another session work.
```

Exits non-zero, so it can gate a commit hook or a script.

### `worktree_done.sh` - cleanup that does not believe git

Ask git whether a squash-merged branch is merged and it will tell you no:

```console
$ git branch --no-merged main
+ feature/pricing          <- merged an hour ago. This is a lie.
```

`--merged` and `--no-merged` answer a question about *ancestry*. A squash merge
puts your content in the base branch under a commit that has no ancestral link to
your branch at all. Same for a rebase merge.

So this compares content instead - for every file the branch touched, is the base
branch's version already identical?

```console
$ worktree_done.sh --yes
worktree : /Users/john/code/demo-app-pricing
branch   : feature/pricing
base     : main

MERGED  main already contains every file this branch changed, byte for byte.
        Not an ancestor: this was a squash or a rebase merge. `git branch
        --merged` would have told you the opposite. Content wins.

removed worktree /Users/john/code/demo-app-pricing
deleted branch feature/pricing
```

And when the work is genuinely not merged, it refuses - including the case where a
pull request was merged before your last commits reached it:

```console
NOT MERGED  main differs from this branch on:
  pricing.txt

  and these commits are not on the upstream yet:
    90de526 autre session: ajoute pricing

  If a pull request for this branch was already merged, it did NOT include
  them. Open a new one rather than assuming they went along for the ride.

STOP - refusing to remove a worktree whose work is not in main.
```

---

## The four rules

1. **One session, one working directory.** Never switch branch where another
   session is working.
2. **Look before you commit.** `git status` and `git log` immediately before
   staging, not at the start of the task.
3. **Never rewrite shared history.** No `reset --hard`, no `push --force`, no
   `checkout` of a config file another session writes.
4. **Never trust `git branch --no-merged`.** Compare content, not ancestry.

The six failures behind these rules, each with the signal that catches it, are in
[`parallel-sessions.md`](skills/safe-worktree/references/parallel-sessions.md).
Why symlinked `node_modules` makes a dev server serve the wrong checkout, and the
rest of what a runnable worktree needs, is in
[`dev-server-in-a-worktree.md`](skills/safe-worktree/references/dev-server-in-a-worktree.md).

---

## Usage

Once installed the skill triggers on its own when parallel work starts or a commit
is coming. Or ask for it:

```
/worktree feature/pricing
/worktree check
```

The scripts are plain POSIX `sh` with no dependencies beyond git, so they also run
standalone, from any other agent, or in CI.

---

## En français

Deux agents dans un même dossier partagent un seul HEAD. La session B fait
`git checkout -b hotfix`, la session A commite : son travail atterrit sur `hotfix`,
au-dessus de fichiers qu'elle n'a jamais lus. Aucune erreur, rien dans les logs.

Ce skill fournit un vrai worktree isolé et immédiatement exécutable (`node_modules`
cloné en copie sur écriture, fichiers `.env` ignorés recopiés, refus de `/tmp`), un
garde-fou à lancer juste avant de commiter, et un nettoyage qui compare le contenu
au lieu de croire `git branch --no-merged`, qui ment sur une branche squash-mergée.

Installation dans Claude Code, pas dans le terminal :

```
/plugin marketplace add JohnJackHouzi/safe-worktree
/plugin install safe-worktree@safe-worktree
```

---

## More skills

One repo per skill, so you install only what you want:
[prove-it](https://github.com/JohnJackHouzi/prove-it) - capture real evidence
before an agent claims success.
[typo-fr](https://github.com/JohnJackHouzi/typo-fr) - French typography
that survives an AI, with a linter that never touches your code.

---

MIT.
