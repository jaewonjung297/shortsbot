"""End-to-end: write -> validate -> preview -> critic -> render -> audio -> mux -> upload -> history."""
import argparse, datetime, json, os, subprocess, sys, time
from .render import render_video, contact_sheet
from .audio import build_audio
from .spec import validate, sheet_times

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HISTORY = os.environ.get("SHORTSBOT_HISTORY", os.path.join(ROOT, "history.json"))

def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)

def load_history():
    try: return json.load(open(HISTORY))
    except FileNotFoundError: return []

def save_history(h):
    json.dump(h, open(HISTORY, "w"), indent=2, ensure_ascii=False)

def produce(spec, outdir, workers=None):
    """Render video + audio and mux. Returns the mp4 path."""
    os.makedirs(outdir, exist_ok=True)
    silent = os.path.join(outdir, "video_silent.mp4")
    wav = os.path.join(outdir, "audio.wav"); wavn = os.path.join(outdir, "audio_norm.wav")
    final = os.path.join(outdir, "short.mp4")
    t0 = time.time()
    render_video(spec, os.path.join(outdir, "chunks"), silent, workers=workers)
    log("render: %.0fs" % (time.time() - t0))
    build_audio(spec, wav)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", wavn], check=True)
    tmp = final + ".part.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", wavn, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, final)
    json.dump(spec, open(os.path.join(outdir, "spec.json"), "w"), indent=2, ensure_ascii=False)
    return final

def run(args):
    history = load_history()
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    outdir = os.path.abspath(args.out or os.path.join(ROOT, "out", stamp))
    os.makedirs(outdir, exist_ok=True)
    if args.spec:
        spec = json.load(open(args.spec))
        errs = validate(spec)
        if errs: sys.exit("spec invalid:\n- " + "\n- ".join(errs))
    else:
        from .writer import write_spec, review
        spec = write_spec(history, log=log)
        if not args.no_review:
            for rnd in range(2):
                sheet = contact_sheet(spec, sheet_times(spec), os.path.join(outdir, "preview_%d.png" % rnd), 0.25)
                verdict = review(spec, sheet, log=log)
                if verdict.get("approve"): break
                rev = verdict.get("revised_spec")
                if rev and not validate(rev): spec = rev; log("critic: using revised spec")
                else: log("critic: revision missing/invalid; keeping current spec"); break
    log("premise: %s  [template=%s]" % (spec["premise"], spec["template"]))
    contact_sheet(spec, sheet_times(spec), os.path.join(outdir, "preview_final.png"), 0.25)
    if args.preview_only:
        json.dump(spec, open(os.path.join(outdir, "spec.json"), "w"), indent=2, ensure_ascii=False)
        log("preview written to", outdir); return
    video = produce(spec, outdir, workers=args.workers)
    log("video:", video)
    entry = {"date": stamp, "premise": spec["premise"], "template": spec["template"], "title": spec["title"], "video_id": None}
    if not args.no_upload:
        from .upload import upload
        vid, privacy = upload(video, spec, log=log)
        entry["video_id"], entry["privacy"] = vid, privacy
    history.append(entry); save_history(history)
    with open(os.path.join(outdir, "result.json"), "w") as f: json.dump(entry, f, indent=2, ensure_ascii=False)

def run_tiktok(args, platform="tiktok"):
    """Human-in-the-loop draft for TikTok or Instagram Reels: write (steerable) -> critic -> render -> package.
    TikTok can also drop the draft into your TikTok inbox; Instagram is published later by instagram-publish."""
    from .tiktok import write_package
    history = load_history()
    stamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    outdir = os.path.abspath(args.out or os.path.join(ROOT, "out", platform + "-" + stamp))
    os.makedirs(outdir, exist_ok=True)
    if args.spec:
        spec = json.load(open(args.spec)); spec.setdefault("platform", "tiktok")
        errs = validate(spec)
        if errs: sys.exit("spec invalid:\n- " + "\n- ".join(errs))
    else:
        from .writer import write_spec, review
        spec = write_spec(history, log=log, premise=args.premise or None,
                          template=None if args.template in (None, "", "auto") else args.template, platform="tiktok")
        if not args.no_review:
            for rnd in range(2):
                sheet = contact_sheet(spec, sheet_times(spec), os.path.join(outdir, "preview_%d.png" % rnd), 0.25)
                verdict = review(spec, sheet, log=log)
                if verdict.get("approve"): break
                rev = verdict.get("revised_spec")
                if rev and not validate(rev): spec = rev; log("critic: using revised spec")
                else: break
    log("premise: %s  [template=%s, %ss]" % (spec["premise"], spec["template"], spec["duration"]))
    contact_sheet(spec, sheet_times(spec), os.path.join(outdir, "preview_final.png"), 0.25)
    video = produce(spec, outdir, workers=args.workers)
    pkg = write_package(spec, video, outdir, platform=platform)
    entry = {"date": stamp, "platform": platform, "cover_time": round(pkg["cover_time"], 2), "premise": spec["premise"], "template": spec["template"],
             "title": spec["title"], "status": "drafted"}
    if getattr(args, "send_to_inbox", False):
        from .tiktok import send_to_inbox
        pid, status = send_to_inbox(video, log=log)
        entry.update(publish_id=pid, status="in_tiktok_inbox" if status else "uploaded")
    history.append(entry); save_history(history)
    json.dump(entry, open(os.path.join(outdir, "result.json"), "w"), indent=2, ensure_ascii=False)
    log("package ready in %s" % outdir)
    log("caption: %s" % pkg["caption"].replace("\n", " | "))

def run_ideas(args):
    from .writer import ideas
    for i, it in enumerate(ideas(load_history(), n=args.n, platform=args.platform), 1):
        print("%d. %s  [%s]\n   %s" % (i, it["premise"], it.get("template", "?"), it.get("why", "")))

def main(argv=None):
    p = argparse.ArgumentParser(prog="shortsbot", description="Automatic 'What if' Shorts")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="write (or load) a spec, render it and upload it")
    r.add_argument("--spec", help="use this spec instead of asking Claude")
    r.add_argument("--out", help="output folder")
    r.add_argument("--no-upload", action="store_true")
    r.add_argument("--no-review", action="store_true", help="skip the vision critic pass")
    r.add_argument("--preview-only", action="store_true", help="stop after the contact sheet")
    r.add_argument("--workers", type=int)
    tk = sub.add_parser("tiktok", help="make a TikTok draft package (and optionally send it to your TikTok inbox)")
    tk.add_argument("--premise", help="steer the writer to this premise")
    tk.add_argument("--template", choices=["auto", "car", "window", "hill"], default="auto")
    tk.add_argument("--spec", help="use this spec instead of asking Claude")
    tk.add_argument("--out"); tk.add_argument("--workers", type=int)
    tk.add_argument("--no-review", action="store_true")
    tk.add_argument("--send-to-inbox", action="store_true", help="upload as a draft to your TikTok inbox")
    ig = sub.add_parser("instagram", help="make an Instagram Reel draft package (publish it later with instagram-publish)")
    ig.add_argument("--premise"); ig.add_argument("--template", choices=["auto", "car", "window", "hill"], default="auto")
    ig.add_argument("--spec"); ig.add_argument("--out"); ig.add_argument("--workers", type=int)
    ig.add_argument("--no-review", action="store_true")
    idp = sub.add_parser("ideas", help="list fresh premise ideas to pick from")
    idp.add_argument("-n", type=int, default=6); idp.add_argument("--platform", default="tiktok")
    v = sub.add_parser("validate"); v.add_argument("spec")
    s = sub.add_parser("sheet"); s.add_argument("spec"); s.add_argument("png")
    a = p.parse_args(argv)
    if a.cmd == "run": run(a)
    elif a.cmd == "tiktok": run_tiktok(a, "tiktok")
    elif a.cmd == "instagram": run_tiktok(a, "instagram")
    elif a.cmd == "ideas": run_ideas(a)
    elif a.cmd == "validate":
        errs = validate(json.load(open(a.spec))); print("OK" if not errs else "\n".join(errs)); sys.exit(1 if errs else 0)
    elif a.cmd == "sheet":
        spec = json.load(open(a.spec)); contact_sheet(spec, sheet_times(spec), a.png, 0.25); print(a.png)
