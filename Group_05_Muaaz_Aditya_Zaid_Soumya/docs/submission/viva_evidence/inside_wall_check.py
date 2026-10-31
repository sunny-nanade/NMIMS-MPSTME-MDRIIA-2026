# Independent check: exterior patrol checkpoints and flown UAV tracks versus the boundary_wall polygon
import os, re, gzip, csv, glob, math, numpy as np
G=os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","..",".."))   # group folder of this tree
RUNS=G+"/analytics/runs"   # local 500 Hz telemetry of the main batch (not committed)
x=open(G+"/models/nmims_main_campus.xml").read()
segs=[]
for m in re.finditer(r'name="boundary_wall_(\d+)"[^>]*size="([\d.]+) [\d.]+ [\d.]+" pos="([-\d.]+) ([-\d.]+) [\d.]+" euler="0 0 ([-\d.]+)"',x):
    i,hx,px,py,yaw=int(m[1]),float(m[2]),float(m[3]),float(m[4]),float(m[5])
    c,s=math.cos(yaw),math.sin(yaw); segs.append((i,(px-hx*c,py-hx*s),(px+hx*c,py+hx*s)))
segs.sort()
print("wall segments",len(segs))
# polygon vertices: midpoint between consecutive segment ends
poly=[]
for k in range(len(segs)):
    a=np.array(segs[k][2]); b=np.array(segs[(k+1)%len(segs)][1])
    poly.append((a+b)/2)
poly=np.array(poly)
def inside(p):
    xq,yq=p; n=len(poly); c=False
    for i in range(n):
        x1,y1=poly[i]; x2,y2=poly[(i+1)%n]
        if (y1>yq)!=(y2>yq) and xq < (x2-x1)*(yq-y1)/(y2-y1)+x1: c=not c
    return c
def dseg(p):
    best=1e9
    for i in range(len(poly)):
        a=poly[i]; b=poly[(i+1)%len(poly)]; ab=b-a; t=np.clip(np.dot(p-a,ab)/np.dot(ab,ab),0,1); best=min(best,np.linalg.norm(p-(a+t*ab)))
    return best
cps=[(m[1],float(m[2]),float(m[3])) for m in re.finditer(r'name="patrol_cp(\d+)" pos="([-\d.]+) ([-\d.]+)',x)]
for n,a,b in cps:
    p=np.array([a,b]); print(f"patrol_cp{n} inside={inside(p)} dist_to_wall={dseg(p):.2f} m")
print("--- flown tracks (exterior UAV runs with telemetry)")
summary=[]
for f in sorted(glob.glob(RUNS+"/exterior_uav_*.csv.gz")):
    out=0; tot=0; worst=0.0; outside_patrol=0
    for r in csv.DictReader(gzip.open(f,"rt")):
        if r["uav"] not in("alpha","bravo"): continue
        tot+=1
        if tot%10: continue   # 50 Hz subsample
        p=np.array([float(r["x"]),float(r["y"])])
        if not inside(p):
            out+=1; worst=max(worst,dseg(p))
            if r["fsm_state"]=="PATROL": outside_patrol+=1
    n=tot//10
    print(f"{f.split('/')[-1]}: samples={n} outside_wall={out} ({100*out/max(n,1):.2f} %), PATROL-outside={outside_patrol}, max distance outside={worst:.2f} m")
print("--- outside-wall samples by fsm_state (all exterior UAV telemetry, 50 Hz subsample)")
import collections
byst=collections.Counter(); maxst=collections.defaultdict(float)
for f in sorted(glob.glob(RUNS+"/exterior_uav_*.csv.gz")):
    k=0
    for r in csv.DictReader(gzip.open(f,"rt")):
        if r["uav"] not in("alpha","bravo"): continue
        k+=1
        if k%10: continue
        p=np.array([float(r["x"]),float(r["y"])])
        if not inside(p):
            byst[r["fsm_state"]]+=1; maxst[r["fsm_state"]]=max(maxst[r["fsm_state"]],dseg(p))
for s,c in byst.most_common(): print(f"  {s}: {c} samples, max {maxst[s]:.2f} m outside")
