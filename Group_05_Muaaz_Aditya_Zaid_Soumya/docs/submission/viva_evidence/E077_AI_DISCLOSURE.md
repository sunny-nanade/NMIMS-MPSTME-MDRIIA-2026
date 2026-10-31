# AI disclosure for E077 (economics, FMEA, claims, git fix)

## What was AI-drafted
Essentially all of it, by an AI coding assistant working from a brief:
- `analytics/campus_security_economics.py` (rewrite): SOURCES table, economics(), M/M/c with Erlang C, sensitivity, break-even, plots, refusal logic.
- `analytics/campus_security_fmea.py`: failure-mode table, occurrence loaders, RPN.
- `tests/test_e077_economics.py`: all 35 tests and the fixture builder.
- `CLAIMS_AND_BASELINE.md` (generated from the research files by a script), `GIT_FIX.md`, `COMMITS.md`, `EXPLAIN.md`, this file.
- Data: none. No real trials CSV existed when this was drafted, so no result file, figure or dossier number was produced from real data. The two PNGs and the results JSON will exist only after the real CSV is run.
Estimated AI-drafted share: about 100 % of the text and code. The member's share so far is zero until she reviews, runs and commits it.

## What the member must verify or redo
1. Read `EXPLAIN.md` and be able to derive kappa, NCRI, P_payback, T_payback, delta FTE and the Erlang C formula on a whiteboard in 30 seconds.
2. Re-run `python -m pytest tests/test_e077_economics.py` on your machine; read the Erlang C hand references (1/3, rho, 4/9) and check them.
3. Decide the ASSUMPTION ranges with the team (CapEx ratio, replacement fraction, running-cost fractions, battery share, endurance, incident rate, responders, guard verification time). They are placeholders for a conversation, not findings; the research found no primary source for them.
4. Agree the S and D scores of the FMEA (TEAM_JUDGEMENT table) in the team; they are judgement, not measurement.
5. Run the script on the real CSV after E043 merges and only then quote numbers; never quote a fixture number.
6. Check the sourced inputs against the pages (OSH Code 2020 s.25(1)(a), DJI product page, Bohannon papers); the research file records how each was retrieved and that some standards pages were read through a fetch summary.
7. Set your own git e-mail (GIT_FIX.md) before any commit.

## A real AI error from this drafting (with evidence)
The first run of the new tests failed on my own text. The no-money test scanned this module's own source for forbidden words, and the AI had put the forbidden word (the first word of the money-token list) into two test function names and a section comment, so the scan matched the file that enforces it:

```
FAILED tests/test_e077_economics.py::test_no_<forbidden word>_in_sources_and_this_test
E   AssertionError: forbidden money token '<the 8-letter word>' in test_e077_economics.py
```
After renaming the tests to `test_no_money_...` the same test passed (35 passed in the final run).

The same run caught a second mistake in the AI's own code, the literal-result scan flagging the number 78 used six times as a print width:

```
FAILED tests/test_e077_economics.py::test_no_literal_results_ast_scan
E   AssertionError: numeric literals outside the input tables in campus_security_economics.py: [78]
```
Fixed by moving the width into the METHOD table. A third near-miss, found before running tests: the first CapEx range ended at 1.2, which is one of the eight deleted constants; it was changed to 1.1.

Evidence is the pytest output above (two failing runs, then `35 passed`).

One discrepancy to note: the brief said the APF-only separation was 0.40 m; the E043 script printed 0.42 m when run on 29 Oct (saved output in results/). The doc quotes the printed value.
