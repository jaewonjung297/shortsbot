"""Template: high-rise apartment window looking across a river at a skyline."""
import math, random
import cairo
from ..engine import *
from ..timeline import clamp, sstep
from .car import draw_tree, draw_tuft, draw_phone, draw_corner_vines

NAME = "window"
DESCRIPTION = ("Inside an 8th-floor apartment at night or day, looking through a big window across a river at a city skyline "
               "and bridge, with a lamp, a potted plant and a phone on the sill. Best for: sky and space premises (sun, moon, "
               "stars), weather (storms, snow, heat), rising water (water=1 floods the river up to just below the window), "
               "city lights/power, smoke and fires, overgrowth.")
FOCUS = (760, 1440)
HUD_Y, CAPTION_Y = 640, 1080
FINAL_CAPTION_Y = 980
ZOOM = 1.6
FOCUS_TO_Y = 1460
WIN = (90, 150, 990, 1350)   # window opening in screen px
CAM = (0.0, 24.0, 0.0)


class Scene:
    def __init__(self, tl, seed):
        self.tl = tl
        r = random.Random(seed)
        self.sky = Sky(seed, 760)
        # skyline on far bank
        self.towers = []
        x = -420
        while x < 420:
            w = r.uniform(10, 26); h = r.choice([18, 25, 32, 40, 55, 70, 90, 120]) * r.uniform(0.8, 1.2)
            z = r.uniform(262, 320); d = r.uniform(12, 24)
            col = r.choice([(0.55, 0.58, 0.64), (0.66, 0.62, 0.55), (0.45, 0.5, 0.58), (0.72, 0.7, 0.66), (0.5, 0.45, 0.42)])
            wins = [(fx, fy, r.random() < 0.55, r.random()) for fy in range(int(h / 3.6)) for fx in range(int(w / 3.0))]
            self.towers.append(dict(box=(x, 0, z, x + w, h, z + d), col=col, wins=wins, seed=r.random(), spire=r.random() < 0.2))
            x += w + r.uniform(1, 6)
        for k in range(30):   # second row
            x = r.uniform(-500, 500); w = r.uniform(14, 30); h = r.uniform(40, 170); z = r.uniform(340, 420)
            self.towers.append(dict(box=(x, 0, z, x + w, h, z + 20), col=(0.5, 0.53, 0.6), wins=[(fx, fy, r.random() < 0.5, r.random()) for fy in range(int(h / 3.6)) for fx in range(int(w / 3.0))], seed=r.random(), spire=False))
        # near bank: low buildings below the window and a street
        self.near = []
        x = -80
        while x < 80:
            w = r.uniform(8, 16); h = r.uniform(5, 14)
            self.near.append(dict(box=(x, 0, 16, x + w, h, 26), col=r.choice([(0.6, 0.45, 0.38), (0.55, 0.55, 0.52), (0.68, 0.6, 0.48)]), seed=r.random()))
            x += w + r.uniform(0.5, 2)
        self.trees = [(r.uniform(-60, 60), r.uniform(37, 45), r.random()) for _ in range(14)]
        self.tufts = [(r.uniform(-60, 60), 2.0, r.uniform(36, 47), r.uniform(0, 0.8), r.uniform(0.4, 1.0), r.random(), r.uniform(0, 6)) for _ in range(160)]
        self.cars = [(r.uniform(-120, 120), 1 if k % 2 else -1, r.choice([(0.8, 0.2, 0.15), (0.2, 0.35, 0.65), (0.85, 0.85, 0.85), (0.2, 0.2, 0.22)])) for k in range(10)]
        self.lamps = [x for x in range(-90, 91, 18)]
        self.plant_seed = r.random()

    def view(self, env, t):
        sx, sy, roll = shake_offset(env, t)
        breath = 0.01 * math.sin(t * 1.1)
        return View((CAM[0] + sx * 3, CAM[1] + breath + sy * 3, CAM[2]), pitch=-0.2, roll=roll, f=980, cx=540, cy=760)

    def draw(self, ctx, env, t):
        env = dict(env); env["fog_d"] = env["fog_d"] * 2.6
        V = self.view(env, t)
        ctx.save()
        ctx.rectangle(WIN[0], WIN[1], WIN[2] - WIN[0], WIN[3] - WIN[1]); ctx.clip()
        self.sky.draw(ctx, env, t, self.tl)
        self.world(ctx, V, env, t)
        draw_precip(ctx, env, t, (WIN[0], WIN[1], WIN[2] - WIN[0], WIN[3] - WIN[1]))
        draw_glass_drops(ctx, env, t, (WIN[0], WIN[1], WIN[2] - WIN[0], WIN[3] - WIN[1]))
        self.glass_fx(ctx, env, t)
        ctx.restore()
        self.room(ctx, env, t)

    def world(self, ctx, V, env, t):
        up = (0, 1, 0)
        snow = env["snow"]
        grass = foliage(env, (0.3, 0.45, 0.2), 0.3)
        ground = lerpc((0.45, 0.44, 0.42), (0.92, 0.94, 0.97), snow)
        # far bank, river, near bank
        for z0 in range(600, 240, -20):
            poly3(ctx, V, [(-900, 2, z0), (-900, 2, z0 + 20), (900, 2, z0 + 20), (900, 2, z0)], shade(env, ground, up, V.dist((0, 2, z0))))
        river_h = 0.5 + env["water"] * 20.5
        rc = lerpc(lerpc((0.08, 0.14, 0.2), env["hor"], 0.4), env["top"], 0.25)
        if snow > 0.8: rc = lerpc(rc, (0.85, 0.9, 0.95), sstep(0.8, 1.0, snow))
        for z0 in range(250, 40, -15):
            poly3(ctx, V, [(-900, 0.5, z0), (-900, 0.5, z0 + 15), (900, 0.5, z0 + 15), (900, 0.5, z0)], fogged(env, rc, V.dist((0, 0, z0))))
        for z0 in range(46, 10, -6):
            c = grass if 34 <= z0 < 48 else lerpc((0.25, 0.25, 0.28), (0.92, 0.94, 0.97), snow)
            if z0 < 34: c = lerpc((0.22, 0.22, 0.25), (0.92, 0.94, 0.97), snow)
            poly3(ctx, V, [(-600, 2, z0), (-600, 2, z0 + 6), (600, 2, z0 + 6), (600, 2, z0)], shade(env, c, up, V.dist((0, 2, z0))))
        poly3(ctx, V, [(-600, 0.5, 48), (-600, 2, 48), (600, 2, 48), (600, 0.5, 48)], shade(env, (0.4, 0.38, 0.35), (0, 0, 1), 60))
        glows = []
        objs = []
        for T in self.towers:
            b = T["box"]; objs.append((V.dist(((b[0] + b[3]) / 2, 20, b[2])), 'T', T))
        objs.append((V.dist((-40, 10, 80)), 'B', None))
        for N in self.near:
            b = N["box"]; objs.append((V.dist(((b[0] + b[3]) / 2, 5, b[2])), 'N', N))
        for (x, z, sd) in self.trees: objs.append((V.dist((x, 4, z)), 'tree', (x, z, sd)))
        for tf in self.tufts:
            if env["vegetation"] > tf[3]: objs.append((V.dist((tf[0], 2, tf[2])), 'g', tf))
        for x in self.lamps: objs.append((V.dist((x, 4, 33)), 'L', x))
        for (x0, d, col) in self.cars:
            x = self.car_x(x0, d, t)
            objs.append((V.dist((x, 2, 29 + (1.5 if d > 0 else -1.5))), 'C', (x, d, col)))
        objs.sort(key=lambda o: -o[0])
        self.flood(ctx, V, env, river_h)
        for d, k, o in objs:
            if k == 'T': self.tower(ctx, V, env, o, glows)
            elif k == 'B': self.bridge(ctx, V, env, glows)
            elif k == 'N': self.lowbuilding(ctx, V, env, o, glows)
            elif k == 'tree': draw_tree(ctx, V, env, o[0], 2.0, o[1], 0.6 + 1.6 * sstep(0.2, 1, env["vegetation"]), o[2])
            elif k == 'g': draw_tuft(ctx, V, env, o[0], o[1], o[2], o[4] * (1 + env["vegetation"]) * 1.5, 0.5, o[5], o[6])
            elif k == 'L': self.lamp(ctx, V, env, o, glows)
            elif k == 'C': self.car(ctx, V, env, *o, glows=glows)
        draw_glows(ctx, glows)

    def car_x(self, x0, d, t):
        ts = self.tl.t_stop
        v = 9.0
        if ts is None or t < ts: return -130 + ((x0 + d * v * t + 130) % 260)
        p0 = -130 + ((x0 + d * v * ts + 130) % 260)
        tau = min(t - ts, v / 4.0)
        return p0 + d * (v * tau - 2.0 * tau * tau)

    def flood(self, ctx, V, env, h):
        """River (and flood) surface; also clip subsequent geometry at this height."""
        if h <= 0.55: return
        rc = lerpc(lerpc((0.2, 0.2, 0.18), env["hor"], 0.45), env["top"], 0.2)
        for z0 in range(600, 0, -20):
            poly3(ctx, V, [(-900, h, z0), (-900, h, z0 + 20), (900, h, z0 + 20), (900, h, z0)], fogged(env, rc, V.dist((0, h, z0))), alpha=0.97, wclip=False)
        rr = random.Random(int(env["t"] * 2))
        for i in range(60):
            p = V.pt((rr.uniform(-80, 80), h, rr.uniform(15, 150)))
            if p: ctx.set_source_rgba(1, 1, 1, 0.12); ctx.rectangle(p[0] - 3000 / p[2], p[1], 6000 / p[2], 1.5); ctx.fill()
        V.water = h

    def tower(self, ctx, V, env, T, glows):
        x0, y0, z0, x1, y1, z1 = T["box"]
        col = lerpc(T["col"], (0.32, 0.30, 0.26), env["decay"] * 0.35)
        d = V.dist(((x0 + x1) / 2, y1 / 2, z0))
        for pts, n in box_faces(x0, y0, z0, x1, y1, z1):
            c = col if n[1] != 1 else lerpc(col, (0.95, 0.96, 0.98), env["snow"])
            if not poly3(ctx, V, pts, shade(env, c, n, d), normal=n): continue
            if n == (0, 0, -1):
                cols = max(1, int((x1 - x0) / 3.0)); fz = z0 - 0.05
                lit_on = env["power"] > 0.5
                for (fx, fy, lit, r) in T["wins"]:
                    wx = x0 + 0.8 + fx * 3.0; wy = 3 + fy * 3.6
                    if wy + 2 > y1 or wx + 1.6 > x1: continue
                    if lit and lit_on: c2 = fogged(env, (1.0, 0.86, 0.55) if r < 0.7 else (0.8, 0.9, 1.0), d * 0.8)
                    else:
                        if r > 0.35 + 0.5 * env["day"]: continue
                        c2 = shade(env, lerpc((0.1, 0.12, 0.16), env["hor"], 0.4), None, d)
                    poly3(ctx, V, [(wx, wy, fz), (wx, wy + 2, fz), (wx + 1.6, wy + 2, fz), (wx + 1.6, wy, fz)], c2)
                v = sstep(0.2, 1.0, env["vegetation"])
                if v > 0:
                    rr = random.Random(int(T["seed"] * 1000))
                    for k in range(3):
                        vx0 = rr.uniform(x0, x1 - 4); vw = rr.uniform(3, 9)
                        hh = (y1 * rr.uniform(0.3, 0.9)) * clamp(v * 1.3 - rr.uniform(0, 0.3))
                        if hh <= 0: continue
                        pts2 = [(vx0, 0, fz - 0.05)] + [(vx0 + vw * i / 6, hh * (0.6 + 0.4 * math.sin(i * 1.9 + k) ** 2), fz - 0.05) for i in range(7)] + [(vx0 + vw, 0, fz - 0.05)]
                        poly3(ctx, V, pts2, shade(env, foliage(env, (0.22, 0.42, 0.16), rr.random()), n, d))
        if T["spire"] and env["power"] > 0.5:
            p = V.pt(((x0 + x1) / 2, y1 + 4, (z0 + z1) / 2))
            if p and int(env["t"] * 1.5) % 2 == 0: glows.append((p[0], p[1], 40, (1.0, 0.2, 0.15), 0.9))

    def bridge(self, ctx, V, env, glows):
        deck = lerpc((0.5, 0.48, 0.45), (0.4, 0.25, 0.15), env["decay"] * 0.5)
        x0, x1 = -48, -36
        for pts, n in box_faces(x0, 9, 46, x1, 10.5, 262):
            poly3(ctx, V, pts, shade(env, lerpc(deck, (0.95, 0.96, 0.98), env["snow"] if n[1] == 1 else 0), n, 80), normal=n)
        for zc in (100, 205):
            for px in (x0 + 0.5, x1 - 1.5):
                for pts, n in box_faces(px, 0, zc - 0.8, px + 1, 34, zc + 0.8):
                    poly3(ctx, V, pts, shade(env, deck, n, 80), normal=n)
        if env["power"] > 0.5:
            for z in range(48, 262, 8):
                p = V.pt((x1, 11, z))
                if p: glows.append((p[0], p[1], 980 * 1.8 / p[2], (1.0, 0.8, 0.5), 0.6))

    def lowbuilding(self, ctx, V, env, N, glows):
        x0, y0, z0, x1, y1, z1 = N["box"]
        col = lerpc(N["col"], (0.32, 0.3, 0.26), env["decay"] * 0.35)
        d = V.dist(((x0 + x1) / 2, y1, z1))
        for pts, n in box_faces(x0, y0, z0, x1, y1, z1):
            c = col if n[1] != 1 else lerpc(lerpc((0.3, 0.3, 0.32), (0.3, 0.45, 0.2), env["vegetation"]), (0.95, 0.96, 0.98), env["snow"])
            poly3(ctx, V, pts, shade(env, c, n, d), normal=n)
        if env["power"] > 0.5:
            p = V.pt(((x0 + x1) / 2, 1.5, z1 + 0.05))
            if p: glows.append((p[0], p[1], 980 * 4 / p[2], (1.0, 0.75, 0.45), 0.25))

    def lamp(self, ctx, V, env, x, glows):
        d = V.dist((x, 4, 33))
        for pts, n in box_faces(x - 0.12, 2, 33, x + 0.12, 8, 33.24):
            poly3(ctx, V, pts, shade(env, (0.25, 0.27, 0.3), n, d), normal=n)
        if env["power"] > 0.5:
            p = V.pt((x, 8, 33))
            if p: glows.append((p[0], p[1], 980 * 3 / p[2], (1.0, 0.78, 0.45), 0.7))

    def car(self, ctx, V, env, x, dirn, col, glows):
        z = 29 + (1.5 if dirn > 0 else -1.5)
        col = lerpc(col, (0.42, 0.26, 0.16), env["decay"] * 0.7)
        d = V.dist((x, 2, z))
        for bb in ((x - 2.1, 2.3, z - 0.9, x + 2.1, 3.1, z + 0.9), (x - 1.1, 3.1, z - 0.8, x + 0.9, 3.6, z + 0.8)):
            for pts, n in box_faces(*bb):
                c = col if n[1] != 1 else lerpc(col, (0.95, 0.96, 0.98), env["snow"])
                poly3(ctx, V, pts, shade(env, c, n, d), normal=n)
        if env["power"] > 0.5 and env["traffic"] > 0.1:
            p = V.pt((x + dirn * 2.1, 2.8, z))
            if p: glows.append((p[0], p[1], 980 * 1.4 / p[2], (1.0, 0.95, 0.8), 0.8))
            p = V.pt((x - dirn * 2.1, 2.8, z))
            if p: glows.append((p[0], p[1], 980 * 0.8 / p[2], (1.0, 0.1, 0.05), 0.7))

    def glass_fx(self, ctx, env, t):
        x0, y0, x1, y1 = WIN
        frost = 0.6 * sstep(0.6, 1.0, env["snow"])
        if frost > 0:
            for (gx, gy) in ((x0, y1), (x1, y1), (x0, y0), (x1, y0), (540, y1)):
                g = cairo.RadialGradient(gx, gy, 0, gx, gy, 650)
                g.add_color_stop_rgba(0, 0.92, 0.95, 1.0, 0.9 * frost); g.add_color_stop_rgba(1, 0.92, 0.95, 1.0, 0)
                ctx.set_source(g); ctx.rectangle(x0, y0, x1 - x0, y1 - y0); ctx.fill()
        if env["decay"] > 0:
            ctx.set_source_rgba(0.55, 0.5, 0.42, 0.25 * env["decay"]); ctx.rectangle(x0, y0, x1 - x0, y1 - y0); ctx.fill()
        heat = clamp(env["heat"] + (env["sun_scale"] - 1) / 3) * env["day"]
        if heat > 0:
            ctx.set_source_rgba(1.0, 0.85, 0.6, 0.18 * heat); ctx.rectangle(x0, y0, x1 - x0, y1 - y0); ctx.fill()
        if env["shake"] > 0.55 or env["decay"] > 0.75:
            a = max(sstep(0.55, 0.85, env["shake"]), sstep(0.75, 1.0, env["decay"]))
            ctx.set_source_rgba(0.92, 0.94, 1.0, 0.55 * a); ctx.set_line_width(2)
            cx, cy = 690, 520
            for k in range(9):
                ang = k * 0.7 + 0.3; L = 140 + 90 * math.sin(k * 2.3)
                ctx.move_to(cx, cy); ctx.line_to(cx + L * 0.5 * math.cos(ang + 0.2), cy + L * 0.5 * math.sin(ang + 0.2)); ctx.line_to(cx + L * math.cos(ang), cy + L * math.sin(ang)); ctx.stroke()

    def room(self, ctx, env, t):
        p = env["power"]
        lm = lum(env["amb"])
        night_lit = p * (1 - env["day"] * 0.7)
        k = 0.35 + 1.1 * lm + 0.55 * night_lit
        wall = mulc((0.42, 0.36, 0.31), k)
        wall = lerpc(wall, mulc((0.35, 0.32, 0.26), k), env["decay"])
        x0, y0, x1, y1 = WIN
        # wall around window
        poly2(ctx, [(0, 0), (W_PX, 0), (W_PX, y0), (0, y0)], wall)
        poly2(ctx, [(0, 0), (x0, 0), (x0, H_PX), (0, H_PX)], wall)
        poly2(ctx, [(x1, 0), (W_PX, 0), (W_PX, H_PX), (x1, H_PX)], wall)
        poly2(ctx, [(0, y1), (W_PX, y1), (W_PX, H_PX), (0, H_PX)], mulc(wall, 0.85))
        # lamp light pool on the wall
        if p > 0.5:
            glow_add(ctx, 900, 1300, 700, (1.0, 0.72, 0.4), 0.22 * night_lit)
        # frame + mullions
        fr = mulc((0.85, 0.84, 0.8), 0.25 + 0.9 * lm + 0.4 * night_lit)
        frd = mulc(fr, 0.7)
        ctx.set_source_rgb(*fr)
        ctx.rectangle(x0 - 26, y0 - 26, x1 - x0 + 52, 26); ctx.fill()
        ctx.rectangle(x0 - 26, y0, 26, y1 - y0); ctx.fill()
        ctx.rectangle(x1, y0, 26, y1 - y0); ctx.fill()
        ctx.set_source_rgb(*frd)
        ctx.rectangle(x0, y0, 14, y1 - y0); ctx.fill(); ctx.rectangle(x1 - 14, y0, 14, y1 - y0); ctx.fill()
        ctx.rectangle(x0, y0, x1 - x0, 14); ctx.fill()
        ctx.set_source_rgb(*fr)
        ctx.rectangle(531, y0, 18, y1 - y0); ctx.fill()
        ctx.rectangle(x0, 520, x1 - x0, 16); ctx.fill()
        # sill
        sill = mulc((0.8, 0.78, 0.74), 0.25 + 0.9 * lm + 0.4 * night_lit)
        poly2(ctx, [(x0 - 60, y1), (x1 + 60, y1), (x1 + 100, y1 + 110), (x0 - 100, y1 + 110)], sill)
        poly2(ctx, [(x0 - 100, y1 + 110), (x1 + 100, y1 + 110), (x1 + 100, y1 + 140), (x0 - 100, y1 + 140)], mulc(sill, 0.7))
        if env["snow"] > 0.5:
            poly2(ctx, [(x0, y1 - 14), (x1, y1 - 14), (x1, y1 - 2), (x0, y1 - 2)], (0.95, 0.96, 1.0), sstep(0.5, 1, env["snow"]))
        if env["water"] > 0.9 or env["rain"] > 0.7:
            a = max(sstep(0.9, 1.0, env["water"]), sstep(0.7, 1.0, env["rain"]) * 0.4)
            poly2(ctx, [(x0 - 60, y1 + 30), (x1 + 60, y1 + 30), (x1 + 100, y1 + 110), (x0 - 100, y1 + 110)], (0.5, 0.6, 0.7), 0.35 * a)
        self.plant(ctx, env, lm, night_lit)
        self.desk_lamp(ctx, env, lm, night_lit)
        draw_phone_flat(ctx, env, t, 660, 1385, 200, 100)
        v = sstep(0.55, 1.0, env["vegetation"])
        if v > 0: draw_corner_vines(ctx, env, v, lm, [(x0 - 20, y1, 1), (x1 + 20, y1, -1), (x0 - 20, 700, 1)], seed=8)

    def plant(self, ctx, env, lm, nl):
        k = 0.3 + 1.0 * lm + 0.4 * nl
        px, py = 250, 1420
        poly2(ctx, [(px - 70, py - 90), (px + 70, py - 90), (px + 52, py + 20), (px - 52, py + 20)], mulc((0.75, 0.38, 0.22), k))
        poly2(ctx, [(px - 76, py - 100), (px + 76, py - 100), (px + 76, py - 80), (px - 76, py - 80)], mulc((0.82, 0.45, 0.28), k))
        g = 1.0 + 2.2 * env["vegetation"]
        dead = clamp(env["heat"] + sstep(0.3, 0.8, env["snow"]) + (1 - clamp(env["sun_scale"])) * 0.8)
        rr = random.Random(int(self.plant_seed * 100))
        for i in range(9):
            a = -math.pi / 2 + rr.uniform(-1.1, 1.1)
            L = rr.uniform(90, 170) * g
            ex, ey = px + math.cos(a) * L, py - 95 + math.sin(a) * L
            col = lerpc(lerpc((0.25, 0.5, 0.2), (0.35, 0.6, 0.25), rr.random()), (0.45, 0.35, 0.2), dead)
            col = mulc(col, k)
            ctx.set_source_rgb(*mulc(col, 0.8)); ctx.set_line_width(5)
            ctx.move_to(px, py - 95); ctx.line_to(ex, ey + dead * 60); ctx.stroke()
            w = 26 * g ** 0.5
            poly2(ctx, [(ex, ey - w + dead * 60), (ex + w * 0.6, ey + dead * 60), (ex, ey + w * 0.9 + dead * 60), (ex - w * 0.6, ey + dead * 60)], col)

    def desk_lamp(self, ctx, env, lm, nl):
        k = 0.3 + 1.0 * lm + 0.4 * nl
        bx, by = 905, 1440
        poly2(ctx, [(bx - 55, by), (bx + 55, by), (bx + 45, by - 22), (bx - 45, by - 22)], mulc((0.15, 0.15, 0.16), k))
        ctx.set_source_rgb(*mulc((0.18, 0.18, 0.2), k)); ctx.set_line_width(10)
        ctx.move_to(bx, by - 20); ctx.line_to(bx - 30, by - 200); ctx.line_to(bx + 30, by - 300); ctx.stroke()
        on = env["power"] > 0.5
        shade_c = (1.0, 0.85, 0.55) if on else mulc((0.75, 0.7, 0.6), k)
        poly2(ctx, [(bx - 10, by - 330), (bx + 80, by - 310), (bx + 110, by - 230), (bx - 20, by - 260)], shade_c)
        if on: glow_add(ctx, bx + 40, by - 250, 300, (1.0, 0.75, 0.4), 0.45)


def draw_phone_flat(ctx, env, t, x, y, w, h):
    """Phone lying flat on the sill (screen faces up, drawn in perspective)."""
    lm = lum(env["amb"])
    p = env["power"]
    pts = [(x + 18, y), (x + w - 18, y), (x + w, y + h), (x, y + h)]
    poly2(ctx, [(a, b + 6) for a, b in pts], (0.02, 0.02, 0.02), 0.5)
    poly2(ctx, pts, mulc((0.08, 0.08, 0.09), 0.7 + lm))
    inner = [(x + 26, y + 6), (x + w - 26, y + 6), (x + w - 10, y + h - 6), (x + 10, y + h - 6)]
    if p > 0.5:
        poly2(ctx, inner, (0.6, 0.4, 0.85))
        ctx.set_source_rgba(1, 1, 1, 0.9); ctx.select_font_face(SANS, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(22)
        ctx.move_to(x + w / 2 - 24, y + h / 2 + 8); ctx.show_text("9:41")
        glow_add(ctx, x + w / 2, y + h / 2, 160, (0.7, 0.45, 0.9), 0.3)
    else:
        poly2(ctx, inner, lerpc((0.02, 0.02, 0.03), env["hor"], 0.2))
        if env["decay"] > 0.4 or env["shake"] > 0.6:
            ctx.set_source_rgba(0.8, 0.8, 0.8, 0.4); ctx.set_line_width(1.2)
            ctx.move_to(x + 60, y + 10); ctx.line_to(x + 75, y + 40); ctx.line_to(x + 55, y + 70); ctx.stroke()
    m = sstep(0.6, 1.0, env["vegetation"])
    if m > 0:
        rr = random.Random(4)
        for i in range(14):
            cx_, cy_, r = x + rr.uniform(0, w), y + rr.uniform(0, h), rr.uniform(6, 16) * m
            poly2(ctx, [(cx_ + r * math.cos(a), cy_ + r * 0.6 * math.sin(a)) for a in [q * math.pi / 3 for q in range(6)]], mulc((0.3, 0.5, 0.2), 0.5 + lm))
