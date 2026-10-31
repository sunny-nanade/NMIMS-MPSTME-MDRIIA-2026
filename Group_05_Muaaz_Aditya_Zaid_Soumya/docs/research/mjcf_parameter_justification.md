# MJCF contact parameters: friction and solref (E043)

Applies to `models/common.xml`: the global geom default `friction="1.0 0.01 0.005"` with `condim="3"`, and the
`quad` class `solref="0.004 1"`, under the mandated `timestep="0.002"` in both scene wrappers.

The three geom friction numbers are, in MuJoCo's words, "tangential (same for both axes), torsional, rolling (same for
both axes)" (MuJoCo docs, Modeling, "Contact parameters"); we keep sliding friction at 1.0 (MuJoCo's own default value),
which is enough to hold a landed airframe on the dock and floors without sliding. Because every geom uses `condim="3"`,
which the docs describe as "a regular frictional contact, which can generate normal force as well as a tangential
friction force opposing slip" (Computation, "Contact"), only the sliding coefficient is active in our scenes: torsional
friction needs condim 4 and rolling friction needs condim 6, so the 0.01 and 0.005 values are inert and are kept only so
that a future switch to condim 4/6 starts from small, documented values rather than zero. For `solref="0.004 1"` the
first number is the contact time constant and the docs state that it "should be at least two times larger than the
simulation time step, otherwise the system can become too stiff relative to the numerical integrator ... This is
enforced internally, unless the refsafe attribute of flag is set to false" (Modeling, "Reference"); at 0.002 s the
0.004 s time constant on the airframe geom is exactly 2 x timestep. A leg-on-surface contact does not use that number
alone, though: MuJoCo mixes the two geoms' solref (equal solmix), and the floor and building keep the default 0.02, so the
contact actually uses 0.012 s (printed from the loaded model, `docs/submission/viva_evidence/viva_contact_solref_mix.txt`),
which is above 2 x timestep at both 0.002 s and the earlier 0.004 s, so no clamp acted on these contacts at either timestep. The second number is the damping ratio, and "the dampratio
parameter would normally be set to 1, corresponding to critical damping" (Modeling, "Reference"), i.e. the leg-ground
contact settles without bounce. Re-running the 300 s flight-quality check after the timestep change (seed 1, both scenes,
both UAV policies) showed no change in collisions (0), laps or altitude-hold error, and the head-on separation test still
gives d_min = 3.29 m, so no gains were re-tuned.

Sources (fetched 29 Oct 2026):
- https://mujoco.readthedocs.io/en/stable/modeling.html (sections "Contact parameters", "Reference")
- https://mujoco.readthedocs.io/en/stable/computation/index.html (section "Contact", condim values)
