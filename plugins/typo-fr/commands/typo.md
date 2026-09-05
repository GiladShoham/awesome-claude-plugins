---
description: Check or fix French typography in the given files, without ever touching code.
argument-hint: [files or directories, optionally "fix" or --profile print]
---

Use the `typo-fr` skill on:

**$ARGUMENTS**

If no path was given, use the files changed in this session.

Run `check` first and show the findings. Only run `fix` when the user asked for it
or when the findings are unambiguous, and never on a whole repository in one go.
Pick the profile from where the text lands: `web` for a site or app, `print` for a
PDF or a book, `data` for CSV, JSON, and database fields.

From now on in this conversation, also apply the enforcement rules to every French
sentence you write yourself: no em dash, correct apostrophe for the profile,
accents on capitals, non-breaking spaces before `;` `:` `!` `?`, guillemets.
