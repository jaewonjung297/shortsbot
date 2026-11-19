"""Render a story spec + narration timeline to video frames."""
import math, random
import cairo
from .art import *
from .art import FLOOR
from .spec import SHIRTS, HAIR

S = 240   # character scale (head size, px)

def looks_from_cast(cast):
    out = {}
    for who, c in cast.items():
        look = c["look"]
        shirt = SHIRTS[c.get("shirt", "blue")]
        hair = HAIR[c.get("hair", "gray" if look == "older_man" else "brown")]
        out[who] = dict(shirt=shirt, hair=hair, pants=(0.25, 0.35, 0.6) if look.startswith("young") else (0.25, 0.25, 0.3),
                        shoes=(0.95, 0.95, 0.95) if look.startswith("young") else (0.15, 0.15, 0.16),
                        long=(look == "young_woman"), style="bun" if look == "older_woman" else "short")
    return out

def char_x(c): return 150 + 780 * float(c.get("x", 0.5))

# ------------------------------------------------------------------ phone chat scene
def scene_phone(ctx, t, u, line):
    g = cairo.LinearGradient(0, 0, 0, H)
    g.add_color_stop_rgb(0, 0.22, 0.2, 0.3); g.add_color_stop_rgb(1, 0.1, 0.1, 0.16)
    ctx.rectangle(-900, -900, 2900, 3800); ctx.set_source(g); ctx.fill()
    px, py, pw, ph = 170, 200, 740, 1380
    rrect(ctx, px - 22, py - 22, pw + 44, ph + 44, 90); fill(ctx, (0.08, 0.08, 0.09))
    rrect(ctx, px, py, pw, ph, 70); fill(ctx, (0.97, 0.97, 0.98))
    rrect(ctx, px + pw / 2 - 90, py + 18, 180, 44, 22); fill(ctx, (0.08, 0.08, 0.09))      # notch
    ctx.rectangle(px, py + 80, pw, 130); fill(ctx, (0.93, 0.93, 0.95))
    ctx.arc(px + pw / 2, py + 125, 38, 0, 2 * math.pi); fill(ctx, (0.7, 0.72, 0.8))
    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(34)
    name = line.get("contact", "")
    te = ctx.text_extents(name); ctx.move_to(px + pw / 2 - te.x_advance / 2, py + 196); ctx.set_source_rgb(0.15, 0.15, 0.2); ctx.show_text(name)
    msgs = line.get("messages", [])
    y = py + 260
    ctx.set_font_size(40)
    for k, m in enumerate(msgs):
        appear = 0.05 + 0.85 * k / max(1, len(msgs))
        if u < appear: break
        pop = ease((u - appear) / 0.06)
        mine = m["from"] == "me"
        lines = wrap(ctx, m["text"], 470)
        bh = 30 + 52 * len(lines); bw = max(ctx.text_extents(s).x_advance for s in lines) + 56
        bx = px + pw - 40 - bw if mine else px + 40
        ctx.save(); ctx.translate(bx + (bw if mine else 0), y + bh / 2); ctx.scale(0.85 + 0.15 * pop, 0.85 + 0.15 * pop); ctx.translate(-(bx + (bw if mine else 0)), -(y + bh / 2))
        rrect(ctx, bx, y, bw, bh, 34); fill(ctx, (0.2, 0.5, 1.0) if mine else (0.88, 0.88, 0.91), pop)
        for j, s in enumerate(lines):
            ctx.move_to(bx + 28, y + 56 + j * 52); ctx.set_source_rgba(*((1, 1, 1) if mine else (0.1, 0.1, 0.12)), pop); ctx.show_text(s)
        ctx.restore()
        y += bh + 26
    # typing dots before the next message
    shown = sum(1 for k in range(len(msgs)) if u >= 0.05 + 0.85 * k / max(1, len(msgs)))
    if shown < len(msgs) and int(t * 3) % 2 == 0:
        rrect(ctx, px + 40, y, 130, 70, 34); fill(ctx, (0.88, 0.88, 0.91))
        for d in range(3): ctx.arc(px + 80 + d * 26, y + 35, 9, 0, 2 * math.pi); fill(ctx, (0.55, 0.55, 0.6))

def wrap(ctx, text, maxw):
    words, out, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if ctx.text_extents(trial).x_advance > maxw and cur: out.append(cur); cur = w
        else: cur = trial
    if cur: out.append(cur)
    return out

# ------------------------------------------------------------------ shots
def draw_shot(ctx, spec, looks, line, t, u):
    sc, fx = line["scene"], line.get("fx", [])
    pet = spec.get("pet")
    SCENES[sc](ctx, t, fx)
    chars = line.get("chars", [])
    if sc == "bed":
        lying = [c for c in chars if c.get("pose") == "lying"] or chars[:1]
        me = lying[0] if lying else {"who": "me", "emotion": "neutral"}
        look = looks.get(me["who"], looks["me"])
        sh = 1.0 if "cold" in fx else 0.0
        hs = 260; hx, hy = 190 + math.sin(t * 47) * 3 * sh, 800
        block(ctx, hx - 40, hy - 40, hs * 1.3, hs * 0.5, look["hair"], 0.12)
        block(ctx, hx, hy, hs, hs * 0.95, mix(SKIN, (0.75, 0.85, 1.0), 0.35 * sh), 0.16)
        face(ctx, hx, hy, hs, me.get("emotion", "neutral"), t, 3)
        block(ctx, hx - 30, hy - 40, hs * 1.15, hs * 0.28, look["hair"], 0.18)
        bl = (0.6, 0.7, 0.95) if sh else mix(look["shirt"], (1, 1, 1), 0.4)
        block(ctx, -150, 1020 + math.sin(t * 2) * 6, 1450, 1300, bl, 0.03)
        for k in range(5): ctx.rectangle(-150, 1080 + k * 90, 1450, 18); fill(ctx, mul(bl, 0.92))
        if any(c["who"] in ("cat", "dog") for c in chars):
            if pet == "dog": draw_poodle(ctx, 700, 1120, 150, t, 1.0)
            else: draw_cat(ctx, 700, 1100, 190, t, "happy" if me.get("emotion") == "happy" else "open")
        if "tears" in fx: tear(ctx, hx + hs * 0.28, hy + hs * 0.55, hs, t)
        return
    desk = sc == "desk"
    for j, c in enumerate(chars):
        who = c["who"]; x = char_x(c)
        if who in ("cat", "dog"):
            crazy = c.get("pose") == "crazy"
            if who == "dog": draw_poodle(ctx, x, FLOOR, 150, t, j * 2.1, crazy=crazy)
            else:
                yy = FLOOR - (abs(math.sin(t * 7 + j)) * 120 if crazy else 0)
                draw_cat(ctx, x, yy, 170, t, "open" if crazy else "happy")
            continue
        look = looks[who]
        pose = c.get("pose", "idle")
        floor_y = FLOOR + 40 if (desk and j == 0) else FLOOR
        if desk and j == 0: x -= 60
        hx, hy, hs = draw_person(ctx, x, floor_y, S, look, c.get("emotion", "neutral"), "hug" if pose == "hold_pet" else pose, t,
                                 seed=j * 1.7, holding_cat=False, shiver=1.0 if "cold" in fx else 0, pet=pet or "cat")
        if j == 0 and "tears" in fx:
            tear(ctx, hx + hs * 0.28, hy + hs * 0.55, hs, t); tear(ctx, hx + hs * 0.72, hy + hs * 0.55, hs, t + 0.5)
        if j == 0 and "sweat" in fx: tear(ctx, hx + hs * 0.95, hy + hs * 0.1, hs * 1.3, t * 0.6)
    if desk: scene_desk_front(ctx, t, fx)
    if "hearts" in fx:
        for k in range(5):
            ph = (t * 0.35 + k * 0.2) % 1
            heart(ctx, 540 + math.sin(k * 2.1 + t) * 260, 900 - ph * 600, 34 + 10 * math.sin(k), (1, 0.4, 0.55), 1 - ph)

def camera(line, u):
    """Camera presets -> (x, y, zoom)."""
    sc = line["scene"]; cam = line.get("cam", "wide"); chars = line.get("chars", [])
    e = ease(u)
    if sc == "phone": return 540, 960, 1.0
    if sc == "bed": a, b = (520, 1150, 1.15), (520, 1120, 1.3)
    elif sc == "desk": a, b = (540, 1100, 1.1), (520, 1050, 1.3)
    elif sc == "exterior": a, b = (380, 1200, 1.0), (700, 1200, 1.08)
    elif cam.startswith("closeup"):
        who = cam.split(":")[1] if ":" in cam else (chars[0]["who"] if chars else "me")
        c = next((c for c in chars if c["who"] == who), chars[0] if chars else {"x": 0.5})
        x = char_x(c)
        a, b = (x, 900, 1.9), (x, 890, 2.1)
    elif cam == "medium": a, b = (540, 1050, 1.35), (540, 1020, 1.5)
    elif cam == "push": a, b = (540, 1150, 1.0), (540, 1000, 1.45)
    else: a, b = (560, 1150, 1.0), (560, 1150, 1.08)
    return lerp(a[0], b[0], e), lerp(a[1], b[1], e), lerp(a[2], b[2], e)

# ------------------------------------------------------------------ captions
def caption_groups(timeline):
    groups = []
    for ln in timeline["lines"]:
        cur = []
        for w in ln["words"]:
            cur.append(w)
            if len(cur) >= 3 or w["w"][-1] in ".?!," or len(" ".join(x["w"] for x in cur)) > 14:
                groups.append(cur); cur = []
        if cur: groups.append(cur)
    return groups

def draw_caption(ctx, groups, t, y=1230):
    grp = None
    for g in groups:
        if g[0]["a"] - 0.02 <= t < g[-1]["b"] + 0.08: grp = g
    if not grp: return
    words = [w["w"].upper().strip(",.\"") for w in grp]
    ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    size = 104; ctx.set_font_size(size)
    widths = [ctx.text_extents(w).x_advance for w in words]; space = size * 0.4
    total = sum(widths) + space * (len(words) - 1)
    if total > 940:
        size *= 940 / total; ctx.set_font_size(size); space = size * 0.4
        widths = [ctx.text_extents(w).x_advance for w in words]; total = sum(widths) + space * (len(words) - 1)
    x = 540 - total / 2
    pop = ease((t - grp[0]["a"]) / 0.08)
    for w, wd, info in zip(words, widths, grp):
        active = info["a"] <= t < info["b"] + 0.05
        sc = (0.88 + 0.12 * pop) * (1.04 if active else 1.0)
        ctx.save(); ctx.translate(x + wd / 2, y); ctx.scale(sc, sc); ctx.translate(-wd / 2, 0)
        ctx.move_to(0, 0); ctx.text_path(w)
        ctx.set_source_rgb(0, 0, 0); ctx.set_line_width(size * 0.16); ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.stroke_preserve()
        ctx.set_source_rgb(*((1.0, 0.86, 0.1) if active else (1, 1, 1))); ctx.fill()
        ctx.restore()
        x += wd + space

# ------------------------------------------------------------------ frames
class StoryRenderer:
    def __init__(self, spec, timeline):
        self.spec, self.tl = spec, timeline
        self.looks = looks_from_cast(spec["cast"])
        self.groups = caption_groups(timeline)
        self.total = timeline["total"]

    def shot_at(self, t):
        for ln in self.tl["lines"]:
            if t < ln["shot_end"]: return ln["i"], ln
        return len(self.tl["lines"]) - 1, self.tl["lines"][-1]

    def frame(self, t):
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); ctx = cairo.Context(surf)
        i, ln = self.shot_at(t)
        start = self.tl["lines"][i - 1]["shot_end"] if i > 0 else 0.0
        u = (t - start) / max(0.01, ln["shot_end"] - start)
        line = self.spec["lines"][i]; fx = line.get("fx", [])
        if line["scene"] == "phone":
            scene_phone(ctx, t, u, line)
        else:
            cx, cy, z = camera(line, u)
            if "punch" in fx: z *= 1 + 0.08 * max(0, 1 - (t - start) / 0.25)
            sx = sy = 0
            if "shake" in fx: sx, sy = math.sin(t * 61) * 12, math.cos(t * 53) * 10
            ctx.save(); ctx.translate(W / 2 + sx, H / 2 + sy); ctx.scale(z, z); ctx.translate(-cx, -cy)
            draw_shot(ctx, self.spec, self.looks, line, t, u)
            ctx.restore()
        if "cold" in fx: ctx.set_source_rgba(0.3, 0.45, 0.9, 0.18); ctx.paint()
        if "desat" in fx: ctx.set_source_rgba(0.35, 0.38, 0.45, 0.3); ctx.paint()
        if "memory" in fx:
            ctx.set_source_rgba(1.0, 0.85, 0.55, 0.22); ctx.paint()
            g = cairo.RadialGradient(540, 960, 300, 540, 960, 1100); g.add_color_stop_rgba(0, 1, 1, 1, 0); g.add_color_stop_rgba(1, 1, 0.95, 0.85, 0.75)
            ctx.set_source(g); ctx.paint()
        if "redflash" in fx: ctx.set_source_rgba(1, 0.1, 0.05, 0.12 + 0.1 * abs(math.sin(t * 6))); ctx.paint()
        if "dark" in fx:
            g = cairo.RadialGradient(540, 900, 200, 540, 900, 900); g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, 0.75 * ease(u * 2))
            ctx.set_source(g); ctx.paint()
        g = cairo.RadialGradient(540, 960, 600, 540, 960, 1300); g.add_color_stop_rgba(0, 0, 0, 0, 0); g.add_color_stop_rgba(1, 0, 0, 0, 0.3)
        ctx.set_source(g); ctx.paint()
        if t - start < 0.06 and i > 0: ctx.set_source_rgba(1, 1, 1, 0.25); ctx.paint()
        draw_caption(ctx, self.groups, t, y=1720 if line["scene"] == "phone" else 1230)
        last = i == len(self.tl["lines"]) - 1
        card = self.spec.get("end_card", "AM I OVERREACTING?")
        if last and card and t > ln["end"] - 1.2:
            a = ease((t - ln["end"] + 1.2) / 0.4)
            ctx.select_font_face("Inter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD); ctx.set_font_size(64)
            te = ctx.text_extents(card.upper())
            rrect(ctx, 540 - te.x_advance / 2 - 40, 340, te.x_advance + 80, 120, 30); fill(ctx, (1, 0.3, 0.35), a)
            ctx.move_to(540 - te.x_advance / 2, 425); ctx.set_source_rgba(1, 1, 1, a); ctx.show_text(card.upper())
        if t > self.total - 0.5:
            ctx.set_source_rgba(0, 0, 0, ease((t - self.total + 0.5) / 0.5)); ctx.paint()
        return surf
