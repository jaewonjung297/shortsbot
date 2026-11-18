"""Spec -> timeline: counter values, stage times, captions and effect channels over video time."""
import math

CHANNELS = {
    # name: (default, description)
    "power": (1.0, "1 = grid, screens and lights on; 0 = all electricity gone"),
    "traffic": (1.0, "1 = vehicles moving; 0 = all vehicles stopped (car template)"),
    "vegetation": (0.0, "0 = clean city; 1 = fully overgrown (grass, vines, trees)"),
    "decay": (0.0, "0 = new; 1 = rust, grime, dust, broken windows"),
    "water": (0.0, "flood/sea level: 0 = normal, 1 = maximum flood for the template"),
    "snow": (0.0, "0 = none; 1 = everything buried white, heavy snowfall while rising"),
    "rain": (0.0, "0 = dry; 1 = heavy storm, dark sky, rain on glass"),
    "smoke": (0.0, "0 = clear; 1 = fires, smoke plumes and ash haze"),
    "red_sky": (0.0, "0 = normal sky; 1 = apocalyptic red/orange tint"),
    "sun_scale": (1.0, "apparent sun size/brightness: 0 = sun gone, 1 = normal, 4 = huge/hot"),
    "moon_scale": (1.0, "apparent moon size: 1 = normal, 8 = moon looming close"),
    "stars": (0.0, "extra star visibility 0..1 (stars also appear automatically when lights go out at night)"),
    "shake": (0.0, "camera shake / earthquake intensity 0..1"),
    "clouds": (0.35, "cloud cover 0..1"),
    "wind": (0.2, "wind strength 0..1 (sound, debris, sway)"),
    "heat": (0.0, "0 = normal; 1 = scorching: warm haze, browned vegetation"),
}

def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def sstep(a, b, x):
    if b == a: return 1.0 if x >= b else 0.0
    t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t)


class Timeline:
    def __init__(self, spec):
        self.spec = spec
        self.dur = float(spec.get("duration", 60))
        self.ev = float(spec.get("event_at", 3.8))
        self.t0 = self.ev + 0.5            # counter starts after the flicker
        self.start_hour = float(spec.get("start_hour", 21))
        c = spec["counter"]
        self.mode = c.get("mode", "time")
        self.counter = c
        if self.mode == "time":
            end = float(c.get("end_world_seconds", 3.156e7 * 5))
            self.a = math.log10(end + 1) / (self.dur - 0.3 - self.t0)
            self.rate_text = c.get("rate_text") or "×10 EVERY %.1f S" % (1 / self.a)
        else:
            self.v0, self.v1 = float(c["start"]), float(c["end"])
            self.log = bool(c.get("log", False)) and self.v0 > 0 and self.v1 > 0
            self.rate_text = c.get("rate_text", "")
        # stage times
        self.stages = []
        for i, st in enumerate(spec["stages"]):
            if i == 0: at = self.ev
            elif self.mode == "time": at = self.t_for_world(float(st["world_seconds"]))
            else: at = self.t_for_value(float(st["value"]))
            self.stages.append(dict(st, at=at))
        self.stages.sort(key=lambda s: s["at"])
        for i, st in enumerate(self.stages):
            st["end"] = self.stages[i + 1]["at"] if i + 1 < len(self.stages) else self.dur
        # captions: hook before the event, stage captions spread over each stage, final at the end
        self.final_at = self.dur - float(spec.get("final_caption_seconds", 2.6))
        caps = [(0.0, self.ev - 0.05, spec["hook"])]
        for st in self.stages:
            texts = st.get("captions", [])
            a, b = st["at"] + 0.35, min(st["end"], self.final_at) - 0.2
            if not texts or b - a < 0.8: continue
            n = len(texts); step = (b - a) / n
            for k, txt in enumerate(texts):
                caps.append((a + k * step, a + (k + 1) * step - 0.15, txt))
        caps.append((self.final_at, self.dur + 1, spec["final_caption"]))
        self.captions = caps
        # channel keyframes
        base = dict((k, v[0]) for k, v in CHANNELS.items())
        base.update(spec.get("baseline", {}))
        self.has_daylight = "daylight" in spec.get("baseline", {}) or any("daylight" in s.get("effects", {}) for s in self.stages)
        if self.has_daylight: base.setdefault("daylight", 0.0)
        self.keys = {}
        for name in list(base.keys()):
            pts = [(0.0, base[name], 0)]
            cur = base[name]
            for st in self.stages:
                eff = st.get("effects", {})
                if name in eff:
                    tgt = float(eff[name])
                    if name in st.get("snap", []):
                        pts.append((st["at"], cur, 0)); pts.append((st["at"] + 0.05, tgt, 1))
                    else:
                        pts.append((st["at"], cur, 0)); pts.append((st["end"], tgt, 1))
                    cur = tgt
            self.keys[name] = pts
        # first time traffic drops
        self.t_stop = None
        for st in self.stages:
            if "traffic" in st.get("effects", {}) and st["effects"]["traffic"] < 0.5:
                self.t_stop = st["at"]; break
        self.t_power_off = None
        for st in self.stages:
            if "power" in st.get("effects", {}) and st["effects"]["power"] < 0.5:
                self.t_power_off = st["at"]; break

    # ---- counter
    def world(self, t):
        if self.mode != "time" or t < self.t0: return 0.0
        return 10 ** (self.a * (t - self.t0)) - 1

    def t_for_world(self, w):
        return self.t0 + math.log10(w + 1) / self.a

    def value(self, t):
        if t < self.t0: return self.v0
        f = clamp((t - self.t0) / (self.dur - 1.0 - self.t0))
        if self.log: return self.v0 * (self.v1 / self.v0) ** f
        return self.v0 + (self.v1 - self.v0) * f

    def t_for_value(self, v):
        if self.log: f = math.log(v / self.v0) / math.log(self.v1 / self.v0)
        else: f = (v - self.v0) / (self.v1 - self.v0)
        return self.t0 + clamp(f) * (self.dur - 1.0 - self.t0)

    def world_rate_days(self, t):
        if self.mode != "time": return 0.0
        w = self.world(t)
        return (w + 1) * math.log(10) * self.a / 86400.0

    def progress(self, t):
        """0..1 log progress of the counter (for generic growth effects)."""
        return clamp((t - self.t0) / (self.dur - self.t0))

    # ---- channels
    def ch(self, name, t):
        pts = self.keys.get(name)
        if pts is None: return CHANNELS[name][0]
        if t <= pts[0][0]: return pts[0][1]
        for i in range(1, len(pts)):
            if t < pts[i][0]:
                a, b = pts[i - 1], pts[i]
                u = sstep(a[0], b[0], t)
                return a[1] + (b[1] - a[1]) * u
        return pts[-1][1]

    def dch(self, name, t, h=0.25):
        return (self.ch(name, t + h) - self.ch(name, t - h)) / (2 * h)

    def stage_index(self, t):
        i = -1
        for k, st in enumerate(self.stages):
            if t >= st["at"]: i = k
        return i

    def hour(self, t):
        if self.mode == "time":
            return (self.start_hour + self.world(t) / 3600.0) % 24.0
        return (self.start_hour + t * float(self.spec.get("hours_per_second", 0.0))) % 24.0

    def caption_at(self, t):
        for (a, b, s) in self.captions:
            if a <= t < b: return a, b, s
        return None

    def counter_text(self, t):
        c = self.counter
        if self.mode == "time":
            return fmt_time(self.world(t))
        v = self.value(t)
        dec = int(c.get("decimals", 0))
        big = ("{:,.%df}" % dec).format(v)
        return big, c.get("unit", "")


def fmt_time(W):
    if W < 10: return "%.1f s" % W, ""
    if W < 60: return "%d s" % W, ""
    if W < 3600: return "%d min" % (W // 60), "%02d s" % (W % 60)
    if W < 86400: return "%d h" % (W // 3600), "%02d min" % ((W % 3600) // 60)
    if W < 86400 * 30:
        dd = int(W // 86400); return ("%d day" % dd) + ("s" if dd != 1 else ""), "%d h" % ((W % 86400) // 3600)
    if W < 3.156e7: return "%.1f months" % (W / 2.63e6), ""
    y = W / 3.156e7
    if y < 100: return "%.1f years" % y, ""
    if y < 1e4: return "{:,} years".format(int(y)), ""
    if y < 1e6: return "%dk years" % (y // 1000), ""
    if y < 1e9: return "%.1fM years" % (y / 1e6), ""
    return "%.1fB years" % (y / 1e9), ""
