"""Reddit post -> story spec via Claude, retried until it validates."""
import json, os, re
from .spec import SCHEMA, SCENES, LOOKS, SHIRTS, HAIR, EMOTIONS, POSES, FX, validate, word_count

MODEL = os.environ.get("SHORTSBOT_MODEL", "claude-sonnet-5-5")

SYSTEM = """You adapt Reddit posts (r/AmIOverreacting, r/AITA and similar) into scripts for 65-85 second vertical
story videos: a narrator reads the story in first person while simple blocky 3D characters act it out, with
big word-by-word captions.

Write the narration IN YOUR OWN WORDS. Never copy sentences from the post. Keep the story's facts and
emotional beats, cut side details, and make it flow when read aloud.

Privacy and care: change identifying details (names, exact ages, schools, cities, employers). Keep painful
material (abuse, self-harm, health) brief and non-graphic: one plain line at most, no specifics. No slurs or
sexual content. If the post is not suitable for a family-friendly video, return {{"refuse": "<reason>"}}.

Structure:
- Line 1 is a hook that states the conflict in one punchy sentence ("My mom wants to sell my cat. And apparently,
  I'm the dramatic one.").
- Then the story in order, one idea per line (6-14 words per line works best).
- If the post mentions texts or messages, use one "phone" scene to show 2-4 of them (paraphrased).
- The last line asks the audience: "So, am I overreacting? Tell me in the comments." (or the post's subreddit framing).
- 185-240 words total, 16-28 lines.

Visual direction: vary scenes and camera (wide, medium, push, closeup:<who>), match emotions to each beat,
change shots every line, use fx sparingly for big moments (shake/redflash for fights, cold/desat for low points,
memory for flashbacks, hearts for warm moments).

Available scenes: {scenes}
Looks: {looks}. Shirts: {shirts}. Hair: {hair}.
Emotions: {emotions}. Poses: {poses} (hold_pet shows the spec's pet in their arms; lying only in scene bed).
Pets as characters: {{"who": "cat"|"dog", "x": 0..1, "pose": "idle"|"crazy"}}.
fx: {fx}

Output ONLY one ```json block with this shape:
{schema}"""

def _client():
    import anthropic
    return anthropic.Anthropic()

def _text(resp): return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")

def _json(text):
    m = re.search(r"```json\s*(\{.*\})\s*```", text, re.S) or re.search(r"(\{.*\})", text, re.S)
    if not m: raise ValueError("no JSON in reply")
    return json.loads(m.group(1))

def condense(story, log=print, max_repairs=4, notes=""):
    system = SYSTEM.format(scenes=json.dumps(SCENES), looks=json.dumps(LOOKS), shirts=", ".join(SHIRTS), hair=", ".join(HAIR),
                           emotions=", ".join(EMOTIONS), poses=", ".join(POSES), fx=json.dumps(FX), schema=SCHEMA)
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
            errs = validate(spec)
        except SystemExit: raise
        except Exception as e:
            spec, errs = None, ["could not parse JSON: %s" % e]
        if not errs:
            log("condense: ok after %d attempt(s): %d lines, %d words" % (attempt + 1, len(spec["lines"]), word_count(spec)))
            return spec
        log("condense: attempt %d: %s" % (attempt + 1, "; ".join(errs[:5])))
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": "That spec failed validation:\n- " + "\n- ".join(errs) + "\nReturn the full corrected JSON."}]
    raise RuntimeError("could not produce a valid spec")
