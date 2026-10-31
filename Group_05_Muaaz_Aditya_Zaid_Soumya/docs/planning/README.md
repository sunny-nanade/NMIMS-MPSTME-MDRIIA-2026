# Planning documents

| PDF | Source |
|---|---|
| `MPSTME_GUARDIAN_PRD_v2.0.pdf` | `source/prd_v2.html` |
| `MPSTME_GUARDIAN_Implementation_Plan_v2.0.pdf` | `source/impl_v2.html` |

Rebuild (from the repo root; needs Google Chrome and Node >= 22, no npm packages):

```bash
node docs/planning/source/build_pdf.mjs docs/planning/source/prd_v2.html  docs/planning/MPSTME_GUARDIAN_PRD_v2.0.pdf                 "Product Requirements Document · v2.0"
node docs/planning/source/build_pdf.mjs docs/planning/source/impl_v2.html docs/planning/MPSTME_GUARDIAN_Implementation_Plan_v2.0.pdf "Implementation Plan · v2.0"
```

`build_pdf.mjs` drives headless Chrome over the DevTools Protocol and waits for `window.__docReady`
(set once Mermaid has rendered and every diagram is scaled to its page). `mermaid.min.js` is vendored
so the build is reproducible offline. Diagrams live inline as `<pre class="mermaid">` blocks.

Note: v2.0 describes the exterior scene; the interior scene is now the default (v2.1 pending).

**Status of these documents (30 Oct 2026).** The planning documents are history, not results. Numbers in them are either
course-scaffold placeholders (labelled so in PRD v2.0) or single-run development checks made before the Monte Carlo batch.
None of them may be quoted as a result: every reported value comes from `analytics/campus_patrol_real_trials.csv`
(N = 30 per cell) and the script outputs listed in `docs/DOSSIER_FILL_SHEET.md`. The v2.0 exterior ring outside the
boundary wall was superseded: all patrolling is planned inside the college (ring offset 3.0 m inward).
`MPSTME_GUARDIAN_PRD_v3.0_Status_and_Submission.pdf` is built from `source/prd_v3_status.html` with the footer title
"PRD v3.0 · Status & Submission".

**Course audit (30 Oct 2026).** The course faculty's `scripts/audit_course_boundaries_and_rules.py` was run over this folder
(wrapper that applies its `audit_file` rules to every file and skips the 12-group roster check, which needs the monorepo root).
Faculty name, currency words and the U+2610 checkbox were removed from the planning documents and the three PRD PDFs were
rebuilt. Repository identifiers are written in the form `github.com/sunny-nanade/...`, the one form the audit allows.
Known false positives, not defects:

- `source/mermaid.min.js` (vendored Mermaid, minified): the currency rule matches a backslash followed by `$` inside JS template strings.
- `docs/MDRIIA_Group_05_Technical_Dossier.docx` and `docs/MDRIIA_Group_05_Technical_Dossier_AUTOFILL_DRAFT.docx`: the audit decodes the
  zipped binary as text, so compressed bytes match the emoji and currency patterns. Checking the unzipped `word/*.xml` text finds no
  currency and no emoji. The course faculty's own template carries his name in the document text; that file stays byte-identical.
- `tests/test_e077_economics.py` line 116: the test deliberately contains the currency regex it uses to guard the economics outputs.
