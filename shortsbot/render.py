"""Frame rendering + parallel encoding."""
import os, subprocess, importlib, math, multiprocessing as mp
import cairo
from .engine import W_PX, H_PX, FPS, environment, add_season, draw_hud, draw_caption, post, ease_io, lerp
from .timeline import Timeline

TEMPLATES = ["car", "window", "hill"]

def load_template(name):
    if name not in TEMPLATES: raise ValueError("unknown template %r" % name)
    return importlib.import_module(".templates." + name, __package__)

class Renderer:
    def __init__(self, spec):
        self.tl = Timeline(spec)
        self.mod = load_template(spec["template"])
        self.scene = self.mod.Scene(self.tl, int(spec.get("seed", 7)))

    def frame(self, t):
        tl = self.tl
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W_PX, H_PX)
        ctx = cairo.Context(surf)
        env = environment(tl, t); add_season(tl, env, t)
        zoom = ease_io((t - (tl.final_at - 0.2)) / (tl.dur - tl.final_at))
        ctx.save()
        if zoom > 0:
            fx, fy = self.mod.FOCUS
            s = 1 + float(getattr(self.mod, "ZOOM", 1.4)) * zoom
            tx, ty = lerp(fx, 540, zoom), lerp(fy, getattr(self.mod, "FOCUS_TO_Y", 1450), zoom)
            ctx.translate(tx, ty); ctx.scale(s, s); ctx.translate(-fx, -fy)
        self.scene.draw(ctx, env, t)
        ctx.restore()
        draw_hud(ctx, tl, t, y0=self.mod.HUD_Y)
        y = self.mod.CAPTION_Y if t < tl.final_at else getattr(self.mod, "FINAL_CAPTION_Y", 1000)
        draw_caption(ctx, tl, t, y=y)
        post(ctx, tl, t)
        return surf

    def still(self, t, path):
        self.frame(t).write_to_png(path)


def _chunk(args):
    spec, f0, f1, out = args
    r = Renderer(spec)
    tmp = out + ".part.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", "%dx%d" % (W_PX, H_PX),
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", tmp],
                         stdin=subprocess.PIPE)
    for fi in range(f0, f1):
        p.stdin.write(bytes(r.frame(fi / FPS).get_data()))
    p.stdin.close()
    if p.wait() != 0: raise RuntimeError("ffmpeg failed for " + out)
    os.replace(tmp, out)
    return out

def render_video(spec, workdir, out_path, workers=None):
    """Render silent video in parallel chunks, then join with the concat demuxer."""
    os.makedirs(workdir, exist_ok=True)
    workers = workers or max(1, os.cpu_count() or 1)
    n = int(round(float(spec.get("duration", 60)) * FPS))
    per = math.ceil(n / workers)
    jobs = [(spec, i, min(n, i + per), os.path.join(workdir, "chunk%02d.mp4" % k)) for k, i in enumerate(range(0, n, per))]
    with mp.get_context("fork").Pool(len(jobs)) as pool:
        outs = pool.map(_chunk, jobs)
    lst = os.path.join(workdir, "chunks.txt")
    with open(lst, "w") as f:
        for o in outs: f.write("file '%s'\n" % os.path.abspath(o))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out_path], check=True)
    return out_path

def contact_sheet(spec, times, path, scale=0.333):
    from PIL import Image
    r = Renderer(spec)
    w, h = int(W_PX * scale), int(H_PX * scale)
    cols = 4; rows = (len(times) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * w, rows * h))
    for i, t in enumerate(times):
        surf = r.frame(t)
        img = Image.frombuffer("RGBA", (W_PX, H_PX), bytes(surf.get_data()), "raw", "BGRA", 0, 1).convert("RGB").resize((w, h))
        sheet.paste(img, ((i % cols) * w, (i // cols) * h))
    sheet.save(path)
    return path
