"""Reddit post or premise -> story spec via Claude, retried until it validates."""
import json, os, re
from .spec import SCHEMA, SCENES, LOOKS, SHIRTS, HAIR, EMOTIONS, POSES, FX, WORDS, LINES, validate, word_count

OPENER = "In this town, everyone goes HUSS HUSS."
HUSS = "HUSS HUSS"
HUSS_MIN = 3                   # interjections after the opener
TOWN_MIN = 6                   # lines that mention the town (reddit_story)

MODEL = os.environ.get("SHORTSBOT_MODEL", "claude-sonnet-5-5")

SYSTEM = """You adapt Reddit posts (r/AmIOverreacting, r/AITA and similar) into scripts for 65-85 second vertical
story videos: a narrator reads the story in first person while simple blocky 3D characters act it out, with
big word-by-word captions.

Write the narration IN YOUR OWN WORDS. Never copy sentences from the post. Keep the story's facts and
emotional beats, cut side details, and make it flow when read aloud.

Privacy and care: change identifying details (names, exact ages, schools, cities, employers). Keep painful
material (abuse, self-harm, health) brief and non-graphic: one plain line at most, no specifics. No slurs or
sexual content. If the post is not suitable for a family-friendly video, return {{"refuse": "<reason>"}}.

Retell the story as if it happens in "this town": a small, nosy town where everyone goes "HUSS HUSS". Keep the
post's facts and beats, but make the town part of the story:
- the people are townspeople ("the town baker", "the guy who runs the town's only gym"), and places are town
  places (the town bakery, Main Street, the town square, the group chat everyone in town is in);
- the town reacts: neighbors watch from porches, gossip spreads, townspeople pick sides;
- use the "exterior" scene for town moments and put townspeople in it;
- say "town" in at least {town_min} lines, spread from start to end.

Structure:
- Line 2 is a hook that states the conflict in one punchy sentence ("My mom wants to sell my cat. And apparently,
  I'm the dramatic one.").
- Then the story in order, one idea per line (6-14 words per line works best).
- If the post mentions texts or messages, use one "phone" scene to show 2-4 of them (paraphrased).
- The last line asks the audience: "So, am I overreacting? Tell me in the comments." (or the post's subreddit framing).
- {w0}-{w1} words total, {l0}-{l1} lines.

{huss}

{visuals}"""

TOWN = """You write "In this town" comedy shorts: 65-80 second vertical videos where a deadpan first-person narrator
describes an absurd town while simple blocky 3D characters act it out, with big word-by-word captions.

The running format is "In this town, everybody <does something absurd>. Except me." Write 3-4 bits. Each bit:
- opens with "In this town, everybody ..." (or a close variation),
- escalates the absurdity in 2-6 short lines shown as scenes,
- lands on a deadpan twist built on "Except me." (the narrator is the odd one out, or turns out to be the weirdest of all).
Bits can share a theme and the last bit should be the biggest. Keep it dry, quick and family-friendly.

Write ORIGINAL jokes. Never reuse bits, catchphrases or characters from existing creators' videos.
If the user gives a premise, build the first bit (or the whole video) around it; otherwise invent fresh premises.
- One idea per line (4-12 words per line works best). The narrator is "me".
- The last line is a short call to action ("Follow if your town is weird too.").
- {w0}-{w1} words total, {l0}-{l1} lines.
- title: the first bit's "In this town, everybody ..." line (<= 70 chars). end_card: "EXCEPT ME." or a short twist.
- tiktok_caption: the title + a question for comments + 3-5 hashtags (#inthistown #animation #comedy ...).
- Set "mode": "in_this_town".

{huss}

{visuals}"""

HUSS_RULES = """HUSS HUSS (required in every video):
- Line 1 is exactly: {opener}
- Add "HUSS HUSS" at least {n} more times, spread through the story at random-feeling moments: a townsperson
  shouting it, the narrator slipping it in, or the whole town reacting with it. Write it in capitals as HUSS HUSS.
- Give lines with HUSS HUSS a punchy shot (fx "punch", pose "yell" or emotion "shocked")."""

VISUALS = """Visual direction: vary scenes and camera (wide, medium, push, closeup:<who>), match emotions to each beat,
change shots every line, use fx sparingly for big moments (shake/redflash for fights, cold/desat for low points,
memory for flashbacks, hearts for warm moments).

Available scenes: {scenes}
Looks: {looks}. Shirts: {shirts}. Hair: {hair}.
Emotions: {emotions}. Poses: {poses} (hold_pet shows the spec's pet in their arms; lying only in scene bed).
Pets as characters: {{"who": "cat"|"dog", "x": 0..1, "pose": "idle"|"crazy"}}.
fx: {fx}

Output ONLY one ```json block with this shape (valid JSON: inside strings use single quotes, never double quotes):
{schema}"""

def _client():
    import anthropic
    return anthropic.Anthropic()

def _text(resp): return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")

def _json(text):
    m = re.search(r"```json\s*(\{.*\})\s*```", text, re.S) or re.search(r"(\{.*\})", text, re.S)
    if not m: raise ValueError("no JSON in reply")
    return json.loads(m.group(1))

def _norm(t): return re.sub(r"[^a-z ]", "", t.lower()).split()

def format_errors(spec, mode="reddit_story"):
    """HUSS HUSS rules (fixed opener, at least HUSS_MIN more) and, for Reddit stories, TOWN_MIN town lines."""
    lines = spec.get("lines") or [{}]
    errs = []
    if _norm(lines[0].get("text", "")) != _norm(OPENER):
        errs.append("line 1 must be exactly: %s" % OPENER)
    n = sum(l.get("text", "").upper().count(HUSS) for l in lines[1:])
    if n < HUSS_MIN:
        errs.append("use HUSS HUSS at least %d times after line 1 (have %d)" % (HUSS_MIN, n))
    if mode == "reddit_story":
        t = sum(1 for l in lines[1:] if re.search(r"\btown", l.get("text", ""), re.I))
        if t < TOWN_MIN:
            errs.append("mention the town in at least %d lines after line 1 (have %d); make the town part of the story" % (TOWN_MIN, t))
    return errs

def condense(story, log=print, max_repairs=4, notes="", mode="reddit_story"):
    fmt = dict(scenes=json.dumps(SCENES), looks=json.dumps(LOOKS), shirts=", ".join(SHIRTS), hair=", ".join(HAIR),
               emotions=", ".join(EMOTIONS), w0=WORDS[0], w1=WORDS[1], l0=LINES[0], l1=LINES[1], poses=", ".join(POSES),
               fx=json.dumps(FX), schema=SCHEMA)
    visuals = VISUALS.format(**fmt)
    fmt["huss"] = HUSS_RULES.format(opener=OPENER, n=HUSS_MIN)
    fmt["town_min"] = TOWN_MIN
    if mode == "in_this_town":
        system = TOWN.format(visuals=visuals, **fmt)
        user = ("Premise: %s" % story.strip()) if story.strip() else "Invent fresh premises."
    else:
        system = SYSTEM.format(visuals=visuals, **fmt)
        user = "Here is the post:\n\n<post>\n%s\n</post>" % story.strip()
    if notes: user += "\n\nCreator notes: %s" % notes
    messages = [{"role": "user", "content": user}]
    client = _client()
    for attempt in range(max_repairs + 1):
        resp = client.messages.create(model=MODEL, max_tokens=6000, system=system, messages=messages)
        text = _text(resp)
        try:
            spec = _json(text)
            if "refuse" in spec: raise SystemExit("Claude declined this post: %s" % spec["refuse"])
            errs = validate(spec) + format_errors(spec, mode)
        except SystemExit: raise
        except Exception as e:
            spec, errs = None, ["could not parse JSON: %s" % e]
        if not errs:
            spec["mode"] = mode
            log("condense: ok after %d attempt(s): %d lines, %d words" % (attempt + 1, len(spec["lines"]), word_count(spec)))
            return spec
        log("condense: attempt %d: %s" % (attempt + 1, "; ".join(errs[:5])))
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": "That spec failed validation:\n- " + "\n- ".join(errs) + "\nReturn the full corrected JSON."}]
    raise RuntimeError("could not produce a valid spec")
