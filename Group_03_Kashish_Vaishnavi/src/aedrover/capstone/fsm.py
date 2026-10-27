"""Mission finite-state machine for the capstone controller (course dossier, Section 2).

    DISPATCH -> ROAD_CRUISE <-> CURB_SIDEWALK -> ARRIVE -> AED_HANDOVER

The FSM supervises any registered local planner. The planner proposes ``(v, delta)``; the FSM
adds a state-dependent speed cap (it never raises the planner's speed and never touches
steering), so the safety filter and the planner keep their guarantees:

============== ==================================================== =====================================
State          Entered when                                         Speed cap
============== ==================================================== =====================================
DISPATCH       episode start (rover leaves the micro-hub)           ``a_launch * t + v_floor`` (ramp)
ROAD_CRUISE    ``t >= t_dispatch_s``, no kerb zone ahead            ``v_cruise``
CURB_SIDEWALK  a kerb edge lies within ``approach_m`` ahead or      ``max(v_curb, v_climb(h, mu_belief)
               ``exit_m`` behind                                    + margin)`` from the measured kerb table
ARRIVE         ``x_goal - x <= arrive_m``                           ``sqrt(2 a_brake d) + v_floor``
AED_HANDOVER   goal reached and the rover is stationary             0 (held for ``handover_s``)
============== ==================================================== =====================================

Kerb positions come from the planned route (the scenario), the way a mapped delivery route would
supply them; the planner itself still senses the kerb from the terrain scan. ``mu_belief`` is a
conservative friction belief (the rover does not observe friction).

Every transition is recorded with its time and trigger, so a run can be replayed state by state
and a viva can point at the line that fired it (``MissionFSM.update``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from ..control.curb import CurbTable
from ..control.safety_filter import SafetyFilter, SafetyParams
from ..nav.base import Controller, make_controller, register


class State(str, Enum):
    DISPATCH = "DISPATCH"
    ROAD_CRUISE = "ROAD_CRUISE"
    CURB_SIDEWALK = "CURB_SIDEWALK"
    ARRIVE = "ARRIVE"
    AED_HANDOVER = "AED_HANDOVER"


STATES = tuple(s.value for s in State)


@dataclass(frozen=True)
class FSMParams:
    v_cruise: float = 1.8          # m/s, ROAD_CRUISE cap (the planner's own cruise speed is the same)
    v_curb: float = 1.2            # m/s, minimum CURB_SIDEWALK cap (course brief value)
    a_launch: float = 1.0          # m/s^2, DISPATCH acceleration ramp
    v_floor: float = 0.3           # m/s, creep speed so ramps never command a stall
    t_dispatch_s: float = 2.0      # s, leave the hub before cruising
    approach_m: float = 4.0        # m, kerb look-ahead that triggers CURB_SIDEWALK
    exit_m: float = 1.5            # m, stay in CURB_SIDEWALK this far beyond the edge
    arrive_m: float = 3.0          # m, distance to the goal that triggers ARRIVE
    a_brake: float = 1.5           # m/s^2, ARRIVE deceleration (ISO 13482 / 3691-4 floor)
    mu_belief: float = 0.5         # conservative friction belief for the kerb table
    climb_margin: float = 0.15     # m/s above the minimum successful climb speed
    handover_s: float = 10.0       # s, bystander retrieves the AED and applies the pads
    climb_assist: bool = False     # raise the approach speed to the climbing minimum just before a kerb up (see FSMSupervisor)
    assist_m: float = 2.0          # m, distance before the kerb edge in which the assist acts
    unblock: bool = False          # search steering with the safety barrier when blocked (see FSMSupervisor)
    unblock_s: float = 1.5         # s, blocked time before the search starts


@dataclass
class Transition:
    t: float
    src: str
    dst: str
    reason: str


@dataclass
class MissionFSM:
    params: FSMParams = field(default_factory=FSMParams)
    state: State = State.DISPATCH
    transitions: list[Transition] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._table: CurbTable | None = None
        self._sc = None

    def reset(self, scenario, wheel_radius: float = 0.15, design: str = "nominal") -> None:
        self._sc = scenario
        self._table = CurbTable.load(wheel_radius=wheel_radius, design=design)      # the kerb table measured for THIS vehicle'
        self.state = State.DISPATCH
        self.transitions = []

    # -------------------------------------------------------------- geometry
    def _kerb_edges(self) -> list[float]:
        sc = self._sc
        return [sc.x_down, sc.x_up] if sc.has_kerb else []

    def in_kerb_zone(self, x: float) -> bool:
        p = self.params
        return any(e - p.approach_m <= x <= e + p.exit_m for e in self._kerb_edges())

    def _go(self, t: float, dst: State, reason: str) -> None:
        if dst is not self.state:
            self.transitions.append(Transition(t, self.state.value, dst.value, reason))
            self.state = dst

    # --------------------------------------------------------------- update
    def update(self, obs: dict) -> State:
        """Advance the state machine from the observation; returns the new state."""
        p, t, x = self.params, obs["t"], obs["x"]
        if self.state is State.AED_HANDOVER:
            return self.state
        if self._sc.x_goal - x <= p.arrive_m:
            self._go(t, State.ARRIVE, f"goal within {p.arrive_m:.1f} m")
        elif self.state is State.DISPATCH:
            if t >= p.t_dispatch_s:
                self._go(t, State.ROAD_CRUISE, f"t >= {p.t_dispatch_s:.1f} s")
        elif self.in_kerb_zone(x):
            self._go(t, State.CURB_SIDEWALK, "kerb edge ahead")
        elif self.state is State.CURB_SIDEWALK:
            self._go(t, State.ROAD_CRUISE, "kerb zone cleared")
        return self.state

    def begin_handover(self, t: float) -> None:
        self._go(t, State.AED_HANDOVER, "goal reached, rover stationary")

    # ------------------------------------------------------------ speed cap
    def speed_cap(self, obs: dict) -> float:
        p = self.params
        if self.state is State.DISPATCH:
            return p.a_launch * obs["t"] + p.v_floor
        if self.state is State.CURB_SIDEWALK:
            sc = self._sc
            climb = self._table.v_climb(sc.kerb_h, min(p.mu_belief, sc.tyre_mu)) + p.climb_margin
            return max(p.v_curb, climb)
        if self.state is State.ARRIVE:
            d = max(self._sc.x_goal - obs["x"], 0.0)
            return math.sqrt(2.0 * p.a_brake * d) + p.v_floor
        if self.state is State.AED_HANDOVER:
            return 0.0
        return p.v_cruise


class FSMSupervisor:
    """Controller wrapper: planner proposal, FSM speed cap. Satisfies the ``Controller`` protocol.

    Two optional behaviours (both off by default, so the original controller is unchanged):

    ``climb_assist``  inside ``assist_m`` of a kerb *up* the planner may have slowed for a pedestrian or obstacle and
                      left too little run-up to climb the lip (the wheels stall on it). The supervisor raises the speed to the
                      measured minimum climbing speed plus a margin; the safety filter still has the last word.
    ``unblock``       when the filtered speed stays below ``blocked_v`` for ``unblock_s`` seconds the planner's arc is blocked
                      and the robot is standing still. The supervisor then searches steering angles with the safety filter's
                      own stopping-distance barrier and takes the one that allows the most speed (ties go to the planner's angle).
    """

    BLOCKED_V = 0.3        # m/s, filtered speed below which the arc counts as blocked

    def __init__(self, inner: Controller, params: FSMParams | None = None, safety=None):
        self.inner = inner
        self.fsm = MissionFSM(params or FSMParams())
        self.name = f"fsm_{inner.name}"
        self.safety = safety
        self._blocked_since: float | None = None
        self.n_assists = 0
        self.n_unblocks = 0

    @property
    def state(self) -> State:
        return self.fsm.state

    def reset(self, env) -> None:
        self.inner.reset(env)
        self.fsm.reset(env.scenario, wheel_radius=env.veh0.wheel_radius, design=env.veh0.name)
        self._blocked_since = None
        self.n_assists = self.n_unblocks = 0

    def _climb_assist(self, obs: dict, v: float) -> float:
        p, sc = self.fsm.params, self.fsm._sc
        if not (p.climb_assist and sc.has_kerb):
            return v
        gap = sc.x_up - obs["x"]
        if 0.0 <= gap <= p.assist_m:
            need = self.fsm._table.v_climb(sc.kerb_h, min(p.mu_belief, sc.tyre_mu)) + p.climb_margin
            if v < need:
                self.n_assists += 1
                return need
        return v

    def _unblock(self, obs: dict, v: float, delta: float) -> tuple[float, float]:
        p = self.fsm.params
        if not (p.unblock and self.safety is not None) or self.fsm.state in (State.ARRIVE, State.AED_HANDOVER):
            return v, delta
        lim = self.safety.v_limit(obs, delta)
        if lim >= self.BLOCKED_V:
            self._blocked_since = None
            return v, delta
        t = obs["t"]
        if self._blocked_since is None:
            self._blocked_since = t
        if t - self._blocked_since < p.unblock_s:
            return v, delta
        grid = np.linspace(-0.5, 0.5, 21)
        limits = np.array([self.safety.v_limit(obs, float(g)) for g in grid])
        best = limits.max()
        near = np.flatnonzero(limits >= best - 1e-9)
        d_best = float(grid[near[np.argmin(np.abs(grid[near] - delta))]])
        if best >= self.BLOCKED_V:
            self.n_unblocks += 1
            return min(max(v, self.BLOCKED_V), best), d_best
        return v, delta

    def act(self, obs: dict) -> tuple[float, float]:
        v, delta = self.inner.act(obs)
        self.fsm.update(obs)
        v = self._climb_assist(obs, v)
        v, delta = self._unblock(obs, v, delta)
        return min(v, self.fsm.speed_cap(obs)), delta


@register("fsm_dwa")
def _fsm_dwa(fsm_kwargs: dict | None = None, safety_kwargs: dict | None = None, **planner_kwargs):
    planner_kwargs.setdefault("v_cruise", FSMParams().v_cruise)
    return FSMSupervisor(make_controller("dwa", **planner_kwargs), FSMParams(**(fsm_kwargs or {})),
                         SafetyFilter(SafetyParams(**(safety_kwargs or {}))))