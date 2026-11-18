"""Spec schema, validation and the reference doc given to the writer agent."""
import importlib, json, math
from .timeline import CHANNELS, Timeline

TEMPLATES = ["car", "window", "hill"]
PLATFORMS = {
    # platform: (min duration, max duration, max stages)
    "youtube": (40, 60, 9),
    "tiktok": (65, 90, 11),     # TikTok Creator Rewards only pays for videos longer than 1 minute
}
RANGES = {"sun_scale": (0, 4), "moon_scale": (0, 10)}

def template_docs():
    out = []
    for name in TEMPLATES:
        m = importlib.import_module(".templates." + name, __package__)
        out.append("- `%s`: %s" % (name, m.DESCRIPTION))
    return "\n".join(out)

def channel_docs():
    rows = ["- `%s` (default %s): %s" % (k, v[0], v[1]) for k, v in CHANNELS.items()]
    rows.append("- `daylight` (optional): if used anywhere, overrides the day/night cycle; 0 = night, 1 = full day")
    return "\n".join(rows)

SCHEMA_DOC = """
{
  "premise": "What if ...?",                 // the question, as a viewer would search it
  "platform": "youtube" | "tiktok",          // tiktok: 65-90 s long (TikTok only pays for videos over 1 minute)
  "template": "car" | "window" | "hill",
  "seed": 1-9999,                            // varies building layout/colours
  "duration": 45-60 (youtube) or 65-90 (tiktok),   // seconds
  "event_at": 3.0-4.5,                       // when the premise kicks in (stage 0 starts here)
  "start_hour": 0-23,                        // local time of day at the start (21 = night, 13 = midday)
  "hours_per_second": 0-0.5,                 // only for counter mode "number": how fast the clock moves
  "counter": EITHER
     {"label": "TIME WITHOUT POWER", "mode": "time", "end_world_seconds": 1e2-1e17}
       // shows elapsed time accelerating x10 every few seconds; day/night cycles automatically and blur into
       // averaged daylight once days pass faster than ~1 per second
     OR {"label": "SEA LEVEL RISE", "mode": "number", "start": 0, "end": 70, "unit": "m", "decimals": 1,
         "log": false, "rate_text": "ICE MELTING WORLDWIDE"},
  "pre_label": "GRID ONLINE",                // HUD status before the event (1-3 words)
  "pre_rate_text": "ALL SYSTEMS NORMAL",     // HUD sub-line before the event
  "hook": "What if all electronics\\nstopped working?",   // shown 0..event_at; max 2 lines, use \\n
  "final_caption": "And your phone?\\nJust a very nice rock.",  // punchline for the last ~2.6 s
  "baseline": {"clouds": 0.3},               // channel values before the event (omit for defaults)
  "stages": [                                // 5-8 stages (tiktok: 6-10), first one starts at event_at
    {"label": "BLACKOUT", "captions": ["line1\\nline2", "..."], "effects": {"power": 0}, "snap": ["power"]},
    {"world_seconds": 60, "label": "...", "captions": ["..."], "effects": {...}},   // time mode: when the stage starts
    {"value": 12, ...}                                                               // number mode: counter value at stage start
  ],
  "title": "What If All Electronics Stopped Working? ⚡",    // <= 70 chars, the question + 1 emoji
  "description": "2-4 sentences + a question for comments + 6-10 hashtags incl. #Shorts",
  "tags": ["what if", "..."],                // 8-15 tags
  "tiktok_caption": "Hook sentence + question for comments + 3-6 hashtags"   // required when platform is tiktok
}
Effects semantics: each stage's "effects" are the channel values reached by the END of that stage (smooth ramp
from the previous value). Channels listed in "snap" jump instantly at the stage start instead.
"""

def validate(spec):
    errs = []
    req = ["premise", "template", "counter", "hook", "final_caption", "stages", "title", "description", "tags"]
    for k in req:
        if k not in spec: errs.append("missing key: " + k)
    if errs: return errs
    if spec["template"] not in TEMPLATES: errs.append("template must be one of %s" % TEMPLATES)
    plat = spec.get("platform", "youtube")
    if plat not in PLATFORMS: errs.append("platform must be one of %s" % list(PLATFORMS)); plat = "youtube"
    dmin, dmax, smax = PLATFORMS[plat]
    dur = spec.get("duration", 60)
    if not (dmin <= dur <= dmax): errs.append("duration must be %d-%d for %s" % (dmin, dmax, plat))
    if plat == "tiktok" and not spec.get("tiktok_caption"): errs.append("tiktok_caption required for platform tiktok")
    if len(spec.get("tiktok_caption", "")) > 2000: errs.append("tiktok_caption too long (max 2000 chars)")
    if not (2.5 <= spec.get("event_at", 3.8) <= 5): errs.append("event_at must be 2.5-5")
    c = spec["counter"]
    mode = c.get("mode")
    if mode == "time":
        if not (60 <= float(c.get("end_world_seconds", 0)) <= 1e18): errs.append("counter.end_world_seconds must be 60..1e18")
    elif mode == "number":
        for k in ("start", "end"):
            if not isinstance(c.get(k), (int, float)): errs.append("counter.%s must be a number" % k)
        if c.get("start") == c.get("end"): errs.append("counter start and end must differ")
    else: errs.append("counter.mode must be 'time' or 'number'")
    if not c.get("label"): errs.append("counter.label required")
    st = spec["stages"]
    if not (4 <= len(st) <= smax): errs.append("need 4-%d stages" % smax)
    allowed = set(CHANNELS) | {"daylight"}
    for i, s in enumerate(st):
        if not s.get("label"): errs.append("stage %d: label required" % i)
        if len(s.get("label", "")) > 24: errs.append("stage %d: label too long (max 24 chars)" % i)
        caps = s.get("captions", [])
        if not (1 <= len(caps) <= 2): errs.append("stage %d: 1-2 captions" % i)
        for cp in caps:
            for line in cp.split("\n"):
                if len(line) > 34: errs.append("stage %d: caption line too long (max 34 chars): %r" % (i, line))
            if cp.count("\n") > 1: errs.append("stage %d: caption max 2 lines" % i)
        for k, v in s.get("effects", {}).items():
            if k not in allowed: errs.append("stage %d: unknown channel %r" % (i, k)); continue
            lo, hi = RANGES.get(k, (0, 1))
            if not isinstance(v, (int, float)) or not (lo <= v <= hi): errs.append("stage %d: %s must be %s..%s" % (i, k, lo, hi))
        for k in s.get("snap", []):
            if k not in s.get("effects", {}): errs.append("stage %d: snap channel %r not in effects" % (i, k))
        if i > 0:
            key = "world_seconds" if mode == "time" else "value"
            if key not in s: errs.append("stage %d: needs %r" % (i, key))
    for k, v in spec.get("baseline", {}).items():
        if k not in allowed: errs.append("baseline: unknown channel %r" % k)
    for name, txt in (("hook", spec["hook"]), ("final_caption", spec["final_caption"])):
        for line in txt.split("\n"):
            if len(line) > 34: errs.append("%s line too long (max 34 chars): %r" % (name, line))
        if txt.count("\n") > 1: errs.append(name + " max 2 lines")
    if len(spec["title"]) > 90: errs.append("title too long")
    if len(spec["description"]) > 4000: errs.append("description too long")
    if len(", ".join(spec["tags"])) > 450: errs.append("tags too long")
    if errs: return errs
    # timing checks via the real timeline
    try:
        tl = Timeline(spec)
    except Exception as e:
        return ["timeline error: %s" % e]
    ats = [s["at"] for s in tl.stages]
    if any(b - a < 0 for a, b in zip(ats, ats[1:])): errs.append("stages must be in increasing order of world_seconds/value")
    for i, s in enumerate(tl.stages):
        span = min(s["end"], tl.final_at) - s["at"]
        n = len(s.get("captions", []))
        if span < 2.6: errs.append("stage %d (%s) lasts only %.1fs on screen; spread world_seconds/values out (min 2.6s)" % (i, s["label"], span))
        elif n and span / n < 2.2: errs.append("stage %d (%s): %d captions in %.1fs is too fast; use 1 caption" % (i, s["label"], n, span))
    if tl.stages[-1]["at"] > tl.final_at - 2.5: errs.append("last stage starts too late (%.1fs); it must start >= 2.5 s before the final caption at %.1fs" % (tl.stages[-1]["at"], tl.final_at))
    return errs

def stage_timing_table(spec):
    tl = Timeline(spec)
    return "\n".join("  stage %d %-22s %5.1fs -> %5.1fs" % (i, s["label"], s["at"], s["end"]) for i, s in enumerate(tl.stages))

def sheet_times(spec):
    tl = Timeline(spec)
    ts = [1.2]
    for s in tl.stages: ts.append(min(s["end"], tl.final_at) * 0.5 + s["at"] * 0.5)
    ts.append(tl.dur - 0.9)
    return ts[:12]
