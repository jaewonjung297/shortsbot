"""Template: standing on a grassy hilltop with your phone, overlooking a coastal town and the sea."""
import math, random
import cairo
from ..engine import *
from ..timeline import clamp, sstep
from .car import draw_tree, draw_tuft, draw_phone

NAME = "hill"
DESCRIPTION = ("Standing on a grassy hilltop holding a phone, with a bench and a lone tree, overlooking a coastal town, "
               "the sea and distant mountains under a huge sky. Best for: sky/space premises (sun, moon, stars), "
               "sea-level rise (water=1 drowns the whole town up to just below the hilltop), weather, fires/smoke, "
               "earthquakes, city lights going out, nature reclaiming everything.")
FOCUS = (845, 1560)
HUD_Y, CAPTION_Y = 640, 1110
FINAL_CAPTION_Y = 1000
ZOOM = 1.3
FOCUS_TO_Y = 1480
CAM = (0.0, 81.7, 0.0)
EDGE, FOOT = 2.6, 140.0

def hy(z):
    """Hill surface height: flat top, then a convex slope down to the valley floor."""
    if z <= EDGE: return 80.0
    u = clamp((z - EDGE) / (FOOT - EDGE))
    return 80.0 * (1 - u) ** 2 * (1 + 0.6 * u)


class Scene:
    def __init__(self, tl, seed):
        self.tl = tl
        r = random.Random(seed)
        self.sky = Sky(seed, 620)
        self.mtn = []
        for k in range(16):
            x = r.uniform(-3200, 3200); w = r.uniform(400, 1100); h = r.uniform(180, 520); z = r.uniform(2600, 3800)
            self.mtn.append((x, w, h, z, r.random()))
        self.mtn.sort(key=lambda m: -m[3])
        self.blds = []
        for i in range(260):
            x = r.gauss(0, 200); z = r.uniform(150, 600)
            if abs(x) > 600: continue
            center = math.exp(-((x / 160) ** 2 + ((z - 360) / 120) ** 2))
            h = r.uniform(5, 16) + center * r.uniform(10, 80)
            w = r.uniform(8, 18); d = r.uniform(8, 16)
            col = r.choice([(0.85, 0.82, 0.75), (0.75, 0.62, 0.52), (0.6, 0.62, 0.66), (0.9, 0.86, 0.78), (0.7, 0.45, 0.38), (0.55, 0.6, 0.7)])
            roof = r.choice([(0.6, 0.3, 0.22), (0.35, 0.35, 0.38), (0.5, 0.25, 0.2)])
            nwin = max(1, int(h / 5))
            wins = [(r.uniform(0.1, 0.8), r.uniform(0.15, 0.9), r.random() < 0.7) for _ in range(nwin)]
            self.blds.append(dict(box=(x - w / 2, 0, z, x + w / 2, h, z + d), col=col, roof=roof, wins=wins, seed=r.random()))
        self.lights = [(r.uniform(-420, 420), r.uniform(150, 600)) for _ in range(260)]
        self.tufts = []
        for k in range(420):
            z = r.uniform(1.0, 2.6) if k < 120 else r.uniform(2.6, 40)
            x = r.uniform(-1.5, 1.5) * (1 + z * 0.9)
            self.tufts.append((x, hy(z), z, r.uniform(0, 0.5) if k < 300 else r.uniform(0.3, 0.9), (r.uniform(0.1, 0.22) if z < 2.6 else r.uniform(0.4, 1.0) * (1 + z / 15)), r.random(), r.uniform(0, 6)))
        self.flowers = [(r.uniform(-2, 2) * (1 + z * 0.3), z, r.random(), r.choice([(0.95, 0.85, 0.2), (0.95, 0.4, 0.5), (0.9, 0.9, 0.95), (0.6, 0.4, 0.9)])) for z in [r.uniform(1.2, 12) for _ in range(90)]]
        self.town_trees = [(r.uniform(-500, 500), r.uniform(150, 600), r.random(), r.random()) for _ in range(70)]

    def draw(self, ctx, env, t):
        env = dict(env); env["fog_d"] = env["fog_d"] * 9
        sx, sy, roll = shake_offset(env, t)
        breath = 0.01 * math.sin(t * 1.2)
        V = View((CAM[0] + sx * 2, CAM[1] + breath + sy * 2, CAM[2]), pitch=-0.3, roll=roll, f=1000, cx=540, cy=930)
        self.sky.draw(ctx, env, t, self.tl)
        self.mountains(ctx, V, env)
        self.lowland(ctx, V, env)
        level = env["water"] * 76.0
        self.sea(ctx, V, env, max(0.0, level))
        V.water = max(0.01, level)
        glows = []
        objs = [(V.dist(((b["box"][0] + b["box"][3]) / 2, 10, b["box"][2])), 'b', b) for b in self.blds]
        tg = sstep(0.3, 1.0, env["vegetation"])
        if tg > 0:
            for tt in self.town_trees:
                if tg > tt[3] * 0.8: objs.append((V.dist((tt[0], 5, tt[1])), 'tt', tt))
        objs.sort(key=lambda o: -o[0])
        for d, k, o in objs:
            if k == 'b': self.building(ctx, V, env, o, glows)
            else: draw_tree(ctx, V, env, o[0], 0, o[1], 2.5 * tg * (0.6 + o[2]), o[2])
        if env["power"] > 0.5:
            for (x, z) in self.lights:
                p = V.pt((x, 4, z))
                if p and 4 > V.water: glows.append((p[0], p[1], 9, (1.0, 0.78, 0.45), 0.9))
        draw_glows(ctx, glows)
        V.water = None
        self.hill(ctx, V, env, t)
        draw_precip(ctx, env, t, (0, 0, W_PX, H_PX))
        self.hand(ctx, env, t)

    def mountains(self, ctx, V, env):
        for (x, w, h, z, s) in self.mtn:
            base = lerpc((0.35, 0.4, 0.45), (0.45, 0.42, 0.38), s)
            c1 = fogged(env, shade(env, base, (-0.5, 0.6, -0.6), 0), z * 0.5)
            c2 = fogged(env, shade(env, base, (0.5, 0.6, -0.6), 0), z * 0.5)
            pk = (x + w * (s - 0.5) * 0.4, h, z)
            poly3(ctx, V, [(x - w, 0, z), pk, (pk[0], 0, z - 1)], c1, wclip=False)
            poly3(ctx, V, [(pk[0], 0, z - 1), pk, (x + w, 0, z)], c2, wclip=False)
            if env["snow"] > 0.1 or h > 420:
                sc = fogged(env, shade(env, (0.95, 0.96, 0.98), (0, 1, -0.3), 0), z * 0.5)
                a = max(env["snow"], 0.8 if h > 420 else 0)
                for side in (-1, 1):
                    q = 0.3 + 0.6 * (1 - env["snow"])
                    poly3(ctx, V, [pk, (lerp(pk[0], x + side * w, 0.25 * (1.2 - q)), h * (1 - 0.25 * (1.2 - q)), z), (pk[0], h * (1 - 0.3 * (1.2 - q)), z - 1)], sc, alpha=a, wclip=False)

    def lowland(self, ctx, V, env):
        up = (0, 1, 0)
        grass = foliage(env, (0.36, 0.5, 0.26), 0.4)
        town = lerpc((0.55, 0.53, 0.5), (0.92, 0.94, 0.97), env["snow"])
        town = lerpc(town, (0.4, 0.5, 0.3), env["vegetation"] * 0.6)
        for z0 in range(2600, 140, -40):
            c = grass if (z0 < 140 or z0 > 620) else town
            if z0 >= 700: c = foliage(env, (0.4, 0.5, 0.3), 0.6)
            poly3(ctx, V, [(-4000, 0, z0), (-4000, 0, z0 + 40), (4000, 0, z0 + 40), (4000, 0, z0)], shade(env, c, up, z0 * 0.6), wclip=False)

    def sea(self, ctx, V, env, h):
        base = lerpc(lerpc((0.1, 0.25, 0.38), env["hor"], 0.35), env["top"], 0.25)
        base = lerpc(base, (0.85, 0.9, 0.95), sstep(0.85, 1.0, env["snow"]))
        z_start = 120 if h > 1 else 760
        for z0 in range(6000, z_start, -100):
            poly3(ctx, V, [(-9000, h, z0), (-9000, h, z0 + 100), (9000, h, z0 + 100), (9000, h, z0)], fogged(env, base, z0 * 0.5), wclip=False)
        if h > 1:   # shoreline glints near the flood edge
            rr = random.Random(int(env["t"] * 2))
            for i in range(70):
                p = V.pt((rr.uniform(-500, 500), h, rr.uniform(200, 900)))
                if p: ctx.set_source_rgba(1, 1, 1, 0.15); ctx.rectangle(p[0] - 9000 / p[2], p[1], 18000 / p[2], 1.2); ctx.fill()
        # moon/sun glitter path
        if env["day"] < 0.5 and env["moon_scale"] > 0.3:
            ctx.set_source_rgba(0.85, 0.9, 1.0, 0.12 * (1 - env["day"]))
            mx = 1080 - self.sky.sun_x * 0.8 + 120
            hz = V.cy - V.f * math.tan(0.3)
            for k in range(14):
                y = hz + 4 + k * 7
                ctx.rectangle(mx - 30 - k * 3, y, 60 + k * 6, 2); ctx.fill()

    def building(self, ctx, V, env, B, glows):
        x0, y0, z0, x1, y1, z1 = B["box"]
        collapse = env["decay"] * env["shake"] + env["decay"] * 0.3
        if collapse > 0.2 and B["seed"] < collapse * 0.6: y1 = y0 + (y1 - y0) * 0.35
        col = lerpc(B["col"], (0.35, 0.33, 0.3), env["decay"] * 0.4)
        col = lerpc(col, (0.35, 0.5, 0.28), sstep(0.3, 1, env["vegetation"]) * 0.6 * B["seed"])
        roof = lerpc(B["roof"], (0.95, 0.96, 0.98), env["snow"])
        d = V.dist(((x0 + x1) / 2, y1, z0))
        for pts, n in box_faces(x0, y0, z0, x1, y1, z1):
            if not poly3(ctx, V, pts, shade(env, roof if n[1] == 1 else col, n, d), normal=n): continue
            if n == (0, 0, -1):
                lit = env["power"] > 0.5
                for (u, v, on) in B["wins"]:
                    wy = y0 + v * (y1 - y0)
                    wx = x0 + u * (x1 - x0)
                    if lit and on: c = fogged(env, (1.0, 0.85, 0.55), d * 0.5)
                    else: c = shade(env, (0.15, 0.17, 0.22), n, d)
                    poly3(ctx, V, [(wx, wy, z0 - 0.1), (wx, wy + 1.8, z0 - 0.1), (wx + 2.2, wy + 1.8, z0 - 0.1), (wx + 2.2, wy, z0 - 0.1)], c)

    def hill(self, ctx, V, env, t):
        up = (0, 1, 0)
        grass = foliage(env, lerpc((0.35, 0.55, 0.22), (0.25, 0.45, 0.18), 0.4), 0.2)
        grass = lerpc(grass, (0.45, 0.38, 0.25), env["decay"] * 0.3)
        # slope down to the valley, then the hilltop meadow (far to near)
        lvl = env["water"] * 76.0
        zs = [EDGE + (FOOT - EDGE) * (i / 14) ** 1.3 for i in range(15)]
        for i in range(14, 0, -1):
            za, zb = zs[i], zs[i - 1]
            ya, yb = hy(za), hy(zb)
            if max(ya, yb) <= lvl: continue
            ny = (zb - za); nz = (ya - yb)
            n = norm((0, abs(ny), -abs(nz)))
            wa, wb = 30 + za * 1.8, 30 + zb * 1.8
            c = lerpc(mulc(grass, 0.92), grass, i % 2)
            V.water = lvl if lvl > 0.5 else None
            poly3(ctx, V, [(-wa, ya, za), (wa, ya, za), (wb, yb, zb), (-wb, yb, zb)], shade(env, c, n, za), wclip=True)
            V.water = None
        poly3(ctx, V, [(-40, 80, 2.6), (-40, 80, 2.61), (40, 80, 2.61), (40, 80, 2.6)], grass, wclip=False)
        for z0 in (0.6, -1.4):
            poly3(ctx, V, [(-40, 80, z0), (-40, 80, z0 + 2.01), (40, 80, z0 + 2.01), (40, 80, z0)], shade(env, grass, up, z0), wclip=False)

        objs = []
        for tf in self.tufts:
            if tf[3] <= 0.15 + env["vegetation"]: objs.append((V.dist((tf[0], 80, tf[2])), 'g', tf))
        objs.append((V.dist((-4.2, 82, 2.2)), 'tree', None))
        objs.append((V.dist((2.9, 80.5, 1.3)), 'bench', None))
        fl = sstep(0.2, 0.7, env["vegetation"]) * (1 - env["snow"]) * (1 - env["heat"])
        if fl > 0:
            for f in self.flowers:
                if fl > f[2]: objs.append((V.dist((f[0], 80, f[1])), 'f', f))
        objs.sort(key=lambda o: -o[0])
        for d, k, o in objs:
            if k == 'g':
                x, y, z, thr, hh, sd, ang = o
                if y < env["water"] * 76.0: continue
                draw_tuft(ctx, V, env, x, y, z, hh * (0.8 + 1.2 * env["vegetation"]) * (1 - 0.7 * env["snow"]), 0.14, sd, ang)
            elif k == 'tree':
                dead = clamp(env["heat"] + (1 - clamp(env["sun_scale"])) * 0.6)
                draw_tree(ctx, V, env, -4.2, 80, 2.2, 0.8 + 0.6 * env["vegetation"] - 0.4 * dead, 0.3)
            elif k == 'bench': self.bench(ctx, V, env)
            else:
                x, z, _, col = o
                p = V.pt((x, hy(z) + 0.35, z))
                if p:
                    r = min(12, max(1.5, 50 / p[2]))
                    ctx.set_source_rgb(*shade(env, col, None, 0)); ctx.arc(p[0], p[1], r, 0, 2 * math.pi); ctx.fill()

    def bench(self, ctx, V, env):
        wood = lerpc((0.55, 0.36, 0.22), (0.35, 0.3, 0.26), env["decay"])
        legs = (0.2, 0.2, 0.22)
        x, z = 2.9, 1.3
        parts = [((x - 0.9, 80, z, x - 0.8, 80.45, z + 0.45), legs), ((x + 0.8, 80, z, x + 0.9, 80.45, z + 0.45), legs),
                 ((x - 1.0, 80.45, z, x + 1.0, 80.52, z + 0.5), wood), ((x - 1.0, 80.7, z + 0.42, x + 1.0, 81.0, z + 0.5), wood),
                 ((x - 0.9, 80.45, z + 0.42, x - 0.82, 80.7, z + 0.5), legs), ((x + 0.82, 80.45, z + 0.42, x + 0.9, 80.7, z + 0.5), legs)]
        if env["decay"] > 0.85: parts = parts[:3]
        for bb, c in parts:
            for pts, n in box_faces(*bb):
                cc = lerpc(c, (0.95, 0.96, 0.98), env["snow"]) if n[1] == 1 else c
                poly3(ctx, V, pts, shade(env, cc, n, 8), normal=n, wclip=False)

    def hand(self, ctx, env, t):
        lm = lum(env["amb"])
        k = 0.35 + 1.0 * lm
        skin = mulc((0.95, 0.80, 0.68), k); skin_d = mulc((0.82, 0.66, 0.54), k); skin_l = mulc((1.0, 0.88, 0.78), k)
        bob = 6 * math.sin(t * 1.4)
        ctx.save(); ctx.translate(0, bob); ctx.translate(845, 1560); ctx.rotate(-0.12); ctx.translate(-845, -1560)
        # forearm + palm behind phone
        poly2(ctx, [(780, 1700), (930, 1690), (1120, 1960), (900, 1960)], skin_d)
        poly2(ctx, [(745, 1560), (950, 1540), (960, 1730), (770, 1760)], skin)
        draw_phone(ctx, env, t, 750, 1390, 190, 350)
        # thumb on the left edge, fingers on the right edge
        poly2(ctx, [(730, 1700), (760, 1600), (800, 1610), (790, 1720)], skin_l)
        for i in range(4):
            y = 1530 + i * 46
            poly2(ctx, [(935, y), (975, y - 6), (985, y + 30), (938, y + 36)], skin if i % 2 else skin_l)
        ctx.restore()
