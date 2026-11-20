"""Story spec schema and validator."""
import re

SPEED = 1.575                  # default narration speed (Kokoro)
WORDS = (300, 360)             # target narration words at SPEED (about 65-85 s)
WORDS_OK = (280, 380)          # accepted range at SPEED
LINES = (18, 34)
MODES = ["reddit_story", "in_this_town"]

SEC_PER_SYL, SEC_PER_PAUSE, SEC_PER_WORD = 0.109, 0.204, 0.2   # Kokoro at SPEED, fitted on rendered timelines
GAP, LEAD, TAIL = 0.38, 0.35, 1.6

def line_seconds(text, speed=SPEED):
    """Spoken length of one line."""
    syl = sum(max(1, len(re.findall(r"[aeiouy]+", re.sub(r"[^a-z]", "", w.lower())))) for w in text.split())
    pauses = len(re.findall(r"[,.;:!?\u2014-]\s", text + " "))
    return (SEC_PER_SYL * syl + SEC_PER_PAUSE * pauses) * SPEED / float(speed)

def estimate_seconds(texts, speed=SPEED):
    """Narration length for these lines (matches narrate.py's gaps)."""
    return LEAD + sum(line_seconds(t, speed) for t in texts) + GAP * max(0, len(texts) - 1) + TAIL

def runtime_lines(runtime):
    """Line (= shot) count range for a runtime: one shot every ~1.9-3 s."""
    return max(6, round(runtime / 3.0)), max(8, round(runtime / 1.9))

def runtime_errors(texts, runtime, speed=SPEED):
    est = estimate_seconds(texts, speed)
    errs = []
    if abs(est - runtime) > max(3.0, 0.1 * runtime):
        words = sum(len(t.split()) for t in texts)
        want = round(words * (runtime - LEAD - TAIL - GAP * (len(texts) - 1)) / max(1, est - LEAD - TAIL - GAP * (len(texts) - 1)))
        errs.append("narration runs about %.0f s but the target is %d s; use about %d words in total (now %d)" % (est, runtime, want, words))
    elif runtime >= 60 and est < 62:
        errs.append("narration runs about %.0f s; it must stay over 60 s for TikTok, add a few words" % est)
    lo, hi = runtime_lines(runtime)
    if not lo <= len(texts) <= hi: errs.append("need %d-%d lines for %d s (have %d)" % (lo, hi, runtime, len(texts)))
    return errs

def word_range(speed=SPEED, rng=WORDS):
    """Word range scaled to the narration speed."""
    k = float(speed) / SPEED
    return round(rng[0] * k), round(rng[1] * k)

SCENES = {
    "bedroom": "a bedroom with a bed, window and poster",
    "bed": "close view of someone lying in bed under a blanket (use pose 'lying' for the main character)",
    "desk": "studying/working late at a desk with books and a laptop (first character sits behind the desk)",
    "living": "living room with a sofa and TV",
    "kitchen": "kitchen with counters and a fridge (good for arguments)",
    "window": "someone alone by a rainy window (sad/reflective moments)",
    "exterior": "street of houses from outside; characters optional (use fx 'night' for night, 'party' for party lights)",
    "phone": "full-screen text-message conversation; needs 'contact' and 'messages'",
}
LOOKS = {"young_woman": "long hair", "young_man": "short hair", "older_woman": "hair in a bun", "older_man": "short gray hair",
         "kid_girl": "child (smaller), long hair", "kid_boy": "child (smaller), short hair"}
SHIRTS = {"lavender": (0.68, 0.58, 0.92), "red": (0.78, 0.22, 0.28), "blue": (0.3, 0.5, 0.85), "green": (0.35, 0.65, 0.45),
          "yellow": (0.95, 0.8, 0.3), "orange": (0.95, 0.55, 0.25), "pink": (0.95, 0.55, 0.7), "black": (0.18, 0.18, 0.2),
          "white": (0.93, 0.93, 0.95), "gray": (0.55, 0.56, 0.6), "teal": (0.25, 0.65, 0.65)}
HAIR = {"brown": (0.32, 0.2, 0.14), "black": (0.12, 0.1, 0.1), "blonde": (0.85, 0.7, 0.4), "red": (0.65, 0.28, 0.15), "gray": (0.7, 0.7, 0.72)}
PETS = {"cat": "gray tabby cat", "dog": "fluffy white dog"}
EMOTIONS = ["happy", "neutral", "smug", "sad", "worried", "cold", "tired", "shocked", "angry"]
POSES = ["idle", "hold_pet", "cross", "point", "shrug", "yell", "facepalm", "phone", "lying"]
PET_POSES = ["idle", "crazy"]
CAMS = ["wide", "medium", "push", "closeup"]
FX = {"hearts": "floating hearts", "sweat": "sweat drop on the first character", "tears": "tears on the first character",
      "shake": "screen shake", "punch": "quick zoom punch on the cut", "redflash": "pulsing red tint (anger)",
      "cold": "blue tint + shivering", "desat": "gloomy desaturated tint", "memory": "warm flashback glow",
      "dark": "vignette closing in (ominous)", "fluff": "fluff/mess flying around (chaos)",
      "night": "night sky with moon and stars (exterior)", "party": "pulsing colored party lights",
      "golden": "low warm sun, long shadows", "haze": "soft haze rolling in (rising tension)",
      "dusk": "orange-purple evening light"}
AURAS = ["gold", "blue", "green", "red", "purple", "white"]
CHAR_EXTRAS = """Optional per-character fields to SHOW a town rule: "hair": <hair color, overrides the cast hair for this shot>,
"aura": one of %s (glow around them), "float": true (hovering), "scale": 0.5-1.5 (shrunk or giant).
Optional per-shot "sign": text (<= 40 chars) on an in-world sign behind the characters (a signpost outdoors, a banner indoors).""" % ", ".join(AURAS)

SCHEMA = """
{
  "title": "AIO for ...",                       // short title (<= 70 chars), like the post title
  "tiktok_caption": "one hook line + a question for comments + 3-5 hashtags (#aio #storytime ...)",
  "voice": "af_heart",                          // narrator voice; af_heart / af_bella (female), am_michael / am_adam (male)
  "end_card": "AM I OVERREACTING?",             // big text card on the last line (<= 24 chars)
  "pet": "cat" | "dog" | null,                  // the pet 'hold_pet' shows (other pets can still appear as characters)
  "cast": {                                      // 1-4 people; "me" = the narrator
    "me":  {"look": "young_woman", "shirt": "lavender", "hair": "brown"},
    "mom": {"look": "older_woman", "shirt": "red", "hair": "black"}
  },
  "lines": [                                     // 18-34 narration lines, each one shot
    {"text": "My mom wants to sell my cat. And apparently, I'm the dramatic one.",
     "scene": "bedroom",
     "chars": [{"who": "me", "x": 0.3, "emotion": "sad", "pose": "hold_pet"},
               {"who": "mom", "x": 0.75, "emotion": "angry", "pose": "point"}],
     "cam": "wide", "fx": ["punch"]},
    {"text": "Then she texted me this.", "scene": "phone", "contact": "Mom",
     "messages": [{"from": "them", "text": "We're selling the cat Saturday."}, {"from": "me", "text": "WHAT??"}]}
  ]
}
"""

def validate(spec):
    errs = []
    for k in ("title", "tiktok_caption", "cast", "lines"):
        if k not in spec: errs.append("missing key: %s" % k)
    if errs: return errs
    if spec.get("mode", "reddit_story") not in MODES: errs.append("mode must be one of %s" % MODES)
    cast = spec["cast"]
    if "me" not in cast: errs.append("cast must include 'me' (the narrator)")
    if not (1 <= len(cast) <= 4): errs.append("cast needs 1-4 people")
    for who, c in cast.items():
        if c.get("look") not in LOOKS: errs.append("cast %s: look must be one of %s" % (who, list(LOOKS)))
        if c.get("shirt", "blue") not in SHIRTS: errs.append("cast %s: shirt must be one of %s" % (who, list(SHIRTS)))
        if c.get("hair", "brown") not in HAIR: errs.append("cast %s: hair must be one of %s" % (who, list(HAIR)))
    pet = spec.get("pet")
    if pet not in (None, *PETS): errs.append("pet must be cat, dog or null")
    if len(spec.get("end_card", "")) > 24: errs.append("end_card max 24 chars")
    lines = spec["lines"]
    speed = spec.get("speed", SPEED)
    if spec.get("runtime"):
        errs += runtime_errors([l.get("text", "") for l in lines], int(spec["runtime"]), speed)
    else:
        if not (LINES[0] <= len(lines) <= LINES[1]): errs.append("need %d-%d lines (have %d)" % (*LINES, len(lines)))
        words = sum(len(l.get("text", "").split()) for l in lines)
        lo, hi = word_range(speed, WORDS_OK)
        if not (lo <= words <= hi):
            errs.append("narration is %d words; aim for %d-%d words (about 65-85 seconds)" % (words, *word_range(speed)))
    for i, l in enumerate(lines):
        t = l.get("text", "")
        if not t or len(t) > 200: errs.append("line %d: text required, max 200 chars" % i)
        if len(l.get("sign") or "") > 40: errs.append("line %d: sign max 40 chars" % i)
        sc = l.get("scene")
        if sc not in SCENES: errs.append("line %d: scene must be one of %s" % (i, list(SCENES))); continue
        if sc == "phone":
            msgs = l.get("messages", [])
            if not (1 <= len(msgs) <= 5): errs.append("line %d: phone scene needs 1-5 messages" % i)
            for m in msgs:
                if m.get("from") not in ("me", "them") or not m.get("text") or len(m["text"]) > 90:
                    errs.append("line %d: each message needs from me/them and text <= 90 chars" % i)
            continue
        chars = l.get("chars", [])
        if sc != "exterior" and not chars: errs.append("line %d: needs at least one character" % i)
        if len(chars) > 3: errs.append("line %d: max 3 characters per shot" % i)
        for c in chars:
            who = c.get("who")
            if who in PETS:
                if c.get("pose", "idle") not in PET_POSES: errs.append("line %d: pet pose must be idle or crazy" % i)
            elif who not in cast: errs.append("line %d: unknown character %r (not in cast)" % (i, who))
            else:
                if c.get("emotion", "neutral") not in EMOTIONS: errs.append("line %d: emotion must be one of %s" % (i, EMOTIONS))
                if c.get("pose", "idle") not in POSES: errs.append("line %d: pose must be one of %s" % (i, POSES))
                if c.get("pose") == "hold_pet" and not pet: errs.append("line %d: hold_pet needs spec.pet" % i)
                if c.get("pose") == "lying" and sc != "bed": errs.append("line %d: pose 'lying' only in scene 'bed'" % i)
                if c.get("hair", "brown") not in HAIR: errs.append("line %d: hair must be one of %s" % (i, list(HAIR)))
                if c.get("aura") not in (None, *AURAS): errs.append("line %d: aura must be one of %s" % (i, AURAS))
                sc_ = c.get("scale", 1.0)
                if not isinstance(sc_, (int, float)) or not 0.5 <= sc_ <= 1.5: errs.append("line %d: scale must be 0.5-1.5" % i)
            x = c.get("x", 0.5)
            if not isinstance(x, (int, float)) or not 0 <= x <= 1: errs.append("line %d: x must be 0..1" % i)
        cam = l.get("cam", "wide")
        if cam.split(":")[0] not in CAMS: errs.append("line %d: cam must be one of %s (closeup:<who> allowed)" % (i, CAMS))
        for f in l.get("fx", []):
            if f not in FX: errs.append("line %d: unknown fx %r" % (i, f))
    return errs

def word_count(spec):
    return sum(len(l["text"].split()) for l in spec["lines"])
