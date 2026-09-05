# The rules, and why they are the rules

French typography is not a matter of taste. Most of these come from the
*Lexique des règles typographiques en usage à l'Imprimerie nationale*, which is
what French publishers, newsrooms, and public administrations follow.

---

## TFR001 - no em dash, no en dash

`—` (U+2014) and `–` (U+2013) belong to English typography. French uses the
comma, the colon, the parenthesis, or a hyphen surrounded by spaces.

An AI writing French reaches for the em dash constantly, because its training text
is mostly English. It is the single clearest tell that a French text was machine
written.

```
wrong   Le prix — et c'est important — reste stable.
right   Le prix, et c'est important, reste stable.
right   Le prix - et c'est important - reste stable.
```

Note the exception nobody breaks: the dash used as a dialogue marker in fiction
is a real French usage. This tool only rewrites dashes surrounded by spaces in
running text, and it never touches a line that starts with one.

## TFR002 - the apostrophe has two right answers

Typographically, French uses `’` (U+2019). Technically, `'` (U+0027) is the one
that survives a copy-paste into a form, a URL slug, a `LIKE` query, a CSV opened
in Excel, and a terminal.

So the answer depends on the destination, which is what the profiles are for:

| Profile | Apostrophe | Use for |
|---|---|---|
| `web` | `'` U+0027 | websites, apps, UI strings, anything searchable |
| `print` | `’` U+2019 | PDF, printed books, anything typeset |
| `data` | `'` U+0027 | CSV, JSON, database fields |

Pick one per project and stay with it. Mixing both in one corpus is worse than
either: a search for `l'offre` will find half your rows.

## TFR003 - capitals keep their accents

`Etat`, `A propos`, `Ecole`: wrong, always. The idea that French capitals lose
their accents is a limitation of mechanical typewriters that survived into folklore.
The Académie francaise is explicit: the accent has full orthographic value.

Detecting a missing accent in general needs a dictionary, so this rule uses a
list of the words that actually show up: `Etat`, `Ecole`, `Eglise`, `Evenement`,
`Etude`, `Equipe`, `Editions`, `Energie`, `Economie`, `Education`, `Ile`, and
their plurals. Lowercase words are not touched.

## TFR004 - the oe ligature

`cœur`, `œuvre`, `sœur`, `nœud`, `vœux`, `œil`, `bœuf`. These are one letter, not
two. `coeur` is a spelling mistake, not a typographic variant.

## TFR005 - unbreakable spaces before high punctuation

French puts a space before `;` `:` `!` `?` and inside guillemets. That space must
not break at the end of a line, or you get a `?` alone at the start of a line.

| Sign | Space |
|---|---|
| `;` `!` `?` | thin no-break, U+202F |
| `:` | no-break, U+00A0 |
| `« »` | thin no-break inside |
| `,` `.` | none before, one after |

If U+202F renders badly in your stack, `--profile data` falls back to plain
spaces everywhere. Never leave a *breaking* space there.

## TFR006 - guillemets

`« comme ceci »`, not `"comme ceci"` and not `"comme ceci"`. For a quote inside a
quote, French uses the English double quotes as the inner pair.

## TFR007 / TFR008 - ellipsis

One character, `…` (U+2026), not three periods. And `etc.` never takes one:
`etc...` is wrong twice over, since `etc.` already ends in a period.

## TFR009 - ordinals

`1er`, `1re`, `2e`, `3e`, `21e`. Not `2ème`, not `2ième`, not `1ère`. The
abbreviation keeps the last letters of the spoken word: *premier* gives `1er`,
*premiere* gives `1re`, *deuxieme* gives `2e`.

## TFR010 - spacing

One space after a comma or period, never before. Never two spaces in a row - the
double space after a period is an American typewriter habit that French never had.

## TFR011 - units and symbols

`30 %`, `20 €`, `15 km`, with a no-break space. The number and its unit belong
together on one line.

## TFR012 - sentence case, not Title Case (check only)

`Notre nouvelle offre`, not `Notre Nouvelle Offre`. French capitalises the first
word and proper nouns, nothing else. This is reported but never auto-fixed:
distinguishing a proper noun from a capitalised common noun needs judgement.
