#!/usr/bin/env python3
"""
Region ownership gate | MDRIIA Group 05 | Owner: E043 Muaaz (integrator)

The course format puts all four members' code in ONE file
(src/aerial_patrol_swarm.py), separated by TODO regions. Shared files are where
parallel work collides and where viva attribution gets blurred, so every PR is
checked before Muaaz merges it to main:

  python src/check_region_ownership.py --author E051            # diff vs main
  python src/check_region_ownership.py --author E075 --base origin/main

Exit 0 = every changed line belongs to the author. Exit 1 = violations listed.
Lines outside any marked region, and the region markers themselves, belong to
E043 (shared integration plumbing).

Run it from the group folder (or the repository root). git reports paths from the
repository root, so the group-folder prefix is stripped before the patterns below
are matched; files outside the group folder belong to E043.
"""
import argparse
import fnmatch
import glob
import os
import re
import subprocess
import sys

REGION_FILE = "src/aerial_patrol_swarm.py"
OPEN = re.compile(r"#\s*>>>\s*(E0\d\d)\b")
CLOSE = re.compile(r"#\s*<<<\s*(E0\d\d)\b")

# whole-file ownership; first match wins. "FROZEN" = course-provided, nobody edits.
FILE_OWNERS = [
    ("RESEARCH_AND_IMPLEMENTATION_GUIDE.md", "FROZEN"),
    ("models/*", "E043"),
    ("src/test_env.py", "E043"),
    ("src/check_region_ownership.py", "E043"),
    ("analytics/campus_security_economics.py", "E077"),
    ("analytics/campus_security_*", "E077"),
    ("analytics/guard_patrol_baseline*", "E077"),
    ("analytics/vision_*", "E051"),
    ("analytics/coverage_*", "E075"),
    ("analytics/statistical_validation*", "E075"),
    ("analytics/geofence_*", "E075"),
    ("analytics/*", "E043"),
    ("tests/test_e043_*", "E043"), ("tests/test_e051_*", "E051"),
    ("tests/test_e075_*", "E075"), ("tests/test_e077_*", "E077"),
    ("docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md", "ALL"),
    ("docs/LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md", "ALL"),
    ("docs/*", "E043"),
    ("README.md", "E043"),
]


def sh(*args):
    return subprocess.run(args, capture_output=True, text=True, check=False).stdout


def region_map(text):
    """line number (1-based) -> owner, for the region file."""
    owner, out, stack = "E043", {}, []
    for i, line in enumerate(text.splitlines(), 1):
        if OPEN.search(line):
            stack.append(OPEN.search(line).group(1)); out[i] = "E043"; continue
        if CLOSE.search(line):
            if stack:
                stack.pop()
            out[i] = "E043"; continue
        out[i] = stack[-1] if stack else owner
    return out


def group_prefix():
    """Repository-relative path of the group folder, e.g. 'Group_05_.../'."""
    if not os.path.exists(REGION_FILE):
        hits = glob.glob(os.path.join("Group_*", REGION_FILE))
        if len(hits) != 1:
            sys.exit("run from the group folder or the repository root")
        os.chdir(os.path.dirname(os.path.dirname(hits[0])))
    return sh("git", "rev-parse", "--show-prefix").strip()


def file_owner(path):
    if path is None:                      # outside the group folder
        return "E043"
    for pat, who in FILE_OWNERS:
        if fnmatch.fnmatch(path, pat):
            return who
    return "E043"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--author", required=True, help="roll number, e.g. E051")
    ap.add_argument("--base", default="main")
    a = ap.parse_args()
    author = a.author.upper()

    prefix = group_prefix()
    merge_base = sh("git", "merge-base", a.base, "HEAD").strip() or a.base
    changed = [l.split("\t") for l in sh("git", "diff", "--name-status", merge_base, "HEAD").splitlines() if l]
    violations = []

    for parts in changed:
        status, repo_path = parts[0], parts[-1]
        path = repo_path[len(prefix):] if repo_path.startswith(prefix) else None
        if status.startswith("R") and file_owner(parts[1][len(prefix):] if parts[1].startswith(prefix) else None) not in ("ALL", author):
            violations.append(f"{parts[1]}: renamed away, owned by someone else")
        if path == REGION_FILE:
            old = region_map(sh("git", "show", f"{merge_base}:{repo_path}"))
            new = region_map(sh("git", "show", f"HEAD:{repo_path}"))
            diff = sh("git", "diff", "-U0", merge_base, "HEAD", "--", f":(top){repo_path}")
            for m in re.finditer(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", diff, re.M):
                o0, on = int(m.group(1)), int(m.group(2) or 1)
                n0, nn = int(m.group(3)), int(m.group(4) or 1)
                for ln in range(o0, o0 + on):
                    if old.get(ln, "E043") != author:
                        violations.append(f"{path}:{ln} (removed/changed) belongs to {old.get(ln, 'E043')}")
                for ln in range(n0, n0 + nn):
                    if new.get(ln, "E043") != author:
                        violations.append(f"{path}:{ln} (added/changed) belongs to {new.get(ln, 'E043')}")
        else:
            who = file_owner(path)
            if who == "FROZEN":
                violations.append(f"{repo_path}: course-provided file, must not be modified")
            elif who not in ("ALL", author):
                violations.append(f"{repo_path}: owned by {who}")

    if violations:
        print(f"[BLOCKED] {len(violations)} change(s) outside {author}'s ownership:")
        for v in violations[:60]:
            print("   ", v)
        if len(violations) > 60:
            print(f"    ... and {len(violations) - 60} more")
        print("Move these edits to the owner's branch, or ask the owner to make them.")
        sys.exit(1)
    print(f"[OK] all {len(changed)} changed file(s) are within {author}'s ownership.")


if __name__ == "__main__":
    main()
