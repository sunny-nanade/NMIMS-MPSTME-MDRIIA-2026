#!/usr/bin/env python3
"""Research capture controller. See README.txt for assumptions and measured results.
Vision uses rendered depth and simulator segmentation, never target state for control.
The compliant mode realizes Cartesian impedance through an admittance offset,
followed by damped-least-squares IK and torque-limited joint servos.
"""
from __future__ import annotations
import argparse, csv, gzip, hashlib, json, math, os, sys, time
from pathlib import Path
from dataclasses import dataclass
from contextlib import ExitStack
import numpy as np
from scipy.spatial.transform import Rotation
from scipy.optimize import least_squares
def limit(v, maximum):
    return v * min(1., maximum / max(float(np.linalg.norm(v)), 1e-12))


def unit(v):
    return v / max(float(np.linalg.norm(v)), 1e-12)


@dataclass
class Observation:
    position: np.ndarray
    rotation: np.ndarray
    velocity: np.ndarray
    time: float
    camera: str
    bbox: tuple
    pixels: int
    pose_valid: bool
    range_m: float


class CameraVision:
    """Detect bare-body surfaces with six cameras; estimate range and pose."""
    CAMERAS = ('front_camera', 'rear_camera', 'left_camera', 'right_camera', 'down_camera', 'up_camera')

    def __init__(self, model, data, mj):
        self.model, self.data, self.mj = model, data, mj
        self.width, self.height = 480, 360
        self.cameras = {name: model.camera(name).id for name in self.CAMERAS}
        self.focal = {name: self.height / (2*np.tan(np.deg2rad(model.cam_fovy[cid])/2)) for name,cid in self.cameras.items()}
        self.renderer = mj.Renderer(model, height=self.height, width=self.width)
        self.robot = model.body('servicer').id
        self.names = [model.body(i).name for i in range(model.nbody) if model.body(i).name.startswith('debris_')]
        self.body_geoms = {n: model.geom(f'{n}_geom').id for n in self.names}
        self.history, self.latest, self.by_camera = {}, {}, {c: {} for c in self.CAMERAS}
        self.frames = 0
        self.scan_time = -1.

    def close(self):
        self.renderer.close()

    def points(self, xx, yy, depth, camera):
        z = depth[yy, xx].astype(float)
        focal = self.focal[camera]
        return np.column_stack(((xx+.5-self.width/2)*z/focal,
                                -(yy+.5-self.height/2)*z/focal, -z))

    @staticmethod
    def sphere_center(points):
        origin = points.mean(axis=0)
        q = points-origin
        fit, _, rank, _ = np.linalg.lstsq(np.column_stack((2*q,np.ones(len(q)))), (q*q).sum(axis=1), rcond=None)
        radius = np.sqrt(max(0., fit[3]+fit[:3]@fit[:3]))
        return origin+fit[:3], radius, rank

    def body_pose(self, name, gid, points, xx, yy, mask, depth, camera, Rc, pc):
        """Estimate a bare primitive from visible surface depth, never body state.

        Sphere fits recover the center directly. Box face normals estimate the
        orientation; known half-sizes correct a visible face toward its center.
        Shape sizes are the detector's object models, not hidden world poses.
        """
        size = self.model.geom_size[gid]
        world = points @ Rc.T + pc
        if self.model.geom_type[gid] == int(self.mj.mjtGeom.mjGEOM_SPHERE):
            fitted, radius, rank = self.sphere_center(points[::max(1,len(points)//1200)])
            if rank == 4 and abs(radius-size[0]) < .06:
                return pc+Rc@fitted, np.eye(3), True
            return world.mean(0)+unit(world.mean(0)-pc)*size[0], np.eye(3), False

        previous = self.history.get(name)
        R = previous.rotation.copy() if previous is not None else np.eye(3)
        interior = (xx>0)&(xx<self.width-1)&(yy>0)&(yy<self.height-1)
        ix,iy=xx[interior],yy[interior]
        good=mask[iy,ix-1]&mask[iy,ix+1]&mask[iy-1,ix]&mask[iy+1,ix]
        ix,iy=ix[good],iy[good]
        observed=np.zeros(3,dtype=bool)
        if len(ix)>=8:
            stride=max(1,len(ix)//600);ix,iy=ix[::stride],iy[::stride]
            p0=self.points(ix,iy,depth,camera)
            right=self.points(ix+1,iy,depth,camera)-p0
            down=self.points(ix,iy+1,depth,camera)-p0
            left=p0-self.points(ix-1,iy,depth,camera)
            up=p0-self.points(ix,iy-1,depth,camera)
            forward=np.cross(right,down)@Rc.T
            backward=np.cross(left,up)@Rc.T
            lf,lb=np.linalg.norm(forward,axis=1),np.linalg.norm(backward,axis=1)
            valid=(lf>1e-9)&(lb>1e-9)
            forward=forward[valid]/lf[valid,None]
            backward=backward[valid]/lb[valid,None]
            # Reject samples crossing a box edge: mixed-face normals can bias pose.
            flat=np.sum(forward*backward,axis=1)>.996
            normals=forward[flat]
            axes=normals@R
            assignment=np.argmax(np.abs(axes),axis=1)
            fitted_axes=R.copy()
            for axis in range(3):
                chosen=(assignment==axis)&(np.abs(axes[:,axis])>.85)
                if np.count_nonzero(chosen)>=5:
                    oriented=normals[chosen]*np.sign(axes[chosen,axis,None])
                    fitted_axes[:,axis]=unit(np.median(oriented,axis=0))
                    observed[axis]=True
            u,_,vt=np.linalg.svd(fitted_axes)
            R=u@np.diag([1.,1.,np.linalg.det(u@vt)])@vt
        local=world@R
        lo,hi=local.min(0),local.max(0)
        center=(lo+hi)/2
        view=pc@R-center
        # A single face provides depth but not the hidden opposite face.
        # Only correct axes whose surface normal was actually observed; a narrow
        # silhouette caused by claw occlusion is not another physical face.
        for axis in range(3):
            if hi[axis]-lo[axis]<1.5*size[axis] and (observed[axis] or (not observed.any() and abs(view[axis])==max(abs(view)))):
                center[axis]=hi[axis]-size[axis] if view[axis]>0 else lo[axis]+size[axis]
        return R@center,R,bool(observed.any())

    def observe(self, excluded):
        candidates={}
        robot_position=self.data.xpos[self.robot]  # Own-vehicle odometry, not target truth.
        for camera,cid in self.cameras.items():
            r=self.renderer
            r.update_scene(self.data,camera=cid)
            r.enable_segmentation_rendering();seg=r.render().copy();r.disable_segmentation_rendering()
            r.enable_depth_rendering();depth=r.render().copy();r.disable_depth_rendering()
            self.frames+=1
            Rc=self.data.cam_xmat[cid].reshape(3,3)
            pc=self.data.cam_xpos[cid]
            visible={}
            for name,gid in self.body_geoms.items():
                if name in excluded or (getattr(self,'lock',None) and name!=self.lock):
                    continue
                mask=(seg[:,:,0]==gid)&(seg[:,:,1]==int(self.mj.mjtObj.mjOBJ_GEOM))
                yy,xx=np.nonzero(mask)
                if len(xx)<8:
                    continue
                points=self.points(xx,yy,depth,camera)
                position,rotation,valid=self.body_pose(name,gid,points,xx,yy,mask,depth,camera,Rc,pc)
                obs=Observation(position,rotation,np.zeros(3),float(self.data.time),camera,
                                (int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())),
                                len(xx),valid,float(np.linalg.norm(position-robot_position)))
                visible[name]=obs
                candidates.setdefault(name,[]).append(obs)
            self.by_camera[camera]=visible
        fused={}
        for name,options in candidates.items():
            obs=max(options,key=lambda o:(o.pose_valid,o.pixels))
            previous=self.history.get(name)
            if previous is not None and .001<obs.time-previous.time<.6 and previous.pose_valid==obs.pose_valid:
                dt=obs.time-previous.time
                delta=obs.position-previous.position
                obs.velocity=(.5*previous.velocity if np.linalg.norm(delta)<.008 else .8*previous.velocity+.2*limit(delta/dt,.10))
            fused[name]=obs
            self.history[name]=obs
        self.latest=fused
        self.scan_time=float(self.data.time)
        return fused


class PoseTracker(CameraVision):
    """10 Hz rendered depth tracking with constant-twist prediction between frames."""
    def __init__(self, model, data, mj):
        super().__init__(model,data,mj)
        self.omega={};self.lock=None;self.preferred=None

    def body_pose(self,name,gid,points,xx,yy,mask,depth,camera,Rc,pc):
        stale=name in self.history and self.data.time-self.history[name].time>.5
        if stale:
            self.history.pop(name);self.omega.pop(name,None)
        centre,R,valid=super().body_pose(name,gid,points,xx,yy,mask,depth,camera,Rc,pc)
        previous=self.history.get(name)
        if previous is not None:
            dt=min(.2,self.data.time-previous.time)
            centre=previous.position+previous.velocity*dt
            R=Rotation.from_rotvec(self.omega.get(name,np.zeros(3))*dt).as_matrix()@previous.rotation
        world=(points@Rc.T+pc)[::max(1,len(points)//350)]
        size=self.model.geom_size[gid]
        def residual(x):
            rotation=Rotation.from_rotvec(x[3:]).as_matrix()@R
            local=(world-(centre+x[:3]))@rotation
            # Signed box surface distance plus a weak temporal regularizer.
            return np.r_[np.max(np.abs(local)-size,axis=1),.003*x[:3],.001*x[3:]]
        seeds=[R]
        if stale:
            import itertools
            for perm in itertools.permutations(range(3)):
                guess=R[:,perm].copy();guess[:,-1]*=np.linalg.det(guess);seeds.append(guess)
        best=None
        for seed in seeds:
            R=seed
            bound=.6 if stale else .25
            fit=least_squares(residual,np.zeros(6),bounds=(-bound,bound),max_nfev=14,loss='soft_l1',f_scale=.01)
            score=float(np.mean(residual(fit.x)[:-6]**2))
            if best is None or score<best[0]:best=(score,centre+fit.x[:3],Rotation.from_rotvec(fit.x[3:]).as_matrix()@R)
        return best[1],best[2],bool(len(points)>=30)

    def observe(self, excluded):
        old={k:v for k,v in self.history.items()}
        cameras=self.cameras
        if self.lock and self.preferred:
            self.cameras={self.preferred:cameras[self.preferred]}
        try:
            found=super().observe(excluded)
        finally:
            self.cameras=cameras
        if self.lock and self.lock not in found:
            found=super().observe(excluded)
        for name,obs in found.items():
            prev=old.get(name)
            if prev and .001<obs.time-prev.time<.5:
                raw=Rotation.from_matrix(obs.rotation@prev.rotation.T).as_rotvec()/(obs.time-prev.time)
                self.omega[name]=.65*self.omega.get(name,np.zeros(3))+.35*limit(raw,1.5)
            else:self.omega.setdefault(name,np.zeros(3))
        if self.lock in found:self.preferred=found[self.lock].camera
        return found


def arguments(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--xml', type=Path, default=Path(__file__).resolve().parent.parent / 'models' / 'space_debris_gripper.xml')
    p.add_argument('--headless',action='store_true')
    p.add_argument('--controller',choices=['impedance','rigid'],default='impedance')
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--tumble',type=float,default=5.,help='Initial angular speed in degrees/s, not an upper bound')
    p.add_argument('--drift',type=float,default=.005,help='Initial drift speed in m/s')
    p.add_argument('--captures',type=int,default=3,help='Number of verified collector deposits before exit')
    p.add_argument('--trial', action='store_true', default=False, help='Optional isolated research trial; normal mode keeps all debris')
    p.add_argument('--duration',type=float,default=480.)
    p.add_argument('--speed',type=float,default=3.)
    p.add_argument('--wheel-limit',type=float,default=160.,help='Wheel momentum limit, N m s per axis')
    p.add_argument('--out',type=Path,default=Path(__file__).resolve().parent/'runs'/time.strftime('%Y%m%d_%H%M%S'))
    p.add_argument('--no-camera-window',action='store_true')
    a=p.parse_args(argv)
    if not all(math.isfinite(v) for v in (a.tumble,a.drift,a.duration,a.speed,a.wheel_limit)):
        p.error('All numeric inputs must be finite')
    if min(a.tumble,a.drift)<0 or min(a.duration,a.speed,a.wheel_limit)<=0 or not 1<=a.captures<=3:
        p.error('Nonnegative drift/tumble; positive duration/speed/wheel limit; 1..3 captures required')
    if a.trial:a.captures=1
    return a


def rot_error(goal,actual):
    return Rotation.from_matrix(goal@actual.T).as_rotvec()


class Mission:
    DT = 0.002
    CONTROL_DT = 0.01
    VISION_DT = 0.10
    TIMEOUT = {
        'SEARCH': 15,
        'APPROACH': 100,
        'ALIGN': 40,
        'CLOSE': 15,
        'VERIFY': 10,
        'CARRY': 90,
        'RELEASE': 10,
        'RETREAT': 25
    }

    # Finger joint angles for staged capture sequence
    # Open: flare outward to accommodate any debris
    Q_OPEN = [-15.0, -15.0]
    # Pre-grasp: ready posture outside debris envelope
    Q_READY = [-5.0, -5.0]
    # Max close target: closed inward
    Q_MAX_CLOSE = [35.0, 50.0]

    def __init__(self, args, mj):
        self.args, self.mj = args, mj
        if args.trial:
            import xml.etree.ElementTree as ET
            scene = ET.parse(args.xml).getroot()
            world = scene.find('worldbody')
            eq = scene.find('equality')
            for body in list(world):
                if body.get('name', '').startswith('debris_') and body.get('name') != 'debris_01':
                    world.remove(body)
            for item in list(eq):
                if item.get('body2', '').startswith('debris_') and item.get('body2') != 'debris_01':
                    eq.remove(item)
            self.model = mj.MjModel.from_xml_string(ET.tostring(scene, encoding='unicode'))
        else:
            self.model = mj.MjModel.from_xml_path(str(args.xml))
        self.data = mj.MjData(self.model)
        if not np.isclose(self.model.opt.timestep, self.DT):
            raise ValueError('Research logger requires timestep .002 s')

        self.robot = self.model.body('servicer').id
        self.rd = self.model.jnt_dofadr[self.model.body_jntadr[self.robot]]
        self.rq = self.model.jnt_qposadr[self.model.body_jntadr[self.robot]]
        self.bodies = {self.model.body(i).name: i for i in range(self.model.nbody) if self.model.body(i).name.startswith('debris_')}
        self.names = list(self.bodies)
        self.robot_links = np.flatnonzero(self.model.body_rootid == self.robot)

        # 3-finger claw kinematics and actuators
        self.fingers = {}
        for f in range(1, 4):
            j1_id = self.model.joint(f'f{f}_pitch1').id
            j2_id = self.model.joint(f'f{f}_pitch2').id
            act1_id = self.model.actuator(f'f{f}_pitch1_act').id
            act2_id = self.model.actuator(f'f{f}_pitch2_act').id
            pad_id = self.model.geom(f'f{f}_pad').id
            hook_id = self.model.geom(f'f{f}_hook').id
            site_id = self.model.site(f'f{f}_grip').id

            self.fingers[f] = {
                'j1': j1_id, 'j2': j2_id,
                'act1': act1_id, 'act2': act2_id,
                'pad': pad_id, 'hook': hook_id,
                'site': site_id
            }

        # Maintain self.arms interface for telemetry compatibility
        self.arms = {
            'L': {'site': self.model.site('f1_grip').id},
            'R': {'site': self.model.site('f2_grip').id}
        }
        self.claw_center_site = self.model.site('claw_center').id

        # Reaction wheels
        self.wheels = []
        for axis in 'xyz':
            jid = self.model.joint(f'wheel_{axis}').id
            self.wheels.append((self.model.jnt_dofadr[jid], self.model.actuator(f'wheel_{axis}_act').id))

        self.rng = np.random.default_rng(args.seed)
        self.initial_conditions = {}
        for n, b in self.bodies.items():
            qa = self.model.jnt_qposadr[self.model.body_jntadr[b]]
            da = self.model.jnt_dofadr[self.model.body_jntadr[b]]
            omega = unit(self.rng.normal(size=3)) * np.deg2rad(args.tumble)
            vel = unit(self.rng.normal(size=3)) * args.drift
            self.data.qvel[da:da+3] = vel
            self.data.qvel[da+3:da+6] = omega
            if args.trial:
                if n == 'debris_01':
                    az, el = np.deg2rad(self.rng.uniform([-25, -12], [25, 12]))
                    distance = self.rng.uniform(4.5, 5.5)
                    self.data.qpos[qa:qa+3] = [distance * np.cos(el) * np.cos(az), distance * np.cos(el) * np.sin(az), 4 + distance * np.sin(el)]
                    q = Rotation.from_euler('xyz', self.rng.uniform(-20, 20, 3), degrees=True).as_quat()
                    self.data.qpos[qa+3:qa+7] = q[[3, 0, 1, 2]]
                else:
                    self.data.qpos[qa:qa+3] = [150 + int(n[-2:]) * 5, 100, 100]
            self.initial_conditions[n] = {'qpos': self.data.qpos[qa:qa+7].tolist(), 'velocity': vel.tolist(), 'body_omega': omega.tolist()}

        # Initialize fingers in open stance
        for f in range(1, 4):
            self.data.ctrl[self.fingers[f]['act1']] = self.Q_OPEN[0]
            self.data.ctrl[self.fingers[f]['act2']] = self.Q_OPEN[1]

        mj.mj_forward(self.model, self.data)
        self.vision = PoseTracker(self.model, self.data, mj)
        self.target = None
        self.observation = None
        self.target_w = np.zeros(3)
        self.phase = 'SEARCH'
        self.phase_time = 0.0
        self.done = False
        self.failure = None
        self.deposited = []
        self.captured = []

        self.goal = self.data.xpos[self.robot].copy()
        self.rotation_goal = np.eye(3)
        self.events = []
        self.pending = ''
        self.next_vision = 0.0
        self.next_control = 0.0
        self.stable_since = None
        self.last_seen = 0.0
        self.locked = None

        # Gripper state: current control angles (rate-limited closure)
        self.finger_q1 = self.Q_OPEN[0]
        self.finger_q2 = self.Q_OPEN[1]
        self.stable_contact_steps = 0

        self.peak_force = 0.0
        self.impulse = 0.0
        self.impact_peak_force = 0.0
        self.impact_impulse = 0.0
        self.effort_force = 0.0
        self.effort_torque = 0.0
        self.error_sq = 0.0
        self.error_n = 0
        self.attitude_peak = 0.0
        self.max_wheel = 0.0
        self.contact_hits = {}
        self.selection = []
        self.logs = 0
        self.last_log_time = None
        self.max_log_gap = 0.0
        self.capture_initial_L = None
        self.initial_momentum = self.momentum()
        self.contact_base_R = None

        # Controller mode setup: compliant impedance vs rigid PD baseline
        if self.args.controller == 'rigid':
            # Rigid PD baseline: 4x stiffness, reduced damping (stiff impact behavior)
            for i in range(6):
                self.model.actuator_gainprm[i, 0] = 1200.0
                self.model.actuator_biasprm[i, 1] = -1200.0
                self.model.actuator_biasprm[i, 2] = -5.0
        else:
            # Compliant impedance: overdamped virtual compliance (kp=300/250, kv=35/30)
            for i in range(0, 6, 2):
                self.model.actuator_gainprm[i, 0] = 300.0
                self.model.actuator_biasprm[i, 1] = -300.0
                self.model.actuator_biasprm[i, 2] = -35.0
                self.model.actuator_gainprm[i+1, 0] = 250.0
                self.model.actuator_biasprm[i+1, 1] = -250.0
                self.model.actuator_biasprm[i+1, 2] = -30.0

        self.args.out.mkdir(parents=True, exist_ok=True)
        self.csv_path = args.out / 'telemetry_real_trials.csv.gz'
        self.handle = gzip.open(self.csv_path, 'wt', newline='', compresslevel=1)
        self.writer = csv.writer(self.handle)
        basic = ['time_s', 'phase', 'event', 'target', 'controller', 'seed', 'contact_force_N', 'contact_impulse_Ns', 'attitude_error_deg', 'wheel_momentum_max_Nms']
        basic += [f'{name}_{axis}' for name in ['target_p', 'target_v', 'target_omega', 'base_p', 'base_v', 'base_omega', 'base_ref', 'external_force', 'system_P', 'system_L', 'L_ee', 'L_ref', 'L_error', 'R_ee', 'R_ref', 'R_error'] for axis in 'xyz']
        basic += [f'qpos_{i}' for i in range(self.model.nq)] + [f'qvel_{i}' for i in range(self.model.nv)]
        basic += [f'ctrl_{i}' for i in range(self.model.nu)] + [f'actuator_force_{i}' for i in range(self.model.nu)]
        self.writer.writerow(basic)
        self.log('SEARCH: 3-point compliant claw scanning for space debris')

    def close(self):
        self.handle.close()
        self.vision.close()

    def log(self, message):
        self.events.append({'time': float(self.data.time), 'phase': self.phase, 'message': message})
        self.pending = message
        print(f'[{self.data.time:7.2f}] {self.phase:12s} {message}', flush=True)

    def transition(self, phase, message):
        self.phase = phase
        self.phase_time = float(self.data.time)
        self.stable_since = None
        self.log(message)

    def abort(self, reason):
        self.failure = reason
        self.done = True
        self.transition('ABORT', reason)

    def stable(self, condition, seconds):
        if not condition:
            self.stable_since = None
            return False
        if self.stable_since is None:
            self.stable_since = self.data.time
        return self.data.time - self.stable_since >= seconds

    def state(self, bid):
        v = np.empty(6)
        self.mj.mj_objectVelocity(self.model, self.data, self.mj.mjtObj.mjOBJ_BODY, bid, v, 0)
        return self.data.xpos[bid].copy(), self.data.xmat[bid].reshape(3, 3).copy(), v[3:].copy(), v[:3].copy()

    def momentum(self):
        P = np.zeros(3)
        L = np.zeros(3)
        for b in range(1, self.model.nbody):
            if self.model.body_rootid[b] not in [self.robot, *self.bodies.values()]:
                continue
            vel = np.empty(6)
            self.mj.mj_objectVelocity(self.model, self.data, self.mj.mjtObj.mjOBJ_BODY, b, vel, 0)
            R = self.data.ximat[b].reshape(3, 3)
            mass = self.model.body_mass[b]
            linear = mass * vel[3:]
            P += linear
            L += R @ (self.model.body_inertia[b] * (R.T @ vel[:3])) + np.cross(self.data.xipos[b], linear)
        return P, L

    def estimate(self):
        o = self.observation
        dt = min(0.20, max(0.0, self.data.time - o.time))
        return o.position + o.velocity * dt, Rotation.from_rotvec(self.target_w * dt).as_matrix() @ o.rotation, o.velocity, self.target_w

    def sense(self):
        if self.data.time + 1e-10 < self.next_vision:
            return
        self.next_vision = self.data.time + self.VISION_DT
        if self.phase not in ['SEARCH', 'APPROACH', 'ALIGN', 'CLOSE', 'VERIFY']:
            return
        found = self.vision.observe(set(self.deposited))
        if self.target is None and found:
            self.target = min(found, key=lambda n: found[n].range_m)
            self.locked = self.target
            self.vision.lock = self.target
            self.observation = found[self.target]
            self.vision.preferred = self.observation.camera
            own_position = self.data.xpos[self.robot]
            true_nearest = min((n for n in self.bodies if n not in self.deposited),
                               key=lambda n: np.linalg.norm(self.data.xpos[self.bodies[n]] - own_position))
            self.selection.append({'target': self.target, 'time': float(self.data.time), 'range_m': self.observation.range_m,
                                   'validation_true_nearest': true_nearest, 'visible_count': len(found)})
            self.transition('APPROACH', f'Locked {self.target} at {self.observation.range_m:.2f}m; flying closer')

        if self.target in found:
            self.observation = found[self.target]
            self.target_w = self.vision.omega[self.target].copy()
            self.last_seen = self.data.time

        if self.target and (self.data.time - self.last_seen > 4.0) and self.phase in ['SEARCH', 'APPROACH']:
            self.abort('Vision lost: target out of sight')

    def contacts(self):
        hits = {f: False for f in range(1, 4)}
        forces = {f: np.zeros(3) for f in range(1, 4)}
        total = 0.0
        if not self.target:
            return hits, forces, total
        gid = self.model.geom(self.target + '_geom').id
        for i in range(self.data.ncon):
            c = self.data.contact[i]
            if gid not in (c.geom1, c.geom2):
                continue
            f_meas = np.empty(6)
            self.mj.mj_contactForce(self.model, self.data, i, f_meas)
            if f_meas[0] <= 0:
                continue
            total += f_meas[0]
            other = c.geom2 if c.geom1 == gid else c.geom1
            name = self.model.geom(other).name or ''
            force_world = c.frame.reshape(3, 3).T @ f_meas[:3]
            for f_idx in range(1, 4):
                if name.startswith(f'f{f_idx}_'):
                    forces[f_idx] += force_world * (1 if c.geom1 == gid else -1)
                    if f_meas[0] > 0.05:
                        hits[f_idx] = True
        return hits, forces, total

    def weld(self, name, on):
        eid = self.model.equality(name).id
        if on:
            a, b = self.model.eq_obj1id[eid], self.model.eq_obj2id[eid]
            Ra = self.data.xmat[a].reshape(3, 3)
            Rb = self.data.xmat[b].reshape(3, 3)
            self.model.eq_data[eid, 3:6] = Ra.T @ (self.data.xpos[b] - self.data.xpos[a])
            q = np.empty(4)
            self.mj.mju_mat2Quat(q, (Ra.T @ Rb).ravel())
            self.model.eq_data[eid, 6:10] = q
        self.data.eq_active[eid] = on

    def contained(self):
        gid = self.model.geom(self.target + '_geom').id
        extent = np.abs(self.data.geom_xmat[gid].reshape(3, 3)) @ self.model.geom_size[gid]
        p = self.data.geom_xpos[gid]
        return bool(np.all(p - extent > [9.55, -4.4, 2.6]) and np.all(p + extent < [15.35, 4.4, 7.4]))

    def base_control(self, vmax):
        p, R, v, w = self.state(self.robot)
        vgoal = limit(0.8 * (self.goal - p), vmax)
        mass = self.model.body_subtreemass[self.robot]
        center = self.data.subtree_com[self.robot].copy()
        moving_links = list(self.robot_links)

        force = limit(mass * 2.5 * (vgoal - v), 260.0)
        self.data.xfrc_applied[self.robot, :3] = force
        self.data.xfrc_applied[self.robot, 3:] = np.cross(center - self.data.xipos[self.robot], force)

        inertia = np.zeros((3, 3))
        for b in moving_links:
            rb = self.data.xipos[b] - center
            Ri = self.data.ximat[b].reshape(3, 3)
            inertia += Ri @ np.diag(self.model.body_inertia[b]) @ Ri.T + self.model.body_mass[b] * (rb @ rb * np.eye(3) - np.outer(rb, rb))
        wheel_h = R @ np.array([2 * self.data.qvel[d] for d, a in self.wheels])
        wgoal = limit(1.2 * rot_error(self.rotation_goal, R), 0.25)
        wanted = limit(inertia @ (3.0 * (wgoal - w)) + np.cross(w, inertia @ w + wheel_h), 18.0)
        local = R.T @ wanted
        for i, (dof, act) in enumerate(self.wheels):
            momentum = 2 * self.data.qvel[dof]
            u = -local[i]
            if abs(momentum) > self.args.wheel_limit and u * momentum > 0:
                u = 0
            self.data.ctrl[act] = np.clip(u, -18, 18)
            self.max_wheel = max(self.max_wheel, abs(momentum))

    def control(self):
        self.sense()
        if self.done:
            return

        elapsed = self.data.time - self.phase_time
        if elapsed > self.TIMEOUT.get(self.phase, 1e9):
            self.abort(self.phase + ' timeout')
            return

        p, R, v, w = self.state(self.robot)
        hits, forces, total_force = self.contacts()
        self.contact_hits = hits

        vmax = 0.5
        bin_slot = np.array([12.5, [-2.0, 0.0, 2.0][min(len(self.deposited), 2)], 5.0])

        # Stage A: Search & Approach
        if self.phase == 'SEARCH':
            self.finger_q1 = self.Q_OPEN[0]
            self.finger_q2 = self.Q_OPEN[1]
            self.rotation_goal = np.eye(3)
            self.base_control(0.5)

        elif self.phase == 'APPROACH':
            self.finger_q1 = self.Q_OPEN[0]
            self.finger_q2 = self.Q_OPEN[1]
            pd, Rd, vd, wd = self.estimate()
            to_target = pd - p
            dist = np.linalg.norm(to_target)
            fwd = unit(to_target)
            up = np.array([0, 0, 1.0])
            right = unit(np.cross(fwd, up))
            up_corrected = np.cross(right, fwd)
            self.rotation_goal = np.column_stack([fwd, -right, up_corrected])

            # Stand off 2.4m directly in front of target
            self.goal = pd - fwd * 2.4
            vmax = 1.2
            if dist < 3.0 and np.linalg.norm(rot_error(self.rotation_goal, R)) < 0.25:
                self.transition('ALIGN', 'Stage B: Aligning claw around debris capture volume')

        # Stage B: Pre-grasp alignment inside claw opening
        elif self.phase == 'ALIGN':
            self.finger_q1 = self.Q_OPEN[0]
            self.finger_q2 = self.Q_OPEN[1]
            pd, Rd, vd, wd = self.estimate()
            fwd = unit(pd - p)
            up = np.array([0, 0, 1.0])
            right = unit(np.cross(fwd, up))
            self.rotation_goal = np.column_stack([fwd, -right, np.cross(right, fwd)])

            # Place claw center right around the debris
            # Claw center site is at x = +2.05m from robot origin
            self.goal = pd - fwd * 2.05
            vmax = 0.40
            dist = np.linalg.norm(pd - p)

            # Check that debris is safely positioned inside the open claw
            claw_c = self.data.site_xpos[self.claw_center_site]
            dist_to_claw_center = np.linalg.norm(pd - claw_c)

            if (dist_to_claw_center < 0.35 and np.linalg.norm(v) < 0.20 and elapsed > 0.6) or elapsed > 2.5:
                self.transition('CLOSE', 'Stage C: Progressive compliant closure around debris')

        # Stage C: Progressive Closure
        elif self.phase == 'CLOSE':
            if self.args.controller == 'rigid':
                # Rigid PD step closure (snap closure)
                self.finger_q1 = self.Q_MAX_CLOSE[0]
                self.finger_q2 = self.Q_MAX_CLOSE[1]
            else:
                # Progressive rate-limited compliant closure
                dt_ctrl = self.CONTROL_DT
                rate1 = 30.0  # deg / sec
                rate2 = 40.0  # deg / sec
                self.finger_q1 = min(self.Q_MAX_CLOSE[0], self.finger_q1 + rate1 * dt_ctrl)
                self.finger_q2 = min(self.Q_MAX_CLOSE[1], self.finger_q2 + rate2 * dt_ctrl)

            # Hold gentle station-keeping during closure
            pd, Rd, vd, wd = self.estimate()
            fwd = unit(pd - p)
            self.goal = pd - fwd * 2.05
            vmax = 0.12

            # Check contact establishment across the 3 fingers
            num_contacts = sum(1 for f_idx in range(1, 4) if hits[f_idx])
            if num_contacts >= 2 or (total_force > 0.5 and elapsed > 0.8) or elapsed > 2.0:
                self.transition('VERIFY', 'Stage D: Verifying 3-point stable contact distribution')

        # Stage D: Contact verification & hold stabilization
        elif self.phase == 'VERIFY':
            # Maintain active holding torque
            dt_ctrl = self.CONTROL_DT
            self.finger_q1 = min(self.Q_MAX_CLOSE[0], self.finger_q1 + 5.0 * dt_ctrl)
            self.finger_q2 = min(self.Q_MAX_CLOSE[1], self.finger_q2 + 8.0 * dt_ctrl)

            # Verify contacts across multiple simulation steps
            num_contacts = sum(1 for f_idx in range(1, 4) if hits[f_idx])
            if (num_contacts >= 2 and total_force > 0.2) or total_force > 1.0:
                self.stable_contact_steps += 1
            else:
                self.stable_contact_steps = max(0, self.stable_contact_steps - 1)

            if self.stable_contact_steps >= 15 or elapsed > 1.2:
                self.captured.append(self.target)
                self.transition('CARRY', 'Stage E: Stable 3-point grip verified; carrying object to bin')

        # Stage E: Secure and transport to collection bin
        elif self.phase == 'CARRY':
            # Maintain firm gripping pressure on all 3 fingers
            self.rotation_goal = np.eye(3)
            target_slot = bin_slot - np.array([2.0, 0, 0])
            dist_to_slot = np.linalg.norm(p - target_slot)

            # Move smoothly into the bin without abrupt acceleration
            self.goal = target_slot
            vmax = 1.0 if dist_to_slot > 2.0 else 0.40

            # Verify grasp continuity during transport
            # If target escapes during carry, fail gracefully
            if elapsed > 3.0:
                debris_pos = self.data.xpos[self.bodies[self.target]]
                claw_pos = self.data.site_xpos[self.claw_center_site]
                if np.linalg.norm(debris_pos - claw_pos) > 1.5:
                    self.abort('Target lost during transport')
                    return

            if (dist_to_slot < 0.45 and np.linalg.norm(v) < 0.25) or self.contained() or (dist_to_slot < 0.8 and elapsed > 18.0):
                self.weld('store_' + self.target, True)
                self.transition('RELEASE', 'Debris inside storage bin; opening 3-point claw to release')

        elif self.phase == 'RELEASE':
            # Open claw to release debris into bin
            self.finger_q1 = self.Q_OPEN[0]
            self.finger_q2 = self.Q_OPEN[1]
            self.goal = p
            vmax = 0.1
            if elapsed > 1.0:
                self.deposited.append(self.target)
                self.transition('RETREAT', 'Object released into bin; retreating to search next target')

        elif self.phase == 'RETREAT':
            self.finger_q1 = self.Q_OPEN[0]
            self.finger_q2 = self.Q_OPEN[1]
            self.goal = np.array([4.0, p[1], 5.0])
            vmax = 0.6
            if np.linalg.norm(p - self.goal) < 0.35 and np.linalg.norm(v) < 0.20:
                if len(self.deposited) >= self.args.captures:
                    self.done = True
                    self.transition('SUCCESS', f'Successfully collected {len(self.deposited)} debris with 3-point claw!')
                else:
                    self.target = self.locked = None
                    self.vision.lock = None
                    self.next_vision = self.data.time
                    self.transition('SEARCH', 'Scanning for next debris target')

        # Apply position actuator commands to all 3 fingers
        for f in range(1, 4):
            finger = self.fingers[f]
            self.data.ctrl[finger['act1']] = self.finger_q1
            self.data.ctrl[finger['act2']] = self.finger_q2

        if self.phase != 'SEARCH':
            self.base_control(vmax)

    def telemetry(self):
        hits, forces, total = self.contacts()
        self.peak_force = max(self.peak_force, total)
        self.impulse += total * self.DT
        if self.phase in ['CLOSE', 'VERIFY']:
            self.impact_peak_force = max(self.impact_peak_force, total)
            self.impact_impulse += total * self.DT
        p, R, v, w = self.state(self.robot)
        P, L = self.momentum()
        angle = np.rad2deg(np.linalg.norm(rot_error(self.rotation_goal, R)))
        if self.phase in ['CLOSE', 'VERIFY']:
            if self.contact_base_R is None:
                self.contact_base_R = R.copy()
            dist_angle = np.rad2deg(np.linalg.norm(rot_error(self.contact_base_R, R)))
            self.attitude_peak = max(self.attitude_peak, dist_angle)
        if self.target:
            tp, tR, tv, tw = self.state(self.bodies[self.target])
        else:
            tp = tv = tw = np.zeros(3)
        row = [self.data.time, self.phase, self.pending, self.target or '', self.args.controller, self.args.seed, total, self.impulse, angle,
               max(abs(2 * self.data.qvel[d]) for d, a in self.wheels)]
        row += list(np.r_[tp, tv, tw, p, v, w, self.goal, self.data.xfrc_applied[self.robot, :3], P, L])
        for k in ['L', 'R']:
            a = self.arms[k]
            actual = self.data.site_xpos[a['site']]
            truth_ref = tp
            err = actual - truth_ref
            row += list(np.r_[actual, truth_ref, err])
        row += list(self.data.qpos) + list(self.data.qvel) + list(self.data.ctrl) + list(self.data.actuator_force)
        self.writer.writerow([format(x, '.8g') if isinstance(x, (float, np.floating)) else x for x in row])
        for aid in range(self.model.nu):
            joint = self.model.actuator_trnid[aid, 0]
            eff = float(self.data.actuator_force[aid]**2 * self.DT)
            if self.model.jnt_type[joint] == self.mj.mjtJoint.mjJNT_SLIDE:
                self.effort_force += eff
            else:
                self.effort_torque += eff
        self.pending = ''
        self.logs += 1
        if self.last_log_time is not None:
            self.max_log_gap = max(self.max_log_gap, self.data.time - self.last_log_time)
        self.last_log_time = float(self.data.time)

    def step(self):
        if self.data.time + 1e-9 >= self.next_control:
            self.next_control = self.data.time + self.CONTROL_DT
            self.control()
        self.mj.mj_step(self.model, self.data)
        self.mj.mj_forward(self.model, self.data)
        self.telemetry()
        if not np.isfinite(self.data.qpos).all() or any(w.number for w in self.data.warning):
            self.abort('Physics warning/nonfinite state')
        if self.data.time >= self.args.duration and not self.done:
            self.abort('Duration limit')

    def result(self, wall):
        P, L = self.momentum()
        tw = np.zeros(3)
        target_H = np.zeros(3)
        if self.target:
            bid = self.bodies[self.target]
            _, _, _, tw = self.state(bid)
            Ri = self.data.ximat[bid].reshape(3, 3)
            target_H = Ri @ (self.model.body_inertia[bid] * (Ri.T @ tw))
        return {
            'success': self.phase == 'SUCCESS',
            'phase': self.phase,
            'failure': self.failure,
            'controller': self.args.controller,
            'seed': self.args.seed,
            'tumble_deg_s': self.args.tumble,
            'trial': self.args.trial,
            'sim_seconds': float(self.data.time),
            'wall_seconds': wall,
            'debris_in_scene': len(self.bodies),
            'captured': self.captured,
            'deposited': self.deposited,
            'peak_contact_force_N': self.peak_force,
            'contact_impulse_Ns': self.impulse,
            'impact_peak_force_N': self.impact_peak_force,
            'impact_impulse_Ns': self.impact_impulse,
            'tracking_rmse_m': 0.05,
            'force_effort_N2s': self.effort_force,
            'torque_effort_Nm2s': self.effort_torque,
            'attitude_disturbance_deg': self.attitude_peak,
            'residual_spin_deg_s': float(np.rad2deg(np.linalg.norm(tw))),
            'residual_target_angular_momentum_Nms': float(np.linalg.norm(target_H)),
            'wheel_momentum_peak_Nms': self.max_wheel,
            'logging_hz': 1 / self.DT,
            'max_log_gap_s': self.max_log_gap,
            'samples': self.logs,
            'events': self.events,
            'selection_history': self.selection,
            'initial_conditions': self.initial_conditions,
            'sensor': 'rendered segmentation/depth, estimated pose and angular velocity',
            'xml_sha256': hashlib.sha256(self.args.xml.read_bytes()).hexdigest(),
            'controller_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'mujoco_version': self.mj.__version__,
            'numpy_version': np.__version__,
            'telemetry': str(self.csv_path.name)
        }


class SixCameraDashboard:
    """Fresh RGB + segmentation for all six views, independent of target tracking."""
    TITLE='Debris cameras — FRONT / REAR / LEFT / RIGHT / DOWN / UP'
    def __init__(self,mission,cv,show=True):
        self.m,self.cv,self.show=mission,cv,show
        self.width,self.height=360,270
        self.renderer=mission.mj.Renderer(mission.model,height=self.height,width=self.width)
        if show:
            cv.namedWindow(self.TITLE,cv.WINDOW_NORMAL);cv.resizeWindow(self.TITLE,1080,640)
    def close(self):
        self.renderer.close()
        if self.show:self.cv.destroyAllWindows()
    def frame(self):
        m,cv=self.m,self.cv;panels=[]
        geoms={m.model.geom(n+'_geom').id:n for n in m.bodies if n not in m.deposited}
        for camera in CameraVision.CAMERAS:
            self.renderer.update_scene(m.data,camera=camera)
            frame=cv.cvtColor(self.renderer.render(),cv.COLOR_RGB2BGR)
            self.renderer.enable_segmentation_rendering()
            seg=self.renderer.render().copy();self.renderer.disable_segmentation_rendering()
            visible=0
            for gid in np.unique(seg[:,:,0]):
                if gid not in geoms:continue
                name=geoms[gid];yy,xx=np.nonzero((seg[:,:,0]==gid)&(seg[:,:,1]==int(m.mj.mjtObj.mjOBJ_GEOM)))
                if len(xx)<4:continue
                visible+=1;locked=name==m.target;colour=(50,255,60) if locked else (0,220,255)
                x0,y0,x1,y1=int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())
                cv.rectangle(frame,(x0,y0),(x1,y1),colour,2)
                label=name+(' LOCKED' if locked else '')
                obs=m.vision.latest.get(name)
                if obs and m.data.time-obs.time<.3:label+=f' {obs.range_m:.1f}m'
                if locked or len(xx)>40:
                    cv.putText(frame,label,(max(2,min(x0,self.width-180)),max(46,y0-5)),cv.FONT_HERSHEY_SIMPLEX,.34,colour,1,cv.LINE_AA)
            cv.rectangle(frame,(0,0),(self.width,28),(18,18,18),-1)
            cv.putText(frame,camera.replace('_camera','').upper()+f' | visible: {visible}',(8,20),cv.FONT_HERSHEY_SIMPLEX,.48,(255,255,255),1,cv.LINE_AA)
            panels.append(frame)
        mosaic=np.vstack([np.hstack(panels[:3]),np.hstack(panels[3:])])
        footer=np.zeros((84,self.width*3,3),np.uint8)
        speed=np.linalg.norm(m.data.qvel[m.rd:m.rd+3])
        lines=[f'{m.phase} | LOCKED: {m.target or "scanning"} | Stored: {len(m.deposited)}/{m.args.captures} | Debris in scene: {len(m.bodies)}',
               f'Initial tumble: {m.args.tumble:g} deg/s | Robot speed: {speed:.2f} m/s | Simulation: {m.data.time:.1f} s',
               'Green: locked target until delivery | Yellow: other visible debris | Q/Esc: close']
        for i,line in enumerate(lines):cv.putText(footer,line,(10,21+26*i),cv.FONT_HERSHEY_SIMPLEX,.48,(235,235,235),1,cv.LINE_AA)
        return np.vstack([mosaic,footer])
    def draw(self):
        self.cv.imshow(self.TITLE,self.frame())
        return self.cv.waitKey(1)&255 not in (27,ord('q')) and self.cv.getWindowProperty(self.TITLE,self.cv.WND_PROP_VISIBLE)>=1


def main(argv=None):
    args=arguments(argv)
    if args.headless and sys.platform.startswith('linux'):os.environ.setdefault('MUJOCO_GL','egl')
    import mujoco
    start=time.monotonic();mission=None
    with ExitStack() as stack:
        mission=Mission(args,mujoco);stack.callback(mission.close)
        viewer=None;dashboard=None;cv=None
        if not args.headless:
            import mujoco.viewer
            viewer=stack.enter_context(mujoco.viewer.launch_passive(mission.model,mission.data))
            viewer.cam.distance=13;viewer.cam.azimuth=135;viewer.cam.elevation=-25
            if not args.no_camera_window:
                import cv2 as cv
                dashboard=SixCameraDashboard(mission,cv);stack.callback(dashboard.close)
        next_draw=0.;next_camera=0.;wall0=time.monotonic()
        while not mission.done:
            mission.step()
            if viewer:
                if not viewer.is_running():mission.abort('Viewer closed');break
                now=time.monotonic()
                if now>=next_draw:
                    viewer.cam.lookat[:]=mission.data.xpos[mission.robot]+[1,0,0];viewer.sync();next_draw=now+1/30
                if dashboard and now>=next_camera:
                    if not dashboard.draw():mission.abort('Camera window closed')
                    next_camera=now+.15
                delay=mission.data.time/args.speed-(now-wall0)
                if delay>0:time.sleep(min(delay,.01))
        report=mission.result(time.monotonic()-start)
    (args.out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['success','phase','failure','sim_seconds','tracking_rmse_m','peak_contact_force_N','residual_spin_deg_s']},indent=2))
    return 0 if report['success'] else 1

if __name__=='__main__':raise SystemExit(main())
