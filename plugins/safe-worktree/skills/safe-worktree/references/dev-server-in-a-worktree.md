# Making a worktree actually runnable

A worktree that cannot run its dev server is a worktree you will abandon. Three
things decide whether it runs.

## 1. node_modules: clone it, never symlink it

`npm install` in every worktree costs minutes and gigabytes. The tempting fix,
`ln -s ../main/node_modules`, is the wrong one: bundlers resolve through the
symlink to its real path, and then load and watch **the other checkout's** files.
Turbopack, Vite, and webpack all do this. You get a dev server that serves code
from a directory you are not editing, and edits that appear to have no effect.

Copy-on-write is the answer. It costs no extra disk space and takes a second:

```sh
cp -Rc  node_modules ../repo-branch/node_modules              # macOS, APFS clonefile
cp -R --reflink=auto node_modules ../repo-branch/node_modules  # Linux, btrfs/xfs
```

`worktree_new.sh` picks the right one and falls back to a plain copy with a
warning when neither is available.

## 2. Same filesystem, and never a temp directory

Copy-on-write only works within one filesystem. A worktree in `/tmp` (often a
different volume, and on macOS a different one than `$HOME`) silently degrades to
a full byte-for-byte copy - and gets wiped without warning, along with any
uncommitted work in it.

Put worktrees beside the repository: `../<repo>-<branch>`. Same volume, obvious
in a file listing, and they sort next to each other.

## 3. Env files and ports

`.env.local` and friends are ignored by git, so a worktree starts without them and
the app boots into a broken configuration that looks like a code bug.
`worktree_new.sh` copies every ignored `.env*` it finds.

The other checkout's dev server is still running on the default port. Start the
worktree's on another one:

```sh
PORT=3001 npm run dev        # or: next dev -p 3001
```

Keep a note of which port belongs to which worktree; two servers on adjacent ports
serving different branches is its own way to lose an afternoon.

## 4. Build caches

`.next`, `.turbo`, `dist`, `.cache`: do not copy them between worktrees. They
contain absolute paths and stale build state from the other branch. Let them
rebuild. The first build is slower; every wrong answer you avoid is worth more.
