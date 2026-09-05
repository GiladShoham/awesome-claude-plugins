#!/usr/bin/env python3
"""typo_fr.py - French typography linter that never touches your code.

Checks by default, fixes only when asked, and only inside the parts of a file
that are prose: never inside code fences, inline code, URLs, HTML tags, import
paths, template-literal expressions, or identifiers.

    typo_fr.py check src/**/*.tsx docs/*.md      # report, exit 1 on findings
    typo_fr.py fix README.md                      # rewrite in place
    typo_fr.py diff README.md                     # unified diff, write nothing
    typo_fr.py check --profile print livre.md     # curly apostrophes for print
    typo_fr.py rules                              # list every rule

Profiles
    web    (default) ASCII apostrophes, guillemets, real non-breaking spaces
    print  curly apostrophes, otherwise identical - for PDF and printed matter
    data   ASCII everything, plain spaces - for CSV, JSON, database fields

Standard library only. Python 3.8+.
"""

import argparse
import difflib
import os
import re
import sys
import unicodedata

NBSP = "\u00a0"        # espace insecable
NNBSP = "\u202f"       # espace fine insecable
APOS_CURLY = "\u2019"
APOS_ASCII = "'"
ELLIPSIS = "\u2026"

TEXT_EXT = {".md", ".mdx", ".txt", ".rst", ".markdown", ""}
CODE_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".php", ".rb", ".go", ".java", ".swift", ".kt", ".css", ".scss"}
HTML_EXT = {".html", ".htm", ".vue", ".svelte"}

PROFILES = {
    "web":   {"apostrophe": APOS_ASCII, "guillemets": True,  "ellipsis": True,  "nbsp": "thin"},
    "print": {"apostrophe": APOS_CURLY, "guillemets": True,  "ellipsis": True,  "nbsp": "thin"},
    "data":  {"apostrophe": APOS_ASCII, "guillemets": False, "ellipsis": False, "nbsp": "none"},
}

# Words an AI routinely strips the accent from, always at the start of a word.
ACCENT_FIXES = {
    "Etat": "État", "Etats": "États", "Etats-Unis": "États-Unis", "Ecole": "École",
    "Eglise": "Église", "Evenement": "Événement", "Evenements": "Événements",
    "Etude": "Étude", "Etudes": "Études", "Equipe": "Équipe", "Equipes": "Équipes",
    "Editions": "Éditions", "Edition": "Édition", "Energie": "Énergie",
    "Economie": "Économie", "Education": "Éducation", "Elysee": "Élysée",
    "Evaluation": "Évaluation", "Etablissement": "Établissement",
    "Etablissements": "Établissements", "Elu": "Élu", "Elus": "Élus",
    "Emission": "Émission", "Emissions": "Émissions", "Ile": "Île",
    "Etre": "Être", "Egalite": "Égalité", "Eleve": "Élève", "Eleves": "Élèves",
    "Ete": "Été", "Ecrit": "Écrit", "Ecrire": "Écrire", "Echec": "Échec",
}

OE_FIXES = {
    "coeur": "cœur", "coeurs": "cœurs", "soeur": "sœur", "soeurs": "sœurs",
    "oeuvre": "œuvre", "oeuvres": "œuvres", "noeud": "nœud", "noeuds": "nœuds",
    "voeu": "vœu", "voeux": "vœux", "oeil": "œil", "boeuf": "bœuf",
    "oeuf": "œuf", "oeufs": "œufs", "manoeuvre": "manœuvre", "manoeuvres": "manœuvres",
    "soeurette": "sœurette", "choeur": "chœur", "choeurs": "chœurs",
    "voeux": "vœux", "oesophage": "œsophage", "foetus": "fœtus",
}

ORDINALS = [
    (re.compile(r"\b1(?:ere|ère|ère)\b"), "1re"),
    (re.compile(r"\b1(?:er|ier)\b(?!e)"), "1er"),
    (re.compile(r"\b(\d+)(?:ème|eme|ieme|ième)\b"), r"\1e"),
]

URL_RE = re.compile(r"""(?:https?://|ftp://|mailto:|www\.)[^\s<>"'`)\]]+""")
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
PATH_RE = re.compile(r"""(?:^|(?<=[\s("'`]))(?:\.{0,2}/)[\w./@-]+""")
ENTITY_RE = re.compile(r"&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);")
TIME_RE = re.compile(r"\b\d{1,2}[:h]\d{2}\b")


class Finding:
    __slots__ = ("start", "end", "repl", "rule", "message", "fixable")

    def __init__(self, start, end, repl, rule, message, fixable=True):
        self.start, self.end, self.repl = start, end, repl
        self.rule, self.message, self.fixable = rule, message, fixable


# --------------------------------------------------------------------------
# Protected regions: everything that is not prose.
# --------------------------------------------------------------------------

def spans_markdown(text):
    spans = []
    for m in re.finditer(r"^```.*?^```", text, re.S | re.M):
        spans.append((m.start(), m.end()))
    for m in re.finditer(r"^~~~.*?^~~~", text, re.S | re.M):
        spans.append((m.start(), m.end()))
    for m in re.finditer(r"`[^`\n]+`", text):
        spans.append((m.start(), m.end()))
    for m in re.finditer(r"^(?: {4}|\t)\S.*$", text, re.M):
        spans.append((m.start(), m.end()))
    # YAML frontmatter: keys and structure are not prose.
    fm = re.match(r"^---\n.*?\n---\n", text, re.S)
    if fm:
        spans.append((fm.start(), fm.end()))
    for m in re.finditer(r"<[^>\n]+>", text):          # raw HTML tags
        spans.append((m.start(), m.end()))
    for m in re.finditer(r"\]\([^)\n]*\)", text):      # link targets
        spans.append((m.start(), m.end()))
    return spans


def spans_code(text):
    """Everything except string literals and comments is protected.

    A string with no whitespace in it is not prose: it is an import path, a class
    name, a key, an identifier. Rewriting one breaks the program, so those are
    protected too. The cost is a missed correction in a one-word sentence; the
    alternative is a broken import, which is not a trade worth making.
    """
    prose = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in "\"'":
            q, j = c, i + 1
            while j < n and text[j] != q:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == "\n":
                    break
                j += 1
            prose.append((i + 1, min(j, n)))
            i = j + 1
            continue
        if c == "`":
            j, depth = i + 1, 0
            start = j
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == "$" and j + 1 < n and text[j + 1] == "{":
                    prose.append((start, j))
                    depth, j = 1, j + 2
                    while j < n and depth:
                        if text[j] == "{":
                            depth += 1
                        elif text[j] == "}":
                            depth -= 1
                        j += 1
                    start = j
                    continue
                if text[j] == "`":
                    break
                j += 1
            prose.append((start, min(j, n)))
            i = j + 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            j = n if j == -1 else j
            prose.append((i + 2, j))
            i = j
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i)
            j = n if j == -1 else j + 2
            prose.append((i + 2, max(i + 2, j - 2)))
            i = j
            continue
        if c == "#":                                    # python / shell comment
            j = text.find("\n", i)
            j = n if j == -1 else j
            prose.append((i + 1, j))
            i = j
            continue
        i += 1
    prose = [(a, b) for (a, b) in prose if re.search(r"\s", text[a:b])]
    return invert(prose, len(text))


def spans_html(text):
    prose = []
    last = 0
    for m in re.finditer(r"<[^>]*>", text):
        prose.append((last, m.start()))
        last = m.end()
    prose.append((last, len(text)))
    protected = invert(prose, len(text))
    for m in re.finditer(r"<(script|style)\b.*?</\1>", text, re.S | re.I):
        protected.append((m.start(), m.end()))
    return protected


def invert(prose, length):
    prose = merge(prose)
    out, cur = [], 0
    for a, b in prose:
        if a > cur:
            out.append((cur, a))
        cur = max(cur, b)
    if cur < length:
        out.append((cur, length))
    return out


def merge(spans):
    spans = sorted(s for s in spans if s[0] < s[1])
    out = []
    for a, b in spans:
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def protected_spans(text, path):
    ext = os.path.splitext(path)[1].lower()
    if ext in CODE_EXT:
        spans = spans_code(text)
    elif ext in HTML_EXT:
        spans = spans_html(text)
    else:
        spans = spans_markdown(text)
    for rx in (URL_RE, EMAIL_RE, PATH_RE, ENTITY_RE, TIME_RE):
        for m in rx.finditer(text):
            spans.append((m.start(), m.end()))
    return merge(spans)


def blocked(spans, start, end):
    for a, b in spans:
        if start < b and end > a:
            return True
    return False


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------

def rule_dashes(text, cfg):
    for m in re.finditer(r"\s*[\u2014\u2013]\s*", text):
        raw = m.group(0)
        repl = " - " if raw.strip() != raw or " " in raw else "-"
        yield Finding(m.start(), m.end(), repl, "TFR001",
                      "tiret cadratin ou demi-cadratin: utiliser ' - ', une virgule ou deux-points")


def rule_apostrophe(text, cfg):
    want = cfg["apostrophe"]
    other = APOS_CURLY if want == APOS_ASCII else APOS_ASCII
    for m in re.finditer(r"(?<=\w)" + re.escape(other) + r"(?=\w)", text):
        yield Finding(m.start(), m.end(), want, "TFR002",
                      f"apostrophe {'typographique' if other == APOS_CURLY else 'ASCII'}: "
                      f"le profil demande {'ASCII' if want == APOS_ASCII else 'courbe'}")


def rule_accents(text, cfg):
    for bad, good in ACCENT_FIXES.items():
        for m in re.finditer(r"\b" + re.escape(bad) + r"\b", text):
            yield Finding(m.start(), m.end(), good, "TFR003",
                          f"accent manquant sur la capitale: {bad} -> {good}")


def rule_oe(text, cfg):
    for bad, good in OE_FIXES.items():
        for m in re.finditer(r"\b" + re.escape(bad) + r"\b", text, re.I):
            src = m.group(0)
            repl = good.capitalize() if src[0].isupper() else good
            yield Finding(m.start(), m.end(), repl, "TFR004",
                          f"ligature oe manquante: {src} -> {repl}")


def rule_spacing(text, cfg):
    mode = cfg["nbsp"]
    if mode == "none":
        for m in re.finditer(r"[" + NBSP + NNBSP + r"]", text):
            yield Finding(m.start(), m.end(), " ", "TFR005",
                          "espace insecable interdite par le profil data")
        return
    thin = NNBSP if mode == "thin" else NBSP
    # Before ; ! ? : a space is required, and it must be unbreakable.
    for m in re.finditer(r"(\S)([ ]?)([;!?])(?=\s|$)", text):
        before, space, punct = m.groups()
        if before in NBSP + NNBSP or before in "!?;":
            continue
        if punct == "!" and text[m.start(3) - 1: m.start(3)] == "<":
            continue
        yield Finding(m.start(2), m.end(3), thin + punct, "TFR005",
                      f"espace fine insecable manquante avant « {punct} »")
    for m in re.finditer(r"(\S)([ ]?):(?=\s|$)", text):
        before = m.group(1)
        if before.isdigit() or before in NBSP + NNBSP:
            continue
        yield Finding(m.start(2), m.end(0), NBSP + ":", "TFR005",
                      "espace insecable manquante avant « : »")


def rule_guillemets(text, cfg):
    if not cfg["guillemets"]:
        return
    for m in re.finditer(r'"([^"\n]{1,200})"', text):
        inner = m.group(1).strip()
        if not inner:
            continue
        thin = NNBSP if cfg["nbsp"] == "thin" else (NBSP if cfg["nbsp"] == "nbsp" else " ")
        yield Finding(m.start(), m.end(), f"«{thin}{inner}{thin}»", "TFR006",
                      "guillemets droits: le francais utilise « » avec une espace insecable")
    for m in re.finditer(r"[\u201c\u201d]", text):
        yield Finding(m.start(), m.end(), '"', "TFR006",
                      "guillemets anglais courbes: utiliser « »")


def rule_ellipsis(text, cfg):
    if cfg["ellipsis"]:
        for m in re.finditer(r"(?<!\.)\.{3}(?!\.)", text):
            yield Finding(m.start(), m.end(), ELLIPSIS, "TFR007",
                          "points de suspension: un seul caractere …")
    else:
        for m in re.finditer(ELLIPSIS, text):
            yield Finding(m.start(), m.end(), "...", "TFR007",
                          "profil data: … doit rester en ASCII")
    for m in re.finditer(r"\betc\s*(?:\.{2,}|" + ELLIPSIS + r")", text):
        yield Finding(m.start(), m.end(), "etc.", "TFR008",
                      "« etc. » ne prend jamais de points de suspension")


def rule_ordinals(text, cfg):
    for rx, repl in ORDINALS:
        for m in rx.finditer(text):
            new = m.expand(repl) if "\\" in repl else repl
            if new == m.group(0):
                continue
            yield Finding(m.start(), m.end(), new, "TFR009",
                          f"ordinal francais: {m.group(0)} -> {new}")


def rule_whitespace(text, cfg):
    for m in re.finditer(r"[ ]{2,}(?=\S)", text):
        if text[:m.start()].rstrip(" ").endswith("\n"):
            continue                                     # indentation
        yield Finding(m.start(), m.end(), " ", "TFR010", "espaces multiples")
    for m in re.finditer(r"\s+([,.])(?=\s|$)", text):
        if "\n" in m.group(0):
            continue
        yield Finding(m.start(), m.end(), m.group(1), "TFR010",
                      f"espace avant « {m.group(1)} »")


def rule_units(text, cfg):
    if cfg["nbsp"] == "none":
        return
    for m in re.finditer(r"(\d)([ ]?)(%|€|\$|km|kg|m2)(?![\w])", text):
        if m.group(2) in (NBSP, NNBSP):
            continue
        yield Finding(m.start(2), m.end(2), NBSP, "TFR011",
                      f"espace insecable manquante avant « {m.group(3)} »")


def rule_advisory_caps(text, cfg):
    """Check only: English-style Title Case in a French heading."""
    for m in re.finditer(r"^#{1,6} +(.+)$", text, re.M):
        title = m.group(1)
        words = [w for w in re.findall(r"[A-Za-zÀ-ÿ]{4,}", title)]
        if len(words) >= 3 and sum(1 for w in words if w[0].isupper()) >= len(words) - 0:
            yield Finding(m.start(1), m.end(1), None, "TFR012",
                          "titre en Title Case anglais: en francais seule la premiere lettre prend une majuscule",
                          fixable=False)


RULES = [rule_dashes, rule_apostrophe, rule_accents, rule_oe, rule_spacing,
         rule_guillemets, rule_ellipsis, rule_ordinals, rule_whitespace,
         rule_units, rule_advisory_caps]

RULE_DOC = [
    ("TFR001", "tiret cadratin ou demi-cadratin", True),
    ("TFR002", "apostrophe non conforme au profil", True),
    ("TFR003", "accent manquant sur une capitale", True),
    ("TFR004", "ligature oe manquante", True),
    ("TFR005", "espace insecable avant ; : ! ?", True),
    ("TFR006", "guillemets droits ou anglais", True),
    ("TFR007", "points de suspension", True),
    ("TFR008", "etc. suivi de points de suspension", True),
    ("TFR009", "ordinal (2eme au lieu de 2e)", True),
    ("TFR010", "espaces multiples ou avant une virgule", True),
    ("TFR011", "espace insecable avant %, EUR, unites", True),
    ("TFR012", "titre en Title Case anglais", False),
]


# --------------------------------------------------------------------------
# Engine
# --------------------------------------------------------------------------

def analyse(text, path, cfg, only=None, skip=None):
    spans = protected_spans(text, path)
    findings = []
    for rule in RULES:
        for f in rule(text, cfg):
            if only and f.rule not in only:
                continue
            if skip and f.rule in skip:
                continue
            if blocked(spans, f.start, f.end):
                continue
            findings.append(f)
    findings.sort(key=lambda f: (f.start, f.end))
    kept, last = [], -1
    for f in findings:
        if f.start >= last:
            kept.append(f)
            last = f.end
    return kept


def apply_fixes(text, findings):
    out = text
    for f in sorted([f for f in findings if f.fixable and f.repl is not None],
                    key=lambda f: f.start, reverse=True):
        out = out[:f.start] + f.repl + out[f.end:]
    return out


def line_col(text, pos):
    line = text.count("\n", 0, pos) + 1
    col = pos - (text.rfind("\n", 0, pos) + 1) + 1
    return line, col


def visible(s):
    """Make invisible characters readable in a report snippet."""
    return (s.replace(NNBSP, "[fine]").replace(NBSP, "[insec]")
             .replace("\n", "\\n").replace("\t", "\\t"))


def visible_ws(s):
    """Same, but keep line structure - for a diff, where newlines must stay."""
    return s.replace(NNBSP, "[fine]").replace(NBSP, "[insec]")


def process(path, args, cfg):
    try:
        with open(path, "r", encoding="utf-8", newline="") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError) as e:
        print(f"{path}: skipped ({e})", file=sys.stderr)
        return 0, 0

    findings = analyse(text, path, cfg, args.only, args.skip)
    if not findings:
        return 0, 0

    fixable = [f for f in findings if f.fixable]

    if args.cmd == "check":
        for f in findings:
            ln, col = line_col(text, f.start)
            snippet = visible(text[f.start:f.end])[:60]
            flag = "" if f.fixable else "  (check only)"
            print(f"{path}:{ln}:{col}  {f.rule}  {f.message}{flag}")
            if snippet.strip():
                print(f"    {snippet}")
        return len(findings), 0

    new = apply_fixes(text, findings)
    if new == text:
        return len(findings), 0

    if args.cmd == "diff":
        for line in difflib.unified_diff(text.splitlines(True), new.splitlines(True),
                                         f"a/{path}", f"b/{path}"):
            sys.stdout.write(visible_ws(line) if line.startswith(("+", "-")) else line)
        return len(findings), 0

    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(new)
    print(f"{path}: {len(fixable)} correction(s)")
    return len(findings), len(fixable)


def collect(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in
                           {".git", "node_modules", "dist", "build", ".next", "vendor", "__pycache__"}]
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in TEXT_EXT | CODE_EXT | HTML_EXT:
                        out.append(os.path.join(root, f))
        else:
            out.append(p)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cmd", choices=["check", "fix", "diff", "rules"])
    p.add_argument("paths", nargs="*", help="files or directories")
    p.add_argument("--profile", choices=sorted(PROFILES), default="web")
    p.add_argument("--only", action="append", help="run only these rules (repeatable)")
    p.add_argument("--skip", action="append", help="skip these rules (repeatable)")
    args = p.parse_args()

    if args.cmd == "rules":
        print("rule    fixable  description")
        for rid, desc, fixable in RULE_DOC:
            print(f"{rid}  {'yes    ' if fixable else 'no     '}  {desc}")
        print("\nprofiles: " + ", ".join(f"{k} ({v['apostrophe']!r} apostrophe)" for k, v in PROFILES.items()))
        return 0

    if not args.paths:
        p.error("give at least one file or directory")

    cfg = PROFILES[args.profile]
    total = fixed = 0
    for path in collect(args.paths):
        f, x = process(path, args, cfg)
        total += f
        fixed += x

    if args.cmd == "fix":
        print(f"\n{fixed} correction(s) applied, {total - fixed} left to review by hand.")
        return 0
    if total:
        print(f"\n{total} finding(s). Nothing was written - run `fix` to apply, `diff` to preview.")
        return 1
    print("clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
