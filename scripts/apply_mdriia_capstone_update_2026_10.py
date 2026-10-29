# -*- coding: utf-8 -*-
"""
MDRIIA 2026 monorepo: capstone deployment, Dr. Sunny Nanade, 16-Oct-2026.

  a) Data-integrity sanitisation in all 12 group folders
     - git mv the 12 known synthetic starter CSVs in Group_XX_*/analytics/ (*_benchmark.csv, and any
       sample_experiment_data.csv) -> SIMULATED_<name>, and update every reference to them
     - add an ACADEMIC INTEGRITY NOTICE header to all 12 analytics/generate_paper_figures.py
     - add docs/figures/README.md marking the starter figures as synthetic
  b) Real data separated from simulated data
     - controllers/loggers that named the benchmark file as their own output now write *_real_trials.csv
       (Groups 01, 11, 12); Group 02's scripted scaffold writes SIMULATED_* until the students switch
       its SCRIPTED_SCAFFOLD flag off, after which it writes fall_triage_real_trials.csv
     - README lines describing where empirical data goes now point to *_real_trials.csv
  c) GRADING_RUBRIC_AND_EVALUATION_POLICY.md -> 20-mark capstone scheme (10 / 5 / 5)
  d) copy each MDRIIA_Group_XX_Technical_Dossier.docx into Group_XX_*/docs/ with a docs/README.md,
     and MDRIIA_LinkedIn_and_GitHub_Showcase_Guide.pdf to the repo root
  e) root README.md: CAPSTONE SUBMISSION DIRECTIVE banner; README + COHORT_DASHBOARD.html relabel the
     benchmark column/section to "Starter Reference Benchmarks (Simulated Targets)"
  f) optional: --commit (exact message below) and --push (origin main)

Safe to run more than once (idempotent). Without --commit it only stages (git add).

Usage:
    python scripts/apply_mdriia_capstone_update_2026_10.py ["<Student_Submission_Packs folder>"] [--commit] [--push]
Default packs folder: D:\\MPSTME\\AY 26-27 Odd Sem ICA\\MDRIIA\\Student_Submission_Packs
Review first:  git status   /   git diff --cached --stat
"""
import glob, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
PACKS = ARGS[0] if ARGS else r"D:\MPSTME\AY 26-27 Odd Sem ICA\MDRIIA\Student_Submission_Packs"
DO_COMMIT = "--commit" in sys.argv or "--push" in sys.argv
DO_PUSH = "--push" in sys.argv
COMMIT_MSG = "chore(capstone): deploy standardized MDRIIA CSBS dossiers, align 20-mark policy, and enforce data provenance"
GUIDE_PDF = "MDRIIA_LinkedIn_and_GitHub_Showcase_Guide.pdf"
N_GROUPS = 12
TEXT_EXT = {".py", ".md", ".json", ".html", ".txt", ".yml", ".yaml", ".xml"}
MARK = "ACADEMIC INTEGRITY NOTICE"
BANNER_MARK = "CAPSTONE SUBMISSION DIRECTIVE"
NEW_LABEL = "Starter Reference Benchmarks (Simulated Targets)"

# Synthetic starter CSVs as committed in 12fa984. Only these names are ever renamed, so re-running the
# script never touches a real-trials file that students add later.
KNOWN_SIMULATED = {
    "icu_medicine_delivery_benchmark.csv", "fall_triage_benchmark.csv", "aed_delivery_benchmark.csv",
    "space_debris_capture_benchmark.csv", "campus_patrol_benchmark.csv", "solar_cleaning_benchmark.csv",
    "clutter_manipulation_benchmark.csv", "flood_relief_benchmark.csv", "ugv_traversability_benchmark.csv",
    "surgical_precision_benchmark.csv", "solar_inspection_benchmark.csv", "pipeline_inspection_benchmark.csv",
    "sample_experiment_data.csv"}

def real_name(n):
    return n.replace("_benchmark.csv", "_real_trials.csv").replace("sample_experiment_data.csv", "experiment_real_trials.csv")

# Exact code edits for the controllers/loggers (old text -> new text). Skipped when already applied.
LOGGER_EDITS = {
    "Group_01_*/src/icu_amr_controller.py": [
        ("import math\nimport csv\n", "import math\nimport csv\nimport os\n"),
        ('def run_simulation(duration_sec=15.0, output_csv="icu_amr_telemetry.csv"):',
         'REAL_TRIALS_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "analytics", "icu_amr_real_trials.csv")\n\n'
         'def run_simulation(duration_sec=15.0, output_csv=REAL_TRIALS_CSV):  # real controller telemetry, never SIMULATED_*')],
    "Group_02_*/src/fall_detection_kinematics.py": [
        ("import math\nimport csv\nimport os\n",
         "import math\nimport csv\nimport os\n\n"
         "# The kinematic values below are SCRIPTED scaffold values (fixed outcomes), not measurements, so their\n"
         "# output is labelled SIMULATED. When you replace them with measured MediaPipe / MuJoCo data, set this\n"
         "# flag to False and the same code writes analytics/fall_triage_real_trials.csv instead.\n"
         "SCRIPTED_SCAFFOLD = True\n"),
        ('out_csv = os.path.join(out_dir, "fall_triage_benchmark.csv")',
         'out_csv = os.path.join(out_dir, "SIMULATED_fall_triage_benchmark.csv" if SCRIPTED_SCAFFOLD else "fall_triage_real_trials.csv")')],
    "Group_11_*/src/solar_defect_detector.py": [
        ("Telemetry logged to analytics/solar_inspection_benchmark.csv.", "Telemetry logged to analytics/solar_inspection_real_trials.csv.")],
    "Group_12_*/src/drone_pipeline_controller.py": [
        ("Telemetry logged to analytics/pipeline_inspection_benchmark.csv.", "Telemetry logged to analytics/pipeline_inspection_real_trials.csv.")],
}
# In Markdown, lines that describe where EMPIRICAL data goes must point to the real-trials file.
REAL_LINE = re.compile(r"Empirical Validation|collect (and expand )?empirical data|Real simulation telemetry", re.I)
DOC_PHRASES = [("<- Empirical benchmark trial dataset", "<- SIMULATED starter targets (np.random), NOT results"),
               ("Real simulation telemetry dataset generated from at least 80 experimental runs.",
                "Your real simulation telemetry (N >= 30 runs per condition) written by your controller. The starter file SIMULATED_solar_cleaning_benchmark.csv holds generated targets, not results.")]

NOTICE = '''# =====================================================================================
# ACADEMIC INTEGRITY NOTICE (MDRIIA capstone, Oct 2026)
# This script GENERATES SYNTHETIC numbers with np.random, aimed at target means. Its CSV output
# (SIMULATED_*.csv) and its figures in docs/figures/ are illustrative STARTER TARGETS, not results.
# Per Section 4 of your MDRIIA Technical Dossier, report ONLY telemetry from MuJoCo runs of your own
# controller (N >= 30 per condition, 500 Hz), saved as analytics/*_real_trials.csv, and re-plot from it.
# Presenting these generated numbers as experimental results violates NMIMS academic integrity policy.
# =====================================================================================
'''

FIG_README = """# Starter figures: NOT experimental results

> **Reference starter figures built on synthetic data (np.random). Re-plot them from your own `analytics/*_real_trials.csv` before using them anywhere.**

The `figure*.png` files here were produced by `analytics/generate_paper_figures.py` from generated target numbers
(see `analytics/SIMULATED_*.csv`). They only show the expected layout of your plots.

1. Run your Monte Carlo trials in MuJoCo (N ≥ 30 per condition) and log them to `analytics/*_real_trials.csv`.
2. Re-plot every figure from **your** CSV and replace or delete these files.

Starter figures in this folder: {files}
"""

DOCS_NOTE = "Before submitting, complete all 6 sections and the sign-off of `{dossier}` in Microsoft Word, export to PDF, and commit BOTH the completed .docx and .pdf to this folder."

DOCS_README = """# docs/: {group}

{note}

| File | What it is |
|---|---|
| `{dossier}` | Your pre-filled Technical Dossier. Fill it in **Microsoft Word** using the "Select ▾" drop-downs and "type here" fields. |
| `{pdf}` | The PDF export of your completed dossier (you add this). The same PDF is turned in on MS Teams by **every** member. |
| `figures/` | Starter figures built on **synthetic** data. Re-plot them from your `analytics/*_real_trials.csv`. |
| `TEAM_ROSTER.json`, `LITERATURE_REVIEW_*.md`, `RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md` | Scaffold documents. Verify every claim and citation before you reuse it. |

**Due: Monday, 26-Oct-2026, 23:59 IST · Studio Showcase, Expo & Viva Voce: Saturday, 31-Oct-2026 · No PPT slides**
Guide: [`/{guide}`](../../{guide})
"""

BANNER = f"""> [!CAUTION]
> ## 🚨 {BANNER_MARK} (Capstone ICA, 20 marks)
> **Due: Monday, 26-Oct-2026, 23:59 IST · Studio Showcase, Expo & Viva Voce: Saturday, 31-Oct-2026**
>
> 1. **Dossier:** complete `Group_XX_*/docs/MDRIIA_Group_XX_Technical_Dossier.docx` in **Microsoft Word** (drop-downs and "type here" fields), export to PDF, and commit **both** the `.docx` and the `.pdf` to your `docs/` folder.
> 2. **MS Teams:** **every member** attaches the group's PDF and clicks **Turn in**. Marks are recorded per student.
> 3. **No PPT slides.** Present the live MuJoCo simulation, your CSBS business sensitivity graphs and a webcam picture-in-picture of every member (Expo and 3–4 min LinkedIn video).
> 4. **Data provenance:** `SIMULATED_*` files and every `generate_paper_figures.py` contain **generated target numbers**, not results. Report only telemetry from MuJoCo runs of your own controller, saved as `analytics/*_real_trials.csv`.
> 5. **Marks:** Component 1 CDIO Robotics Engineering & MuJoCo Physics **10** · Component 2 CSBS Techno-Economic Business Systems Analysis **5** · Component 3 Studio Showcase & Viva Voce **5**. See [`GRADING_RUBRIC_AND_EVALUATION_POLICY.md`](./GRADING_RUBRIC_AND_EVALUATION_POLICY.md) and [`{GUIDE_PDF}`](./{GUIDE_PDF}).
"""

RUBRIC = r"""# MDRIIA (702CO0E012) Capstone: Grading Rubric & Evaluation Policy
**Modern Day Robotics & Its Industrial Applications · B.Tech CSBS (TCS partnership)**
**SVKM's NMIMS · MPSTME Mumbai · AY 2026–27 Odd Semester · Dr. Sunny Nanade**

> This document replaces the earlier 100-mark, 4-milestone scheme. The capstone is an **ICA component worth 20 marks**.

| Item | Detail |
|---|---|
| **Total Capstone Marks** | **20 Marks** |
| **Submission Due Date** | **Monday, 26-Oct-2026, 23:59 IST** |
| **Studio Showcase, Expo & Viva Voce** | **Saturday, 31-Oct-2026** |
| What you submit | (1) Your group's Technical Dossier as PDF on MS Teams, turned in by **every** member · (2) the filled `.docx` **and** `.pdf` committed to `Group_XX_*/docs/` · (3) your model, controller, business script and `*_real_trials.csv` in your group folder · (4) your LinkedIn video URL in dossier Section 5 |
| Presentation format | **No PPT slides.** Live MuJoCo simulation + CSBS business sensitivity graphs + webcam picture-in-picture of every member |

---

## Component 1: CDIO Robotics Engineering & MuJoCo Physics (10 Marks)
Dossier Sections 1, 2 and 4, checked against your group folder.
| Criterion | Evidence | Marks |
|---|---|---|
| Problem framing | Authorised Aalborg title, verified baseline friction, governing standards decided with clauses, claim verification table (Section 1) | 2 |
| MuJoCo rigid-body model | `models/*.xml` loads; contact friction / `solref` / timestep justified; the mechanism matches the title (Section 2) | 2 |
| Closed-loop control | `src/*.py` controller with an implemented FSM and a stated control law (PID / impedance / DLS-IK), honest script-authorship table (Section 2) | 2 |
| Telemetry & Monte Carlo | 500 Hz logging, N ≥ 30 randomised runs per condition with recorded seeds, tracking RMSE and control effort ∫τ² dt (Section 4) | 2 |
| Statistical validation | Baseline vs proposed, t-test, Cohen's d, 95 % CI, plots that re-generate from `analytics/*_real_trials.csv` (Section 4) | 2 |

## Component 2: CSBS Techno-Economic Business Systems Analysis (5 Marks)
Dossier Section 3 and `analytics/*_roi.py` (or the group's renamed business script).
| Criterion | Evidence | Marks |
|---|---|---|
| Labour reallocation and payback | H_reclaimed and the dimensionless payback horizon P_payback computed by the script from sourced inputs | 1.5 |
| Cost reduction | Normalised Cost Reduction Index NCRI (= 1 − κ), dimensionless, no currency amounts | 1 |
| Queuing model | M/M/1 or M/M/c delay model with stated λ, μ, c and utilisation ρ | 1 |
| Risk | FMEA with at least four failure modes, RPN before and after mitigation, mitigation shown in simulation or code | 1 |
| Sensitivity | Sensitivity graph on the most uncertain input with the break-even value | 0.5 |

## Component 3: Studio Showcase & Viva Voce (5 Marks)
| Criterion | Evidence | Marks |
|---|---|---|
| LinkedIn video (3–4 min) | Live MuJoCo simulation, business graph, every member on webcam picture-in-picture (Section 5) | 1 |
| AI audit and peer review | Three verified AI-error cases; peer review of the two assigned groups (Sections 5.1–5.2) | 1 |
| Live Expo demonstration | Simulation running from a fresh clone, FSM states and one handled failure shown | 1 |
| Individual viva voce | Each member defends their own role, code and the whole project, including the business model | 2 |

---

## Mandatory Individual Turn-in Rule
The work is collaborative, but marks are entered **per student** in the NMIMS Examination Portal.
**Every member must open the MS Teams assignment, attach the group's final PDF dossier, and click "Turn in" individually.**
A student who does not turn in cannot be awarded capstone marks, even if teammates have submitted.

## Integrity Safeguards
1. **Data provenance:** files named `SIMULATED_*`, every `generate_paper_figures.py` and the starter figures in `docs/figures/` contain **generated target numbers** (np.random). Reporting them as experimental results is data fabrication and scores **zero** for the component in which they appear. Results come only from MuJoCo runs of the group's own controller, saved as `analytics/*_real_trials.csv`.
2. **Hard-coded results:** constants typed into a business script as outputs (e.g. a payback period) are not analysis. Every economic number must be computed from sourced inputs or labelled as an assumption and varied in the sensitivity graph.
3. **Evidence authenticity:** every factual claim and citation must be verified at its primary source (dossier Section 1.1). Fabricated citations or DOIs score zero for the component in which they appear.
4. **AI use:** permitted, but must be logged in dossier Section 5.1. Undisclosed AI-generated content is treated as an integrity breach.
5. **Attribution:** individual contributions must match the git history and the dossier (Sections 2.2 and 6), and are defended in the viva.
6. **Zero Currency Rule:** cost comparisons are expressed as dimensionless ratios (κ, NCRI, P_payback), not raw monetary amounts.
7. **Research use:** dossier Section 6 is not marked. Data is used in anonymised education research only for students who gave the optional research consent in the sign-off; the answer has no effect on marks.
"""

def git(*args, check=True):
    return subprocess.run(["git", "-C", ROOT] + list(args), capture_output=True, text=True, check=check)

def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()

def write(path, text, like=None):
    """Write text, keeping the line-ending style of `like` (or of the existing file)."""
    ref = like if like is not None else (read(path) if os.path.exists(path) else "")
    crlf = "\r\n" in ref or (not ref and os.name == "nt")
    text = text.replace("\r\n", "\n")
    if crlf:
        text = text.replace("\n", "\r\n")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)

def edit(path, fn):
    """Apply fn to the file's LF-normalised text; write back (original line endings) only if changed."""
    raw = read(path); txt = raw.replace("\r\n", "\n")
    new = fn(txt)
    if new != txt:
        write(path, new, like=raw); touched.add(path)
        return True
    return False

touched, renamed, headers, compiled_bad, logger_changes = set(), [], [], [], []

def sub_names(line, names, to_real):
    for n in names:
        line = re.sub(r"(?<![\w])" + re.escape(n), real_name(n) if to_real else "SIMULATED_" + n, line)
    return line

def main():
    if not os.path.isdir(PACKS):
        sys.exit(f"Submission packs folder not found: {PACKS}")
    groups = sorted(d for d in glob.glob(os.path.join(ROOT, "Group_[0-9][0-9]_*")) if os.path.isdir(d))
    if len(groups) != N_GROUPS:
        sys.exit(f"Expected {N_GROUPS} group folders, found {len(groups)}")
    names = sorted(KNOWN_SIMULATED)

    # b) logger / controller edits first, so their output names never become SIMULATED_
    for pattern, edits in LOGGER_EDITS.items():
        for path in glob.glob(os.path.join(ROOT, pattern)):
            def apply(txt, edits=edits):
                for old, new in edits:
                    if new not in txt and old in txt:   # skip when already applied
                        txt = txt.replace(old, new, 1)
                return txt
            if edit(path, apply):
                logger_changes.append(os.path.relpath(path, ROOT))

    for gdir in groups:
        gname = os.path.basename(gdir); gnum = gname[6:8]
        ana = os.path.join(gdir, "analytics")

        # a) rename synthetic CSVs
        for n in names:
            p = os.path.join(ana, n)
            if os.path.exists(p):
                new = os.path.join(ana, "SIMULATED_" + n)
                git("mv", os.path.relpath(p, ROOT), os.path.relpath(new, ROOT))
                renamed.append((os.path.relpath(p, ROOT), os.path.basename(new)))

        # a) + b) references in every text file of the group folder
        for root, _, files in os.walk(gdir):
            for fn in files:
                fp = os.path.join(root, fn)
                ext = os.path.splitext(fn)[1].lower()
                if ext not in TEXT_EXT or fn.startswith("SIMULATED_"):
                    continue
                in_src = os.path.basename(os.path.dirname(fp)) == "src"
                def fix(txt, ext=ext, in_src=in_src):
                    for a, b in DOC_PHRASES:
                        txt = txt.replace(a, b)
                    out = []
                    for line in txt.split("\n"):
                        to_real = in_src or (ext == ".md" and bool(REAL_LINE.search(line)))
                        out.append(sub_names(line, names, to_real))
                    return "\n".join(out)
                edit(fp, fix)

        # a) integrity header on the figure generator
        for py in glob.glob(os.path.join(ana, "*.py")):
            src = read(py)
            synthetic = os.path.basename(py) == "generate_paper_figures.py" or ("np.random" in src and "benchmark" in src)
            if not synthetic or MARK in src:
                continue
            lines = src.splitlines(keepends=True); i = 0
            while i < len(lines) and i < 2 and (lines[i].startswith("#!") or re.match(r"#.*coding[:=]", lines[i])):
                i += 1
            write(py, "".join(lines[:i]) + NOTICE + "".join(lines[i:]), like=src); touched.add(py)
            headers.append(os.path.relpath(py, ROOT))
        for py in glob.glob(os.path.join(gdir, "**", "*.py"), recursive=True):
            try:
                compile(read(py), py, "exec")          # syntax check without writing __pycache__
            except SyntaxError as e:
                compiled_bad.append(f"{py}: {e}")

        figdir = os.path.join(gdir, "docs", "figures")
        if os.path.isdir(figdir):
            figs = sorted(f for f in os.listdir(figdir) if f.lower().endswith(".png"))
            fr = os.path.join(figdir, "README.md")
            write(fr, FIG_README.format(files=", ".join(f"`{f}`" for f in figs) or "(none)"), like=read(fr) if os.path.exists(fr) else "")
            touched.add(fr)

        # d) dossier + docs README
        dossier = f"MDRIIA_Group_{gnum}_Technical_Dossier.docx"
        src_doc = os.path.join(PACKS, dossier)
        if not os.path.exists(src_doc):
            sys.exit(f"Missing dossier in packs folder: {src_doc}")
        os.makedirs(os.path.join(gdir, "docs"), exist_ok=True)
        dst_doc = os.path.join(gdir, "docs", dossier)
        shutil.copy2(src_doc, dst_doc); touched.add(dst_doc)
        dr = os.path.join(gdir, "docs", "README.md")
        note = DOCS_NOTE.format(dossier=dossier)
        if os.path.exists(dr):
            cur = read(dr)
            if note not in cur.replace("\r\n", "\n"):
                write(dr, cur.rstrip() + "\n\n" + note + "\n", like=cur)
        else:
            write(dr, DOCS_README.format(group=gname, note=note, dossier=dossier, pdf=dossier.replace(".docx", ".pdf"), guide=GUIDE_PDF), like="")
        touched.add(dr)

    # c) grading policy
    gp = os.path.join(ROOT, "GRADING_RUBRIC_AND_EVALUATION_POLICY.md")
    write(gp, RUBRIC, like=read(gp) if os.path.exists(gp) else ""); touched.add(gp)

    # e) root README banner + relabel; dashboard relabel
    rd = os.path.join(ROOT, "README.md")
    def readme(txt):
        if BANNER_MARK not in txt:
            m = re.search(r"\n---\n", txt)               # after the title block, before the first rule
            pos = m.start() if m else 0
            txt = txt[:pos] + "\n\n" + BANNER + txt[pos:]
        txt = txt.replace("| Key Validated Benchmarks |", f"| {NEW_LABEL} |")
        txt = txt.replace("| **Quality Audit** | 100% Zero Defects Verified across all repository files |",
                          "| **Data Provenance** | Starter benchmark values are simulated targets (`SIMULATED_*`); results come only from each group's `analytics/*_real_trials.csv` |")
        return sub_names(txt, names, False)
    edit(rd, readme)
    dash = os.path.join(ROOT, "COHORT_DASHBOARD.html")
    if os.path.exists(dash):
        def dashboard(txt):
            txt = re.sub(r"Validated Telemetry (?:Benchmarks|&amp; CSBS ROI|& CSBS ROI)", NEW_LABEL, txt)
            return sub_names(txt, names, False)
        edit(dash, dashboard)

    # d) guide PDF at root
    gsrc = os.path.join(PACKS, GUIDE_PDF)
    if not os.path.exists(gsrc):
        sys.exit(f"Missing guide PDF: {gsrc}")
    shutil.copy2(gsrc, os.path.join(ROOT, GUIDE_PDF)); touched.add(os.path.join(ROOT, GUIDE_PDF))

    # This script itself is part of the change set
    touched.add(os.path.abspath(__file__))
    git("add", "-A", "--", *[os.path.relpath(p, ROOT) for p in sorted(touched)])

    print(f"Renamed {len(renamed)} simulated CSV files (git mv):")
    for o, n in renamed:
        print(f"   {o}  ->  {n}")
    print(f"Integrity header added to {len(headers)} generate_paper_figures.py scripts.")
    print(f"Controllers/loggers pointed at *_real_trials.csv (or SIMULATED_ scaffold output): {len(logger_changes)}")
    for p in logger_changes:
        print("   " + p)
    leftovers = git("grep", "-n", "-E", r"(^|[^_A-Za-z])(" + "|".join(re.escape(n) for n in names) + ")",
                    "--", ".", ":(exclude)scripts/apply_mdriia_capstone_update_2026_10.py", check=False).stdout.strip()
    if leftovers:
        print("WARNING, references to old CSV names remain:\n" + leftovers)
    if compiled_bad:
        print("WARNING, scripts that do not compile:\n  " + "\n  ".join(compiled_bad))
    print(f"Files written/updated: {len(touched)}")

    if DO_COMMIT:
        if not git("diff", "--cached", "--quiet", check=False).returncode:
            print("Nothing new to commit.")
        else:
            r = git("commit", "-m", COMMIT_MSG, check=False)
            print(r.stdout.strip() or r.stderr.strip())
            if r.returncode:
                sys.exit("Commit failed (see above).")
        if DO_PUSH:
            r = git("push", "origin", "main", check=False)
            print((r.stdout + r.stderr).strip())
            if r.returncode:
                sys.exit("Push failed: run `git pull --rebase origin main`, then re-run with --push.")
            print("Pushed to origin main.")
    else:
        print("\nStaged, NOT committed. Review with:  git status  /  git diff --cached --stat")
        print("Then re-run with --commit --push, or commit yourself with the message:\n  " + COMMIT_MSG)

if __name__ == "__main__":
    main()
