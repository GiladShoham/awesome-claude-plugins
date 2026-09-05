#!/usr/bin/env sh
# Regression tests for typo_fr.py. Run: sh tests/run.sh
set -u
DIR=$(cd "$(dirname "$0")" && pwd)
TYPO="$DIR/../scripts/typo_fr.py"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
PASS=0; FAIL=0
NNBSP=$(printf '\342\200\257')   # espace fine insecable
CURLY=$(printf '\342\200\231')   # apostrophe courbe

t() { # t <name> <expected> <actual>
  if [ "$2" = "$3" ]; then PASS=$((PASS+1)); printf '  ok    %s\n' "$1"
  else FAIL=$((FAIL+1)); printf '  FAIL  %s\n    expected: %s\n    actual  : %s\n' "$1" "$2" "$3"; fi
}

printf 'Le coeur — la 2ème étape !\n' > "$TMP/a.md"
python3 "$TYPO" fix "$TMP/a.md" >/dev/null
t "markdown prose" "Le cœur - la 2e étape${NNBSP}!" "$(cat "$TMP/a.md")"

printf 'clean\n' > "$TMP/b.md"
python3 "$TYPO" check "$TMP/b.md" >/dev/null
t "idempotent second pass" "0" "$?"

cat > "$TMP/c.tsx" <<'TSX'
import { A } from "./coeur-utils";
const K = "coeur_2eme";
const label = "Le coeur — la 2ème étape";
TSX
python3 "$TYPO" fix "$TMP/c.tsx" >/dev/null
t "import path untouched"  "1" "$(grep -c 'coeur-utils' "$TMP/c.tsx")"
t "identifier untouched"   "1" "$(grep -c 'coeur_2eme' "$TMP/c.tsx")"
t "prose string fixed"     "1" "$(grep -c 'Le cœur - la 2e étape' "$TMP/c.tsx")"

cat > "$TMP/d.md" <<'MD'
Texte : voir `npm run dev !` et https://x.com/a?b=1 puis fin.

```js
const s = "coeur — 2ème !";
```
MD
python3 "$TYPO" fix "$TMP/d.md" >/dev/null
t "code fence untouched"   "1" "$(grep -c 'coeur — 2ème !' "$TMP/d.md")"
t "inline code untouched"  "1" "$(grep -c 'npm run dev !' "$TMP/d.md")"
t "url untouched"          "1" "$(grep -c 'https://x.com/a?b=1' "$TMP/d.md")"

printf "l'enfant\n" > "$TMP/e.md"
python3 "$TYPO" fix --profile print "$TMP/e.md" >/dev/null
t "print profile curly"    "l${CURLY}enfant" "$(cat "$TMP/e.md")"

printf 'Prix\302\240: 30\302\240%% et l\342\200\231offre\342\200\246\n' > "$TMP/f.md"
python3 "$TYPO" fix --profile data "$TMP/f.md" >/dev/null
t "data profile ascii"     "Prix : 30 % et l'offre..." "$(cat "$TMP/f.md")"

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
