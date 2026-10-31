#!/usr/bin/env python
"""Verify every file:line reference in the viva prep and AI audit documents (gap G-23).

Run from anywhere; the group folder is found from this file's location:
    python docs/submission/viva_refs_check.py [--files FILE ...] [--strict] [--quiet]

Default files: docs/submission/viva_prep_E0*.md and docs/submission/ai_audit_candidates.md.

What it checks, per markdown line:
  1. REFERENCE FORMS recognised:   `path/to/file.py:123`   `path:120-135`   `path:12, 40-44`
     and a short continuation `:540-553` (in backticks) that reuses the last path named earlier on the same line.
  2. RESOLVES: the file exists (relative to the group folder, or to the repository root when it starts with the
     group folder name) and every cited line number is inside the file.
  3. SYMBOL: the identifiers cited in backticks next to the reference (between the previous and the next reference on
     the same line, e.g.  `select_tracking_uav` at `src/aerial_patrol_swarm.py:957-967`) must occur on the cited
     line(s). A reference with identifiers none of which occurs in its range FAILS. A reference with no identifier
     next to it only passes the resolve check and is listed as a note (--strict makes that a failure).
  4. STALE MARKERS fail: W51, W75, W77 (worktree lines that no longer exist), SP/ (scratchpad paths), _handoff.
Exit status 0 = all references verified, 1 = at least one failure, 2 = a file to check is missing.
Nothing is written; it only reads.
"""
import argparse
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GROUP = os.path.normpath(os.path.join(HERE, "..", ".."))
REPO = os.path.dirname(GROUP)
EXT = r"(?:py|xml|md|sh|json|txt|csv|yaml|yml|toml|mjs|js|html)"
PATH_REF = re.compile(r"(?P<path>[A-Za-z0-9_./\-]*[A-Za-z0-9_\-]\." + EXT + r"):(?P<spec>\d+(?:-\d+)?(?:\s*,\s*\d+(?:-\d+)?)*)")
SHORT_REF = re.compile(r"`:(?P<spec>\d+(?:-\d+)?(?:\s*,\s*\d+(?:-\d+)?)*)`")
TICKS = re.compile(r"`([^`]+)`")
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*(?:\(\))?$")
STALE = re.compile(r"\b(W51|W75|W77)\b|(?<![A-Za-z0-9_])SP/|_handoff")
_cache = {}


def read_lines(rel):
    for base in (GROUP, REPO):
        p = os.path.join(base, rel)
        if os.path.isfile(p):
            if p not in _cache:
                with open(p, encoding="utf-8", errors="replace") as f:
                    _cache[p] = f.read().splitlines()
            return _cache[p]
    return None


def parse_spec(spec):
    """'12, 40-44' -> [(12, 12), (40, 44)]"""
    out = []
    for part in re.split(r"\s*,\s*", spec.strip()):
        a, _, b = part.partition("-")
        out.append((int(a), int(b or a)))
    return out


def idents_between(text, start, end):
    syms = []
    for m in TICKS.finditer(text, start, end):
        tok = m.group(1).strip()
        if ":" in tok or "/" in tok or re.search(r"\." + EXT + r"$", tok):
            continue
        if IDENT.match(tok):
            tok = tok[:-2] if tok.endswith("()") else tok
            tail = tok.split(".")[-1]
            if len(tail) >= 3 and tail not in ("src", "True", "False", "None"):
                syms.append(tail)
    return syms


def check_file(path, strict):
    fails, notes, ok = [], [], 0
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    for ln, text in enumerate(lines, 1):
        where = f"{os.path.relpath(path, GROUP)}:{ln}"
        if STALE.search(text):
            fails.append(f"{where}: stale marker {STALE.search(text).group(0)!r}")
        refs = []   # (start, end, path, spec)
        last_path = None
        events = sorted([(m.start(), m.end(), "p", m) for m in PATH_REF.finditer(text)]
                        + [(m.start(), m.end(), "s", m) for m in SHORT_REF.finditer(text)])
        for s, e, kind, m in events:
            if kind == "p":
                last_path = m.group("path")
                refs.append((s, e, last_path, m.group("spec")))
            elif last_path:
                refs.append((s, e, last_path, m.group("spec")))
            else:
                fails.append(f"{where}: short reference `:{m.group('spec')}` with no file named earlier on the line")
        for i, (s, e, rel, spec) in enumerate(refs):
            src = read_lines(rel)
            label = f"{rel}:{spec}"
            if src is None:
                fails.append(f"{where}: {label} -> file not found")
                continue
            ranges = parse_spec(spec)
            bad = [r for r in ranges if r[0] < 1 or r[1] < r[0] or r[1] > len(src)]
            if bad:
                fails.append(f"{where}: {label} -> beyond the end of the file ({len(src)} lines)")
                continue
            seg_start = refs[i - 1][1] if i else 0
            seg_end = refs[i + 1][0] if i + 1 < len(refs) else len(text)
            syms = idents_between(text, seg_start, s) + idents_between(text, e, seg_end)
            if not syms:
                notes.append(f"{where}: {label} resolves; no symbol cited next to it")
                if strict:
                    fails.append(f"{where}: {label} cites no symbol (--strict)")
                else:
                    ok += 1
                continue
            body = "\n".join("\n".join(src[a - 1:b]) for a, b in ranges)
            hit = [x for x in syms if x in body]
            if hit:
                ok += 1
            else:
                fails.append(f"{where}: {label} -> none of {sorted(set(syms))} occurs on the cited line(s); "
                             f"line {ranges[0][0]} reads: {src[ranges[0][0] - 1].strip()[:90]!r}")
    return fails, notes, ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--files", nargs="*")
    ap.add_argument("--strict", action="store_true", help="a reference with no symbol next to it also fails")
    ap.add_argument("--quiet", action="store_true", help="do not list the no-symbol notes")
    a = ap.parse_args(argv)
    files = a.files or sorted(glob.glob(os.path.join(HERE, "viva_prep_E0*.md"))) + [os.path.join(HERE, "ai_audit_candidates.md")]
    total_f = total_ok = 0
    for f in files:
        if not os.path.isfile(f):
            print(f"[MISSING] {f}")
            return 2
        fails, notes, ok = check_file(f, a.strict)
        total_f += len(fails)
        total_ok += ok
        print(f"{os.path.relpath(f, GROUP)}: {ok} reference(s) verified, {len(fails)} failure(s), {len(notes)} without a symbol")
        for x in fails:
            print("  FAIL " + x)
        if not a.quiet:
            for x in notes:
                print("  note " + x)
    print(f"TOTAL: {total_ok} verified, {total_f} failed")
    return 1 if total_f else 0


if __name__ == "__main__":
    sys.exit(main())
