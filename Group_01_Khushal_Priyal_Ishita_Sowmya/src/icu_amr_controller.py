"""
Autonomous ICU Medicine Delivery AMR Simulation & Telemetry Logger
Conforming to ISO 13482:2014 & ISO 3691-4:2023 Safety Standards.
Group 01 - B.Tech CSBS MDRIIA
"""
import math
import csv

def run_simulation(duration_sec=10.0, output_csv="icu_amr_telemetry.csv"):
    print("[MDRIIA Group 01] Running ICU Medicine Delivery AMR simulation...")
    wheel_radius = 0.10
    track_width = 0.50
    max_linear_vel = 0.80
    max_lateral_acc = 0.40
    dt = 0.01

    x, y, theta = -5.0, 0.0, 0.0
    v, w = 0.0, 0.0
    obstacles = [(3.0, 0.5, 0.6), (6.5, -0.6, 0.5)]
    target_x, target_y = 5.5, 0.0

    records = []
    t = 0.0
    while t < duration_sec:
        dx, dy = target_x - x, target_y - y
        dist = math.hypot(dx, dy)
        if dist < 0.25:
            print(f"[Docked] Mission complete at t = {t:.2f}s")
            break
        target_h = math.atan2(dy, dx)
        h_err = math.atan2(math.sin(target_h - theta), math.cos(target_h - theta))
        d_obs = min([math.hypot(ox - x, oy - y) - orad for (ox, oy, orad) in obstacles] + [10.0])
        
        fsm = "CRUISE"
        if d_obs < 1.2:
            fsm = "OBSTACLE_AVOIDANCE"
            v_cmd, w_cmd = 0.35, (-0.75 if y >= 0 else 0.75)
        else:
            v_cmd = min(max_linear_vel, 0.5 * dist + 0.1)
            w_cmd = 1.8 * h_err

        if abs(v_cmd * w_cmd) > max_lateral_acc:
            w_cmd = math.copysign(max_lateral_acc / max(v_cmd, 0.1), w_cmd)

        v = 0.9 * v + 0.1 * v_cmd
        w = 0.9 * w + 0.1 * w_cmd
        x += v * math.cos(theta) * dt
        y += v * math.sin(theta) * dt
        theta += w * dt
        lat_acc = abs(v * w)

        records.append({
            "t": round(t, 3), "x": round(x, 4), "y": round(y, 4),
            "v": round(v, 4), "w": round(w, 4), "lat_acc": round(lat_acc, 4),
            "fsm": fsm
        })
        t += dt

    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)
    print(f"[Done] Logged {len(records)} samples to {output_csv}. Peak lat_acc: {max(r['lat_acc'] for r in records):.3f} m/s^2")

if __name__ == "__main__":
    run_simulation()
