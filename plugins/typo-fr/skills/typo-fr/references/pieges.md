# Traps

Everything below has cost somebody a real afternoon.

## Never run `fix` on a whole repository the first time

`check` first. Read the findings. Fix one directory at a time. The rules are
conservative, but the first run on an unknown corpus is where you discover that a
"text" file was actually a fixture.

## Two invisible characters that carry meaning

**The BOM at the start of a CSV.** Excel needs it to read UTF-8 accents. Strip it
and every accented character in your export turns to mojibake, in a file you will
only open weeks later. `typo_fr.py` never touches the first bytes of a file.

**Significant whitespace in a dump or a fixture.** A trailing space in a
`.txt` fixture can be exactly what a parser test asserts on. This tool does not
strip trailing whitespace at all - that is a formatter's job, not a typographer's.

This is also the argument against replacing the tool with a `sed -i` one-liner.
A regex over an entire repository has no idea which files are data.

## Non-breaking spaces are invisible in a code review

A diff that inserts U+00A0 looks like a diff that changed nothing. Reviewers
approve it without seeing it, and it lands in a search index, a slug, or a
comparison that then fails.

- Review with `git diff --word-diff-regex=.` or `cat -v`
- `typo_fr.py diff` prints them as `[insec]` and `[fine]` so they are visible
- In a JSON API payload or a database key, prefer `--profile data`

## Curly apostrophes break search

`l’offre` and `l'offre` are different strings. A user typing `l'offre` into your
search box finds nothing. If your content is searchable, use `--profile web`. If
it is typeset, use `--profile print`. Do not mix them in one corpus.

## A French linter run on English text

`Prix : 30` gets a no-break space; `Price: 30` should not. The rules assume
French. Point the tool at your French content, not at the whole repository, or
you will insert French spacing into your English README.

## Strings that look like prose but are not

`"flex items-center gap-2"` is a class list. `"./coeur-utils"` is an import path.
`"user_2eme_visite"` is a key. Rewriting any of them breaks the program silently.

The heuristic: inside code, a string with no whitespace is never prose. That means
a one-word French string in a `.tsx` file will not be corrected. That is the price
of never breaking an import, and it is the right trade.

## The frontmatter question

YAML frontmatter in Markdown is skipped entirely. A `description:` in there is
prose and would benefit from the rules, but a key, a slug, or a date would be
corrupted by them. Fix frontmatter by hand.

## Prompts written in ASCII produce output in ASCII

If you write a prompt in stripped-down ASCII - no accents, straight quotes - the
model copies that register and answers the same way. When you want accented,
correctly typeset French out, write accented, correctly typeset French in. The
typography of your prompt is part of the prompt.
