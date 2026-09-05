# typo-fr

**French typography that survives an AI.**

A Claude Code skill in two parts: rules applied automatically when writing French,
and a linter that fixes existing text without ever touching your code.

```
/plugin marketplace add JohnJackHouzi/typo-fr
/plugin install typo-fr@typo-fr
```

> Type these in Claude Code (the interface you get by running `claude`), not in
> your shell. From a plain shell, the same thing is:
>
> ```
> claude plugin marketplace add JohnJackHouzi/typo-fr
> claude plugin install typo-fr@typo-fr
> ```

**What you get.** The `typo-fr` skill, which applies the rules to every French
sentence the agent writes, and a `/typo` command to check or fix existing files.

**Requirements.** Python 3.8+, standard library only. No pip install, no
dependencies.

**Without Claude Code.** The linter is a single file:
`git clone https://github.com/JohnJackHouzi/typo-fr && python3 typo-fr/skills/typo-fr/scripts/typo_fr.py check mon-texte.md`

---

## The problem

An AI writing French writes English typography. Em dashes everywhere, because its
training text is mostly English. `Etat` without its accent, because the model saw
`State`. `2ème` instead of `2e`. `"guillemets droits"` instead of `« guillemets »`.
And never, not once, the non-breaking space French requires before `; : ! ?`.

Every one of those is a tell. A French reader sees machine output before reading a
sentence.

## What it does

**When writing**, the skill applies the rules silently - no em dash, correct
apostrophe, accents on capitals, `cœur` not `coeur`, `30 %` not `30%`,
sentence case in titles.

**When reviewing**, the linter finds and fixes them:

```console
$ typo_fr.py check demo.md
demo.md:1:3   TFR012  titre en Title Case anglais  (check only)
demo.md:3:14  TFR001  tiret cadratin: utiliser ' - ', une virgule ou deux-points
demo.md:3:51  TFR003  accent manquant sur la capitale: Etats -> États
demo.md:5:16  TFR004  ligature oe manquante: coeur -> cœur
demo.md:5:41  TFR009  ordinal francais: 2ème -> 2e
demo.md:5:51  TFR005  espace fine insecable manquante avant « ! »
demo.md:8:12  TFR006  guillemets droits: le francais utilise « » avec une espace insecable
demo.md:8:48  TFR008  « etc. » ne prend jamais de points de suspension

14 finding(s). Nothing was written - run `fix` to apply, `diff` to preview.
```

## It never touches your code

This is the part other tools get wrong. Given this file:

```tsx
// Le coeur du composant — voir la 2ème version
import { Truc } from "./coeur-utils";
const KEY = "coeur_2eme";
const label = "Prix : 30% de remise";
```

`typo_fr.py fix` produces:

```tsx
// Le cœur du composant - voir la 2e version
import { Truc } from "./coeur-utils";     <- untouched
const KEY = "coeur_2eme";                  <- untouched
const label = "Prix : 30 % de remise";     <- fixed
```

In code, only string literals and comments are prose - and a string with no
whitespace in it (an import path, a class name, a key) is left alone even then.
In Markdown, code fences, inline code, link targets, HTML tags, and frontmatter
are protected. URLs, emails, file paths, HTML entities, and times like `14:30`
are protected everywhere.

## Three profiles, because the apostrophe has no single right answer

| Profile | Apostrophe | Spaces | For |
|---|---|---|---|
| `web` (default) | `'` U+0027 | real non-breaking | sites, apps, UI strings |
| `print` | `’` U+2019 | real non-breaking | PDF, printed books |
| `data` | `'` U+0027 | plain | CSV, JSON, database fields |

Typographically the curly apostrophe is correct. Technically the ASCII one
survives copy-paste, search, slugs and `LIKE` queries. Pick one per project and
stay with it: `l’offre` and `l'offre` are different strings, and a search for one
will not find the other.

Accents are never optional. "ASCII apostrophes" does not mean "strip the accents".

## Usage

```bash
typo_fr.py check src/ docs/          # report, exits 1 on findings
typo_fr.py diff README.md            # preview, writes nothing
typo_fr.py fix README.md             # apply
typo_fr.py fix --profile print livre.md
typo_fr.py check --skip TFR012 .     # ignore a rule
typo_fr.py rules                     # the twelve rules
```

Or through the skill:

```
/typo src/app/**/*.tsx
```

Standard library Python, no dependencies, so it also runs in CI or from any other
agent. Regression suite:

```console
$ sh tests/run.sh
  ok    markdown prose
  ok    idempotent second pass
  ok    import path untouched
  ok    identifier untouched
  ok    prose string fixed
  ok    code fence untouched
  ok    inline code untouched
  ok    url untouched
  ok    print profile curly
  ok    data profile ascii

10 passed, 0 failed
```

## Never run `fix` blind

Two invisible characters carry meaning: the BOM at the head of a CSV exported for
Excel, and significant whitespace in a fixture. This tool touches neither - which
is exactly why you should not replace it with a `sed` one-liner that would. Run
`check` first, read the findings, fix a directory at a time.

The twelve rules with their typographic sources are in
[`regles.md`](skills/typo-fr/references/regles.md). The traps - non-breaking
spaces invisible in a code review, curly apostrophes breaking a search index,
strings that look like prose and are not - are in
[`pieges.md`](skills/typo-fr/references/pieges.md).

---

## En français

Une IA qui écrit en français applique la typographie anglaise : tirets cadratins
partout, `Etat` sans accent, `2ème` au lieu de `2e`, guillemets droits, et jamais
l'espace insécable avant `;` `:` `!` `?`. Ce sont des marqueurs : un lecteur
français voit que le texte sort d'une machine avant même de le lire.

Ce skill applique les règles quand il écrit, et les corrige quand il relit, sans
jamais toucher au code. Trois profils, parce que l'apostrophe n'a pas une seule
bonne réponse : `web` (ASCII, résiste au copier-coller et à la recherche),
`print` (courbe, pour le PDF et l'imprimé), `data` (tout en ASCII, pour les CSV
et les champs de base).

Installation dans Claude Code, pas dans le terminal :

```
/plugin marketplace add JohnJackHouzi/typo-fr
/plugin install typo-fr@typo-fr
```

---

## More skills

One repo per skill, so you install only what you want:
[prove-it](https://github.com/JohnJackHouzi/prove-it) - capture real evidence
before an agent claims success.
[safe-worktree](https://github.com/JohnJackHouzi/safe-worktree) - run several
agents on one repository without stealing each other's work.

---

MIT.
