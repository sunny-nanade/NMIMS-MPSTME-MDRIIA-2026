"""Free-body diagram of the SkyHydro UAV + slung canister (docs/figures/fig_fbd.png)."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Rectangle, Circle, Arc
import numpy as np

fig, ax = plt.subplots(figsize=(3.6, 3.4))
ax.set_xlim(-3.2, 3.6); ax.set_ylim(-6.4, 2.2); ax.set_aspect("equal"); ax.axis("off")


def arrow(x0, y0, x1, y1, txt, col="k", dx=0.08, dy=0.08, ha="left"):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=11, lw=1.4, color=col))
    ax.text(x1 + dx, y1 + dy, txt, color=col, fontsize=8, ha=ha)


# airframe (tilted into the wind by phi)
phi = np.radians(-12)
R = np.array([[np.cos(phi), -np.sin(phi)], [np.sin(phi), np.cos(phi)]])
body = np.array([[-1.2, 0], [1.2, 0]]) @ R.T
ax.plot(body[:, 0], body[:, 1], color="#333", lw=4, solid_capstyle="round")
ax.add_patch(Circle((0, 0), 0.22, color="#34495e"))
for s in (-1, 1):
    p = np.array([s * 1.05, 0.08]) @ R.T
    ax.plot([p[0] - 0.4, p[0] + 0.4], [p[1] - 0.4 * np.tan(phi), p[1] + 0.4 * np.tan(phi)], color="#888", lw=2)
    zb = np.array([0, 1.15]) @ R.T
    arrow(p[0], p[1] + 0.05, p[0] + zb[0], p[1] + zb[1], "T₂,T₃" if s < 0 else "T₁,T₄", "#1f6fb4")
arrow(0.35, -0.2, 0.35, -1.2, "m_u g", "#444", dx=0.1, dy=0.1)
arrow(2.9, 0.15, 1.55, 0.15, "F_d,u", "#c0392b", dx=-0.2, dy=0.12, ha="right")
ax.text(2.25, 1.0, "wind  v_w", color="#c0392b", fontsize=8)
ax.add_patch(FancyArrowPatch((3.3, 0.85), (2.25, 0.85), arrowstyle="-|>", mutation_scale=10, color="#c0392b", lw=1))

# cable + canister swung downwind (wind from +x to -x in the sketch)
th = np.radians(14)
L = 4.2
px, py = -L * np.sin(th), -0.3 - L * np.cos(th)
ax.plot([0, px], [-0.3, py], color="#777", lw=1.4)
ax.plot([0, 0], [-0.3, -0.3 - 1.6], color="#aaa", lw=0.8, ls="--")
ax.add_patch(Arc((0, -0.3), 2.4, 2.4, theta1=-90 - 14, theta2=-90, color="k", lw=0.8))
ax.text(-0.42, -1.85, "θ", fontsize=9)
ax.add_patch(Rectangle((px - 0.3, py - 0.42), 0.6, 0.6, color="#e74c3c"))
arrow(px, py - 0.42, px, py - 1.4, "m_p g", "#444", dx=0.1, dy=0.0)
arrow(px + 1.3, py - 0.12, px + 0.32, py - 0.12, "F_d,p", "#c0392b", dx=0.1, dy=0.12)
cdir = np.array([0 - px, -0.3 - py]); cdir /= np.linalg.norm(cdir)
arrow(px + 0.05, py + 0.2, px + 0.05 + 1.0 * cdir[0], py + 0.2 + 1.0 * cdir[1], "T_c", "#7d3c98", dx=0.08, dy=-0.05)
ax.text(-3.1, 1.85, "UAV + slung canister (hover in crosswind)", fontsize=8, weight="bold")
ax.text(-3.1, -6.3, "tan θ = F_d,p / (m_p g),   F_d = ½ ρ C_dA v²", fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fig_fbd.png"), dpi=220)
