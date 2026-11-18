"""Template: driver's POV, stopped at a red light on a city street."""
import math, random
import cairo
from ..engine import *
from ..timeline import clamp, sstep

NAME = "car"
DESCRIPTION = ("Driver's-seat POV at night or day, stopped at a red light on a city street with traffic, street lamps, "
               "a phone on a dash mount and the driver's hand on the wheel. Best for: power/technology, traffic, "
               "street-level flooding (water=1 is ~1 m of water on the road), snow, rain, overgrowth, decay, quakes.")
FOCUS = (917, 1377)        # finale push-in target (phone)
HUD_Y, CAPTION_Y = 640, 1060
CAM = (1.6, 1.22, 0.0)
V_ON, A_DEC, V_CR = 11.0, 4.4, 9.0

BUILD_COLS = [(0.62, 0.52, 0.44), (0.55, 0.57, 0.62), (0.70, 0.62, 0.50), (0.48, 0.42, 0.40),
              (0.64, 0.66, 0.66), (0.58, 0.46, 0.40), (0.42, 0.47, 0.55), (0.74, 0.70, 0.62)]
CAR_COLS = [(0.78, 0.16, 0.14), (0.15, 0.32, 0.62), (0.85, 0.85, 0.82), (0.18, 0.18, 0.2),
            (0.9, 0.62, 0.15), (0.36, 0.55, 0.42), (0.62, 0.64, 0.68), (0.45, 0.2, 0.35)]


class Scene:
    def __init__(self, tl, seed):
        self.tl = tl
        rng = random.Random(seed)
        self.sky = Sky(seed, 860)
        self.buildings = []
        for sign in (1, -1):
            z = -12.0
            while z < 180:
                if 28 <= z < 42: z = 42.0; continue
                w = rng.uniform(8, 15)
                z1 = min(z + w, 28.5) if z < 28 else z + w
                h = rng.choice([9, 12, 15, 18, 24, 30, 38, 46]) * (0.6 if z < 10 else 1.0)
                depth = rng.uniform(14, 22)
                x0 = 12.0 if sign > 0 else -12.0 - depth
                col = rng.choice(BUILD_COLS)
                wins = []
                for f in range(int((h - 3) / 3.2)):
                    for c in range(int((z1 - z - 1.5) / 2.6)):
                        wins.append((z + 1.2 + c * 2.6, 3.6 + f * 3.2, rng.random() < 0.62,
                                     rng.choice([(1.0, 0.82, 0.48), (1.0, 0.9, 0.62), (0.85, 0.9, 1.0), (1.0, 0.75, 0.4)]), rng.random()))
                vines = []
                for k in range(rng.randint(2, 4)):
                    vz0 = rng.uniform(z, z1 - 3); vz1 = min(z1, vz0 + rng.uniform(3, 8))
                    vines.append((vz0, vz1, rng.uniform(0.5, 0.95) * h, [rng.uniform(0.5, 1.0) for _ in range(9)], rng.random() * 0.5))
                self.buildings.append(dict(box=(x0, 0, z, x0 + depth, h, z1), col=col, sign=sign,
                                           face_x=12.0 if sign > 0 else -12.0, wins=wins, vines=vines))
                z = z1 + rng.uniform(0.0, 1.5)
        self.lamps = [(s * 9.0, z) for s in (1, -1) for z in [6, 24, 50, 70, 92, 116, 142]]
        self.trees = [dict(x=s * 10.4 + rng.uniform(-0.3, 0.3), z=z + rng.uniform(-2, 2), road=False, thr=0, seed=rng.random())
                      for s in (1, -1) for z in [14, 45, 60, 82, 104, 128]]
        self.trees += [dict(x=rng.uniform(-7.5, 7.5), z=rng.uniform(12, 120), road=True, thr=rng.uniform(0, 0.6), seed=rng.random()) for _ in range(16)]
        self.tufts = []
        for i in range(700):
            if rng.random() < 0.6: x, z, y = rng.uniform(-8, 8), rng.uniform(1.8, 110), 0.0
            else: x, z, y = rng.choice([-1, 1]) * rng.uniform(8, 12), rng.uniform(1, 110), 0.15
            if rng.random() < 0.3: x = rng.choice([-8, 8, 0, 4, -4]) + rng.uniform(-0.3, 0.3)
            self.tufts.append((x, y, z, rng.uniform(0.0, 0.85), rng.uniform(0.25, 0.7), rng.random(), rng.uniform(0, 6.28)))
        cc = CAR_COLS[:]; rng.shuffle(cc)
        self.queue = [(2.0, 8.6, 'car', cc[0]), (2.0, 15.0, 'car', cc[1]), (2.0, 21.2, 'car', cc[2]),
                      (6.0, 11.0, 'van', (0.92, 0.92, 0.9)), (6.0, 18.6, 'car', cc[3]), (6.0, 24.0, 'car', cc[4])]
        self.oncoming = [(-2.0 if i % 2 == 0 else -6.0, rng.uniform(0, 160), cc[i % len(cc)]) for i in range(9)]
        self.cross = [(32.5, rng.uniform(-60, 60), 1, cc[5]), (32.5, rng.uniform(-60, 60), 1, cc[6]),
                      (37.5, rng.uniform(-60, 60), -1, cc[7]), (37.5, rng.uniform(-60, 60), -1, cc[2])]
        sr = random.Random(seed + 1)
        self.leaves = [(sr.uniform(60, 1020), sr.uniform(1196, 1250), sr.uniform(0, 1), sr.uniform(10, 22), sr.uniform(0, 6.28),
                        sr.choice([(0.75, 0.42, 0.12), (0.62, 0.25, 0.1), (0.8, 0.62, 0.2), (0.45, 0.35, 0.15)])) for _ in range(90)]
        self.hand_out_at = tl.stages[1]["at"] + 0.6 if len(tl.stages) > 1 else None
        self.hood_col = rng.choice([(0.10, 0.18, 0.30), (0.30, 0.08, 0.08), (0.12, 0.12, 0.13), (0.55, 0.55, 0.58)])

    # ----- traffic positions
    def moving_pos(self, start, v, t, lo, hi):
        span = hi - lo
        return lo + ((start - v * t - lo) % span)

    def traffic_pos(self, start, v, t, lo, hi, direction):
        ts = self.tl.t_stop
        if ts is None or t < ts:
            if direction < 0: return self.moving_pos(start, v, t, lo, hi)
            return lo + ((start + v * t - lo) % (hi - lo))
        p0 = self.traffic_pos(start, v, ts - 1e-6, lo, hi, direction)
        tau = min(t - ts, v / A_DEC)
        return p0 + direction * (v * tau - 0.5 * A_DEC * tau * tau)

    # ----- drawing
    def draw(self, ctx, env, t):
        tl = self.tl
        powered = env["power"] > 0.5
        running = powered and env["traffic"] > 0.5
        vib = 0.006 * math.sin(t * 2 * math.pi * 13.3) + 0.004 * math.sin(t * 2 * math.pi * 7.1) if running else 0.0
        seated = 1.0 if self.hand_out_at is None else 1 - sstep(self.hand_out_at, self.hand_out_at + 1, t)
        breath = 0.012 * math.sin(t * 1.3) * seated
        sx, sy, roll = shake_offset(env, t)
        V = View((CAM[0] + sx, CAM[1] + vib + breath + sy, CAM[2]), pitch=-0.03, roll=roll, f=900, cx=540, cy=840)
        if running: ctx.translate(0, vib * 300)
        self.sky.draw(ctx, env, t, tl)
        self.draw_ground(ctx, V, env)
        level = env["water"] * 1.15
        if level > 0.02:
            self.draw_water(ctx, V, env, level)
            V.water = level
        glows = []
        objs = []
        for B in self.buildings:
            x0, y0, z0, x1, y1, z1 = B["box"]
            nx = clamp(V.p[0], x0, x1); nz = clamp(V.p[2], z0, z1)
            objs.append((V.dist((nx, min(V.p[1], y1), nz)) + 6, 'b', B))
        for (lx, lz) in self.lamps: objs.append((V.dist((lx, 3, lz)), 'l', (lx, lz)))
        objs.append((V.dist((5, 4, 29)), 's', None))
        veg = env["vegetation"]
        for T in self.trees: objs.append((V.dist((T["x"], 2, T["z"])), 't', T))
        for tf in self.tufts:
            if veg > tf[3]: objs.append((V.dist((tf[0], 0, tf[2])) - 0.5, 'g', tf))
        lo = env["power"]
        for i, (x, z, kind, col) in enumerate(self.queue):
            objs.append((V.dist((x, 0.8, z)), 'c', (x, z, 'z', 1, kind, col, lo, i * 0.13)))
        for i, (x, z0, col) in enumerate(self.oncoming):
            z = self.traffic_pos(z0, V_ON, t, -10, 160, -1)
            if z < -9: continue
            objs.append((V.dist((x, 0.8, z)), 'c', (x, z, 'z', -1, 'car', col, lo, 0.5 + i * 0.05)))
        for i, (zc, x0, fac, col) in enumerate(self.cross):
            x = self.traffic_pos(x0, V_CR, t, -70, 70, fac)
            objs.append((V.dist((x, 0.8, zc)) + 1, 'c', (x, zc, 'x', fac, 'car', col, lo, 0.2 + i * 0.2)))
        objs.sort(key=lambda o: -o[0])
        for d, kind, o in objs:
            if kind == 'b': self.building(ctx, V, env, o, glows)
            elif kind == 'l': self.lamp(ctx, V, env, o[0], o[1], glows)
            elif kind == 's': self.signal(ctx, V, env, glows)
            elif kind == 't': self.tree(ctx, V, env, o)
            elif kind == 'g': self.tuft(ctx, V, env, o)
            elif kind == 'c': self.car(ctx, V, env, *o, glows=glows)
        draw_glows(ctx, glows)
        draw_precip(ctx, env, t, (0, 0, W_PX, 1260))
        self.interior(ctx, env, t)

    def ground_col(self, env, c):
        return lerpc(c, (0.9, 0.92, 0.95), env["snow"])

    def draw_ground(self, ctx, V, env):
        asphalt = self.ground_col(env, lerpc((0.20, 0.20, 0.23), (0.12, 0.12, 0.14), env["rain"] * 0.6))
        walk = self.ground_col(env, (0.50, 0.49, 0.47)); curb = self.ground_col(env, (0.6, 0.6, 0.58))
        up = (0, 1, 0)
        segs = [(-4, 0), (0, 3), (3, 7), (7, 12)] + [(z, z + 8) for z in range(12, 200, 8)]
        for z0, z1 in reversed(segs):
            d = V.dist((0, 0, (z0 + z1) / 2))
            poly3(ctx, V, [(-8, 0, z0), (-8, 0, z1), (8, 0, z1), (8, 0, z0)], shade(env, asphalt, up, d))
        for x0 in range(-200, 200, 20):
            d = V.dist((x0 + 10, 0, 35))
            poly3(ctx, V, [(x0, 0, 29), (x0, 0, 41), (x0 + 20, 0, 41), (x0 + 20, 0, 29)], shade(env, asphalt, up, d))
        for side in (1, -1):
            for z0, z1 in reversed(segs):
                if z1 <= 29 or z0 >= 41: parts = [(z0, z1)]
                else: parts = ([(z0, 29)] if z0 < 29 else []) + ([(41, z1)] if z1 > 41 else [])
                for a, b in parts:
                    xi, xo = side * 8, side * 12
                    d = V.dist((side * 10, 0, (a + b) / 2))
                    poly3(ctx, V, [(xi, 0.15, a), (xi, 0.15, b), (xo, 0.15, b), (xo, 0.15, a)], shade(env, walk, up, d))
                    poly3(ctx, V, [(xi, 0, a), (xi, 0.15, a), (xi, 0.15, b), (xi, 0, b)], shade(env, curb, (-side, 0, 0), d), normal=(-side, 0, 0))
        wear = (1 - 0.5 * env["vegetation"]) * (1 - env["snow"])
        if wear > 0.02:
            white = (0.85, 0.85, 0.8); yellow = (0.9, 0.72, 0.2)
            for z in range(-3, 200, 9):
                if 27 < z < 45: continue
                for lx in (4.0, -4.0):
                    poly3(ctx, V, [(lx - 0.08, 0.005, z), (lx - 0.08, 0.005, z + 3), (lx + 0.08, 0.005, z + 3), (lx + 0.08, 0.005, z)],
                          shade(env, white, up, V.dist((lx, 0, z))), alpha=wear)
            for zz in [(-4, 25.5), (44, 200)]:
                for off in (-0.16, 0.04):
                    poly3(ctx, V, [(off, 0.005, zz[0]), (off, 0.005, zz[1]), (off + 0.12, 0.005, zz[1]), (off + 0.12, 0.005, zz[0])],
                          shade(env, yellow, up, 30), alpha=wear)
            poly3(ctx, V, [(0, 0.006, 25.2), (0, 0.006, 25.7), (8, 0.006, 25.7), (8, 0.006, 25.2)], shade(env, white, up, 25), alpha=wear)
            for zc in (26.2, 41.8):
                for i in range(16):
                    x = -7.6 + i * 1.0
                    poly3(ctx, V, [(x, 0.006, zc), (x, 0.006, zc + 2.6), (x + 0.5, 0.006, zc + 2.6), (x + 0.5, 0.006, zc)], shade(env, white, up, zc), alpha=wear)
        p = env["power"]
        if p > 0.01 and env["water"] < 0.05:
            for (lx, lz) in self.lamps:
                cx_ = lx * 0.72
                pts = [(cx_ + 3.6 * math.cos(a), 0.17, lz + 3.6 * math.sin(a)) for a in [i * math.pi / 10 for i in range(20)]]
                cp = clip_near([V.to_cam(q) for q in pts])
                if len(cp) < 3: continue
                s = [V.proj(q) for q in cp]
                ctx.move_to(*s[0]); [ctx.line_to(*q) for q in s[1:]]; ctx.close_path()
                ctx.set_source_rgba(1.0, 0.72, 0.38, 0.16 * p); ctx.fill()

    def draw_water(self, ctx, V, env, h):
        base = lerpc((0.25, 0.22, 0.15), env["hor"], 0.45)
        for z0 in range(-6, 400, 10):
            d = V.dist((0, h, z0 + 5))
            c = fogged(env, lerpc(base, env["top"], 0.25), d)
            poly3(ctx, V, [(-300, h, z0), (-300, h, z0 + 10), (300, h, z0 + 10), (300, h, z0)], c, wclip=False)
        # ripples
        r = random.Random(int(env["t"] * 3))
        for i in range(40):
            x, z = r.uniform(-12, 12), r.uniform(2, 60)
            p = V.pt((x, h, z))
            if p: ctx.set_source_rgba(1, 1, 1, 0.12); ctx.rectangle(p[0] - 900 / p[2], p[1], 1800 / p[2], 1.5); ctx.fill()

    def building(self, ctx, V, env, B, glows):
        x0, y0, z0, x1, y1, z1 = B["box"]
        col = lerpc(B["col"], (0.32, 0.30, 0.26), env["decay"] * 0.3)
        for pts, n in box_faces(x0, y0, z0, x1, y1, z1):
            c = col if n[1] != 1 else lerpc(col, (0.95, 0.96, 0.98), env["snow"])
            cen = tuple(sum(p[i] for p in pts) / 4 for i in range(3))
            d = V.dist(cen)
            if not poly3(ctx, V, pts, shade(env, c, n, d), normal=n): continue
            if n[0] == -B["sign"] and n[0] != 0:
                fx = B["face_x"] - B["sign"] * 0.02
                dd = V.dist((fx, 5, (z0 + z1) / 2))
                sf = lerpc((0.1, 0.12, 0.15), env["hor"], 0.25)
                shop = env["power"]
                poly3(ctx, V, [(fx, 0.4, z0 + 0.6), (fx, 2.8, z0 + 0.6), (fx, 2.8, z1 - 0.6), (fx, 0.4, z1 - 0.6)],
                      lerpc(shade(env, sf, n, dd), fogged(env, (1.0, 0.85, 0.6), dd), shop * 0.85))
                if shop > 0.5:
                    c2 = V.pt((fx, 1.6, (z0 + z1) / 2))
                    if c2 and (V.water is None or V.water < 1.6): glows.append((c2[0], c2[1], 900 * 4.0 / c2[2], (1.0, 0.75, 0.45), 0.10 * shop))
                for (wz, wy, lit, warm, r) in B["wins"]:
                    if wy + 1.5 > y1: continue
                    dwin = V.dist((fx, wy, wz))
                    if lit and env["power"] > 0.5: c = fogged(env, warm, dwin * 0.7)
                    else:
                        c = shade(env, lerpc((0.08, 0.1, 0.14), env["hor"], 0.35 + 0.2 * r), None, dwin)
                        if r < 0.25 * env["decay"]: c = mulc(c, 0.35)
                    poly3(ctx, V, [(fx, wy, wz), (fx, wy + 1.6, wz), (fx, wy + 1.6, wz + 1.4), (fx, wy, wz + 1.4)], c)
                v = sstep(0.15, 1.0, env["vegetation"])
                if v > 0.01:
                    fx2 = B["face_x"] - B["sign"] * 0.04
                    for (vz0, vz1, vh, prof, delay) in B["vines"]:
                        g = clamp((v - delay) / (1 - delay))
                        if g <= 0: continue
                        pts2 = [(fx2, 0.15, vz0)]
                        for i, pf in enumerate(prof):
                            pts2.append((fx2, 0.15 + vh * g * pf * (0.55 + 0.45 * math.sin(i * 1.7 + delay * 9) ** 2), lerp(vz0, vz1, i / (len(prof) - 1))))
                        pts2.append((fx2, 0.15, vz1))
                        poly3(ctx, V, pts2, shade(env, foliage(env, (0.22, 0.42, 0.16), delay), n, dd))

    def car(self, ctx, V, env, x, z, axis, facing, kind, col, lights_on, seed, glows):
        rust = env["decay"] * (0.6 + 0.4 * seed)
        col = lerpc(col, (0.42, 0.26, 0.16), rust * 0.75)
        sink = 0.12 * env["decay"]
        L, Wd, Hb = (5.4, 2.05, 2.45) if kind == 'van' else (4.3, 1.86, 0.98)
        glass = lerpc((0.08, 0.1, 0.14), env["hor"], 0.3)
        def bx(a0, a1, w0, w1, y0, y1):
            if axis == 'z': return (x + w0, y0 - sink, z + a0, x + w1, y1 - sink, z + a1)
            return (x + a0, y0 - sink, z + w0, x + a1, y1 - sink, z + w1)
        parts = []
        for aa in (-L / 2 + 0.55, L / 2 - 1.15):
            for ww in (-Wd / 2 - 0.02, Wd / 2 - 0.26):
                parts.append((bx(aa, aa + 0.6, ww, ww + 0.28, 0.0, 0.62), (0.07, 0.07, 0.08)))
        parts.append((bx(-L / 2, L / 2, -Wd / 2, Wd / 2, 0.3, Hb), col))
        if kind == 'car':
            c0, c1 = (-1.35, 0.85) if facing > 0 else (-0.85, 1.35)
            parts.append((bx(c0, c1, -Wd / 2 + 0.12, Wd / 2 - 0.12, Hb, Hb + 0.56), glass))
        snow = env["snow"]
        for (bb, c) in parts:
            d = V.dist(((bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, (bb[2] + bb[5]) / 2))
            for pts, n in box_faces(*bb):
                cc = c
                if n[1] == 1: cc = lerpc(col if c is glass else c, (0.95, 0.96, 0.98), snow)
                poly3(ctx, V, pts, shade(env, cc, n, d), normal=n)
        d = V.dist((x, 1, z))
        if axis == 'z':
            endz = z - L / 2 - 0.01
            ly0, ly1 = (0.62, 0.86) if kind == 'car' else (0.5, 0.9)
            front = facing < 0
            on_c = (1.0, 0.95, 0.8) if front else (1.0, 0.1, 0.06)
            off_c = (0.85, 0.85, 0.8) if front else (0.45, 0.05, 0.04)
            for side in (-1, 1):
                xa, xb = x + side * (Wd / 2 - 0.15), x + side * (Wd / 2 - 0.55)
                lc = fogged(env, on_c, d) if lights_on > 0.5 else shade(env, off_c, (0, 0, -1), d)
                poly3(ctx, V, [(xa, ly0 - sink, endz), (xa, ly1 - sink, endz), (xb, ly1 - sink, endz), (xb, ly0 - sink, endz)], lc)
                if lights_on > 0.5 and (V.water is None or V.water < ly0):
                    c = V.pt(((xa + xb) / 2, (ly0 + ly1) / 2, endz))
                    if c: glows.append((c[0], c[1], 900 * (1.6 if front else 0.9) / c[2], on_c, 0.85 * lights_on))
            if kind == 'van':
                poly3(ctx, V, [(x - 0.8, 1.55, endz - 0.005), (x - 0.8, 2.15, endz - 0.005), (x + 0.8, 2.15, endz - 0.005), (x + 0.8, 1.55, endz - 0.005)], shade(env, glass, (0, 0, -1), d))
                poly3(ctx, V, [(x - 1.02, 1.1, endz - 0.005), (x - 1.02, 1.3, endz - 0.005), (x + 1.02, 1.3, endz - 0.005), (x + 1.02, 1.1, endz - 0.005)], shade(env, (0.15, 0.45, 0.8), (0, 0, -1), d))
        elif lights_on > 0.5:
            fx = x + facing * L / 2
            for zz in (z - 0.6, z + 0.6):
                c = V.pt((fx, 0.75, zz))
                if c: glows.append((c[0], c[1], 900 * 1.5 / c[2], (1.0, 0.95, 0.8), 0.8))
            c = V.pt((x - facing * L / 2, 0.75, z - 0.7))
            if c: glows.append((c[0], c[1], 900 * 0.8 / c[2], (1.0, 0.1, 0.05), 0.7))

    def lamp(self, ctx, V, env, lx, lz, glows):
        side = 1 if lx > 0 else -1
        pole = lerpc((0.25, 0.27, 0.3), (0.4, 0.25, 0.15), env["decay"] * 0.6)
        d = V.dist((lx, 4, lz))
        for pts, n in box_faces(lx - 0.1, 0.15, lz - 0.1, lx + 0.1, 7.2, lz + 0.1):
            poly3(ctx, V, pts, shade(env, pole, n, d), normal=n)
        ax0, ax1 = (lx - 2.2, lx) if side > 0 else (lx, lx + 2.2)
        for pts, n in box_faces(ax0, 7.05, lz - 0.08, ax1, 7.2, lz + 0.08):
            poly3(ctx, V, pts, shade(env, pole, n, d), normal=n)
        hx = lx - side * 2.2
        p = env["power"]
        head = (1.0, 0.85, 0.55) if p > 0.5 else shade(env, (0.55, 0.55, 0.5), None, d)
        for pts, n in box_faces(hx - 0.35, 6.9, lz - 0.2, hx + 0.35, 7.1, lz + 0.2):
            poly3(ctx, V, pts, head if n[1] != 1 else shade(env, lerpc(pole, (1, 1, 1), env["snow"]), n, d), normal=n)
        if p > 0.5:
            c = V.pt((hx, 6.85, lz))
            if c: glows.append((c[0], c[1], 900 * 2.6 / c[2], (1.0, 0.78, 0.45), 0.75 * p))

    def signal(self, ctx, V, env, glows):
        pole = lerpc((0.22, 0.24, 0.27), (0.4, 0.25, 0.15), env["decay"] * 0.6)
        px, pz = 8.8, 29.0
        d = V.dist((5, 5, pz))
        for pts, n in box_faces(px - 0.14, 0.15, pz - 0.14, px + 0.14, 6.6, pz + 0.14):
            poly3(ctx, V, pts, shade(env, pole, n, d), normal=n)
        for pts, n in box_faces(0.5, 6.35, pz - 0.09, px, 6.55, pz + 0.09):
            poly3(ctx, V, pts, shade(env, pole, n, d), normal=n)
        p = env["power"]
        for hx in (2.0, 5.6):
            for pts, n in box_faces(hx - 0.24, 4.9, pz - 0.2, hx + 0.24, 6.35, pz + 0.2):
                poly3(ctx, V, pts, shade(env, (0.12, 0.12, 0.1), n, d), normal=n)
            for i, (yy, oc) in enumerate([(6.05, (1.0, 0.12, 0.08)), (5.62, (1.0, 0.7, 0.1)), (5.19, (0.2, 1.0, 0.5))]):
                on = i == 0 and p > 0.5
                zf = pz - 0.205
                poly3(ctx, V, [(hx - 0.13, yy - 0.13, zf), (hx - 0.13, yy + 0.13, zf), (hx + 0.13, yy + 0.13, zf), (hx + 0.13, yy - 0.13, zf)], oc if on else mulc(oc, 0.12))
                if on:
                    pp = V.pt((hx, yy, zf))
                    if pp: glows.append((pp[0], pp[1], 900 * 1.3 / pp[2], oc, 0.9))

    def tree(self, ctx, V, env, T):
        grow = sstep(0.35, 1.0, env["vegetation"])
        if T["road"]:
            g = clamp((grow - T["thr"]) / (1 - T["thr"]))
            if g <= 0: return
            s = 0.2 + 2.0 * g
        else:
            s = 0.55 + 1.6 * grow
        draw_tree(ctx, V, env, T["x"], 0.0, T["z"], s, T["seed"])

    def tuft(self, ctx, V, env, tf):
        x, y, z, thr, hgt, seed, ang = tf
        g = clamp((env["vegetation"] - thr) / 0.15)
        if g <= 0: return
        draw_tuft(ctx, V, env, x, y, z, hgt * g * (1 + 0.8 * env["vegetation"]), 0.12 + 0.25 * g, seed, ang)

    # ----- interior
    def interior(self, ctx, env, t):
        p = env["power"]
        lm = lum(env["amb"])
        k = 0.35 + 1.1 * lm
        dash_top = mulc((0.22, 0.22, 0.23), k); dash = mulc((0.15, 0.15, 0.165), k); dash_dark = mulc((0.09, 0.09, 0.10), k)
        du = env["decay"]
        if du > 0:
            g = cairo.LinearGradient(0, 0, 0, 1240)
            g.add_color_stop_rgba(0, 0.6, 0.55, 0.45, 0.10 * du); g.add_color_stop_rgba(0.7, 0.6, 0.55, 0.45, 0.16 * du)
            g.add_color_stop_rgba(1, 0.5, 0.45, 0.35, 0.45 * du)
            ctx.set_source(g); ctx.rectangle(0, 0, W_PX, 1240); ctx.fill()
        draw_glass_drops(ctx, env, t, (130, 60, 820, 1150))
        frost = sstep(0.5, 1.0, env["snow"])
        if frost > 0:
            for (gx, gy, r) in ((0, 1240, 700), (1080, 1240, 700), (540, 1260, 600), (0, 0, 500), (1080, 0, 500)):
                g = cairo.RadialGradient(gx, gy, 0, gx, gy, r)
                g.add_color_stop_rgba(0, 0.92, 0.95, 1.0, 0.85 * frost); g.add_color_stop_rgba(1, 0.92, 0.95, 1.0, 0)
                ctx.set_source(g); ctx.rectangle(0, 0, W_PX, 1262); ctx.fill()
        if env["shake"] > 0.5 or env["decay"] > 0.7:
            a = max(sstep(0.5, 0.8, env["shake"]), sstep(0.7, 1.0, env["decay"]))
            ctx.set_source_rgba(0.9, 0.9, 0.95, 0.5 * a); ctx.set_line_width(2)
            for (pts) in ([(700, 200), (640, 340), (690, 470), (600, 620)], [(640, 340), (520, 380), (420, 360)], [(690, 470), (820, 520)]):
                ctx.move_to(*pts[0]); [ctx.line_to(*q) for q in pts[1:]]; ctx.stroke()
        hood = lerpc(mulc(self.hood_col, k * 1.3), (0.4, 0.28, 0.18), env["decay"] * 0.6)
        hood = lerpc(hood, (0.92, 0.94, 0.97), env["snow"] * 0.9)
        poly2(ctx, [(0, 1262), (0, 1180), (300, 1158), (780, 1158), (1080, 1176), (1080, 1262)], hood)
        poly2(ctx, [(300, 1158), (780, 1158), (760, 1166), (320, 1166)], addc(hood, (0.05, 0.05, 0.06)))
        lv = max(env["decay"], env["vegetation"]) * (1 - env["snow"])
        for (lx, ly, thr, sz, ang, col) in self.leaves:
            if lv < thr: continue
            s = sz * clamp((lv - thr) * 4)
            c = mulc(col, 0.5 + 0.9 * lm)
            pts = [(lx + s * math.cos(ang), ly + 0.5 * s * math.sin(ang)), (lx + 0.4 * s * math.cos(ang + 1.6), ly + 0.25 * s * math.sin(ang + 1.6)),
                   (lx - s * math.cos(ang), ly - 0.5 * s * math.sin(ang)), (lx - 0.4 * s * math.cos(ang + 1.6), ly - 0.25 * s * math.sin(ang + 1.6))]
            poly2(ctx, [(a, b - 20) for a, b in pts], c)
        poly2(ctx, [(0, 1250), (1080, 1232), (1080, 1330), (0, 1352)], dash_top)
        poly2(ctx, [(0, 1352), (1080, 1330), (1080, 1920), (0, 1920)], dash)
        poly2(ctx, [(170, 1300), (230, 1255), (640, 1250), (700, 1296), (690, 1345), (180, 1352)], dash_dark)
        poly2(ctx, [(205, 1335), (665, 1330), (650, 1470), (220, 1478)], mulc((0.03, 0.03, 0.035), k))
        if p > 0.5:
            for gx in (320, 545):
                ctx.set_line_width(8); ctx.set_source_rgba(0.2, 0.9, 0.95, 0.9)
                ctx.arc(gx, 1418, 62, math.pi * 0.8, math.pi * 2.2); ctx.stroke()
                ctx.set_source_rgba(1, 0.35, 0.2, 1); ctx.set_line_width(4)
                a = math.pi * 0.8 + (0.08 if gx == 320 else 0.25)
                ctx.move_to(gx, 1418); ctx.line_to(gx + 55 * math.cos(a), 1418 + 55 * math.sin(a)); ctx.stroke()
            ctx.set_source_rgba(0.6, 1, 1, 0.9)
            ctx.select_font_face(SANS, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(30)
            ctx.move_to(418, 1400); ctx.show_text("0")
            glow_add(ctx, 432, 1410, 300, (0.1, 0.7, 0.8), 0.18)
        else:
            for gx in (320, 545):
                ctx.set_line_width(3); ctx.set_source_rgba(*mulc((0.2, 0.2, 0.22), k), 1)
                ctx.arc(gx, 1418, 62, math.pi * 0.8, math.pi * 2.2); ctx.stroke()
        sx, sy = 760, 1370
        scr = [(sx, sy), (sx + 280, sy - 8), (sx + 290, sy + 170), (sx + 6, sy + 180)]
        poly2(ctx, [(sx - 12, sy - 12), (sx + 292, sy - 20), (sx + 302, sy + 182), (sx - 6, sy + 192)], dash_dark)
        if p > 0.5:
            poly2(ctx, scr, (0.06, 0.1, 0.16))
            ctx.save(); ctx.move_to(*scr[0]); [ctx.line_to(*q) for q in scr[1:]]; ctx.close_path(); ctx.clip()
            ctx.set_source_rgba(0.25, 0.55, 0.95, 0.9); ctx.set_line_width(6)
            ctx.move_to(sx + 20, sy + 150); ctx.line_to(sx + 120, sy + 90); ctx.line_to(sx + 150, sy + 20); ctx.stroke()
            ctx.set_source_rgba(0.4, 0.45, 0.55, 0.7); ctx.set_line_width(3)
            for i in range(5): ctx.move_to(sx, sy + 30 + i * 35); ctx.line_to(sx + 300, sy + 10 + i * 35); ctx.stroke()
            ctx.restore()
            glow_add(ctx, sx + 140, sy + 85, 260, (0.2, 0.45, 0.9), 0.2)
        else:
            poly2(ctx, scr, lerpc((0.015, 0.015, 0.02), env["hor"], 0.08))
        for vx in (720, 1000):
            poly2(ctx, [(vx, 1590), (vx + 60, 1588), (vx + 62, 1640), (vx + 2, 1642)], dash_dark)
        draw_phone(ctx, env, t, 842, 1232, 150, 290, mount=True)
        pil = mulc((0.07, 0.07, 0.08), k)
        poly2(ctx, [(0, 0), (60, 0), (128, 1260), (0, 1270)], pil)
        poly2(ctx, [(1080, 0), (1020, 0), (952, 1240), (1080, 1236)], pil)
        poly2(ctx, [(0, 0), (1080, 0), (1080, 48), (0, 58)], pil)
        poly2(ctx, [(520, 50), (560, 50), (556, 108), (524, 108)], pil)
        poly2(ctx, [(420, 100), (660, 98), (650, 178), (430, 182)], mulc((0.09, 0.09, 0.1), k))
        poly2(ctx, [(432, 110), (648, 108), (640, 168), (440, 172)], lerpc(mulc(env["hor"], 0.5), (0.0, 0.0, 0.0), 0.3))
        wcx, wcy = 430, 1985
        wheel = mulc((0.075, 0.075, 0.08), k)
        ctx.set_source_rgb(*wheel)
        ctx.new_path(); ctx.arc(wcx, wcy, 575, 0, 2 * math.pi); ctx.arc_negative(wcx, wcy, 505, 2 * math.pi, 0); ctx.fill()
        ctx.set_source_rgb(*addc(wheel, mulc((0.12, 0.12, 0.12), k)))
        ctx.set_line_width(10); ctx.new_path(); ctx.arc(wcx, wcy, 562, math.pi * 1.05, math.pi * 1.95); ctx.stroke()
        poly2(ctx, [(wcx - 480, wcy - 260), (wcx - 150, wcy - 140), (wcx - 150, wcy - 60), (wcx - 490, wcy - 180)], wheel)
        poly2(ctx, [(wcx + 480, wcy - 260), (wcx + 150, wcy - 140), (wcx + 150, wcy - 60), (wcx + 490, wcy - 180)], wheel)
        ctx.arc(wcx, wcy - 40, 170, 0, 2 * math.pi); ctx.set_source_rgb(*mulc(wheel, 1.15)); ctx.fill()
        out = 0.0 if self.hand_out_at is None else ease_io((t - self.hand_out_at) / 1.0)
        if out < 1: draw_wheel_hand(ctx, k, out)
        v = sstep(0.4, 1.0, env["vegetation"])
        if v > 0: draw_corner_vines(ctx, env, v, lm, [(0, 1240, 1), (1080, 1230, -1), (128, 1262, 1)])


# ------------------------------------------------------------------ shared props (used by other templates too)
def draw_tree(ctx, V, env, x, y, z, s, seed):
    d = V.dist((x, y + 3 * s, z))
    tw = 0.12 * s + 0.05
    for pts, n in box_faces(x - tw, y, z - tw, x + tw, y + 2.6 * s, z + tw):
        poly3(ctx, V, pts, shade(env, (0.35, 0.25, 0.18), n, d), normal=n)
    base = foliage(env, lerpc((0.18, 0.42, 0.16), (0.3, 0.5, 0.18), seed), seed)
    cy = y + 4.0 * s; r = 1.7 * s
    top = (x, cy + 1.6 * s, z); bot = (x, cy - 1.2 * s, z)
    ring = [(x + r * math.cos(a + seed), cy, z + r * math.sin(a + seed)) for a in [i * math.pi / 3 for i in range(6)]]
    faces = []
    for i in range(6):
        a, b = ring[i], ring[(i + 1) % 6]
        for apex, up in ((top, True), (bot, False)):
            tri = [a, apex, b] if up else [a, b, apex]
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = apex[0] - a[0], apex[1] - a[1], apex[2] - a[2]
            nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
            if up: nx, ny, nz = -nx, -ny, -nz
            l = math.sqrt(nx * nx + ny * ny + nz * nz) or 1
            n = (nx / l, ny / l, nz / l)
            cen = tuple(sum(p[k] for p in tri) / 3 for k in range(3))
            faces.append((V.dist(cen), tri, n))
    faces.sort(key=lambda f: -f[0])
    for dd, tri, n in faces:
        c = base
        if n[1] > 0.3: c = lerpc(base, (0.95, 0.96, 0.98), env["snow"])
        poly3(ctx, V, tri, shade(env, c, n, dd), normal=n)

def draw_tuft(ctx, V, env, x, y, z, h, w, seed, ang):
    d = V.dist((x, y, z))
    base = foliage(env, lerpc((0.25, 0.48, 0.15), (0.42, 0.55, 0.2), seed), seed)
    c = shade(env, base, (0, 1, 0), d); c2 = mulc(c, 0.8)
    for k in range(3):
        a = ang + k * 2.1
        dx, dz = math.cos(a) * w, math.sin(a) * w
        tip = (x + dx * 1.4, y + h * (0.8 + 0.3 * k / 2), z + dz * 1.4)
        poly3(ctx, V, [(x - dz * 0.4, y, z + dx * 0.4), tip, (x + dz * 0.4, y, z - dx * 0.4)], c if k % 2 else c2)

def draw_phone(ctx, env, t, x, y, w, h, mount=False):
    p = env["power"]
    lm = lum(env["amb"])
    if mount:
        poly2(ctx, [(x + w / 2 - 30, y + h - 10), (x + w / 2 + 30, y + h - 10), (x + w / 2 + 40, y + h + 98), (x + w / 2 - 40, y + h + 98)], mulc((0.15, 0.15, 0.16), 0.6 + lm))
    body = lerpc((0.06, 0.06, 0.07), (0.3, 0.28, 0.22), env["decay"] * 0.5)
    rrect(ctx, x - 6, y - 6, w + 12, h + 12, 26); ctx.set_source_rgb(*mulc(body, 0.7 + lm)); ctx.fill()
    rrect(ctx, x, y, w, h, 20)
    if p > 0.5:
        g = cairo.LinearGradient(x, y, x + w, y + h)
        g.add_color_stop_rgb(0, 0.35, 0.25, 0.75); g.add_color_stop_rgb(1, 0.95, 0.45, 0.45)
        ctx.set_source(g); ctx.fill()
        ctx.set_source_rgba(1, 1, 1, 0.95)
        ctx.select_font_face(SANS, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(40 * w / 150)
        te = ctx.text_extents("9:41"); ctx.move_to(x + w / 2 - te.width / 2 - te.x_bearing, y + 70 * h / 290); ctx.show_text("9:41")
        for i in range(min(3, int(t / 0.9) + 1)):
            yy = y + (100 + i * 52) * h / 290
            rrect(ctx, x + 10, yy, w - 20, 44 * h / 290, 10); ctx.set_source_rgba(1, 1, 1, 0.55); ctx.fill()
        glow_add(ctx, x + w / 2, y + h / 2, 240 * w / 150, (0.7, 0.4, 0.8), 0.25)
    else:
        ctx.set_source_rgb(*lerpc((0.02, 0.02, 0.03), env["hor"], 0.12)); ctx.fill()
        poly2(ctx, [(x + 10, y + 10), (x + w * 0.4, y + 10), (x + 10, y + h * 0.4)], (1, 1, 1), 0.05 + 0.05 * env["day"])
        if env["decay"] > 0.4 or env["shake"] > 0.6:
            a = max(env["decay"], env["shake"])
            ctx.set_source_rgba(0.8, 0.8, 0.8, 0.35 * a); ctx.set_line_width(1.5)
            ctx.move_to(x + w * 0.66, y + h * 0.2); ctx.line_to(x + w * 0.46, y + h * 0.45); ctx.line_to(x + w * 0.56, y + h * 0.65); ctx.line_to(x + w * 0.27, y + h * 0.9); ctx.stroke()
        if env["decay"] > 0:
            rrect(ctx, x, y, w, h, 20); ctx.set_source_rgba(0.55, 0.5, 0.4, 0.35 * env["decay"]); ctx.fill()
    m = sstep(0.55, 1.0, env["vegetation"])
    if m > 0:
        mr = random.Random(11)
        for i in range(28):
            cx_ = x + mr.uniform(-10, w + 10); cy_ = y + h - mr.uniform(0, h * 0.9) ** 1.2 * 0.9
            thr = mr.uniform(0, 1)
            if m < thr: continue
            r = mr.uniform(8, 26) * clamp((m - thr) * 3) * w / 150
            col = mulc(lerpc((0.22, 0.4, 0.14), (0.38, 0.52, 0.2), mr.random()), 0.55 + 0.9 * env["amb"][1])
            poly2(ctx, [(cx_ + r * math.cos(a) * mr.uniform(0.7, 1.2), cy_ + r * math.sin(a) * mr.uniform(0.7, 1.2)) for a in [k * math.pi / 3.5 for k in range(7)]], col)
    if env["snow"] > 0.6:
        rrect(ctx, x - 6, y - 6, w + 12, h * 0.25, 20); ctx.set_source_rgba(0.95, 0.96, 1.0, sstep(0.6, 1.0, env["snow"])); ctx.fill()

def draw_wheel_hand(ctx, k, out):
    ctx.save()
    ctx.translate(320 * out, 760 * out ** 1.4)
    skin = mulc((0.95, 0.80, 0.68), k * 1.1); skin_d = mulc((0.82, 0.66, 0.54), k * 1.1); skin_l = mulc((1.0, 0.88, 0.78), k * 1.1)
    wcx, wcy, R = 430, 1985, 540
    ang = -math.radians(58)
    px, py = wcx + R * math.cos(ang), wcy + R * math.sin(ang)
    wx, wy = px + 95, py + 70
    poly2(ctx, [(wx - 60, wy - 30), (wx + 55, wy - 60), (1120, 1880), (1120, 1960), (980, 1960)], skin_d)
    ctx.translate(px, py); ctx.rotate(ang + math.pi / 2)
    poly2(ctx, [(-78, -30), (-60, -96), (10, -120), (88, -92), (112, -30)], skin)
    poly2(ctx, [(-60, -96), (10, -120), (40, -100), (-30, -80)], skin_l)
    for i in range(4):
        x0 = -76 + i * 40
        poly2(ctx, [(x0, -34), (x0 + 36, -36), (x0 + 38, 30), (x0 + 30, 44), (x0 + 4, 44), (x0 - 2, 30)], skin if i % 2 == 0 else skin_l)
        poly2(ctx, [(x0 + 2, 26), (x0 + 36, 26), (x0 + 30, 44), (x0 + 4, 44)], skin_d)
    poly2(ctx, [(88, -40), (128, -10), (120, 30), (92, 22)], skin_d)
    ctx.restore()

def draw_corner_vines(ctx, env, g, lm, origins, seed=5):
    vr = random.Random(seed)
    for (ox, oy, dirx) in origins:
        for j in range(7):
            L = (120 + vr.uniform(0, 260)) * g
            a = vr.uniform(-1.4, -0.3) if dirx > 0 else vr.uniform(-2.8, -1.7)
            ex, ey = ox + math.cos(a) * L, oy + math.sin(a) * L
            col = mulc(foliage(env, (0.2, 0.42, 0.15), vr.random()), 0.5 + 0.9 * lm)
            ctx.set_source_rgb(*col); ctx.set_line_width(6 * g + 2)
            ctx.move_to(ox, oy); ctx.curve_to(ox + (ex - ox) * 0.3 + 30, oy + (ey - oy) * 0.5, ex - 20, ey + 30, ex, ey); ctx.stroke()
            for q in range(5):
                u = (q + 1) / 6
                lx_, ly_ = lerp(ox, ex, u) + vr.uniform(-15, 15), lerp(oy, ey, u) + vr.uniform(-15, 15)
                s = vr.uniform(10, 22) * g
                poly2(ctx, [(lx_, ly_ - s), (lx_ + s * 0.8, ly_), (lx_, ly_ + s * 0.6), (lx_ - s * 0.8, ly_)], mulc(col, vr.uniform(0.9, 1.25)))
