"""Flicker inside one region of a render over a frame range (fire, glows, lightning): mean luma per frame and the
frame-to-frame jumps. A real flame changes smoothly; a strobing effect jumps every frame.

    python tools/region_flicker.py out/renders/short_v4.mp4 <f0> <f1> [x y w h as fractions of the frame]

  default region = the whole frame. Reports: mean luma, std, the largest frame-to-frame jump, and the share of
  frames whose jump changes sign every frame (strobing: > 0.6 with jumps > 4 luma levels is a FAIL).
"""
import subprocess, sys
import numpy as np

video, f0, f1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
x, y, w, h = (float(v) for v in sys.argv[4:8]) if len(sys.argv) >= 8 else (0.0, 0.0, 1.0, 1.0)
W, H = 270, 480
p = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"trim=start_frame={f0}:end_frame={f1 + 1},scale={W}:{H}",
                    "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
if p.returncode != 0 or not p.stdout:
    sys.exit(f"ffmpeg failed: {p.stderr.decode(errors='replace')[-400:]}")
g = np.frombuffer(p.stdout, np.uint8).reshape(-1, H, W).astype(np.float32)
r = g[:, int(y * H):int((y + h) * H), int(x * W):int((x + w) * W)]
m = r.mean(axis=(1, 2))
d = np.diff(m)
alt = float(np.mean(np.sign(d[1:]) != np.sign(d[:-1]))) if len(d) > 2 else 0.0
big = float(np.max(np.abs(d))) if len(d) else 0.0
print(f"frames {f0}-{f1} ({len(m)}), region x{x:.2f} y{y:.2f} w{w:.2f} h{h:.2f}")
print(f"mean luma {m.mean():.1f}, std {m.std():.2f}, largest jump {big:.2f}, sign alternation {alt:.2f}")
print("luma:", " ".join(f"{v:.0f}" for v in m))
fail = alt > 0.6 and np.mean(np.abs(d)) > 4
print("FAIL strobing" if fail else "OK (no strobing)")
