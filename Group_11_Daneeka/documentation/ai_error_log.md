# AI errors found and fixed (material for dossier Section 5.1)

These are errors made by the AI assistant (Claude) while building this project, each found by running the code. Add your own
(what *you* caught, and how) before submitting; do not claim ones you did not see.

| # | What went wrong | How it was caught | Fix |
|---|---|---|---|
| 1 | Robot would not move: torque 6 Nm, wheel speed 0.04 rad/s. I assumed the skid casters had friction 0.01, but MuJoCo combines the friction of two touching geoms with `max`, so the floor's 1.2 won. | Printed contact forces; caster tangential/normal force ratio was 0.33, not 0.01 | Gave caster geoms `priority="1"` so their own friction is used |
| 2 | Range finder (mj_ray) returned nothing against the module slab; I thought it was a group-filter mistake. The slab geom had alpha 0 and mj_ray skips fully transparent geoms. The robot then silently dead-reckoned and drifted 18 cm by row 4. | Per-row cross-track error grew 0.7 -> 18 cm; direct ray test with all groups returned a hit, with group 3 only returned none | alpha 0.004 on the slab |
| 3 | After that fix a constant 5.9 cm offset remained: the slab was 4 cm thick, the ray hit its front face, not the module plane. | Offset equalled 0.02 / sin(20 deg) | slab half-thickness 0.5 mm |
| 4 | Shaded cells ran *cooler* than neighbours in the thermal model (reverse-bias heating too weak) | Unit test of a shaded cell | KAPPA_RB raised to 55 K and documented as an uncalibrated assumption |
| 5 | I tuned detector thresholds while looking at the evaluation seeds and then planned to report those seeds. | Self-review of the protocol | Tuning seeds (1000-1029) kept separately; reported results use fresh seeds 3000-3029 |
| 6 | Starter files contained unsourced numbers (8.5 h/MW, 1.6 h/MW, kappa 0.176, 78.5 %, 13.4 months) and unverified DOIs. | Read the dossier warning and the README literature table | Not used; replaced by computed values and a sourced 10 h/MW (secondary) |
| 7 | I first assumed sun glint would be a major failure mode at the project site. A numerical check over all months showed it never reaches the camera at Mumbai with this geometry. | Min mirror-angle search | Documented; glint is a labelled stress scenario at 6 N |
| 8 | The fiducial (post-marker) position fixes never fired: I passed `row - 1` to the marker reader, so it looked for markers near the wrong lane. The estimator unit test passed (it only tests the maths), so the bug survived until the misassociation stress test showed the proposed controller mislabelling modules (recall 0.76). | Stress scenario "misassociation" gave implausibly poor proposed results; traced the call | Pass the current row; the scenario then gave 0 label errors in the 3 seeds checked. All evaluation and scenario runs were repeated after this fix (earlier scenario file kept as `analytics/prefix_scenario_trials_fiducial_bug.csv`). |
