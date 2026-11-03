"""Physical constants of the AMR. Shared by the MJCF generator and the controller so the
model and the control law can never disagree about wheel radius or track width."""

WHEEL_RADIUS = 0.12          # r [m]
WHEEL_HALF_WIDTH = 0.035     # [m]
TRACK_WIDTH = 0.56           # b: distance between wheel centres [m]
CHASSIS_HALF = (0.34, 0.24, 0.07)   # half-extents of the chassis box [m]
CHASSIS_Z0 = 0.20            # chassis centre height when resting on the wheels [m]
WHEEL_Z_REL = -0.08          # wheel axle height relative to the chassis centre [m]
CASTER_X = 0.30              # +/- caster x offset [m]
CASTER_RADIUS = 0.04
CASTER_Z_REL = -0.16

MAST_X = 0.10                # mast base x offset from chassis centre [m]
MAST_BASE_Z = 0.07           # mast base height relative to chassis centre [m]
HEAD_Z_IN_SLIDER = 0.95      # pan axis height above mast base at zero lift [m]
LIFT_MIN, LIFT_MAX = 0.0, 0.5
PAN_LIMIT = 2.4              # rad
TILT_MIN, TILT_MAX = -0.9, 1.3   # rad; positive tilt pitches the head DOWN
LENS_X = 0.08                # lens position ahead of the tilt axis [m]

# range sensors (side-looking along the chassis y axis, front-looking along x)
RF_X = 0.28
RF_Y = 0.24
RF_Z_REL = 0.55              # height above chassis centre -> ~0.75 m above ground

# actuator limits
WHEEL_TORQUE_LIMIT = 6.0     # Nm

# motion limits used by the planner
V_CRUISE = 0.7               # m/s
V_TURN = 0.35
OMEGA_MAX = 1.2              # rad/s
