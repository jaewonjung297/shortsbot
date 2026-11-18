"""Shared low-poly renderer: projection, lighting, sky, weather, HUD and captions."""
import math, random
import cairo
from .timeline import clamp, sstep

W_PX, H_PX, FPS = 1080, 1920, 30
SERIF, SANS = "Caladea", "Inter"

def lerp(a, b, t): return a + (b - a) * t
def lerpc(c1, c2, t): return tuple(lerp(c1[i], c2[i], t) for i in range(3))
def mulc(c, k): return tuple(x * k for x in c)
def addc(a, b): return tuple(a[i] + b[i] for i in range(3))
def ease_io(x): x = clamp(x); return x * x * (3 - 2 * x)
def norm(v):
    l = math.sqrt(sum(x * x for x in v)) or 1; return tuple(x / l for x in v)
def lum(c): return (c[0] + c[1] + c[2]) / 3


# ------------------------------------------------------------------ camera + polygons
class View:
    """Camera + projection + optional water clip plane."""
    def __init__(self, pos, pitch=0.0, roll=0.0, yaw=0.0, f=900.0, cx=540.0, cy=840.0):
        self.p = pos; self.f, self.cx, self.cy = f, cx, cy
        self.cp, self.sp = math.cos(pitch), math.sin(pitch)
        self.cr, self.sr = math.cos(roll), math.sin(roll)
        self.cy_, self.sy_ = math.cos(yaw), math.sin(yaw)
        self.water = None

    def to_cam(self, v):
        x, y, z = v[0] - self.p[0], v[1] - self.p[1], v[2] - self.p[2]
        x, z = x * self.cy_ - z * self.sy_, x * self.sy_ + z * self.cy_
        y, z = y * self.cp - z * self.sp, y * self.sp + z * self.cp
        x, y = x * self.cr - y * self.sr, x * self.sr + y * self.cr
        return (x, y, z)

    def proj(self, c):
        return (self.cx + self.f * c[0] / c[2], self.cy - self.f * c[1] / c[2])

    def pt(self, p):
        c = self.to_cam(p)
        if c[2] < NEAR: return None
        return self.proj(c) + (c[2],)

    def dist(self, p):
        return math.sqrt((p[0] - self.p[0]) ** 2 + (p[1] - self.p[1]) ** 2 + (p[2] - self.p[2]) ** 2)

NEAR = 0.15

def _clip(pts, inside, inter):
    out = []; n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        ia, ib = inside(a), inside(b)
        if ia: out.append(a)
        if ia != ib: out.append(inter(a, b))
    return out

def clip_near(pts):
    def inter(a, b):
        t = (NEAR - a[2]) / (b[2] - a[2])
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, NEAR)
    return _clip(pts, lambda p: p[2] >= NEAR, inter)

def clip_above(pts, h):
    def inter(a, b):
        t = (h - a[1]) / (b[1] - a[1])
        return (a[0] + (b[0] - a[0]) * t, h, a[2] + (b[2] - a[2]) * t)
    return _clip(pts, lambda p: p[1] >= h, inter)

def poly3(ctx, V, pts, color, alpha=1.0, normal=None, wclip=True):
    if normal is not None:
        c0 = pts[0]
        if (V.p[0] - c0[0]) * normal[0] + (V.p[1] - c0[1]) * normal[1] + (V.p[2] - c0[2]) * normal[2] <= 0:
            return False
    if wclip and V.water is not None:
        pts = clip_above(pts, V.water)
        if len(pts) < 3: return False
    cp = [V.to_cam(p) for p in pts]
    cp = clip_near(cp)
    if len(cp) < 3: return False
    s = [V.proj(c) for c in cp]
    ctx.move_to(*s[0])
    for q in s[1:]: ctx.line_to(*q)
    ctx.close_path()
    ctx.set_source_rgba(color[0], color[1], color[2], alpha)
    ctx.fill()
    return True

def poly2(ctx, pts, col, a=1.0):
    ctx.move_to(*pts[0])
    for p in pts[1:]: ctx.line_to(*p)
    ctx.close_path()
    ctx.set_source_rgba(col[0], col[1], col[2], a); ctx.fill()

def rrect(ctx, x, y, w, h, r):
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0); ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi); ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()

def box_faces(x0, y0, z0, x1, y1, z1, top=True):
    f = [
        ([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], (-1, 0, 0)),
        ([(x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)], (1, 0, 0)),
        ([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], (0, 0, -1)),
        ([(x0, y0, z1), (x0, y1, z1), (x1, y1, z1), (x1, y0, z1)], (0, 0, 1)),
    ]
    if top: f.append(([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], (0, 1, 0)))
    return f

def glow(ctx, x, y, r, col, a):
    if r < 0.5 or a <= 0.01: return
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, col[0], col[1], col[2], a)
    g.add_color_stop_rgba(0.25, col[0], col[1], col[2], a * 0.45)
    g.add_color_stop_rgba(1, col[0], col[1], col[2], 0)
    ctx.set_source(g); ctx.arc(x, y, r, 0, 2 * math.pi); ctx.fill()

def glow_add(ctx, x, y, r, col, a):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD); glow(ctx, x, y, r, col, a); ctx.restore()

def draw_glows(ctx, glows):
    ctx.save(); ctx.set_operator(cairo.OPERATOR_ADD)
    for (gx, gy, r, col, a) in glows: glow(ctx, gx, gy, min(r, 420), col, a)
    ctx.restore()


# ------------------------------------------------------------------ environment
def environment(tl, t):
    """Everything time-dependent that templates share."""
    ch = lambda n: tl.ch(n, t)
    env = {k: ch(k) for k in ("power", "traffic", "vegetation", "decay", "water", "snow", "rain", "smoke",
                              "red_sky", "sun_scale", "moon_scale", "stars", "shake", "clouds", "wind", "heat")}
    # flicker right when power drops
    if tl.t_power_off is not None and tl.t_power_off <= t < tl.t_power_off + 0.55:
        seq = [1, 0, 1, 0, 0, 0.6, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        env["power"] = seq[min(len(seq) - 1, int((t - tl.t_power_off) * 30))]
    elif tl.t_power_off is not None and t >= tl.t_power_off + 0.55:
        env["power"] = min(env["power"], tl.ch("power", t))
    hour = tl.hour(t)
    e = math.sin((hour - 6.0) / 24.0 * 2 * math.pi)        # sun elevation proxy
    env["hour"], env["elev"] = hour, e
    sun_bright = clamp(env["sun_scale"], 0, 1.4)
    d = sstep(-0.12, 0.3, e)
    tw = math.exp(-(e / 0.16) ** 2)
    rate = tl.world_rate_days(t)
    b = sstep(0.5, 2.2, rate)                              # fast cycling -> averaged daylight
    d = lerp(d, 0.8, b); tw = lerp(tw, 0.08, b)
    if tl.has_daylight: d = ch("daylight"); tw = 0.0; b = 0.0
    d *= min(1.0, sun_bright)
    env["fast"] = b
    overcast = clamp(env["rain"] * 0.9 + env["smoke"] * 0.5 + env["clouds"] * 0.15)
    d_eff = d * (1 - 0.45 * overcast)
    env["day"], env["tw"] = d, tw
    night_top, night_hor = (0.012, 0.018, 0.05), (0.06, 0.08, 0.15)
    city_top, city_hor = (0.06, 0.045, 0.07), (0.36, 0.22, 0.17)
    day_top, day_hor = (0.30, 0.55, 0.86), (0.76, 0.86, 0.94)
    p = env["power"]
    glow_night = p * (1 - d)
    top = lerpc(lerpc(night_top, city_top, glow_night), day_top, d)
    hor = lerpc(lerpc(night_hor, city_hor, glow_night), day_hor, d)
    hor = lerpc(hor, (1.0, 0.55, 0.32), tw * 0.8 * sun_bright)
    top = lerpc(top, (0.35, 0.30, 0.55), tw * 0.4 * sun_bright)
    amb = lerpc(lerpc((0.13, 0.15, 0.23), (0.30, 0.25, 0.24), glow_night), (0.50, 0.53, 0.60), d)
    sun = lerpc(lerpc((0.16, 0.18, 0.28), (0.30, 0.24, 0.16), glow_night), (0.78, 0.72, 0.60), d)
    sun = lerpc(sun, (0.9, 0.5, 0.3), tw * 0.6)
    L = norm((-0.45, lerp(0.6, 0.75, d), -0.5)) if d > 0.3 else norm((0.5, 0.6, 0.55))
    fog_d = lerp(140, 230, d)
    # big hot sun
    hot = clamp((env["sun_scale"] - 1.0) / 3.0) + env["heat"] * 0.6
    if hot > 0:
        top = lerpc(top, (0.85, 0.55, 0.3), hot * 0.5 * d); hor = lerpc(hor, (1.0, 0.85, 0.6), hot * 0.6 * d)
        amb = lerpc(amb, (0.75, 0.6, 0.45), hot * 0.4 * d); sun = lerpc(sun, (1.0, 0.8, 0.55), hot * 0.5)
    # weather / disasters
    gray = (0.42, 0.44, 0.48)
    top = lerpc(top, mulc(gray, 0.4 + 0.6 * d), overcast * 0.75)
    hor = lerpc(hor, mulc(gray, 0.5 + 0.7 * d), overcast * 0.6)
    sun = mulc(sun, 1 - 0.6 * overcast)
    fog_d = fog_d * (1 - 0.55 * env["rain"]) * (1 - 0.6 * env["smoke"])
    red = env["red_sky"]
    if red > 0:
        top = lerpc(top, (0.35, 0.06, 0.04), red * 0.8); hor = lerpc(hor, (0.95, 0.35, 0.12), red * 0.85)
        amb = lerpc(amb, (0.55, 0.28, 0.2), red * 0.6); sun = lerpc(sun, (0.9, 0.35, 0.15), red * 0.6)
    sn = env["snow"]
    if sn > 0:
        amb = lerpc(amb, addc(amb, (0.12, 0.13, 0.16)), sn)
        hor = lerpc(hor, lerpc(hor, (0.85, 0.88, 0.92), 0.5), sn * d)
    env.update(top=top, hor=hor, amb=amb, sun=sun, L=L, fog=hor, fog_d=fog_d)
    # stars: dark sky after lights go out, plus explicit channel
    st = 0.0
    if p < 0.5:
        since = t - (tl.t_power_off or 0)
        st = 0.3 + 0.7 * sstep(4.0, 9.0, since)
    st = clamp(max(st * (1 - 0.3 * p), env["stars"]))
    env["stars_a"] = st * (1 - d) * (1 - b) * (1 - overcast * 0.9)
    env["sun_a"] = clamp(env["sun_scale"] * 3) * (1 - b) * (1 - overcast * 0.8)
    env["t"] = t
    return env

def shade(env, base, n, dist):
    if n is None: k = addc(env["amb"], mulc(env["sun"], 0.5))
    else:
        L = env["L"]
        dot = max(0.0, n[0] * L[0] + n[1] * L[1] + n[2] * L[2])
        k = addc(env["amb"], mulc(env["sun"], dot))
    c = tuple(base[i] * k[i] * 1.6 for i in range(3))
    f = 1 - math.exp(-dist / env["fog_d"])
    return lerpc(c, env["fog"], f)

def fogged(env, c, dist):
    f = 1 - math.exp(-dist / env["fog_d"]); return lerpc(c, env["fog"], f)

def foliage(env, base, seed):
    autumn = lerpc((0.85, 0.5, 0.15), (0.72, 0.3, 0.12), seed)
    c = base
    if env.get("season_w", 0) > 0:
        s = sstep(0.55, 0.95, env["season"]) * env["season_w"]
        c = lerpc(c, autumn, s * 0.55)
    c = lerpc(c, (0.62, 0.55, 0.3), env["heat"] * 0.8)
    c = lerpc(c, (0.92, 0.94, 0.97), env["snow"] * 0.85)
    return c

def add_season(tl, env, t):
    W = tl.world(t)
    env["season"] = 0.5 + 0.5 * math.sin(W / (365.25 * 86400) * 2 * math.pi - 1.2) if W > 2.6e6 else 0.0
    env["season_w"] = sstep(2.6e6, 1.2e7, W)


# ------------------------------------------------------------------ sky
class Sky:
    def __init__(self, seed, horizon_y, sky_bottom=None):
        r = random.Random(seed)
        self.hy = horizon_y
        self.stars = [(r.uniform(0, W_PX), r.uniform(0, horizon_y), r.uniform(0.2, 1.0) ** 2, r.uniform(0.8, 2.4)) for _ in range(650)]
        ang = r.uniform(0.3, 0.7)
        for _ in range(1400):
            u = r.uniform(0, 1); off = r.gauss(0, 55)
            self.stars.append((lerp(-100, 1200, u), lerp(80, horizon_y - 60, u) * 1 + off, r.uniform(0.1, 0.6) ** 2, r.uniform(0.6, 1.5)))
        self.mw_ang = math.atan2(horizon_y - 140, 1300)
        self.clouds = [(r.uniform(0, 1700), r.uniform(60, horizon_y * 0.7), r.uniform(0.6, 1.5), r.uniform(0.7, 1.3), r.random(),
                        [(r.uniform(-90, 90), r.uniform(-20, 20), r.uniform(40, 80)) for _ in range(4)]) for _ in range(14)]
        self.birds = [(r.uniform(0, 1), r.uniform(120, horizon_y * 0.6), r.uniform(0.6, 1.3), r.uniform(0, 6.28)) for _ in range(9)]
        self.sun_x = r.uniform(300, 780)
        self.plumes = [(r.uniform(150, 930), r.uniform(0.6, 1.3), r.random()) for _ in range(3)]

    def sun_pos(self, env):
        e = env["elev"]
        h = env["hour"]
        x = self.sun_x + (h - 12) * 40
        y = self.hy - 120 - e * 720
        return x, y

    def draw(self, ctx, env, t, tl):
        g = cairo.LinearGradient(0, 0, 0, self.hy + 40)
        g.add_color_stop_rgb(0, *env["top"]); g.add_color_stop_rgb(1, *env["hor"])
        ctx.set_source(g); ctx.rectangle(0, 0, W_PX, H_PX); ctx.fill()
        sa = env["stars_a"]
        if sa > 0.01:
            ctx.save(); ctx.translate(540, self.hy * 0.5); ctx.rotate(self.mw_ang)
            for (hh, a_, col) in ((150, 0.16, (0.75, 0.7, 0.95)), (55, 0.12, (0.95, 0.85, 0.8))):
                band = cairo.LinearGradient(0, -hh, 0, hh)
                band.add_color_stop_rgba(0, *col, 0); band.add_color_stop_rgba(0.5, *col, a_ * sa); band.add_color_stop_rgba(1, *col, 0)
                ctx.set_source(band); ctx.rectangle(-1000, -hh, 2000, 2 * hh); ctx.fill()
            ctx.restore()
            for (sx, sy, b, r) in self.stars:
                if sy > self.hy: continue
                tw = 0.75 + 0.25 * math.sin(t * 3 + sx * 0.1)
                ctx.set_source_rgba(1, 1, 0.95, clamp(b * sa * tw))
                ctx.arc(sx, sy, r, 0, 2 * math.pi); ctx.fill()
        # sun
        if env["sun_a"] > 0.01 and env["elev"] > -0.25 and env["sun_scale"] > 0.02:
            x, y = self.sun_pos(env)
            r = 46 * env["sun_scale"]
            col = lerpc((1.0, 0.95, 0.8), (1.0, 0.55, 0.3), env["tw"] * 0.8 + env["red_sky"] * 0.5)
            glow_add(ctx, x, y, r * 5, col, 0.35 * env["sun_a"])
            pts = [(x + r * math.cos(a), y + r * math.sin(a)) for a in [k * math.pi / 6 for k in range(12)]]
            poly2(ctx, pts, col, env["sun_a"])
        # moon (opposite the sun); looms when moon_scale is big
        ms = env["moon_scale"]
        night = 1 - env["day"]
        if ms > 0.05 and (night > 0.05 or ms > 2):
            mx = 1080 - self.sun_x * 0.8 + 120
            my = self.hy * 0.32 - (ms - 1) * 25
            r = 30 * ms
            a = clamp(night * 1.2 + (ms - 1) * 0.15) * (1 - env["rain"] * 0.8)
            glow_add(ctx, mx, my, r * 3.2, (0.8, 0.85, 1.0), 0.25 * a)
            rr = random.Random(9)
            facets = 14
            pts = [(mx + r * math.cos(k * 2 * math.pi / facets), my + r * math.sin(k * 2 * math.pi / facets)) for k in range(facets)]
            poly2(ctx, pts, lerpc((0.85, 0.86, 0.9), (0.95, 0.75, 0.6), env["red_sky"]), a)
            for k in range(7):
                cxp, cyp, cr = mx + rr.uniform(-0.6, 0.6) * r, my + rr.uniform(-0.6, 0.6) * r, rr.uniform(0.08, 0.22) * r
                pts = [(cxp + cr * math.cos(q * math.pi / 3), cyp + cr * math.sin(q * math.pi / 3)) for q in range(6)]
                poly2(ctx, pts, (0.62, 0.63, 0.68), a * 0.8)
            # shading crescent side
            ctx.save(); ctx.arc(mx, my, r, 0, 2 * math.pi); ctx.clip()
            poly2(ctx, [(mx + r * 0.35, my - r), (mx + r, my - r), (mx + r, my + r), (mx + r * 0.35, my + r)], (0.1, 0.1, 0.15), a * 0.45)
            ctx.restore()
        # clouds
        cover = env["clouds"]
        if cover > 0.02:
            disp = 25 * t + 260 * max(0.0, t - (tl.t0 + 25)) ** 1.5 * env["fast"] + 60 * env["wind"] * t
            ca = clamp(0.25 + env["day"]) * 0.92
            base = lerpc((0.95, 0.96, 0.98), (1.0, 0.75, 0.6), env["tw"])
            base = lerpc(base, (0.35, 0.36, 0.4), clamp(env["rain"] + env["smoke"] * 0.7))
            base = lerpc(mulc(base, 0.35), base, env["day"])
            base = lerpc(base, (0.8, 0.4, 0.25), env["red_sky"] * 0.6)
            shadow = lerpc(base, env["top"], 0.35)
            n = int(len(self.clouds) * clamp(cover))
            for (x0, cy_, sc, sp, ph, blobs) in self.clouds[:max(1, n)]:
                cx_ = (x0 + disp * sp * (0.4 + 0.6 * (cy_ / self.hy))) % 1700 - 300
                s2 = sc * (1 + cover * 0.8)
                for (bx, by, br) in blobs:
                    for layer, col, dy in ((0, shadow, 6), (1, base, 0)):
                        r = br * s2 * (0.85 if layer else 1)
                        pts = [(cx_ + bx * s2 + r * math.cos(a), cy_ + by * s2 + dy + r * 0.62 * math.sin(a)) for a in [k * math.pi / 3 + 0.3 for k in range(6)]]
                        poly2(ctx, pts, col, ca)
        # smoke plumes on the horizon
        sm = env["smoke"]
        if sm > 0.02:
            for (px, sc, ph) in self.plumes:
                for k in range(16):
                    u = k / 15
                    yy = self.hy + 30 - u * 650 * sc * sm
                    xx = px + math.sin(u * 3 + t * 0.6 + ph * 6) * 40 * u + env["wind"] * 220 * u * u
                    r = (25 + 90 * u) * sc * (0.5 + sm)
                    col = lerpc((0.22, 0.2, 0.2), (0.45, 0.42, 0.4), u)
                    col = lerpc(mulc(col, 0.5), col, env["day"] * 0.8 + 0.2)
                    pts = [(xx + r * math.cos(a + u * 2), yy + r * 0.8 * math.sin(a + u * 2)) for a in [q * math.pi / 3 for q in range(6)]]
                    poly2(ctx, pts, col, 0.75 * sm * (1 - u * 0.6))
                glow_add(ctx, px, self.hy + 20, 160 * sc, (1.0, 0.45, 0.15), 0.35 * sm * (1 - env["day"] * 0.6))
        # birds
        if env["vegetation"] > 0.25 and env["day"] > 0.3 and env["rain"] < 0.4:
            ctx.set_line_width(3); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            bc = mulc(env["top"], 0.3)
            for (u, by, sp, ph) in self.birds:
                bx = ((u + t * 0.05 * sp) % 1.3) * W_PX - 100
                yy = by + 20 * math.sin(t * 0.7 + ph)
                fl = math.sin(t * 9 * sp + ph) * 10
                ctx.set_source_rgba(bc[0], bc[1], bc[2], 0.8 * sstep(0.25, 0.5, env["vegetation"]))
                ctx.move_to(bx - 14, yy - fl); ctx.line_to(bx, yy); ctx.line_to(bx + 14, yy - fl); ctx.stroke()


# ------------------------------------------------------------------ weather particles (screen space)
def draw_precip(ctx, env, t, region=(0, 0, W_PX, 1260), seed=1):
    x0, y0, w, h = region
    rain, snow = env["rain"], env["snow"]
    wind = env["wind"]
    if rain > 0.03:
        r = random.Random(seed)
        n = int(260 * rain)
        ctx.set_line_width(2); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        c = lerpc((0.7, 0.75, 0.85), (0.9, 0.92, 1.0), env["day"])
        for i in range(n):
            sx = r.uniform(0, 1); sy = r.uniform(0, 1); sp = r.uniform(0.8, 1.3)
            yy = y0 + ((sy + t * 1.9 * sp) % 1.0) * h
            xx = x0 + ((sx + (yy - y0) / h * 0.15 * wind) % 1.0) * w
            ctx.set_source_rgba(c[0], c[1], c[2], 0.35 * rain)
            ctx.move_to(xx, yy); ctx.line_to(xx - 12 * wind - 3, yy - 46 * sp); ctx.stroke()
    fall = snow * (1.0 if snow < 0.97 else 0.4)
    if fall > 0.03:
        r = random.Random(seed + 5)
        n = int(320 * fall)
        for i in range(n):
            sx = r.uniform(0, 1); sy = r.uniform(0, 1); sp = r.uniform(0.4, 1.0); sz = r.uniform(2, 6)
            yy = y0 + ((sy + t * 0.18 * sp) % 1.0) * h
            xx = x0 + ((sx + math.sin(t * 1.3 + i) * 0.01 + t * 0.03 * wind) % 1.0) * w
            ctx.set_source_rgba(1, 1, 1, 0.85 * fall)
            ctx.arc(xx, yy, sz * sp, 0, 2 * math.pi); ctx.fill()
    sm = env["smoke"]
    if sm > 0.3:
        r = random.Random(seed + 9)
        for i in range(int(120 * (sm - 0.3))):
            sx, sy, sp = r.uniform(0, 1), r.uniform(0, 1), r.uniform(0.3, 0.8)
            yy = y0 + ((sy + t * 0.08 * sp) % 1.0) * h
            xx = x0 + ((sx + t * 0.02) % 1.0) * w
            ctx.set_source_rgba(0.55, 0.52, 0.5, 0.5 * sm)
            ctx.rectangle(xx, yy, 3, 3); ctx.fill()

def draw_glass_drops(ctx, env, t, region, seed=3):
    """Raindrops sliding on a windshield/window."""
    rain = env["rain"]
    if rain < 0.05: return
    x0, y0, w, h = region
    r = random.Random(seed)
    for i in range(int(90 * rain)):
        sx, sy, sp, sz = r.uniform(0, 1), r.uniform(0, 1), r.uniform(0.02, 0.15), r.uniform(4, 11)
        yy = y0 + ((sy + t * sp) % 1.0) * h; xx = x0 + sx * w
        ctx.set_source_rgba(0.85, 0.9, 1.0, 0.22 * rain)
        ctx.arc(xx, yy, sz, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgba(1, 1, 1, 0.3 * rain)
        ctx.arc(xx - sz * 0.3, yy - sz * 0.3, sz * 0.3, 0, 2 * math.pi); ctx.fill()


# ------------------------------------------------------------------ HUD + captions
def text_shadow(ctx, x, y, s, size, face, weight=cairo.FONT_WEIGHT_NORMAL, col=(1, 1, 1), a=1.0, spacing=0.0, center=False):
    ctx.select_font_face(face, cairo.FONT_SLANT_NORMAL, weight); ctx.set_font_size(size)
    if spacing == 0:
        te = ctx.text_extents(s)
        if center: x = x - te.x_advance / 2
        for (dx, dy, aa) in [(0, 3, 0.45), (0, 1, 0.5)]:
            ctx.set_source_rgba(0, 0, 0, aa * a); ctx.move_to(x + dx, y + dy); ctx.show_text(s)
        ctx.set_source_rgba(col[0], col[1], col[2], a); ctx.move_to(x, y); ctx.show_text(s)
        return te.x_advance
    xx = x
    for ch in s:
        ctx.set_source_rgba(0, 0, 0, 0.5 * a); ctx.move_to(xx, y + 2); ctx.show_text(ch)
        ctx.set_source_rgba(col[0], col[1], col[2], a); ctx.move_to(xx, y); ctx.show_text(ch)
        xx += ctx.text_extents(ch).x_advance + spacing
    return xx - x

def fit_size(ctx, s, face, size, maxw):
    ctx.select_font_face(face, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL); ctx.set_font_size(size)
    w = ctx.text_extents(s).x_advance
    return size if w <= maxw else size * maxw / w

def draw_hud(ctx, tl, t, x0=70, y0=640):
    a = sstep(0.1, 0.5, t)
    c = tl.counter
    text_shadow(ctx, x0, y0, c.get("label", "TIME").upper(), 25, SANS, cairo.FONT_WEIGHT_BOLD, a=a * 0.95, spacing=2.5)
    big, small = tl.counter_text(t)
    si = tl.stage_index(t)
    pop = 0.0
    if si >= 0:
        tt = t - tl.stages[si]["at"]
        if 0 <= tt < 0.5: pop = math.sin(tt / 0.5 * math.pi) * (1 - tt / 0.5)
    ctx.save()
    ctx.translate(x0, y0 + 112); ctx.scale(1 + 0.12 * pop, 1 + 0.12 * pop)
    size = fit_size(ctx, big, SERIF, 112, 560)
    wbig = text_shadow(ctx, 0, 0, big, size, SERIF, a=a)
    if small: text_shadow(ctx, wbig + 16, 0, small, 52, SERIF, a=a * 0.85)
    ctx.restore()
    if si < 0:
        lab, dotc, rate = tl.spec.get("pre_label", "NORMAL").upper(), (0.3, 1.0, 0.45), tl.spec.get("pre_rate_text", "ALL SYSTEMS NORMAL").upper()
    else:
        lab, dotc, rate = tl.stages[si]["label"].upper(), (1.0, 0.25, 0.2), tl.rate_text.upper()
    labc = (1, 1, 1) if pop < 0.05 else lerpc((1, 1, 1), (1.0, 0.85, 0.4), pop)
    text_shadow(ctx, x0, y0 + 160, lab, 25, SANS, cairo.FONT_WEIGHT_BOLD, col=labc, a=a * 0.95, spacing=2.5)
    if rate:
        blink = 0.6 + 0.4 * math.sin(t * 6)
        ctx.set_source_rgba(dotc[0], dotc[1], dotc[2], a * blink); ctx.arc(x0 + 7, y0 + 192, 7, 0, 2 * math.pi); ctx.fill()
        text_shadow(ctx, x0 + 24, y0 + 200, rate, 21, SANS, cairo.FONT_WEIGHT_BOLD, a=a * 0.85, spacing=1.5)

def draw_caption(ctx, tl, t, y=1060):
    cap = tl.caption_at(t)
    if not cap: return
    a, b, s = cap
    fade = min(sstep(a, a + 0.18, t), 1 - sstep(b - 0.15, b, t)) if b < tl.dur else sstep(a, a + 0.18, t)
    rise = (1 - sstep(a, a + 0.25, t)) * 14
    lines = wrap_caption(ctx, s)
    for i, line in enumerate(lines):
        size = fit_size(ctx, line, SERIF, 56, 900)
        text_shadow(ctx, 540, y + i * 66 + rise, line, size, SERIF, col=(1, 1, 1), a=fade, center=True)

def wrap_caption(ctx, s, maxw=880):
    if "\n" in s: return s.split("\n")
    ctx.select_font_face(SERIF, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL); ctx.set_font_size(56)
    if ctx.text_extents(s).x_advance <= maxw: return [s]
    words = s.split(); best = None
    for i in range(1, len(words)):
        l1, l2 = " ".join(words[:i]), " ".join(words[i:])
        w = max(ctx.text_extents(l1).x_advance, ctx.text_extents(l2).x_advance)
        if best is None or w < best[0]: best = (w, [l1, l2])
    return best[1]

def post(ctx, tl, t):
    g = cairo.RadialGradient(540, 960, 500, 540, 960, 1250)
    g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, 0.35)
    ctx.set_source(g); ctx.paint()
    if t > tl.dur - 0.6:
        ctx.set_source_rgba(0, 0, 0, sstep(tl.dur - 0.6, tl.dur, t)); ctx.paint()
    if tl.t_power_off is not None and tl.t_power_off <= t < tl.t_power_off + 0.55:
        ctx.set_source_rgba(0, 0, 0, 0.2); ctx.paint()

def shake_offset(env, t):
    s = env["shake"]
    if s <= 0.01: return 0.0, 0.0, 0.0
    dx = (math.sin(t * 37.0) + 0.6 * math.sin(t * 23.3 + 1) + 0.4 * math.sin(t * 61.7)) * 0.04 * s
    dy = (math.sin(t * 41.0 + 2) + 0.5 * math.sin(t * 29.1)) * 0.03 * s
    roll = math.sin(t * 17.0) * 0.012 * s
    return dx, dy, roll
