"""Drawing kit for story videos: blocky characters, faces, pets and rooms."""
import math, random
import cairo

FLOOR = 1560

W, H, FPS = 1080, 1920, 30

def clamp(x, a=0.0, b=1.0): return a if x < a else b if x > b else x
def ease(x): x = clamp(x); return x * x * (3 - 2 * x)
def lerp(a, b, t): return a + (b - a) * t
def mul(c, k): return tuple(clamp(v * k) for v in c)
def mix(a, b, t): return tuple(lerp(a[i], b[i], t) for i in range(3))

# ------------------------------------------------------------------ primitives
def rrect(ctx, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0); ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi); ctx.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    ctx.close_path()

def fill(ctx, col, a=1.0):
    ctx.set_source_rgba(col[0], col[1], col[2], a); ctx.fill()

def poly(ctx, pts, col, a=1.0):
    ctx.move_to(*pts[0]); [ctx.line_to(*p) for p in pts[1:]]; ctx.close_path(); fill(ctx, col, a)

def block(ctx, x, y, w, h, col, depth=0.16, r=0.14):
    """Toy-like block: soft rounded front with gradient, lit top face, shaded right side."""
    d = min(w, h) * depth
    dx, dy = d * 0.75, d * 0.55
    poly(ctx, [(x + w - 2, y + 2), (x + w + dx, y - dy + 4), (x + w + dx, y + h - dy - 4), (x + w - 2, y + h - 2)], mul(col, 0.68))
    poly(ctx, [(x + 4, y + 2), (x + dx + 6, y - dy), (x + w + dx - 2, y - dy), (x + w - 2, y + 2)], mul(col, 1.18))
    g = cairo.LinearGradient(x, y, x + w * 0.4, y + h)
    g.add_color_stop_rgb(0, *mul(col, 1.1)); g.add_color_stop_rgb(1, *mul(col, 0.86))
    rrect(ctx, x, y, w, h, min(w, h) * r); ctx.set_source(g); ctx.fill()
    # soft highlight
    rrect(ctx, x + w * 0.08, y + h * 0.06, w * 0.35, h * 0.12, min(w, h) * 0.06); fill(ctx, (1, 1, 1), 0.12)

def shadow(ctx, x, y, rx, ry, a=0.25):
    ctx.save(); ctx.translate(x, y); ctx.scale(1, ry / rx)
    g = cairo.RadialGradient(0, 0, 0, 0, 0, rx)
    g.add_color_stop_rgba(0, 0, 0, 0, a); g.add_color_stop_rgba(1, 0, 0, 0, 0)
    ctx.set_source(g); ctx.arc(0, 0, rx, 0, 2 * math.pi); ctx.fill(); ctx.restore()

# ------------------------------------------------------------------ faces
def face(ctx, x, y, s, emo, t, seed=0, look=0.0):
    """Draw a face on a head front face whose top-left is (x, y) and size s."""
    blink = (t * 0.9 + seed) % 3.7 < 0.12
    ex, ey = s * 0.22, s * 0.46
    cx = x + s / 2 + look * s * 0.05
    dark = (0.08, 0.07, 0.08)
    def eye(px, py, w=0.085, h=0.13):
        if blink:
            ctx.set_source_rgb(*dark); ctx.set_line_width(s * 0.025)
            ctx.move_to(px - s * w, py); ctx.line_to(px + s * w, py); ctx.stroke(); return
        ctx.save(); ctx.translate(px, py); ctx.scale(1, h / w)
        ctx.arc(0, 0, s * w, 0, 2 * math.pi); ctx.restore(); fill(ctx, dark)
        ctx.arc(px - s * w * 0.3, py - s * h * 0.35, s * w * 0.32, 0, 2 * math.pi); fill(ctx, (1, 1, 1))
    def brow(px, py, ang, inner_up):
        ctx.save(); ctx.translate(px, py); ctx.rotate(ang)
        rrect(ctx, -s * 0.11, -s * 0.022, s * 0.22, s * 0.045, s * 0.02); fill(ctx, dark); ctx.restore()
    lw = s * 0.03
    ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    if emo == "happy":
        ctx.set_source_rgb(*dark); ctx.set_line_width(s * 0.035)
        for sx in (-1, 1):
            ctx.arc(cx + sx * ex, y + ey + s * 0.03, s * 0.075, math.pi * 1.1, math.pi * 1.9); ctx.stroke()
        ctx.arc(cx, y + s * 0.62, s * 0.13, math.pi * 0.15, math.pi * 0.85); ctx.set_line_width(lw); ctx.stroke()
        for sx in (-1, 1):
            ctx.arc(cx + sx * s * 0.33, y + s * 0.64, s * 0.06, 0, 2 * math.pi); fill(ctx, (1, 0.45, 0.5), 0.35)
        return
    if emo in ("neutral", "smug"):
        eye(cx - ex, y + ey); eye(cx + ex, y + ey)
        ctx.set_source_rgb(*dark); ctx.set_line_width(lw)
        if emo == "smug":
            ctx.move_to(cx - s * 0.12, y + s * 0.72); ctx.curve_to(cx, y + s * 0.74, cx + s * 0.08, y + s * 0.72, cx + s * 0.14, y + s * 0.66); ctx.stroke()
            brow(cx - ex, y + ey - s * 0.16, 0.0, False); brow(cx + ex, y + ey - s * 0.19, -0.25, False)
        else:
            ctx.move_to(cx - s * 0.1, y + s * 0.72); ctx.line_to(cx + s * 0.1, y + s * 0.72); ctx.stroke()
        return
    if emo in ("sad", "worried", "cold"):
        eye(cx - ex, y + ey + s * 0.02); eye(cx + ex, y + ey + s * 0.02)
        brow(cx - ex, y + ey - s * 0.15, -0.35, True); brow(cx + ex, y + ey - s * 0.15, 0.35, True)
        ctx.set_source_rgb(*dark); ctx.set_line_width(lw)
        if emo == "sad":
            ctx.arc(cx, y + s * 0.8, s * 0.11, math.pi * 1.2, math.pi * 1.8); ctx.stroke()
        else:   # wavy mouth
            ctx.move_to(cx - s * 0.14, y + s * 0.74)
            for k in range(6):
                ctx.line_to(cx - s * 0.14 + (k + 1) * s * 0.047, y + s * 0.74 + (s * 0.025 if k % 2 == 0 else -s * 0.025))
            ctx.stroke()
        if emo == "cold":
            for sx in (-1, 1):
                ctx.arc(cx + sx * s * 0.33, y + s * 0.62, s * 0.06, 0, 2 * math.pi); fill(ctx, (0.5, 0.7, 1.0), 0.4)
        return
    if emo == "tired":
        for sx in (-1, 1):
            px = cx + sx * ex
            ctx.save(); ctx.translate(px, y + ey); ctx.scale(1, 0.6); ctx.arc(0, 0, s * 0.085, 0, math.pi); ctx.restore(); fill(ctx, dark)
            ctx.set_source_rgba(0.45, 0.35, 0.5, 0.5); ctx.set_line_width(s * 0.02)
            ctx.arc(px, y + ey + s * 0.04, s * 0.08, math.pi * 0.2, math.pi * 0.8); ctx.stroke()
        ctx.set_source_rgb(*dark); ctx.set_line_width(lw)
        ctx.move_to(cx - s * 0.08, y + s * 0.74); ctx.line_to(cx + s * 0.08, y + s * 0.73); ctx.stroke()
        return
    if emo == "shocked":
        for sx in (-1, 1):
            ctx.arc(cx + sx * ex, y + ey, s * 0.1, 0, 2 * math.pi); fill(ctx, (1, 1, 1))
            ctx.arc(cx + sx * ex, y + ey, s * 0.05, 0, 2 * math.pi); fill(ctx, dark)
        brow(cx - ex, y + ey - s * 0.2, 0.15, True); brow(cx + ex, y + ey - s * 0.2, -0.15, True)
        ctx.save(); ctx.translate(cx, y + s * 0.76); ctx.scale(1, 1.3); ctx.arc(0, 0, s * 0.07, 0, 2 * math.pi); ctx.restore(); fill(ctx, dark)
        return
    if emo == "angry":
        eye(cx - ex, y + ey + s * 0.03, 0.08, 0.1); eye(cx + ex, y + ey + s * 0.03, 0.08, 0.1)
        brow(cx - ex, y + ey - s * 0.11, 0.45, False); brow(cx + ex, y + ey - s * 0.11, -0.45, False)
        open_ = 0.5 + 0.5 * abs(math.sin(t * 9))
        rrect(ctx, cx - s * 0.16, y + s * 0.66, s * 0.32, s * (0.08 + 0.12 * open_), s * 0.05); fill(ctx, (0.35, 0.05, 0.08))
        rrect(ctx, cx - s * 0.14, y + s * 0.665, s * 0.28, s * 0.035, s * 0.01); fill(ctx, (1, 1, 1))
        return
    if emo == "crazy":   # poodles
        eye(cx - ex, y + ey); eye(cx + ex, y + ey)
        return

def tear(ctx, x, y, s, t):
    u = (t * 0.8) % 1.0
    yy = y + u * s * 0.4
    ctx.move_to(x, yy - s * 0.05); ctx.curve_to(x + s * 0.04, yy, x + s * 0.03, yy + s * 0.05, x, yy + s * 0.05)
    ctx.curve_to(x - s * 0.03, yy + s * 0.05, x - s * 0.04, yy, x, yy - s * 0.05); fill(ctx, (0.45, 0.75, 1.0), 0.9 * (1 - u * 0.5))

# ------------------------------------------------------------------ characters
SKIN = (0.96, 0.78, 0.58)
GIRL = dict(shirt=(0.68, 0.58, 0.92), pants=(0.25, 0.35, 0.6), hair=(0.32, 0.2, 0.14), shoes=(0.95, 0.95, 0.95), long=True)
MOM = dict(shirt=(0.78, 0.22, 0.28), pants=(0.25, 0.25, 0.3), hair=(0.18, 0.13, 0.12), shoes=(0.15, 0.15, 0.16), long=False)

ARMS = {  # (left angle, right angle) in radians; 0 = down
    "idle": (0.08, -0.08), "hug": (-0.95, 0.95), "cross": None, "point": (0.08, -1.45), "shrug": (2.3, -2.3),
    "yell": (2.6, -2.6), "facepalm": (0.08, 2.6), "phone": (0.08, 2.75), "holdcat": (-0.95, 0.95),
}

def draw_cat(ctx, x, y, k, t, emo="happy"):
    """Cat sitting; (x, y) = bottom centre; k = scale."""
    gray, dark, white = (0.62, 0.62, 0.66), (0.36, 0.36, 0.4), (0.97, 0.96, 0.94)
    tail = math.sin(t * 2.2) * 0.25
    ctx.save(); ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.set_source_rgb(*mul(gray, 0.85)); ctx.set_line_width(k * 0.18)
    ctx.move_to(x + k * 0.45, y - k * 0.2); ctx.curve_to(x + k * 1.0, y - k * 0.3, x + k * (0.95 + tail), y - k * 0.9, x + k * (0.7 + tail), y - k * 1.1); ctx.stroke(); ctx.restore()
    block(ctx, x - k * 0.55, y - k * 0.95, k * 1.1, k * 0.95, gray, 0.18)
    rrect(ctx, x - k * 0.25, y - k * 0.7, k * 0.5, k * 0.6, k * 0.15); fill(ctx, white)
    for i in range(3):
        poly(ctx, [(x - k * 0.55, y - k * (0.85 - i * 0.2)), (x - k * 0.35, y - k * (0.8 - i * 0.2)), (x - k * 0.55, y - k * (0.75 - i * 0.2))], dark)
    bob = math.sin(t * 2.0) * k * 0.02
    hx, hy, hs = x - k * 0.5, y - k * 1.75 + bob, k
    for sx in (0.12, 0.66):
        poly(ctx, [(hx + hs * sx, hy + hs * 0.08), (hx + hs * (sx + 0.11), hy - hs * 0.22), (hx + hs * (sx + 0.22), hy + hs * 0.08)], gray)
        poly(ctx, [(hx + hs * (sx + 0.05), hy + hs * 0.06), (hx + hs * (sx + 0.11), hy - hs * 0.12), (hx + hs * (sx + 0.17), hy + hs * 0.06)], (1, 0.7, 0.75))
    block(ctx, hx, hy, hs, hs * 0.82, gray, 0.15)
    for i in range(3):
        rrect(ctx, hx + hs * (0.38 + i * 0.1), hy + hs * 0.02, hs * 0.04, hs * 0.16, hs * 0.02); fill(ctx, dark)
    ex, ey = hx + hs * 0.3, hy + hs * 0.38
    if emo == "happy":
        ctx.set_source_rgb(0.1, 0.1, 0.1); ctx.set_line_width(hs * 0.04)
        for px in (ex, ex + hs * 0.4):
            ctx.arc(px, ey + hs * 0.03, hs * 0.07, math.pi * 1.1, math.pi * 1.9); ctx.stroke()
    else:
        for px in (ex, ex + hs * 0.4):
            ctx.save(); ctx.translate(px, ey); ctx.scale(1, 1.3); ctx.arc(0, 0, hs * 0.075, 0, 2 * math.pi); ctx.restore(); fill(ctx, (0.45, 0.75, 0.35))
            ctx.save(); ctx.translate(px, ey); ctx.scale(0.35, 1.2); ctx.arc(0, 0, hs * 0.065, 0, 2 * math.pi); ctx.restore(); fill(ctx, (0.05, 0.05, 0.05))
    nx, ny = hx + hs * 0.5, hy + hs * 0.55
    poly(ctx, [(nx - hs * 0.05, ny), (nx + hs * 0.05, ny), (nx, ny + hs * 0.05)], (1, 0.55, 0.6))
    ctx.set_source_rgb(0.15, 0.15, 0.15); ctx.set_line_width(hs * 0.02)
    ctx.arc(nx - hs * 0.04, ny + hs * 0.07, hs * 0.04, 0, math.pi); ctx.stroke()
    ctx.arc(nx + hs * 0.04, ny + hs * 0.07, hs * 0.04, 0, math.pi); ctx.stroke()
    ctx.set_line_width(hs * 0.012); ctx.set_source_rgba(0.2, 0.2, 0.2, 0.7)
    for sx in (-1, 1):
        for dy in (-0.03, 0.03):
            ctx.move_to(nx + sx * hs * 0.12, ny + hs * 0.05); ctx.line_to(nx + sx * hs * 0.42, ny + hs * (0.02 + dy * 2)); ctx.stroke()

def draw_person(ctx, x, floor, s, look, emo, pose, t, seed=0, holding_cat=False, shiver=0.0, pet="cat"):
    sk = SKIN
    breathe = math.sin(t * 2.0 + seed) * s * 0.012
    jit = (math.sin(t * 47) * s * 0.012 * shiver)
    x += jit
    if pose == "yell": breathe += abs(math.sin(t * 9)) * s * 0.03
    leg_h, torso_h, head = s * 0.85, s * 0.95, s
    ty = floor - leg_h - torso_h + breathe
    shadow(ctx, x, floor, s * 0.95, s * 0.16)
    # back hair
    if look["long"]:
        block(ctx, x - s * 0.6, ty - head * 0.98, s * 1.2, head * 1.55, look["hair"], 0.12)
    # legs
    for sx in (-1, 1):
        block(ctx, x + sx * s * 0.26 - s * 0.23, floor - leg_h, s * 0.46, leg_h, look["pants"], 0.14)
        block(ctx, x + sx * s * 0.26 - s * 0.25, floor - s * 0.16, s * 0.5, s * 0.16, look["shoes"], 0.2)
    # torso
    block(ctx, x - s * 0.52, ty, s * 1.04, torso_h, look["shirt"], 0.16)
    # arms
    angs = ARMS.get(pose)
    aw, ah = s * 0.36, s * 0.92
    if angs is None:   # crossed arms
        for sx in (-1, 1):
            block(ctx, x + sx * s * 0.54 - (aw if sx < 0 else 0), ty + s * 0.05, aw, ah * 0.55, mul(look["shirt"], 0.95), 0.14)
        block(ctx, x - s * 0.62, ty + s * 0.42, s * 1.24, s * 0.3, mul(look["shirt"], 1.05), 0.14)
        for sx in (-1, 1):
            rrect(ctx, x + sx * s * 0.45 - s * 0.13, ty + s * 0.43, s * 0.26, s * 0.27, s * 0.08); fill(ctx, sk)
    else:
        la, ra = angs
        if pose in ("shrug", "yell"):
            wob = math.sin(t * (9 if pose == "yell" else 3)) * 0.15
            la += wob; ra -= wob
        for sx, ang in ((-1, la), (1, ra)):
            ctx.save(); ctx.translate(x + sx * s * 0.68, ty + s * 0.12); ctx.rotate(ang)
            block(ctx, -aw / 2, 0, aw, ah * 0.72, look["shirt"], 0.14)
            rrect(ctx, -aw * 0.45, ah * 0.7, aw * 0.9, ah * 0.28, aw * 0.25); fill(ctx, sk)
            if pose == "phone" and sx == 1:
                rrect(ctx, -aw * 0.35, ah * 0.78, aw * 0.7, ah * 0.42, aw * 0.12); fill(ctx, (0.1, 0.1, 0.12))
                rrect(ctx, -aw * 0.27, ah * 0.82, aw * 0.54, ah * 0.33, aw * 0.08); fill(ctx, (0.5, 0.8, 1.0))
            ctx.restore()
    if holding_cat or pose in ("hug", "holdcat"):
        if pet == "dog": draw_poodle(ctx, x + s * 0.1, ty + torso_h * 0.95, s * 0.42, t, seed)
        else: draw_cat(ctx, x + s * 0.05, ty + torso_h * 0.95, s * 0.62, t, "happy" if emo in ("happy", "smug") else "open")
        for sx in (-1, 1):   # hands in front of the cat
            rrect(ctx, x + sx * s * 0.3 - s * 0.15, ty + s * 0.55, s * 0.3, s * 0.24, s * 0.09); fill(ctx, sk)
    # head
    hx, hy = x - head / 2, ty - head * 0.98
    tilt = math.sin(t * 1.3 + seed) * 0.025
    ctx.save(); ctx.translate(x, ty); ctx.rotate(tilt); ctx.translate(-x, -ty)
    block(ctx, hx, hy, head, head * 0.95, mix(sk, (0.75, 0.85, 1.0), 0.35 * shiver), 0.16)
    face(ctx, hx, hy, head, emo, t, seed)
    # hair top
    hair = look["hair"]
    block(ctx, hx - head * 0.06, hy - head * 0.12, head * 1.12, head * 0.3, hair, 0.18)
    if look["long"]:
        block(ctx, hx - head * 0.08, hy + head * 0.05, head * 0.2, head * 0.8, hair, 0.15)
        block(ctx, hx + head * 0.88, hy + head * 0.05, head * 0.2, head * 0.8, hair, 0.15)
        poly(ctx, [(hx + head * 0.1, hy + head * 0.18), (hx + head * 0.55, hy + head * 0.12), (hx + head * 0.2, hy + head * 0.3)], hair)
    elif look.get("style", "bun") == "bun":
        block(ctx, hx + head * 0.3, hy - head * 0.42, head * 0.4, head * 0.32, hair, 0.2)   # bun
        block(ctx, hx - head * 0.06, hy + head * 0.05, head * 0.14, head * 0.45, hair, 0.15)
        block(ctx, hx + head * 0.92, hy + head * 0.05, head * 0.14, head * 0.45, hair, 0.15)
    else:   # short hair
        block(ctx, hx - head * 0.04, hy + head * 0.02, head * 0.12, head * 0.28, hair, 0.15)
        block(ctx, hx + head * 0.92, hy + head * 0.02, head * 0.12, head * 0.28, hair, 0.15)
    ctx.restore()
    if pose == "facepalm":
        rrect(ctx, hx + head * 0.05, hy + head * 0.32, head * 0.55, head * 0.32, head * 0.12); fill(ctx, sk)
    return (hx, hy, head)

def draw_poodle(ctx, x, floor, k, t, seed, crazy=False):
    bounce = abs(math.sin(t * (7 if crazy else 2.5) + seed)) * k * (0.6 if crazy else 0.08)
    y = floor - bounce
    shadow(ctx, x, floor, k * 0.9, k * 0.15, 0.25 * (1 - bounce / (k * 1.5)))
    white, pink = (0.98, 0.97, 0.96), (1.0, 0.6, 0.7)
    for sx in (-0.45, -0.15, 0.2, 0.5):
        block(ctx, x + sx * k - k * 0.08, y - k * 0.55, k * 0.16, k * 0.55, (0.95, 0.94, 0.92), 0.2)
        puff(ctx, x + sx * k, y - k * 0.05, k * 0.16, white)
    for (px, py, r) in ((-0.3, -0.85, 0.42), (0.2, -0.9, 0.45), (-0.05, -1.05, 0.4)):
        puff(ctx, x + px * k, y + py * k, r * k, white)
    puff(ctx, x + k * 0.7, y - k * 1.0, k * 0.18, white)
    hx, hy = x - k * 0.55, y - k * 1.5
    puff(ctx, hx - k * 0.18, hy + k * 0.05, k * 0.2, white); puff(ctx, hx + k * 0.38, hy + k * 0.05, k * 0.2, white)
    puff(ctx, hx + k * 0.1, hy - k * 0.15, k * 0.36, white)
    puff(ctx, hx + k * 0.1, hy - k * 0.45, k * 0.24, white)
    for sx in (-0.08, 0.28):
        ctx.arc(hx + sx * k, hy - k * 0.16, k * 0.05, 0, 2 * math.pi); fill(ctx, (0.08, 0.08, 0.08))
    ctx.arc(hx + k * 0.1, hy - k * 0.02, k * 0.06, 0, 2 * math.pi); fill(ctx, (0.1, 0.1, 0.1))
    if crazy:
        rrect(ctx, hx + k * 0.04, hy + k * 0.05, k * 0.13, k * 0.22, k * 0.06); fill(ctx, pink)

def puff(ctx, x, y, r, col):
    g = cairo.RadialGradient(x - r * 0.3, y - r * 0.35, r * 0.1, x, y, r)
    g.add_color_stop_rgb(0, *col); g.add_color_stop_rgb(1, *mul(col, 0.82))
    ctx.set_source(g)
    for k in range(8):
        a = k * math.pi / 4
        ctx.arc(x + math.cos(a) * r * 0.45, y + math.sin(a) * r * 0.45, r * 0.6, 0, 2 * math.pi); ctx.fill()

# ------------------------------------------------------------------ scenes
def wall(ctx, col, dots=True, x0=-900, x1=1980, y0=-900, y1=FLOOR - 120):
    ctx.rectangle(x0, y0, x1 - x0, y1 - y0); fill(ctx, col)
    if dots:
        for yy in range(y0, y1, 70):
            for xx in range(x0 + (35 if (yy // 70) % 2 else 0), x1, 70):
                ctx.arc(xx, yy, 6, 0, 2 * math.pi); fill(ctx, mul(col, 0.9))
    ctx.rectangle(x0, y1 - 40, x1 - x0, 40); fill(ctx, mul(col, 0.8))

def floor(ctx, col, y0=FLOOR - 120, x0=-900, x1=1980):
    ctx.rectangle(x0, y0, x1 - x0, 2000); fill(ctx, col)
    for i in range(14):
        yy = y0 + 18 + i * i * 9
        ctx.rectangle(x0, yy, x1 - x0, 3); fill(ctx, mul(col, 0.88))
    for xx in range(x0, x1, 160):
        ctx.move_to(540 + (xx - 540) * 0.5, y0); ctx.line_to(540 + (xx - 540) * 2.2, y0 + 1600)
        ctx.set_source_rgba(*mul(col, 0.85), 1); ctx.set_line_width(3); ctx.stroke()

def window_frame(ctx, x, y, w, h, sky, night=True, t=0, rain=0):
    block(ctx, x - 20, y - 20, w + 40, h + 40, (0.95, 0.93, 0.9), 0.05)
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgb(0, *sky[0]); g.add_color_stop_rgb(1, *sky[1])
    ctx.rectangle(x, y, w, h); ctx.set_source(g); ctx.fill()
    if night:
        r = random.Random(1)
        for i in range(30):
            ctx.arc(x + r.uniform(0, w), y + r.uniform(0, h * 0.6), r.uniform(1, 3), 0, 2 * math.pi); fill(ctx, (1, 1, 0.9), 0.8)
        ctx.arc(x + w * 0.75, y + h * 0.25, w * 0.09, 0, 2 * math.pi); fill(ctx, (1, 0.97, 0.85))
    if rain:
        r = random.Random(4); ctx.set_line_width(3)
        for i in range(60):
            px = x + r.uniform(0, w); py = y + ((r.uniform(0, 1) + t * 1.2) % 1) * h
            ctx.move_to(px, py); ctx.line_to(px - 6, py + 40); ctx.set_source_rgba(0.75, 0.82, 0.95, 0.6); ctx.stroke()
    ctx.rectangle(x + w / 2 - 8, y, 16, h); fill(ctx, (0.95, 0.93, 0.9))
    ctx.rectangle(x, y + h / 2 - 8, w, 16); fill(ctx, (0.95, 0.93, 0.9))

def scene_bedroom(ctx, t, fx):
    wall(ctx, (0.98, 0.82, 0.86))
    floor(ctx, (0.8, 0.6, 0.42))
    window_frame(ctx, 600, 520, 380, 440, ((0.12, 0.14, 0.32), (0.3, 0.25, 0.5)), True, t)
    block(ctx, -420, 1090, 560, 360, (0.5, 0.75, 0.95), 0.1)     # bed
    block(ctx, -420, 1020, 200, 90, (1, 1, 1), 0.2)
    rrect(ctx, 120, 560, 230, 300, 12); fill(ctx, (0.55, 0.5, 0.85))   # poster
    ctx.arc(235, 680, 70, 0, 2 * math.pi); fill(ctx, (1, 0.85, 0.4))
    block(ctx, 1100, 1060, 380, 380, (0.95, 0.9, 0.78), 0.1)       # dresser
    ctx.rectangle(-900, 980, 2900, 0)

def scene_bed(ctx, t, fx):
    wall(ctx, (0.85, 0.82, 0.98), y1=1100)
    window_frame(ctx, 640, 260, 340, 380, ((0.12, 0.14, 0.32), (0.3, 0.25, 0.5)), True, t)
    block(ctx, -200, 1050, 1480, 600, (0.95, 0.95, 0.98), 0.06)   # bed
    block(ctx, -200, 980, 1480, 120, (0.85, 0.85, 0.9), 0.08)
    block(ctx, 60, 900, 360, 170, (1, 1, 1), 0.18)                # pillow

def scene_desk(ctx, t, fx):
    wall(ctx, (0.8, 0.86, 0.95), y1=1250)
    window_frame(ctx, 90, 300, 320, 360, ((0.05, 0.06, 0.18), (0.15, 0.12, 0.3)), True, t)
    # clock showing 2:00
    ctx.arc(820, 420, 110, 0, 2 * math.pi); fill(ctx, (1, 1, 1)); ctx.set_source_rgb(0.2, 0.2, 0.2); ctx.set_line_width(10)
    ctx.arc(820, 420, 110, 0, 2 * math.pi); ctx.stroke()
    ctx.set_line_width(12); ctx.move_to(820, 420); ctx.line_to(820 + 55 * math.cos(-math.pi / 2 + math.pi / 3), 420 + 55 * math.sin(-math.pi / 2 + math.pi / 3)); ctx.stroke()
    ctx.set_line_width(8); a = -math.pi / 2 + t * 1.5
    ctx.move_to(820, 420); ctx.line_to(820 + 85 * math.cos(a), 420 + 85 * math.sin(a)); ctx.stroke()
    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(40)
    ctx.set_source_rgb(0.9, 0.3, 0.3); ctx.move_to(770, 590); ctx.show_text("2 AM")

def scene_desk_front(ctx, t, fx):
    # desk surface in front of the character
    block(ctx, -300, 1400, 1700, 900, (0.72, 0.52, 0.36), 0.04)
    for i, (bx, h, c) in enumerate([(40, 70, (0.9, 0.35, 0.3)), (30, 60, (0.3, 0.55, 0.9)), (55, 75, (0.35, 0.75, 0.45)), (35, 65, (0.95, 0.75, 0.3)), (45, 70, (0.6, 0.4, 0.8))]):
        block(ctx, bx - 120, 1340 - i * 72, 280, h, c, 0.25)
    block(ctx, 700, 1180, 340, 230, (0.25, 0.25, 0.28), 0.1)      # laptop
    rrect(ctx, 720, 1198, 300, 190, 8); fill(ctx, (0.75, 0.9, 1.0))
    for i in range(6):
        ctx.rectangle(745, 1220 + i * 26, 160 + (i * 37) % 100, 8); fill(ctx, (0.35, 0.45, 0.6))

def scene_living(ctx, t, fx):
    wall(ctx, (0.75, 0.88, 0.86))
    floor(ctx, (0.62, 0.5, 0.42))
    block(ctx, -500, 1040, 560, 380, (0.9, 0.55, 0.35), 0.1)       # sofa
    block(ctx, -520, 960, 600, 140, mul((0.9, 0.55, 0.35), 0.9), 0.15)
    rrect(ctx, 760, 520, 420, 260, 14); fill(ctx, (0.15, 0.15, 0.18))  # TV
    rrect(ctx, 775, 535, 390, 230, 10); fill(ctx, (0.3, 0.4, 0.55))
    ctx.save(); ctx.translate(540, 1530); ctx.scale(1, 0.18); ctx.arc(0, 0, 640, 0, 2 * math.pi); ctx.restore(); fill(ctx, (0.85, 0.75, 0.55))
    rrect(ctx, 250, 500, 160, 200, 10); fill(ctx, (0.95, 0.9, 0.7))
    if "fluff" in fx:
        r = random.Random(int(t * 6))
        for i in range(18):
            px, py = 300 + r.uniform(0, 700), 700 + r.uniform(0, 700)
            puff(ctx, px, py, r.uniform(10, 26), (1, 1, 1))

def scene_kitchen(ctx, t, fx):
    wall(ctx, (0.98, 0.95, 0.85), dots=False)
    for yy in range(-900, FLOOR - 160, 90):
        for xx in range(-900, 1980, 90):
            ctx.rectangle(xx, yy, 88, 88); fill(ctx, (0.98, 0.95, 0.85) if (xx // 90 + yy // 90) % 2 else (0.95, 0.91, 0.8))
    floor(ctx, (0.85, 0.85, 0.88))
    block(ctx, -600, 1000, 700, 440, (0.55, 0.75, 0.6), 0.08)      # counter
    block(ctx, -620, 960, 740, 60, (0.95, 0.95, 0.95), 0.2)
    block(ctx, 1050, 640, 330, 800, (0.92, 0.94, 0.96), 0.08)     # fridge
    window_frame(ctx, 120, 420, 320, 300, ((0.55, 0.75, 0.95), (0.85, 0.92, 1.0)), False, t)

def scene_window(ctx, t, fx):
    wall(ctx, (0.7, 0.72, 0.82), y1=1700)
    floor(ctx, (0.55, 0.45, 0.4), y0=1660)
    window_frame(ctx, 140, 260, 800, 900, ((0.3, 0.33, 0.42), (0.5, 0.52, 0.6)), False, t, rain=1)
    block(ctx, 60, 1180, 960, 70, (0.95, 0.95, 0.95), 0.15)       # sill

def scene_exterior(ctx, t, fx):
    g = cairo.LinearGradient(0, -900, 0, 1300)
    g.add_color_stop_rgb(0, 0.45, 0.65, 0.95); g.add_color_stop_rgb(1, 0.85, 0.92, 1.0)
    ctx.rectangle(-900, -900, 2900, 2300); ctx.set_source(g); ctx.fill()
    for (cx, cy, r) in ((100, 300, 60), (180, 290, 80), (260, 310, 55), (800, 200, 50), (870, 190, 70)):
        ctx.arc(cx, cy, r, 0, 2 * math.pi); fill(ctx, (1, 1, 1), 0.9)
    ctx.rectangle(-900, 1350, 2900, 1500); fill(ctx, (0.55, 0.78, 0.45))
    ctx.rectangle(-900, 1560, 2900, 120); fill(ctx, (0.55, 0.55, 0.58))
    for i, (hx, col, roof) in enumerate([(-350, (0.95, 0.85, 0.7), (0.65, 0.35, 0.3)), (230, (0.75, 0.82, 0.95), (0.35, 0.4, 0.55)),
                                          (800, (0.98, 0.92, 0.8), (0.55, 0.3, 0.3)), (1350, (0.85, 0.9, 0.75), (0.4, 0.45, 0.35))]):
        w, h = 470, 380
        block(ctx, hx, 1360 - h, w, h, col, 0.12)
        poly(ctx, [(hx - 40, 1360 - h + 6), (hx + w / 2, 1360 - h - 230), (hx + w + 40, 1360 - h + 6)], roof)
        poly(ctx, [(hx + w + 40, 1360 - h + 6), (hx + w / 2, 1360 - h - 230), (hx + w / 2 + 50, 1360 - h - 260), (hx + w + 90, 1360 - h - 25)], mul(roof, 0.75))
        block(ctx, hx + w * 0.4, 1360 - 180, w * 0.2, 180, mul(roof, 0.9), 0.1)
        for wx in (hx + 50, hx + w - 150):
            rrect(ctx, wx, 1360 - h + 70, 100, 100, 8); fill(ctx, (1, 0.9, 0.55) if i == 1 else (0.6, 0.8, 0.95))
        ctx.set_source_rgb(0.3, 0.6, 0.3); ctx.arc(hx - 60, 1330, 60, 0, 2 * math.pi); ctx.fill()

SCENES = dict(bedroom=scene_bedroom, bed=scene_bed, desk=scene_desk, living=scene_living, kitchen=scene_kitchen,
              window=scene_window, exterior=scene_exterior)


def heart(ctx, x, y, r, col, a):
    ctx.move_to(x, y + r * 0.9)
    ctx.curve_to(x - r * 1.4, y - r * 0.1, x - r * 0.6, y - r * 1.1, x, y - r * 0.35)
    ctx.curve_to(x + r * 0.6, y - r * 1.1, x + r * 1.4, y - r * 0.1, x, y + r * 0.9); fill(ctx, col, a)

