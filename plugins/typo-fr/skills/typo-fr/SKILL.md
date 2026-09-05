---
name: typo-fr
description: French typography that survives an AI - no em dashes, correct apostrophes, accented capitals, non-breaking spaces before ; : ! ? and guillemets - applied when writing French text and enforced with a linter that never touches code. Use whenever writing, reviewing, or fixing French copy, UI strings, emails, or documents, and when the user mentions typographie, tiret cadratin, em dash, apostrophe, guillemets, espace insecable, accents, or asks to clean up French text.
---

# Typographie francaise

Two modes. Read the one you need.

## Enforcement mode - you are writing French

Apply these silently, every time. Do not ask, do not explain, just write it right.

| Rule | Wrong | Right |
|---|---|---|
| No em or en dash | `Le prix — 30 €` | `Le prix - 30 €` (or a comma, or a colon) |
| Apostrophe: ASCII by default | `l’offre` (U+2019) | `l'offre` (U+0027) |
| Accents on capitals | `Etat`, `A propos` | `État`, `À propos` |
| oe ligature | `coeur`, `oeuvre` | `cœur`, `œuvre` |
| Thin no-break space before `;` `!` `?` | `Bonjour !` (plain space) | `Bonjour !` (U+202F) |
| No-break space before `:` | `Prix : 30` (plain space) | `Prix : 30` (U+00A0) |
| Guillemets, not straight quotes | `"oui"` | `« oui »` |
| Ordinals | `2ème`, `1ère` | `2e`, `1re` |
| `etc.` | `etc...` | `etc.` |
| No-break space before a unit | `30%`, `20€` | `30 %`, `20 €` (U+00A0) |
| Sentence case in titles | `Notre Nouvelle Offre` | `Notre nouvelle offre` |

The apostrophe rule has a profile, because the right answer depends on where the
text lands:

- **web** (default) - ASCII `'`. Survives copy-paste, search, URLs, database
  round-trips, and every editor.
- **print** - curly `’`. Correct French typography, for PDF and printed matter.
- **data** - ASCII everything, plain spaces, `...` instead of `…`. For CSV, JSON,
  and database fields where an invisible character becomes a bug.

Accents are never optional. "ASCII apostrophes" does not mean "strip the accents":
`é è à ç ù` always stay.

## Audit mode - you are reviewing existing text

```bash
scripts/typo_fr.py check src/ docs/          # report, exits 1 on findings
scripts/typo_fr.py diff README.md            # preview the rewrite
scripts/typo_fr.py fix README.md             # apply
scripts/typo_fr.py fix --profile print livre.md
scripts/typo_fr.py rules                     # the twelve rules
```

It never edits code. In a `.tsx` or `.py` file only string literals and comments
are prose, and a string with no whitespace in it - an import path, a class name, a
key - is left alone even then. In Markdown, code fences, inline code, link
targets, HTML tags, and frontmatter are protected. URLs, emails, file paths, HTML
entities, and times like `14:30` are protected everywhere.

Standard library Python, no dependencies. Regression suite: `sh tests/run.sh`.

## Never run `fix` blind

A whole-repository `fix` on a first run is how you corrupt data. Run `check`,
read the findings, then fix a directory at a time.

Two characters carry meaning even when they look like noise: the BOM at the head
of a CSV exported for Excel, and significant whitespace in a fixture or a dump.
This tool does not touch either, and that is exactly why you should not replace it
with a `sed` one-liner that would.

The remaining traps - non-breaking spaces being invisible in a code review, curly
apostrophes breaking a search index, English text run through a French linter -
are in `references/pieges.md`. The full rule set with its typographic sources is
in `references/regles.md`.
