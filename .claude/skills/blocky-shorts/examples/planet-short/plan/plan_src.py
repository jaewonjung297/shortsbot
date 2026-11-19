"""Plan source for "The Planet That Talks Back": shots, accents and tags anchored to WORDS of the voice-over, not to
seconds. Re-run after every VO change; the times move with the words. Writes src/plan.gen.ts and plan/SHOTS.md.

    python plan/plan_src.py vo/timings.json

timings.json: {"turns": [{"turn": 1, "words": [{"w": "Hello", "t": 0.12, "end": 0.48}, ...]}, ...]}  (vo/transcribe.py)
One turn = one line of script.txt.
"""
import json, sys
from pathlib import Path

FPS = 30
LEAD = 2  # captions appear 2 frames before the word
TAIL = 0.6  # picture runs on after the last word (references/scripts.md: 0.5-0.9 s)

# ---- the story, by words ---------------------------------------------------------------------------------------
# Pace from references/style.md section 5: a hard cut about every 1.25-1.5 s, ~half face close-ups.
# A shot starts on its anchor word (line, word, nth occurrence in that line). Sets: store (the planet store, day),
# home (the kid's room at night), jar (macro on the Earth in its glass jar), earth (down on Earth's surface),
# store2 (the store, the next day), space (outside the store).
SHOTS = [
    # id,   anchor,                     set,     what we see
    ("S01", (1, "in", 1), "store", "HOOK at 0.0 s: kid + dad walk the aisle, kid's face 3/4, planets glowing on the shelves, price tags in frame"),
    ("S02", (1, "aliens", 1), "store", "close-up: the kid looks up in wonder, a planet's glow on the face"),
    ("S03", (1, "planets", 1), "store", "wide, high: the whole store, shelves of planets, a big window onto space, the PLANET SHOP sign"),
    ("S04", (2, "big", 1), "store", "low angle: the dad looks up at a huge gas giant on a stand"),
    ("S05", (2, "shiny", 1), "store", "close-up: the kid beside a chrome planet, seeing his own reflection"),
    ("S06", (2, "ones", 3), "store", "medium: a ringed planet spins on a shelf, the kid points"),
    ("S07", (3, "saturn", 1), "store", "insert: the ringed gold planet with its tag SATURN $9,999,999"),
    ("S08", (3, "fortune", 1), "store", "close-up: the dad's shock (mouth O, antennae straight up)"),
    ("S09", (3, "jupiter", 1), "store", "insert: the striped giant, a tiny storm crackling on it, tag FREE STORMS!"),
    ("S10", (3, "storms", 1), "store", "close-up: the kid laughs as the little lightning flickers on his face"),
    ("S11", (4, "but", 1), "store", "medium: the kid crouches by the bottom shelf, curious"),
    ("S12", (4, "earth", 2), "store", "low by the floor: a small dusty Earth on the bottom shelf among junk"),
    ("S13", (4, "planet", 1), "store", "high 3/4: the kid kneeling at the bottom shelf, the dad behind looking down"),
    ("S14", (5, "ninety-nine", 1), "store", "insert: the big paper 99¢ tag next to the dusty Earth"),
    ("S15", (6, "an", 1), "store", "medium: the dad picks Earth up and holds it in his palm"),
    ("S16", (6, "and", 1), "store", "close-up: the dad, one brow up, turns toward the counter"),
    ("S17", (7, "the", 1), "store", "medium: the little seller behind the counter leans in over it"),
    ("S18", (7, "whispered", 1), "store", "close-up: the seller, hand by his mouth, sly eyes"),
    ("S19", (8, "it", 1), "store", "macro: Earth in the dad's hand, tiny city lights twinkling"),
    ("S20", (8, "humans", 1), "store", "close-up: the dad's shock"),
    ("S21", (9, "the", 1), "store", "medium: the dad puts Earth back on the bottom shelf"),
    ("S22", (9, "too", 1), "store", "close-up: the dad shakes his head, arms crossed"),
    ("S23", (10, "but", 1), "store", "close-up: the kid hugs Earth to his chest"),
    ("S24", (10, "fallen", 1), "store", "medium-close: the kid holds Earth up, heart eyes, sparkles"),
    ("S25", (11, "so", 1), "store", "wide: dad and kid walk to the door, the kid carries Earth in a glass jar"),
    ("S26", (11, "earth", 1), "store", "close: the jar in the kid's arms, Earth bobbing inside, the kid's happy face above"),
    ("S27", (12, "and", 1), "home", "the kid's room at night: the jar on the windowsill, the kid's face close beside it"),
    ("S28", (12, "human", 1), "jar", "macro through the glass: Earth turns, tiny houses and lights on it"),
    ("S29", (13, "they", 1), "earth", "down on Earth: tiny blocky houses pop up out of the grass (cities)"),
    ("S30", (13, "they", 2), "earth", "two humans tug-of-war over a sandwich on a lawn"),
    ("S31", (13, "they", 3), "earth", "a red car with a rocket flame shoots up into the sky"),
    ("S32", (13, "just", 1), "home", "close-up: the kid at the jar, head tilted, the little car floating past inside the glass"),
    ("S33", (14, "every", 1), "home", "wide room at night: kid at the round window, the jar glowing on the sill"),
    ("S34", (14, "kid", 1), "home", "close-up: the kid, chin on his hands, the jar's glow on his face"),
    ("S35", (14, "through", 1), "home", "from outside the round window: kid and jar inside, stars around"),
    ("S36", (15, "until", 1), "jar", "macro: Earth's night side, city lights blink"),
    ("S37", (15, "humans", 1), "earth", "night on Earth: humans on a hill shine flashlights up at the sky"),
    ("S38", (16, "it", 1), "jar", "glowing letters rise from Earth inside the jar: IS ANYONE OUT THERE?"),
    ("S39", (16, "anyone", 1), "home", "close-up: the kid reads it, eyes wide"),
    ("S40", (17, "the", 1), "home", "close-up: the kid's slow smile"),
    ("S41", (17, "and", 1), "home", "medium: the kid holds a hand-written card HI! up to the glass"),
    ("S42", (18, "the", 1), "store2", "next day: the seller at the counter flips through a big catalog"),
    ("S43", (18, "looked", 1), "store2", "insert: the catalog page, Earth, 99¢"),
    ("S44", (19, "earth", 1), "store2", "close-up: the seller's shock"),
    ("S45", (19, "cents", 1), "store2", "insert: the tag flips from 99¢ to PRICELESS"),
    ("S46", (20, "because", 1), "store2", "wide: a crowd of aliens squeezed in at the door, all pointing at the Earth poster"),
    ("S47", (20, "every", 1), "space", "outside: flying saucers queue up in space to the shop's door"),
    ("S48", (20, "wanted", 1), "home", "the kid hugs the jar on the windowsill, smiling; Earth's lights blink"),
    ("S49", (20, "talks", 1), "jar", "macro: Earth in the jar, its little lights blink HI back (end)"),
]
# ONE accent word per sentence or moment, never more (yellow; everything else white).
ACCENT = {(1, "planets"), (3, "fortune"), (4, "cheapest"), (5, "ninety-nine"), (8, "humans"), (9, "risky"), (10, "love"),
          (13, "sandwiches"), (14, "night"), (16, "anyone"), (19, "anymore"), (20, "talks")}
# Painted tags: only the story's key facts, on the key object. Never on everything.
TAGS = [
    # (line, word, text, on-object note)
    (3, "saturn", "SATURN $9,999,999", "price tag on the ringed gold planet"),
    (3, "jupiter", "FREE STORMS!", "tag on the striped giant"),
    (5, "ninety-nine", "99¢", "big paper price tag beside the dusty Earth on the bottom shelf"),
    (16, "is", "IS ANYONE OUT THERE?", "glowing letters inside the jar"),
    (19, "cents", "PRICELESS", "the flipped price tag"),
]
CHUNK_WORDS = 2  # 1-2 lowercase words per caption chunk


def load(p):
    words = []
    for tr in json.loads(Path(p).read_text(encoding="utf8"))["turns"]:
        for w in tr["words"]:
            words.append({"turn": tr["turn"], "w": w["w"], "t": w["t"], "end": w["end"]})
    return words


def bare(w):
    return w.lower().strip(".,!?;:\"'")


def find(words, turn, word, nth=1):
    k = 0
    for w in words:
        if w["turn"] == turn and bare(w["w"]) == word.lower():
            k += 1
            if k == nth:
                return w
    raise SystemExit(f"anchor not found: turn {turn} word {word!r} #{nth}")


def main(p):
    words = load(p)
    total = words[-1]["end"] + TAIL
    shots = []
    for i, (sid, (tn, wd, nth), set_, note) in enumerate(SHOTS):
        t0 = 0.0 if i == 0 else find(words, tn, wd, nth)["t"]
        shots.append({"id": sid, "t": round(t0, 3), "set": set_, "word": f"{tn}:{wd}", "note": note})
    for a, b in zip(shots, shots[1:] + [{"t": total}]):
        a["end"] = round(b["t"], 3)
        if a["end"] - a["t"] < 0.75:
            print(f"WARN {a['id']} is only {a['end'] - a['t']:.2f} s")
        if a["end"] - a["t"] > 2.2:
            print(f"WARN {a['id']} is {a['end'] - a['t']:.2f} s (cut about every 1.25-1.5 s)")
    assert all(a["t"] < b["t"] for a, b in zip(shots, shots[1:])), "shots out of order"
    caps, chunk = [], []
    for w in words:
        chunk.append(w)
        if len(chunk) == CHUNK_WORDS or w["w"][-1:] in ".,!?;:":
            caps.append(chunk)
            chunk = []
    if chunk:
        caps.append(chunk)
    captions = [{
        "text": " ".join(c["w"].lower() for c in ch),
        "accent": [c["w"].lower() for c in ch if (c["turn"], bare(c["w"])) in ACCENT],
        "frame": max(0, round(ch[0]["t"] * FPS) - LEAD),
    } for ch in caps]
    tags = [{"text": tx, "t": round(find(words, tn, wd)["t"], 3), "note": nt} for tn, wd, tx, nt in TAGS]
    n_acc = sum(1 for c in captions if c["accent"])
    lens = [s["end"] - s["t"] for s in shots]
    print(f"{len(shots)} shots (mean {sum(lens) / len(lens):.2f} s, min {min(lens):.2f}, max {max(lens):.2f}), "
          f"{len(captions)} caption chunks, {n_acc} accented, {len(tags)} tags, {total:.2f} s = {round(total * FPS)} frames")
    if n_acc > max(1, total / 4):
        print("WARN too many accents: about one per sentence")
    if len(tags) > max(1, total / 15 + 1):
        print("WARN too many tags: about one per 15 s, key facts only")
    root = Path(__file__).resolve().parent.parent
    plain = [[w["w"], w["t"], w["end"]] for w in words]
    accent = sorted({bare(w["w"]) for w in words if (w["turn"], bare(w["w"])) in ACCENT})
    (root / "src" / "plan.gen.ts").write_text(
        "// generated by plan/plan_src.py; do not edit\n"
        f"export const FPS = {FPS};\nexport const DURATION = {round(total * FPS)};\nexport const END = {total:.3f};\n"
        f"export const LAST_WORD_END = {words[-1]['end']:.3f};\n"
        f"export const SHOTS = {json.dumps(shots)} as const;\n"
        f"export const WORDS: [string, number, number][] = {json.dumps(plain)};\n"
        f"export const ACCENT = {json.dumps(accent)};\n"
        f"export const CAPTIONS = {json.dumps(captions)} as const;\n"
        f"export const TAGS = {json.dumps(tags)} as const;\n", encoding="utf8")
    # the readable plan
    by_turn = {}
    for w in words:
        by_turn.setdefault(w["turn"], []).append(w)
    md = ["# Shot plan: The Planet That Talks Back", "",
          f"Generated by `plan/plan_src.py` from `vo/timings.json`. {len(shots)} shots, {total:.2f} s "
          f"({round(total * FPS)} frames at {FPS} fps), hard cuts, mean shot {sum(lens) / len(lens):.2f} s.", "",
          "| shot | start | end | len | frames | set | starts on the word | spoken during the shot | what we see |",
          "|---|---|---|---|---|---|---|---|---|"]
    for s in shots:
        said = " ".join(w["w"] for w in words if s["t"] - 1e-6 <= w["t"] < s["end"] - 1e-6)
        anchor = next(w["w"] for w in words if abs(w["t"] - s["t"]) < 1e-6) if s["t"] > 0 else words[0]["w"]
        md.append(f"| {s['id']} | {s['t']:.2f} | {s['end']:.2f} | {s['end'] - s['t']:.2f} | "
                  f"{round(s['t'] * FPS)}-{round(s['end'] * FPS) - 1} | {s['set']} | {anchor} | {said} | {s['note']} |")
    md += ["", "Signs and tags (diegetic text, readable muted):", ""]
    md += [f"- {tg['t']:.2f} s · **{tg['text']}** · {tg['note']}" for tg in tags]
    md += ["", "Accent (yellow) caption words: " + ", ".join(accent)]
    (root / "plan" / "SHOTS.md").write_text("\n".join(md) + "\n", encoding="utf8")
    print("wrote src/plan.gen.ts, plan/SHOTS.md")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "vo/timings.json")
