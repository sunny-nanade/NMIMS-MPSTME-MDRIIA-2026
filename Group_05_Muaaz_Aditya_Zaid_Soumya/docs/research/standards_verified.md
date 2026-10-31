# Standards verified (G-19) and guard-baseline inputs re-checked (G-20)

Checked 30 Oct 2026. Companion to `docs/research/sources_verified.md` (L-23, L-24), which this file refines. Nothing below is estimated. Clause text of ISO, IEC and ANSI/A3 standards is paywalled, so a clause number is given only where a public page shows one; otherwise the row carries the scope sentence and the words "clause text paywalled".

## How each page was read

| Publisher page | Result |
|---|---|
| IEC webstore (official) | read: https://webstore.iec.ch/publication/2612 |
| ASTM store (official) | read: https://store.astm.org/f3322-24a.html (scope shown as clause 1.1) |
| India e-gazette PDF (official) | downloaded and text-extracted, rules quoted below are from this text: https://egazette.gov.in/WriteReadData/2021/229221.pdf |
| iso.org, webstore.ansi.org, automate.org (A3), blog.ansi.org | HTTP 403 to the fetch tool and to curl; not read |
| Catalogue pages used instead (Genorma, Saudi GSO store, UNI store, SIS) | read; they reproduce the ISO scope text. Fetch results are summaries returned by the fetch tool, so quotes are "as returned by the fetch tool" |

Where an official ISO or A3 page was blocked, the row says so in the Source column. No clause number was invented.

## The five template rows (dossier table T5, section 1.2)

| # | Standard | Applies? | Verdict | Clause or scope (quote) | Source | URL |
|---|---|---|---|---|---|---|
| 1 | ISO 10218-1/-2 (industrial robots) | No | Verified; edition updated | ISO 10218-1:2025 (published 5 Feb 2025, replaces ISO 10218-1:2011, which is withdrawn) scope: "This document specifies requirements for the inherently safe design, risk reduction measures and information for use of robots for an industrial environment." Its list of non-applicable uses and products includes "airborne and space robots, including outer space" and "service robots". Clause number of the exclusion list: not shown on the public page; clause text paywalled. The 2011 scope sentence earlier recorded in L-23 ("does not apply to non-industrial robots") belongs to the withdrawn edition. | Genorma catalogue and Saudi GSO store (iso.org page 403) | https://genorma.com/en/standards/iso-10218-1-2025 ; https://dgsm.gso.org.sa/store/standards/iso:pub:std:IS:73933/ISO%2010218-1:2025 ; 2011 edition: https://store.uni.com/iso-10218-1-2011 |
| 2 | ISO 3691-4 (driverless industrial trucks) | No | Verified | ISO 3691-4:2023 (published 12 Jun 2023): "Industrial trucks - Safety requirements and verification - Part 4: Driverless industrial trucks and their systems". Scope summary: driverless industrial trucks including AGVs and AMRs; excludes rail-guided and remotely controlled trucks and public roads. A multirotor is not an industrial truck. Clause text paywalled; no clause number visible. | Genorma catalogue (iso.org page 403) | https://genorma.com/en/standards/iso-3691-4-2023 |
| 3 | ANSI/RIA R15.06 | No | Verified; edition updated | The 2012 RIA edition has been revised as ANSI/A3 R15.06-2025 (published Sep 2025), "the U.S. national adoption of ISO 10218 Parts 1 and 2" (Part 1 industrial robots, Part 2 robot applications and cells). Same industrial-robot scope as row 1. Clause text paywalled; the A3 store page itself returned 403, so this is a trade-press report of A3's announcement, not the A3 page. | The Robot Report | https://www.therobotreport.com/updated-ansi-a3-standards-address-industrial-robot-safety/ ; earlier 2012 description: https://www.certifico.com/id/2121 |
| 4 | IEC 60601-1 (medical electrical equipment) | No | Verified | Edition 3.1 (2005 + A1:2012 consolidated), status "Current": "IEC 60601-1:2005+A1:2012 contains requirements concerning basic safety and essential performance that are generally applicable to medical electrical equipment." Campus security UAVs are not medical electrical equipment. Clause text paywalled. | IEC webstore (official) | https://webstore.iec.ch/publication/2612 |
| 5 | Domain-specific: India Drone Rules 2021 (G.S.R. 589(E)) | Partly (decision below) | Verified from official gazette text | Rule 2(1)(a)-(c), 2(3), 3(1)(k), 3(1)(l), 3(1)(zb), 5, 12(1)(c), 14(1), 21, 22, 36, 42 quoted below | Gazette of India, Extraordinary, Part II Sec 3(i), 25 Aug 2021 | https://egazette.gov.in/WriteReadData/2021/229221.pdf |

## Section 1.2 notes (rows the template does not have)

| Standard | Applies? | Verdict | Clause or scope (quote) | Source | URL |
|---|---|---|---|---|---|
| ISO 21384-3 (UAS, operational procedures) | Yes, as the operations reference for any real deployment; not used as a numeric source in the simulation | Verified; edition updated | Current edition ISO 21384-3:2026 (published 7 Aug 2026; the 2023 edition is withdrawn). Scope: "This document specifies the requirements for safe commercial operations of uncrewed aircraft system (UAS), including the external safety-critical service providing command and control (C2) Link." A search-result snippet adds that it "applies to all commercial UAS regardless of size, application or location"; that sentence was not on a page we fetched, so do not quote it in the dossier. 2023 edition scope, same wording with "unmanned": "...safe commercial unmanned aircraft system (UAS) operations...". Clause numbers and any return-to-home or geofence clause: not publicly visible, clause text paywalled. The 2.5 s telemetry-loss return-to-home value comes from the course Standards Manual section 2.4, not from this standard (not verifiable here). Our project is a non-commercial capstone simulation, so "commercial operations" does not strictly cover it. | Genorma (2026 and 2023), Saudi GSO store (2023) | https://genorma.com/en/standards/iso-21384-3-2026 ; https://genorma.com/en/standards/iso-21384-3-2023 ; https://dgsm.gso.org.sa/store/standards/iso:pub:std:IS:80124/ISO%2021384-3:2023 |
| ASTM F3322 (small UAS parachutes) | Not as a geofencing or return-to-home source (course Manual attribution corrected); relevant only to parachute recovery, which is not modelled | Corrected | Current edition F3322-24a (active, updated 7 Feb 2025). Clause 1.1: "This specification covers the design and manufacture requirements for deployable parachutes of small Unmanned Aircraft (sUA)/small Unmanned Aircraft Systems (sUAS)." The page fetch reported no mention of geofencing or return-to-home. | ASTM store (official) | https://store.astm.org/f3322-24a.html |

## India Drone Rules 2021: decision

Decision: Partly applies. Reason in one line: the Rules apply to any unmanned aircraft operated "in or over India" (Rule 2(1)(c)) and have no private-property carve-out, so outdoor flight on the campus inside the boundary wall is covered; the text is silent on flight inside a building, and our project is simulation only.

Text read from the gazette (the quotes are the extracted PDF text):

- Rule 2(1): "These rules shall apply to-- (a) all persons owning or possessing, or engaged in leasing, operating, transferring or maintaining an unmanned aircraft system in India; (b) all unmanned aircraft systems that are registered in India; and (c) all unmanned aircraft systems that are being operated for the time being, in or over India."
- Rule 2(3): "These rules shall not apply to an unmanned aircraft system belonging to, or used by, the naval, military or air forces of the Union of India." No other exemption, and none for indoor flight. Search of the full text for "indoor" and "enclosed": no hit.
- Rule 3(1)(zb): "'unmanned aircraft system' means an aircraft that can operate autonomously or can be operated remotely without a pilot on board". Our autonomous UAVs fall inside this definition.
- Rule 3(1)(k): "'Geo-fencing' means restricting the movement of unmanned aircraft system within a defined airspace". Rule 12(1)(c) lists "Geo-fencing capability" among safety features the Central Government "may, in future" notify, so no geofence is mandatory under the text read.
- Rule 3(1)(l): green zone is airspace "upto a vertical distance of 400 feet or 120 metre" not designated red or yellow; yellow and red zones are defined in the same clause.
- Rule 5: classes by all-up weight (nano up to 250 g; micro over 250 g up to 2 kg; small over 2 kg up to 25 kg). Our MuJoCo model is not a real airframe, so no class is assigned.
- Rule 14(1): "No person shall operate an unmanned aircraft system without first registering it on the digital sky platform and obtaining a unique identification number, unless exempted ...".
- Rule 21: mandatory pre-flight check of the digital sky platform. Rule 22(1): "No person shall operate an unmanned aircraft system in a red zone or yellow zone without prior permission." Rule 22(2): none needed in a green zone, subject to rule 21.
- Rule 36: no remote pilot licence for nano, and for micro "for non-commercial purposes".
- Rule 42 (research, development and testing): an educational institution "under the administrative control of, or recognised by, the Central Government or State Government or Union Territory Administration" does not need a type certificate, unique identification number, prior permission or remote pilot licence, "Provided that such unmanned aircraft system operations takes place within a green zone and within the premises of the person where such research, development and testing is being carried out or within an open area in a green zone under such person's control."

Not verified (state as such in the dossier): (1) the Digital Sky zone of the campus, so green, yellow or red is not measured; (2) whether the college qualifies under Rule 42(b); (3) the Drone (Amendment) Rules 2022 and 2023, which this gazette copy does not contain; (4) the draft Civil Drone (Promotion and Regulation) Bill 2025, released for consultation on 16 Sep 2025, which secondary sources (https://www.mondaq.com/india/constitutional-administrative-law/1799264/the-draft-civil-drone-promotion-regulation-bill-2025-what-it-means-for-operators-and-businesses-in-india) say would repeal the Rules; its enactment status as of Oct 2026 was not checked. The 2.5 s return-to-home limit is not in the Rules.

Suggested dossier cell (T5 R5 C3 = Partly): "Partly. India Drone Rules 2021, G.S.R. 589(E): Rule 2(1)(c) covers any UAS operated in or over India, so outdoor campus flight would need Rule 14 registration and Rule 21/22 zone checks unless Rule 42 applies (green zone, own premises); indoor flight is not addressed (no hit for 'indoor' or 'enclosed'). Simulation only; zone not checked."

## G-20: guard stop time, lift waiting time, human detect radius (max 10 min sourcing)

Searches run: guard-tour checkpoint dwell time; office lift waiting time; human visual detection range. Result: no primary source for guard stop time or guard detect radius; lift waiting time has only a design target, not a measurement for a campus lift. All three stay ASSUMPTION with a swept range. The `CONFIG` ranges in `src/foot_patrol_baseline.py` (stop_mean_s 10 to 60 s, lift_wait_s 15 to 60 s, detect_radius_m 15 m with a 10 to 20 m range) are unchanged.

| Parameter | Value or range kept | Status | What was found | URL |
|---|---|---|---|---|
| guard stop time per checkpoint | 10 to 60 s | ASSUMPTION (no primary source) | Search returned airport passenger-screening and vehicle-gate items only (not guard patrol tours); none used. | none |
| lift waiting time (guard descending to ground floor) | 15 to 60 s | ASSUMPTION; the range brackets the design targets found | A building-services wiki page reports office lift design criteria: "20 to 30 seconds provides a range from standard to prestige" for average interval, and a survey recommendation "Average waiting time: 25 secs lunchtime"; it cites BS 5655 part 6 and CIBSE Guide D without per-figure attribution, so it is a secondary source and the numbers are not primary. A CIBSE seminar slide (2023) gives only "Average Waiting Time = Interval/2" and no target. Design targets are for new offices, not measured waits in a college building. The arXiv paper 2012.01471 (Feng and Redner, J. Stat. Mech. 2021) is a theoretical model and reports no measured wait. | https://designingbuildings.co.uk/wiki/Lifts_for_office_buildings ; https://www.cibse.org/media/5a4lpbwp/chapter-3-4-9-a2.pdf ; https://arxiv.org/abs/2012.01471 |
| guard detect radius of a person | 10 to 20 m (base 15 m) | ASSUMPTION (no primary source) | Results were about beach-lifeguard visual acuity, CCTV range tests and RCNN detectors, none about a guard noticing a person in a building corridor; none used. | none |

Sweeps: the three parameters are already drawn per seed or per event inside the stated ranges (stop mean per seed, lift wait per descent); the detect radius is a fixed 15 m base, so a sensitivity run at 10 m and 20 m is the remaining step if the report claims robustness to it (not run by this task).
