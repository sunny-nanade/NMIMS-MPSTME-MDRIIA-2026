# AI audit: evidence candidates for dossier section 5.1

Section 5.1 asks each group for **three cases where an AI tool gave wrong robotics or economic data**, how the group
caught each one and what was actually true. Only the group knows which tool it used and what it was told, so this file
does **not** fill the dossier. It lists discrepancies that were found while reconciling the starter pack with primary
sources, each with the evidence needed to defend it in the viva. Use a case only if your group really met it; replace
the tool, the prompt and the "how we caught it" with your own account.

| # | What the starter material said | What the primary source or the code shows | Error type (dossier list) | How to verify it yourself |
|---|---|---|---|---|
| 1 | Survival model `0.67 - 0.023 t_CPR - 0.046 t_defib` attributed to Larsen et al. (1993) | The published model has three terms: 0.023 (CPR), **0.011** (first shock), 0.021 (ACLS). `0.046` is not a coefficient of this model (`docs/CLINICAL_MODEL.md`; tests pin the published values in `tests/test_survival.py`) | Wrong number or statistic | Read the abstract of Larsen 1993 (PMID 8214853); run `python -m pytest tests/test_survival.py` |
| 2 | Schierbeck et al. (2023): "211 suspected OHCAs", median time saving 1 min 52 s | Secondary coverage and the hosted paper give 55 suspected-arrest deliveries, AED first in 37 (67 %), median lead 3 min 14 s. The title also differs: the paper is a prospective observational study of real-life suspected arrests in Sweden | Real source, wrong details (author, year, venue) | Open doi 10.1016/S2589-7500(23)00161-9 and compare the abstract with `docs/LITERATURE_REVIEW_AND_FOUNDATIONAL_PAPERS.md` of the starter pack |
| 3 | Manuscript blueprint: "Larsen et al. formulated robust collision avoidance algorithms", "Tripathi et al. evaluated multi-agent coordination", "Naess et al. developed formulations for mechanical damping" | The three papers are a cardiac-arrest survival model, an in-hospital arrest circadian study and a retrospective study of ambulance response times. None concerns robot control | Real source, wrong details | Read the three titles and abstracts; compare with Section II of the blueprint |
| 4 | Starter economics script: `kappa = 0.095`, `payback_horizon_months = (0.35 / (1 - kappa)) * 12`, ambulance speed 7.5 km/h typed in as constants | These are inputs typed in as outputs. Computed from stated inputs the labour-lens kappa is far above 1 (`analytics/roi_results.json`); the course rules call hard-coded results "not analysis" | Wrong economics / cost logic | Run `python analytics/aed_delivery_roi.py` and compare; read the rubric's integrity safeguard 2 |
| 5 | Starter MJCF and controller: payload shock in `step_simulation` is `2.68 + np.random.normal(0, 0.08)` at kerbs | That is a generated target, not physics; real payload acceleration comes from the MuJoCo accelerometer on the isolator (`aed_shock_sensor` / `payload_acc`) | Other | Read `aed_navigation_controller.py` of the starter pack; compare with `analytics/aed_delivery_real_trials.csv` column `peak_payload_g` |

If you used an AI tool for any part of this repository's code or text, log it in dossier 5.1 and in the share-of-writing
question in Section 6 even if it is not one of the three error cases.
