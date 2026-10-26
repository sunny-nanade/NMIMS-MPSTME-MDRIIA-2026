// skyrender.c — offscreen MuJoCo renderer for the SkyHydro flood scene.
//
// Like MuJoCo's `record` sample, but:
//   * every mocap body (drone, camera gimbal, helicopter, floating debris)
//     follows a motion script: one line per frame with 7 numbers
//     (x y z qw qx qy qz) per mocap body, in model order. Physics
//     runs normally underneath — the winch cable + payload pendulum swings
//     for real as the drone accelerates/stops.
//   * rotors spin: hinge joints named heli_main_rotor, heli_tail_rotor and
//     uav_prop1..4 are driven at fixed rates every frame.
//   * five passes per frame (selected with geom groups / scene transform):
//       A  scene, no scan beam
//       B  water mask (water drawn flat magenta)
//       C  scene with the translucent scan beam (group 4)
//       D  planar reflection: the scene mirrored about the water plane
//          (terrain/grass/water hidden, no sky) + coverage mask from depth
//       E  scene with the water hidden (submerged ground, for the shallows)
//     The water shader combines them.
//
// Build: gcc -O2 skyrender.c -I<mj>/include -L<mj>/lib -lmujoco -l:libEGL.so.1 -l:libGL.so.1 -lm -Wl,-rpath,<mj>/lib -o skyrender
// Usage: EGL_PLATFORM=surfaceless ./skyrender scene.xml path.txt fps out_prefix water_z

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <mujoco/mujoco.h>

typedef void* EGLDisplay; typedef void* EGLConfig; typedef void* EGLContext; typedef void* EGLSurface;
typedef int EGLint; typedef unsigned int EGLBoolean; typedef unsigned int EGLenum;
extern EGLDisplay eglGetDisplay(void*);
extern EGLBoolean eglInitialize(EGLDisplay, EGLint*, EGLint*);
extern EGLBoolean eglChooseConfig(EGLDisplay, const EGLint*, EGLConfig*, EGLint, EGLint*);
extern EGLBoolean eglBindAPI(EGLenum);
extern EGLContext eglCreateContext(EGLDisplay, EGLConfig, EGLContext, const EGLint*);
extern EGLBoolean eglMakeCurrent(EGLDisplay, EGLSurface, EGLSurface, EGLContext);
extern EGLint eglGetError(void);

static void init_egl(void) {
  const EGLint a[] = {0x3024, 8, 0x3023, 8, 0x3022, 8, 0x3021, 8, 0x3025, 24, 0x3026, 8, 0x303F, 0x308E,
                      0x3033, 0x0001, 0x3040, 0x0008, 0x3038};
  EGLDisplay dpy = eglGetDisplay(0);
  EGLint maj, min, n; EGLConfig cfg;
  if (!dpy || !eglInitialize(dpy, &maj, &min)) { fprintf(stderr, "EGL init failed\n"); exit(1); }
  if (!eglChooseConfig(dpy, a, &cfg, 1, &n) || n < 1) { fprintf(stderr, "EGL config failed\n"); exit(1); }
  eglBindAPI(0x30A2);
  EGLContext ctx = eglCreateContext(dpy, cfg, 0, NULL);
  if (!ctx || !eglMakeCurrent(dpy, 0, 0, ctx)) { fprintf(stderr, "EGL context failed\n"); exit(1); }
}

#define NSPIN 6
static const char* spin_names[NSPIN] = {"heli_main_rotor", "heli_tail_rotor", "uav_prop1", "uav_prop2", "uav_prop3", "uav_prop4"};
static const double spin_rates[NSPIN] = {17.0, 50.0, 33.0, -33.0, 33.0, -33.0};

int main(int argc, char** argv) {
  if (argc != 6) { printf("usage: skyrender scene.xml path.txt fps out_prefix water_z\n"); return 1; }
  double fps = atof(argv[3]), water_z = atof(argv[5]);
  const char* pre = argv[4];

  init_egl();
  char err[1000] = "";
  mjModel* m = mj_loadXML(argv[1], NULL, err, 1000);
  if (!m) { fprintf(stderr, "load error: %s\n", err); return 1; }
  mjData* d = mj_makeData(m);

  // motion script: one line per frame, 7 numbers (x y z qw qx qy qz) for
  // EVERY mocap body, in model order (drone, gimbal, helicopter, debris...)
  int K = m->nmocap, NC = 7 * K;
  FILE* pf = fopen(argv[2], "r");
  if (!pf) { fprintf(stderr, "cannot open path\n"); return 1; }
  int cap = 8192, nf = 0;
  double* path = calloc((size_t)NC * cap, sizeof(double));
  size_t lcap = 1 << 16; char* line = malloc(lcap);
  while (nf < cap && fgets(line, (int)lcap, pf)) {
    char* q = line; char* e; int k = 0;
    for (; k < NC; k++) { double v = strtod(q, &e); if (e == q) break; path[(size_t)NC * nf + k] = v; q = e; }
    if (k == NC) nf++;
    else if (k > 0) { fprintf(stderr, "path line %d has %d numbers, need %d (7 x %d mocap bodies)\n", nf + 1, k, NC, K); return 1; }
  }
  fclose(pf);
  if (nf == 0) { fprintf(stderr, "empty path\n"); return 1; }
  #define P(f_, k_) path[(size_t)NC * (f_) + (k_)]

  int spin_q[NSPIN], spin_v[NSPIN];
  for (int i = 0; i < NSPIN; i++) {
    int j = mj_name2id(m, mjOBJ_JOINT, spin_names[i]);
    spin_q[i] = j >= 0 ? m->jnt_qposadr[j] : -1;
    spin_v[i] = j >= 0 ? m->jnt_dofadr[j] : -1;
  }

  mjvCamera cam; mjvOption opt; mjvScene scn; mjrContext con;
  mjv_defaultCamera(&cam); mjv_defaultOption(&opt); mjv_defaultScene(&scn); mjr_defaultContext(&con);
  mjv_makeScene(m, &scn, 60000);
  mjr_makeContext(m, &con, mjFONTSCALE_100);
  mjv_defaultFreeCamera(m, &cam);
  mjr_setBuffer(mjFB_OFFSCREEN, &con);
  mjrRect vp = mjr_maxViewport(&con);
  int W = vp.width, H = vp.height;
  unsigned char* rgb = malloc(3 * W * H);
  float* depth = malloc(sizeof(float) * W * H);
  unsigned char* cov = malloc(W * H);

  #define SETPOSE(f_) do { for (int b = 0; b < K; b++) { \
      for (int k = 0; k < 3; k++) d->mocap_pos[3*b + k] = P(f_, 7*b + k); \
      for (int k = 0; k < 4; k++) d->mocap_quat[4*b + k] = P(f_, 7*b + 3 + k); } } while (0)

  SETPOSE(0);
  mj_forward(m, d);
  for (int i = 0; i < 500; i++) mj_step(m, d);
  double t0 = d->time;

  char fn[1024];
  FILE* fo[6]; const char* tag[6] = {"A", "B", "C", "D", "Dm", "E"};
  for (int i = 0; i < 6; i++) { snprintf(fn, sizeof fn, "%s_%s.raw", pre, tag[i]); fo[i] = fopen(fn, "wb"); }

  int substeps = (int)(1.0 / (fps * m->opt.timestep) + 0.5);
  for (int f = 0; f < nf; f++) {
    if (f > 0) {
      for (int s = 1; s <= substeps; s++) {
        double a = (double)s / substeps;
        for (int b = 0; b < K; b++) {
          double q[4], nrm = 0, dot = 0;
          for (int k = 0; k < 4; k++) dot += P(f-1, 7*b + 3 + k) * P(f, 7*b + 3 + k);
          double sg = dot < 0 ? -1 : 1;                  // shortest-arc quaternion blend
          for (int k = 0; k < 3; k++) d->mocap_pos[3*b + k] = P(f-1, 7*b + k) * (1 - a) + P(f, 7*b + k) * a;
          for (int k = 0; k < 4; k++) { q[k] = P(f-1, 7*b + 3 + k) * (1 - a) + sg * P(f, 7*b + 3 + k) * a; nrm += q[k]*q[k]; }
          for (int k = 0; k < 4; k++) d->mocap_quat[4*b + k] = q[k] / sqrt(nrm);
        }
        mj_step(m, d);
      }
    }
    for (int i = 0; i < NSPIN; i++) if (spin_q[i] >= 0) {
      d->qpos[spin_q[i]] = spin_rates[i] * (d->time - t0);
      d->qvel[spin_v[i]] = spin_rates[i];
    }
    mj_forward(m, d);

    for (int pass = 0; pass < 5; pass++) {
      for (int g = 0; g < 6; g++) opt.geomgroup[g] = 0;
      opt.geomgroup[0] = 1; opt.geomgroup[1] = 1;
      scn.enabletransform = 0;
      scn.flags[mjRND_SKYBOX] = 1; scn.flags[mjRND_SHADOW] = 1;
      if (pass == 0) { opt.geomgroup[2] = 1; }
      if (pass == 1) { opt.geomgroup[3] = 1; }
      if (pass == 2) { opt.geomgroup[2] = 1; opt.geomgroup[4] = 1; }
      if (pass == 3) {
        opt.geomgroup[1] = 0; opt.geomgroup[4] = 1;
        scn.flags[mjRND_SKYBOX] = 0; scn.flags[mjRND_SHADOW] = 0;
      }
      // planar reflection: camera mirrored about the water plane (below it,
      // looking up) with the ground hidden. Its image equals the reflection
      // flipped left-right (mirroring flips handedness); the shader un-flips it.
      mjvCamera rc = cam;
      if (pass == 3) { rc.lookat[2] = 2 * water_z - cam.lookat[2]; rc.elevation = -cam.elevation; }
      mjv_updateScene(m, d, &opt, NULL, pass == 3 ? &rc : &cam, mjCAT_ALL, &scn);
      mjr_render(vp, &scn, &con);
      mjr_readPixels(rgb, pass == 3 ? depth : NULL, vp, &con);
      int slot = pass < 3 ? pass : (pass == 3 ? 3 : 5);
      fwrite(rgb, 3, W*H, fo[slot]);
      if (pass == 3) {
        for (int i = 0; i < W*H; i++) cov[i] = depth[i] < 0.99999f ? 255 : 0;
        fwrite(cov, 1, W*H, fo[4]);
      }
    }
    if (f % 10 == 0) { printf("frame %d/%d\n", f, nf); fflush(stdout); }
  }
  for (int i = 0; i < 6; i++) fclose(fo[i]);
  printf("done %dx%d %d frames\n", W, H, nf);
  mjr_freeContext(&con); mjv_freeScene(&scn); mj_deleteData(d); mj_deleteModel(m);
  return 0;
}
