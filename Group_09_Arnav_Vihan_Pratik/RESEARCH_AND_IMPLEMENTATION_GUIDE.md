# Research and Implementation Guide: Autonomous Hazardous Terrain UGV

## Project: MDRIIA Group 09
## Target Venue: IEEE SSRR / IEEE CASE / AIR Conference Track

---

## 1. Mathematical and Algorithmic Formulation

### 1.1 Skid-Steer Kinematics and Instantaneous Centers of Rotation (ICR)
Skid-steer mobile robots turn through differential wheel velocities, introducing unavoidable lateral tire slippage. In the local coordinate frame, the kinematic equations are governed by the positions of the lateral Instantaneous Centers of Rotation $x_{ICR}, y_{ICR}$:

$$\begin{bmatrix} v_x \\ v_y \\ \omega_z \end{bmatrix} = \begin{bmatrix} 0 & \frac{r}{2} & \frac{r}{2} \\ 0 & 0 & 0 \\ 0 & -\frac{r}{2 y_{ICR}} & \frac{r}{2 y_{ICR}} \end{bmatrix} \begin{bmatrix} 1 \\ \omega_L \\ \omega_R \end{bmatrix}$$

where $r$ is wheel radius, and $\omega_L, \omega_R$ are the left and right wheel angular velocities.

### 1.2 2.5D Elevation Mapping and Traversability Cost Formulation
The environment is discretized into a 2.5D grid $G(x, y)$ with cell resolution $\Delta c = 0.10$ m. Each cell stores mean elevation $\mu_z(x, y)$ and elevation variance $\sigma_z^2(x, y)$. Traversability cost $C_{\text{trav}}(x, y) \in [0, 1]$ is evaluated using three normalized geometric metrics:

1. **Slope Inclination Metric ($S$):** Evaluated from the surface normal vector $\mathbf{n} = [n_x, n_y, n_z]^T$:
   $$\theta_{\text{slope}} = \arccos(n_z), \quad S = \min\left(1.0, \frac{\theta_{\text{slope}}}{\theta_{\max}}\right)$$

2. **Surface Roughness Metric ($R$):** Residual standard deviation of points from the best-fit plane:
   $$R = \min\left(1.0, \frac{\sigma_{\text{plane}}}{\sigma_{\max}}\right)$$

3. **Step Height Metric ($H$):** Maximum elevation difference between adjacent neighboring cells:
   $$H = \min\left(1.0, \frac{\Delta z_{\max}}{h_{\text{clearance}}}\right)$$

The composite traversability cost is:
$$C_{\text{trav}}(x, y) = w_S \cdot S + w_R \cdot R + w_H \cdot H$$

Cells with $C_{\text{trav}} \ge 0.70$ are classified as non-traversable lethal obstacles.

### 1.3 Operator Cognitive Workload (NASA-TLX) & Communication Latency
Under manual teleoperation with round-trip network delay $\tau_{\text{lat}}$, operator performance degrades exponentially. Cognitive workload $W_{\text{TLX}} \in [0, 100]$ is modeled as:

$$W_{\text{TLX}}(\tau_{\text{lat}}, C_{\text{autonomy}}) = W_{\text{base}} \cdot (1 + \alpha \tau_{\text{lat}}) \cdot (1 - \beta C_{\text{autonomy}})$$

where $C_{\text{autonomy}} \in [0, 1]$ represents the level of shared autonomy (where the UGV automatically overrides operator commands heading toward hazardous high-cost cells).

### 1.4 CSBS Industrial Risk Mitigation Economics
Safety economics are evaluated through dimensionless operational cost parity $\kappa$:

$$\kappa = \frac{\text{OpEx}_{\text{ugv}}}{\text{OpEx}_{\text{human\_entry}}} = \frac{C_{\text{energy}} + C_{\text{maintenance}} + C_{\text{remote\_pilot}}}{C_{\text{hazmat\_gear}} + C_{\text{human\_risk\_insurance}} + C_{\text{safety\_crews}}}$$

The capital amortization payback horizon in operational months is:

$$\text{Payback Months} = \frac{K_{\text{capex}}}{1 - \kappa} \times 12$$

---

## 2. Individual Student Work Boundaries & Responsibilities

```
===================================================================================================
Student Roll & Name        Assigned Technical Module                       Primary Deliverable
===================================================================================================
E064 - Arnav Saurabh Surve UGV Skid-Steer Dynamics & MuJoCo Terrain        models/hazardous_terrain_ugv.xml
                                                                           (Multi-Body Physics & Incline)
E070 - Vihan Shripad Joshi LiDAR Rangefinder & Traversability Cost Mapping src/rough_terrain_recon_controller.py
                                                                           (Raycasting & Cost Grid Engine)
E073 - Pratik Mangesh Gaikwad CSBS Safety, Shared Autonomy & Workload      analytics/hazardous_recon_economics.py
                                                                           (NASA-TLX & Latency Economics)
===================================================================================================
```

### 2.1 E064 - Arnav Saurabh Surve (UGV Skid-Steer Dynamics)
- Formulate the 4-wheel skid-steer chassis, suspension damping, and contact friction parameters in `hazardous_terrain_ugv.xml`.
- Implement skid-steer kinematics and wheel slip dynamics under tilted pitch/roll angles.
- **Git Branch:** `feat/e064-lead-ugv-skid-steer-`

### 2.2 E070 - Vihan Shripad Joshi (LiDAR & Traversability Mapping)
- Implement multi-channel LiDAR raycast sensor simulation in Python.
- Develop the 2.5D elevation grid and multi-metric traversability cost function ($S, R, H$).
- **Git Branch:** `feat/e070-lidar-perception-3d-`

### 2.3 E073 - Pratik Mangesh Gaikwad (Shared Autonomy & Safety Economics)
- Implement the teleoperation latency simulator (50 ms to 1200 ms delay buffer).
- Implement the shared autonomy collision avoidance override logic.
- Conduct NASA-TLX cognitive workload evaluations and dimensionless economic payback modeling.
- **Git Branch:** `feat/e073-csbs-hazardous-opera`

---

## 3. Step-by-Step Implementation Roadmap

1. **Sprint 0: Setup & Verification**
   - Run `python src/test_env.py` to confirm scientific packages and MuJoCo simulation environment.
   - Inspect `models/hazardous_terrain_ugv.xml` in MuJoCo viewer.
2. **Sprint 1: Skid-Steer Locomotion & Pitch/Roll Limits**
   - Drive the UGV across sloped obstacles and record wheel slippage.
   - Verify that center-of-mass prevents tip-over up to 28-degree inclines.
3. **Sprint 2: LiDAR Raycasting & Traversability Cost Grid**
   - Run `python src/rough_terrain_recon_controller.py` to produce real-time traversability maps.
   - Verify obstacle boundary inflation around impassable rubble.
4. **Sprint 3: Benchmarking and Economics Simulation**
   - Run `python analytics/generate_paper_figures.py` to produce benchmark CSV and 300 DPI figures.
   - Run `python analytics/hazardous_recon_economics.py` to evaluate safety economics.
5. **Sprint 4: Paper Preparation & Git Push**
   - Draft manuscript sections using `docs/RESEARCH_PAPER_MANUSCRIPT_BLUEPRINT.md`.
   - Run compliance audit script before final commit and push.
