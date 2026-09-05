#!/usr/bin/env sh
# worktree_new.sh - create an isolated, immediately runnable worktree.
#
# Sibling directory, same filesystem, copy-on-write node_modules, ignored env
# files carried over. Refuses the placements that quietly break dev servers.
#
# Usage:
#   worktree_new.sh BRANCH [PATH] [--from BASE] [--existing] [--no-deps] [--no-env] [--dry-run]
#
#   BRANCH        branch to create (or to check out, with --existing)
#   PATH          worktree location (default: ../<repo>-<branch slug>)
#   --from BASE   base branch or commit for the new branch (default: current HEAD)
#   --existing    check out an existing branch instead of creating one
#   --no-deps     do not clone node_modules
#   --no-env      do not copy ignored env files
#   --dry-run     print what would happen, change nothing

set -u

BRANCH=""
TARGET=""
BASE=""
EXISTING=0
DEPS=1
ENVS=1
DRY=0

die() { printf 'STOP - %s\n' "$*" >&2; exit 1; }
say() { printf '%s\n' "$*"; }
run() { if [ "$DRY" -eq 1 ]; then printf '  would run: %s\n' "$*"; else eval "$@"; fi; }

while [ $# -gt 0 ]; do
  case "$1" in
    --from)     [ $# -ge 2 ] || die "--from needs a value"; BASE="$2"; shift 2 ;;
    --existing) EXISTING=1; shift ;;
    --no-deps)  DEPS=0; shift ;;
    --no-env)   ENVS=0; shift ;;
    --dry-run)  DRY=1; shift ;;
    -h|--help)  sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)         die "unknown option: $1" ;;
    *)          if [ -z "$BRANCH" ]; then BRANCH="$1"; elif [ -z "$TARGET" ]; then TARGET="$1";
                else die "unexpected argument: $1"; fi; shift ;;
  esac
done

[ -n "$BRANCH" ] || die "usage: worktree_new.sh BRANCH [PATH] [options]  (--help for more)"
command -v git >/dev/null 2>&1 || die "git not found"

ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || die "not inside a git repository"
REPO=$(basename "$ROOT")
SLUG=$(printf '%s' "$BRANCH" | sed -e 's#.*/##' -e 's/[^A-Za-z0-9._-]/-/g')
[ -n "$TARGET" ] || TARGET="$(dirname "$ROOT")/$REPO-$SLUG"

# Absolute path without requiring the directory to exist yet.
case "$TARGET" in
  /*) ;;
  *)  TARGET="$(cd "$(dirname "$TARGET")" 2>/dev/null && pwd)/$(basename "$TARGET")" ;;
esac

# --- refusals -------------------------------------------------------------
case "$TARGET" in
  /tmp/*|/private/tmp/*|/var/folders/*)
    die "refusing to create a worktree under a temp directory.
     Temp dirs are wiped without warning and are usually on another filesystem,
     which defeats the copy-on-write clone of node_modules and breaks dev servers." ;;
esac
[ -e "$TARGET" ] && die "target already exists: $TARGET"

case "$TARGET" in
  "$ROOT"/*) die "refusing to nest a worktree inside the repository: $TARGET" ;;
esac

if git worktree list --porcelain | grep -q "^branch refs/heads/$BRANCH$"; then
  WHERE=$(git worktree list | grep "\[$BRANCH\]" | awk '{print $1}')
  die "branch '$BRANCH' is already checked out at: ${WHERE:-another worktree}
     Two checkouts of one branch is exactly the collision this script prevents."
fi

if [ "$EXISTING" -eq 1 ]; then
  git show-ref --verify --quiet "refs/heads/$BRANCH" || die "branch '$BRANCH' does not exist (drop --existing to create it)"
else
  git show-ref --verify --quiet "refs/heads/$BRANCH" && die "branch '$BRANCH' already exists (use --existing to check it out)"
fi

# Same filesystem? Copy-on-write cloning needs it, and so does a fast setup.
fsid() { if [ "$(uname)" = "Darwin" ]; then stat -f %d "$1" 2>/dev/null; else stat -c %d "$1" 2>/dev/null; fi; }
SAME_FS=1
if [ "$(fsid "$ROOT")" != "$(fsid "$(dirname "$TARGET")")" ]; then
  SAME_FS=0
  say "WARNING: $TARGET is on a different filesystem than the repository."
  say "         node_modules will be copied byte for byte, not cloned. This is slow."
fi

# --- create ---------------------------------------------------------------
say "repository : $ROOT"
say "worktree   : $TARGET"
say "branch     : $BRANCH$([ "$EXISTING" -eq 1 ] && echo ' (existing)')"
[ -n "$BASE" ] && say "base       : $BASE"

if [ "$EXISTING" -eq 1 ]; then
  run "git worktree add \"$TARGET\" \"$BRANCH\""
else
  run "git worktree add -b \"$BRANCH\" \"$TARGET\" ${BASE:+\"$BASE\"}"
fi

# --- dependencies ---------------------------------------------------------
if [ "$DEPS" -eq 1 ] && [ -d "$ROOT/node_modules" ]; then
  say ""
  say "cloning node_modules (copy-on-write, no reinstall)"
  if [ "$(uname)" = "Darwin" ] && [ "$SAME_FS" -eq 1 ]; then
    # -c uses APFS clonefile: near-instant, no extra disk usage.
    run "cp -Rc \"$ROOT/node_modules\" \"$TARGET/node_modules\"" || \
      run "cp -R \"$ROOT/node_modules\" \"$TARGET/node_modules\""
  elif cp --help 2>&1 | grep -q reflink; then
    run "cp -R --reflink=auto \"$ROOT/node_modules\" \"$TARGET/node_modules\""
  else
    run "cp -R \"$ROOT/node_modules\" \"$TARGET/node_modules\""
  fi
  say "  never symlink node_modules into a worktree: bundlers resolve through the"
  say "  link and load the other checkout's code. See references/."
fi

# --- ignored env files ----------------------------------------------------
if [ "$ENVS" -eq 1 ]; then
  COPIED=""
  for f in .env .env.local .env.development .env.development.local .env.test.local .env.production.local; do
    if [ -f "$ROOT/$f" ] && git -C "$ROOT" check-ignore -q "$f" 2>/dev/null; then
      run "cp \"$ROOT/$f\" \"$TARGET/$f\""
      COPIED="$COPIED $f"
    fi
  done
  [ -n "$COPIED" ] && { say ""; say "copied ignored env files:$COPIED"; }
fi

say ""
say "NEXT"
say "  cd $TARGET"
say "  scripts/session_guard.sh init"
say ""
say "  Do not switch branch in $ROOT while this worktree is open."
say "  A dev server here needs its own port: the other checkout is still running."
