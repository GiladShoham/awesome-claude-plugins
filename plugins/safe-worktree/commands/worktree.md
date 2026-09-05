---
description: Create an isolated, runnable git worktree for this task, or check that the repository has not moved under you.
argument-hint: [branch name, or "check" to run the guard]
---

Use the `safe-worktree` skill.

**$ARGUMENTS**

- If a branch name was given, create a worktree for it with `worktree_new.sh`,
  then run `session_guard.sh init` inside it and continue the work there.
- If the argument is `check` (or empty and work is already in progress), run
  `session_guard.sh check` and report every finding before doing anything else.
- If the work is finished, use `worktree_done.sh` - it decides whether the branch
  is really merged by comparing content, not ancestry.

Never switch branch in a directory another session may be using, and never run
`reset --hard`, `push --force`, or `checkout` on a shared config file.
