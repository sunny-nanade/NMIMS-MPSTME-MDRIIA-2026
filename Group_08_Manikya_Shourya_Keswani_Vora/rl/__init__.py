"""SkyHydro RL package: flood-relief pickup & drop with a winch UAV in MuJoCo."""
import os as _os

# one maths thread per process (set before numpy loads): training runs many
# simulation processes, and without this each one opens a thread + memory pool
# per CPU core and the machine runs out of RAM. The GPU does the heavy maths.
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")
from .skyhydro_env import SkyHydroDeliveryEnv

# curriculum stages used by train.py / evaluate.py
STAGES = {
    1: dict(max_targets=1, start="warehouse", max_steps=1500),   # pick up at the base, supply one house
    2: dict(max_targets=2, start="mixed", max_steps=2600),       # two houses, start anywhere / at base
    3: dict(max_targets=None, start="random", max_steps=4000),   # full mission: every house with survivors
}

try:
    import gymnasium as gym
    gym.register(id="SkyHydro-Delivery-v0", entry_point="rl.skyhydro_env:SkyHydroDeliveryEnv")
except Exception:  # registration is optional
    pass
