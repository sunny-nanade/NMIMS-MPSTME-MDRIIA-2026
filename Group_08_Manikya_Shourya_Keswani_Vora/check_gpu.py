"""check_gpu.py — confirm this machine is ready for fast GPU training."""
import os
import platform
import time

print(f"python  {platform.python_version()}  ({platform.system()} {platform.machine()})")
print(f"CPU     {os.cpu_count()} threads  -> training runs {max(1, min(16, (os.cpu_count() or 2) - 2))} parallel simulations")
try:
    import mujoco
    print(f"mujoco  {mujoco.__version__}")
except ImportError:
    print("mujoco  MISSING  (pip install -r requirements.txt)")
try:
    import torch as th
    print(f"torch   {th.__version__}   CUDA build: {th.version.cuda}")
    if th.cuda.is_available():
        for i in range(th.cuda.device_count()):
            p = th.cuda.get_device_properties(i)
            print(f"GPU {i}   {p.name}  {p.total_memory / 2**30:.0f} GB")
        th.backends.cuda.matmul.allow_tf32 = True
        a = th.randn(4096, 4096, device="cuda"); th.cuda.synchronize(); t = time.time()
        for _ in range(20):
            a @ a
        th.cuda.synchronize()
        print(f"GPU OK  {20 * 2 * 4096 ** 3 / (time.time() - t) / 1e12:.1f} TFLOP/s  -> training will use cuda")
    else:
        print("GPU     NOT visible to PyTorch -> training would run on the CPU.\n"
              "        fix:  pip uninstall -y torch  &&  pip install torch --index-url https://download.pytorch.org/whl/cu126\n"
              "        (RTX 50-series: cu128).  Also check `nvidia-smi` works.")
except ImportError:
    print("torch   MISSING")
