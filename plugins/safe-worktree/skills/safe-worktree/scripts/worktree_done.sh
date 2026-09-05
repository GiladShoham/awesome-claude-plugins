#!/usr/bin/env sh
# worktree_done.sh - finish a branch and remove its worktree, safely.
#
#   worktree_done.sh [--base main] [--keep-branch] [--yes] [--dry-run]
#
# Refuses while uncommitted or untracked work exists. Then decides whether the
# branch is merged by comparing FILE CONTENTS against the base branch, because
# `git branch --merged` reports a squash-merged branch as unmerged and a
# rebase-merged branch as unmerged too.

set -u

BASE=""
KEEP=0
YES=0
DRY=0

die() { printf 'STOP - %s\n' "$*" >&2; exit 1; }
say() { printf '%s\n' "$*"; }
run() { if [ "$DRY" -eq 1 ]; then printf '  would run: %s\n' "$*"; else eval "$@"; fi; }

while [ $# -gt 0 ]; do
  case "$1" in
    --base)         [ $# -ge 2 ] || die "--base needs a value"; BASE="$2"; shift 2 ;;
    --keep-branch)  KEEP=1; shift ;;
    --yes|-y)       YES=1; shift ;;
    --dry-run)      DRY=1; shift ;;
    -h|--help)      sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *)              die "unknown argument: $1" ;;
  esac
done

command -v git >/dev/null 2>&1 || die "git not found"
ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || die "not inside a git repository"
BRANCH=$(git rev-parse --abbrev-ref HEAD)
[ "$BRANCH" = "HEAD" ] && die "detached HEAD - check out a branch first"

# Is this a linked worktree, or the main checkout?
COMMON=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || git rev-parse --git-common-dir)
MAIN_ROOT=$(dirname "$COMMON")
IS_WORKTREE=0
[ "$ROOT" != "$MAIN_ROOT" ] && IS_WORKTREE=1

# Base branch: given, or the first of main/master/develop that exists.
if [ -z "$BASE" ]; then
  for b in main master develop; do
    git show-ref --verify --quiet "refs/heads/$b" && { BASE="$b"; break; }
  done
fi
[ -n "$BASE" ] || die "no base branch found - pass --base <branch>"
[ "$BASE" = "$BRANCH" ] && die "you are on the base branch ($BASE), nothing to finish"

say "worktree : $ROOT$([ "$IS_WORKTREE" -eq 0 ] && echo '  (main checkout, not a linked worktree)')"
say "branch   : $BRANCH"
say "base     : $BASE"
say ""

# --- 1. unfinished work ---------------------------------------------------
DIRTY=$(git status --porcelain 2>/dev/null)
if [ -n "$DIRTY" ]; then
  say "UNFINISHED WORK IN THIS WORKTREE:"
  printf '%s\n' "$DIRTY" | sed 's/^/  /'
  die "commit it, stash it, or delete it deliberately. This script will not decide for you."
fi

UNPUSHED=""
if git rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
  UNPUSHED=$(git log --oneline '@{u}..HEAD' 2>/dev/null)
else
  UNPUSHED=$(git log --oneline "$BASE..HEAD" 2>/dev/null)
fi

# --- 2. is the content actually in the base branch? -----------------------
git show-ref --verify --quiet "refs/heads/$BASE" || die "base branch '$BASE' not found locally"
MERGE_BASE=$(git merge-base "$BASE" HEAD) || die "no common ancestor with $BASE"

CHANGED=$(git diff --name-only "$MERGE_BASE" HEAD)
PENDING=""
if [ -n "$CHANGED" ]; then
  OLDIFS=$IFS; IFS='
'
  for f in $CHANGED; do
    if ! git diff --quiet "$BASE" HEAD -- "$f" 2>/dev/null; then
      PENDING="$PENDING$f
"
    fi
  done
  IFS=$OLDIFS
fi

ANCESTOR=0
git merge-base --is-ancestor HEAD "$BASE" 2>/dev/null && ANCESTOR=1

if [ -z "$CHANGED" ]; then
  say "MERGED  the branch introduces no changes against $BASE."
elif [ -z "$PENDING" ]; then
  if [ "$ANCESTOR" -eq 1 ]; then
    say "MERGED  every commit is an ancestor of $BASE."
  else
    say "MERGED  $BASE already contains every file this branch changed, byte for byte."
    say "        Not an ancestor: this was a squash or a rebase merge. \`git branch"
    say "        --merged\` would have told you the opposite. Content wins."
  fi
else
  say "NOT MERGED  $BASE differs from this branch on:"
  printf '%s' "$PENDING" | sed 's/^/  /'
  if [ -n "$UNPUSHED" ]; then
    say ""
    say "  and these commits are not on the upstream yet:"
    printf '%s\n' "$UNPUSHED" | sed 's/^/    /'
    say ""
    say "  If a pull request for this branch was already merged, it did NOT include"
    say "  them. Open a new one rather than assuming they went along for the ride."
  fi
  die "refusing to remove a worktree whose work is not in $BASE."
fi

# --- 3. remove ------------------------------------------------------------
say ""
if [ "$YES" -eq 0 ] && [ "$DRY" -eq 0 ]; then
  printf 'Remove the worktree%s? [y/N] ' "$([ "$KEEP" -eq 0 ] && echo " and delete branch '$BRANCH'")"
  read -r ANSWER </dev/tty 2>/dev/null || ANSWER=""
  case "$ANSWER" in y|Y|yes|YES) ;; *) die "cancelled - nothing was removed" ;; esac
fi

if [ "$IS_WORKTREE" -eq 1 ]; then
  run "git -C \"$MAIN_ROOT\" worktree remove \"$ROOT\""
  say "removed worktree $ROOT"
else
  say "main checkout: not removing the directory."
fi

if [ "$KEEP" -eq 0 ]; then
  if [ "$ANCESTOR" -eq 1 ]; then
    run "git -C \"$MAIN_ROOT\" branch -d \"$BRANCH\""
  else
    # Content is provably in the base branch; git would still refuse -d here.
    run "git -C \"$MAIN_ROOT\" branch -D \"$BRANCH\""
  fi
  say "deleted branch $BRANCH"
fi
