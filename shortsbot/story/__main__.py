"""Story pipeline stages; each reads and writes one work folder.

  python -m shortsbot.story condense  --story story.txt --dir work      # Claude -> spec.json
  python -m shortsbot.story narrate   --dir work                        # Kokoro -> narration.wav, timeline.json
  python -m shortsbot.story render    --dir work --part 0 --parts 4     # frames -> part_0.mp4
  python -m shortsbot.story assemble  --dir work                        # join + music + mix -> short.mp4 + package
  python -m shortsbot.story deliver   --dir work                        # short.mp4 -> TikTok inbox draft
  python -m shortsbot.story all       --story story.txt --dir work      # everything locally
  python -m shortsbot.story preview   --dir work                        # contact sheet of every shot
"""
import argparse, json, math, os, subprocess, sys, time
from .spec import validate

FPS = 30

def log(*a): print(time.strftime("[%H:%M:%S]"), *a, flush=True)

def load(d, name): return json.load(open(os.path.join(d, name)))

def stage_condense(a):
    from .condense import condense
    story = open(a.story).read()
    spec = condense(story, log=log, notes=a.notes or "")
    if a.voice: spec["voice"] = a.voice
    if a.speed: spec["speed"] = a.speed
    os.makedirs(a.dir, exist_ok=True)
    json.dump(spec, open(os.path.join(a.dir, "spec.json"), "w"), indent=1, ensure_ascii=False)
    log("title:", spec["title"])

def stage_narrate(a):
    from .narrate import narrate
    spec = load(a.dir, "spec.json")
    errs = validate(spec)
    if errs: sys.exit("spec invalid:\n- " + "\n- ".join(errs))
    narrate(spec, a.dir, log=log)

def stage_render(a):
    from .render import StoryRenderer
    spec, tl = load(a.dir, "spec.json"), load(a.dir, "timeline.json")
    n = int(round(tl["total"] * FPS)); per = math.ceil(n / a.parts)
    f0, f1 = a.part * per, min(n, (a.part + 1) * per)
    out = os.path.join(a.dir, "part_%02d.mp4" % a.part); tmp = out + ".tmp.mp4"
    r = StoryRenderer(spec, tl)
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", "1080x1920", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    t0 = time.time()
    for fi in range(f0, f1):
        p.stdin.write(bytes(r.frame(fi / FPS).get_data()))
        if (fi - f0) % 300 == 0: log("render part %d: frame %d/%d" % (a.part, fi - f0, f1 - f0))
    p.stdin.close()
    if p.wait() != 0: sys.exit("ffmpeg failed")
    os.replace(tmp, out)
    log("render part %d: %d frames in %.0fs" % (a.part, f1 - f0, time.time() - t0))

def stage_assemble(a):
    from .music import mix_audio
    spec, tl = load(a.dir, "spec.json"), load(a.dir, "timeline.json")
    parts = sorted(f for f in os.listdir(a.dir) if f.startswith("part_") and f.endswith(".mp4") and ".tmp" not in f)
    lst = os.path.join(a.dir, "parts.txt")
    with open(lst, "w") as f:
        for p in parts: f.write("file '%s'\n" % os.path.abspath(os.path.join(a.dir, p)))
    silent = os.path.join(a.dir, "video.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent], check=True)
    mix = mix_audio(spec, tl, a.dir)
    norm = os.path.join(a.dir, "mix_norm.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mix, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", norm], check=True)
    final = os.path.join(a.dir, "short.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", norm, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", final], check=True)
    # posting package
    open(os.path.join(a.dir, "caption.txt"), "w").write(spec["tiktok_caption"].strip() + "\n")
    with open(os.path.join(a.dir, "script.txt"), "w") as f:
        f.write(spec["title"] + "\n\n")
        for ln, L in zip(tl["lines"], spec["lines"]): f.write("[%5.1f] %s\n" % (ln["start"], L["text"]))
    mid = tl["lines"][len(tl["lines"]) // 3]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "%.2f" % ((mid["start"] + mid["end"]) / 2), "-i", final,
                    "-frames:v", "1", "-q:v", "3", os.path.join(a.dir, "cover.jpg")], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", final],
                               capture_output=True, text=True).stdout.strip() or 0)
    json.dump({"title": spec["title"], "duration": round(dur, 1), "lines": len(spec["lines"])},
              open(os.path.join(a.dir, "result.json"), "w"), indent=1)
    log("assemble: %s (%.1fs)" % (final, dur))

def stage_deliver(a):
    from ..tiktok import send_to_inbox
    publish_id, status = send_to_inbox(os.path.join(a.dir, "short.mp4"), log=log)
    res = load(a.dir, "result.json"); res.update(publish_id=publish_id, tiktok_status=status)
    json.dump(res, open(os.path.join(a.dir, "result.json"), "w"), indent=1)

def stage_preview(a):
    from PIL import Image
    from .render import StoryRenderer
    spec, tl = load(a.dir, "spec.json"), load(a.dir, "timeline.json")
    r = StoryRenderer(spec, tl)
    ts, prev = [], 0.0
    for ln in tl["lines"]: ts.append((prev + ln["shot_end"]) / 2); prev = ln["shot_end"]
    w, h = 216, 384; cols = 7
    sheet = Image.new("RGB", (cols * w, ((len(ts) + cols - 1) // cols) * h))
    for k, t in enumerate(ts):
        s = r.frame(t)
        im = Image.frombuffer("RGBA", (1080, 1920), bytes(s.get_data()), "raw", "BGRA", 0, 1).convert("RGB").resize((w, h))
        sheet.paste(im, ((k % cols) * w, (k // cols) * h))
    out = os.path.join(a.dir, "preview.png"); sheet.save(out); log("preview:", out)

def stage_all(a):
    if a.story: stage_condense(a)
    stage_narrate(a)
    parts = a.parts
    procs = [subprocess.Popen([sys.executable, "-m", "shortsbot.story", "render", "--dir", a.dir, "--part", str(k), "--parts", str(parts)])
             for k in range(parts)]
    if any(p.wait() for p in procs): sys.exit("a render part failed")
    stage_assemble(a)

def main(argv=None):
    p = argparse.ArgumentParser(prog="shortsbot.story")
    p.add_argument("stage", choices=["condense", "narrate", "render", "assemble", "deliver", "all", "preview"])
    p.add_argument("--dir", default="work")
    p.add_argument("--story"); p.add_argument("--notes"); p.add_argument("--voice"); p.add_argument("--speed", type=float)
    p.add_argument("--part", type=int, default=0); p.add_argument("--parts", type=int, default=os.cpu_count() or 2)
    a = p.parse_args(argv)
    {"condense": stage_condense, "narrate": stage_narrate, "render": stage_render, "assemble": stage_assemble, "deliver": stage_deliver,
     "all": stage_all, "preview": stage_preview}[a.stage](a)

if __name__ == "__main__":
    main()
