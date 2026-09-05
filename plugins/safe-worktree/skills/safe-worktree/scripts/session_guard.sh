#!/usr/bin/env sh
# session_guard.sh - detect that the repository moved under you, before you commit.
#
#   session_guard.sh init      record where this session starts
#   session_guard.sh check     compare now against that baseline (exit 1 on findings)
#   session_guard.sh accept    adopt the current state as the new baseline
#   session_guard.sh status    print the baseline
#
# Run `check` immediately before staging. It reports a branch that changed under
# you, commits you did not make, an upstream that moved, staged files that belong
# to another session, and a branch checked out in two places at once.

set -u

die() { printf 'STOP - %s\n' "$*" >&2; exit 2; }
command -v git >/dev/null 2>&1 || die "git not found"
GITDIR=$(git rev-parse --git-dir 2>/dev/null) || die "not inside a git repository"
BASELINE="$GITDIR/safe-worktree-baseline"

# Files that more than one session routinely writes. Staging one of these means
# committing another session's in-flight configuration.
SHARED_PATTERNS='^\.claude/launch\.json$|^\.claude/settings\.local\.json$|^\.env|^\.vscode/launch\.json$|^\.idea/'

CMD="${1:-check}"

now_branch() { git rev-parse --abbrev-ref HEAD 2>/dev/null; }
now_head()   { git rev-parse HEAD 2>/dev/null; }

write_baseline() {
  printf 'branch=%s\nhead=%s\nat=%s\nuser=%s\n' \
    "$(now_branch)" "$(now_head)" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(git config user.email 2>/dev/null)" \
    > "$BASELINE"
}

read_baseline() {
  [ -f "$BASELINE" ] || return 1
  B_BRANCH=$(sed -n 's/^branch=//p' "$BASELINE")
  B_HEAD=$(sed -n 's/^head=//p' "$BASELINE")
  B_AT=$(sed -n 's/^at=//p' "$BASELINE")
  return 0
}

case "$CMD" in
  init|accept)
    write_baseline
    printf 'baseline: %s at %s\n' "$(now_branch)" "$(now_head | cut -c1-8)"
    exit 0 ;;
  status)
    read_baseline || die "no baseline - run: session_guard.sh init"
    cat "$BASELINE"; exit 0 ;;
  check) ;;
  -h|--help) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) die "unknown command: $CMD" ;;
esac

FINDINGS=0
report() { FINDINGS=$((FINDINGS + 1)); printf '\n[%d] %s\n' "$FINDINGS" "$1"; }

C_BRANCH=$(now_branch)
C_HEAD=$(now_head)

if read_baseline; then
  if [ "$C_BRANCH" != "$B_BRANCH" ]; then
    report "THE BRANCH CHANGED UNDER YOU"
    printf '    started on : %s\n    now on     : %s\n' "$B_BRANCH" "$C_BRANCH"
    printf '    Anything you commit now lands on %s. Another session very likely\n' "$C_BRANCH"
    printf '    switched this directory. Do not commit. Use a worktree.\n'
  elif [ "$C_HEAD" != "$B_HEAD" ]; then
    if git merge-base --is-ancestor "$B_HEAD" "$C_HEAD" 2>/dev/null; then
      NEW=$(git log --oneline "$B_HEAD..$C_HEAD" 2>/dev/null | wc -l | tr -d ' ')
      report "COMMITS APPEARED THAT YOU DID NOT MAKE ($NEW since you started)"
      git log --pretty='    %h  %an  %s' "$B_HEAD..$C_HEAD" 2>/dev/null | head -10
      printf '    If none of these are yours, another session is committing here.\n'
      printf '    Confirm they are yours, then: session_guard.sh accept\n'
    else
      report "HISTORY WAS REWRITTEN OR RESET UNDER YOU"
      printf '    baseline %s is no longer an ancestor of HEAD %s.\n' "$(printf %s "$B_HEAD" | cut -c1-8)" "$(printf %s "$C_HEAD" | cut -c1-8)"
      printf '    Someone ran reset, rebase, or a force fetch. Your commits may be unreachable:\n'
      printf '    check `git reflog` before doing anything else.\n'
    fi
  fi
else
  report "NO BASELINE RECORDED"
  printf '    Nothing to compare against. Run: session_guard.sh init\n'
fi

# Upstream movement.
UPSTREAM=$(git rev-parse --abbrev-ref '@{u}' 2>/dev/null || true)
if [ -n "$UPSTREAM" ]; then
  BEHIND=$(git rev-list --count "HEAD..$UPSTREAM" 2>/dev/null || echo 0)
  if [ "${BEHIND:-0}" -gt 0 ]; then
    report "THE UPSTREAM MOVED ($BEHIND commit(s) on $UPSTREAM you do not have)"
    git log --pretty='    %h  %an  %s' "HEAD..$UPSTREAM" 2>/dev/null | head -5
    printf '    Pull or rebase before pushing. Never force.\n'
  fi
fi

# Staged files that belong to other sessions.
STAGED=$(git diff --cached --name-only 2>/dev/null | grep -E "$SHARED_PATTERNS" || true)
if [ -n "$STAGED" ]; then
  report "STAGED FILES THAT OTHER SESSIONS WRITE"
  printf '%s\n' "$STAGED" | sed 's/^/    /'
  printf '    Unstage them: git restore --staged <file>\n'
  printf '    Never `git checkout` these either - that discards another session work.\n'
fi

# Same branch checked out twice.
DUPES=$(git worktree list --porcelain 2>/dev/null | grep -c "^branch refs/heads/$C_BRANCH$" || true)
if [ "${DUPES:-0}" -gt 1 ]; then
  report "BRANCH '$C_BRANCH' IS CHECKED OUT IN MORE THAN ONE WORKTREE"
  git worktree list | sed 's/^/    /'
fi

# Other worktrees, for awareness only.
OTHERS=$(git worktree list 2>/dev/null | wc -l | tr -d ' ')
printf '\n'
if [ "$FINDINGS" -eq 0 ]; then
  printf 'SAFE  %s at %s  (%s worktree(s) on this repository)\n' "$C_BRANCH" "$(printf %s "$C_HEAD" | cut -c1-8)" "$OTHERS"
  exit 0
fi
printf 'STOP  %d finding(s) - read them before you commit.\n' "$FINDINGS"
exit 1
