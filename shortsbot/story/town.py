"""In this town: rule pitches -> story bible (approval checkpoint) -> shot spec."""
import json, re
from .condense import _client, _text, _json, MODEL, OPENER, HUSS, HUSS_MIN, HUSS_RULES, VISUALS, format_errors
from .spec import (SCHEMA, SCENES, LOOKS, SHIRTS, HAIR, EMOTIONS, POSES, FX, CHAR_EXTRAS, SPEED, SEC_PER_WORD, GAP, LEAD, TAIL,
                   estimate_seconds, line_seconds, runtime_errors, runtime_lines, validate)

RUNTIME = 75
SECTIONS = [("hook", 0), ("life", 15), ("anomaly", 35), ("twist", 60), ("cliffhanger", 85)]
SECTION_SLACK = 8              # percentage points a section start may drift
MAX_BEAT_WORDS = 16
MORAL = re.compile(r"\b(lesson|moral|learned|the point is|remember to|always remember|never forget|be yourself|"
                   r"matters most|what really matters|the real treasure)\b", re.I)

WORLD = """The world is a stylized, Roblox-like blocky 3D town: original toy-like characters (no Roblox assets, names
or logos). The renderer can show:
- scenes: {scenes}
- looks: {looks}; shirts: {shirts}; hair: {hair}
- emotions: {emotions}; poses: {poses}
- {extras}
- fx: {fx}
Design the rule so it is visible with these tools (hair color changes, auras, floating, shrinking or giant people,
signs, lighting, pets, text messages, crowds of up to 3 per shot)."""

PITCH = """You are the showrunner of "In This Town..." shorts: vertical videos set in a stylized, Roblox-like blocky 3D
world, where one strange town rule drives a tight story with a kid hero.

Pitch 10 distinct, visually readable town rules. Each rule must produce an unmistakable visual effect on
characters, props or the environment within the first 1-2 seconds, readable on mute and reinforced by an
in-world sign or a visual contrast. Make them original, family-friendly and varied (body, weather, objects,
time, sound, animals...), each with an obvious way for it to turn cruel or risky later.

{world}

Return JSON:
{{"pitches": [{{"rule": "In this town, ...", "frame1": "what viewers see in frame 1", "curiosity": "why curiosity spikes"}}]}}"""

BIBLE = """You are both the Showrunner / Scriptwriter and the Scene & Camera Director of "In This Town..." shorts:
vertical 9:16 videos set in a stylized, Roblox-like blocky 3D world. Turn the town rule into a tight,
high-retention story and write its Step 1 story bible: title, town name, logline, planted details tracker
and a beat-by-beat script. Each beat is one narration line and one shot.

Creative rules (non-negotiable):
1. Visual first: the rule produces an unmistakable visual effect in beat 1 (readable on mute), reinforced by
   an in-world sign: beat 1 has a "sign" that names the town and the rule (<= 40 chars, e.g. "WELCOME TO
   DIMWICK - STAY CURIOUS").
2. Story arc, by share of the runtime (beats carry a "section"):
   - hook (0-15%): the rule in action in the opening shot; establish the town name and normal life.
   - life (15-35%): townsfolk embracing or adapting to the rule in everyday routines.
   - anomaly (35-60%): a kid notices something is off, and a new arrival or event twists the rule into
     something cruel or risky. The crowd cheers while only the kid sees the threat.
   - twist (60-85%): the kid makes one smart move to counter it, followed by an unexpected twist.
   - cliffhanger (85-100%): never end with a moral or lecture. End right as the next danger arrives, so the
     viewer wants Part 2.
3. Exactly three planted payoffs, each planted in the first half and brought back in the twist or cliffhanger:
   - A: a phrase the protagonist has to repeat (quote it word for word in the narration both times),
   - B: something strange or out of place the protagonist notices early,
   - C: something Grandma (or another elder) always says (quote it word for word both times).
4. Pacing: punchy, spoken-word-friendly narration (3-{maxw} words per beat; one shot every 1-3 seconds),
   clear emotions (happy, curious, smug, shocked, fearful) and atmospheric lighting (low warm sun and long
   shadows early, haze when tension rises).
5. Length: {runtime} seconds of narration: {l0}-{l1} beats and about {words} words in total.
6. The kid hero narrates in the first person ("I") and is cast "me". Write ORIGINAL material; no existing
   characters or catchphrases. Family-friendly.

{huss}
(Here "line" means beat. Beat 1's voiceover is the opener; the rule itself is stated in beat 2.)

{world}

Return JSON:
{{
  "title": "<= 70 chars",
  "town_name": "...",
  "logline": "one sentence",
  "rule": "In this town, ...",
  "details": {{
    "A": {{"what": "the exact phrase", "plant": <beat number>, "payoff": <beat number>, "note": "how it pays off"}},
    "B": {{"what": "...", "plant": <beat number>, "payoff": <beat number>, "note": "..."}},
    "C": {{"what": "the exact saying", "plant": <beat number>, "payoff": <beat number>, "note": "..."}}
  }},
  "beats": [
    {{"section": "hook", "vo": "clean voiceover text for TTS", "visual": "on-screen action and rule cue",
      "sign": "optional in-world sign text", "camera": "shot and move, e.g. wide establishing, slow push-in",
      "light": "lighting / mood"}}
  ]
}}
Beat numbers count from 1."""

SPEC = """You are the Scene & Camera Director. Turn this approved story bible into the shot spec the renderer reads.
One spec line per beat, in order; each line's "text" is that beat's "vo" copied EXACTLY. Translate each beat's
visual, sign, camera and light into scene, chars (who, x, emotion, pose and the per-character extras), cam, fx
and sign. Keep the rule visible whenever it applies (e.g. gray hair stays gray). Cut every line; vary cameras.
Cast is a list of {{who, look, shirt, hair}}; the kid hero is who "me" (look kid_girl or kid_boy); include Grandma or the elder from detail C; 1-4 people.
Set "mode": "in_this_town", "runtime": {runtime}, title from the bible, end_card <= 24 chars (e.g. "PART 2?"),
tiktok_caption = hook line + a question for comments + 3-5 hashtags (#inthistown #animation #story ...).

{visuals}
{extras}"""

def _obj(props, required=None):
    return {"type": "object", "properties": props, "required": list(props) if required is None else required, "additionalProperties": False}

STR, INT, BOOL, NUM = {"type": "string"}, {"type": "integer"}, {"type": "boolean"}, {"type": "number"}
PITCH_SCHEMA = _obj({"pitches": {"type": "array", "items": _obj({"rule": STR, "frame1": STR, "curiosity": STR})}})
_DETAIL = _obj({"what": STR, "plant": INT, "payoff": INT, "note": STR})
BIBLE_SCHEMA = _obj({
    "title": STR, "town_name": STR, "logline": STR, "rule": STR,
    "details": _obj({"A": _DETAIL, "B": _DETAIL, "C": _DETAIL}),
    "beats": {"type": "array", "items": _obj({"section": {"type": "string", "enum": [s for s, _ in SECTIONS]}, "vo": STR,
                                              "visual": STR, "sign": STR, "camera": STR, "light": STR},
                                             ["section", "vo", "visual", "camera"])}})
def _fmt():
    return dict(scenes=json.dumps(SCENES), looks=json.dumps(LOOKS), shirts=", ".join(SHIRTS), hair=", ".join(HAIR),
                emotions=", ".join(EMOTIONS), poses=", ".join(POSES), fx=json.dumps(FX), extras=CHAR_EXTRAS)

def _ask(system, user, check, log, what, schema, max_repairs=4, max_tokens=24000):
    messages = [{"role": "user", "content": user}]
    client = _client()
    extra = {"output_config": {"format": {"type": "json_schema", "schema": schema}}} if schema else {}
    for attempt in range(max_repairs + 1):
        with client.messages.stream(model=MODEL, max_tokens=max_tokens, system=system, messages=messages, **extra) as st:
            resp = st.get_final_message()
        if resp.stop_reason == "refusal": raise SystemExit("Claude declined this request")
        if resp.stop_reason == "max_tokens":
            log("%s: attempt %d: reply hit max_tokens, retrying" % (what, attempt + 1))
            messages = messages[:1]
            continue
        text = _text(resp)
        try:
            out = _json(text)
            errs = check(out)
        except SystemExit: raise
        except Exception as e:
            out, errs = None, ["could not parse JSON: %s" % e]
        if not errs:
            log("%s: ok after %d attempt(s)" % (what, attempt + 1))
            return out
        log("%s: attempt %d: %s" % (what, attempt + 1, "; ".join(errs[:5])))
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": "That failed validation:\n- " + "\n- ".join(errs) + "\nReturn the full corrected JSON."}]
    raise RuntimeError("could not produce a valid %s" % what)

# ------------------------------------------------------------------ pitches
def pitch_errors(p):
    ps = p.get("pitches", [])
    errs = [] if len(ps) == 10 else ["need exactly 10 pitches (have %d)" % len(ps)]
    for i, x in enumerate(ps):
        if not str(x.get("rule", "")).lower().startswith("in this town"): errs.append("pitch %d: rule must start with 'In this town'" % (i + 1))
        if not x.get("frame1") or not x.get("curiosity"): errs.append("pitch %d: needs frame1 and curiosity" % (i + 1))
    return errs

def pitch(theme="", notes="", log=print):
    system = PITCH.format(world=WORLD.format(**_fmt()))
    user = ("Theme to riff on: %s" % theme.strip()) if theme.strip() else "Pitch 10 fresh rules."
    if notes: user += "\n\nCreator notes: %s" % notes
    return _ask(system, user, pitch_errors, log, "pitch", PITCH_SCHEMA)["pitches"]

def pitches_md(ps):
    out = ["## Pick a town rule", "", "| # | rule | frame 1 | why curiosity spikes |", "|---|---|---|---|"]
    out += ["| %d | %s | %s | %s |" % (i + 1, p["rule"], p["frame1"], p["curiosity"]) for i, p in enumerate(ps)]
    return "\n".join(out) + "\n"

# ------------------------------------------------------------------ story bible
def _norm(t): return " ".join(re.sub(r"[^a-z0-9 ]", " ", t.lower()).split())

def beat_times(beats, speed=SPEED):
    """Start time of each beat and the total, using narrate.py's pacing."""
    t, out = LEAD, []
    for b in beats:
        out.append(t)
        t += line_seconds(b.get("vo", ""), speed) + GAP
    return out, estimate_seconds([b.get("vo", "") for b in beats], speed)

def target_words(runtime, speed=SPEED):
    lo, hi = runtime_lines(runtime)
    n = (lo + hi) / 2
    return round((runtime - LEAD - TAIL - GAP * (n - 1)) / SEC_PER_WORD * float(speed) / SPEED)

def bible_errors(b, runtime=RUNTIME, speed=SPEED):
    errs = [("missing key: %s" % k) for k in ("title", "town_name", "logline", "rule", "details", "beats") if not b.get(k)]
    if errs: return errs
    beats = b["beats"]; n = len(beats)
    if not str(b["rule"]).lower().startswith("in this town"): errs.append("rule must start with 'In this town'")
    errs += runtime_errors([x.get("vo", "") for x in beats], runtime, speed)
    for i, x in enumerate(beats, 1):
        w = len(x.get("vo", "").split())
        if not 3 <= w <= MAX_BEAT_WORDS: errs.append("beat %d: voiceover needs 3-%d words (has %d)" % (i, MAX_BEAT_WORDS, w))
        if not x.get("visual") or not x.get("camera"): errs.append("beat %d: needs visual and camera" % i)
        if len(x.get("sign") or "") > 40: errs.append("beat %d: sign max 40 chars" % i)
    if errs: return errs
    # opener and HUSS HUSS
    errs += [e.replace("line", "beat") for e in format_errors({"lines": [{"text": x["vo"]} for x in beats]}, "in_this_town")]
    # visual first: sign in beat 1 naming the town
    sign = beats[0].get("sign") or ""
    if not sign: errs.append("beat 1 needs an in-world 'sign' that names the town and shows the rule")
    hook = [x for x in beats if x.get("section") == "hook"]
    if _norm(b["town_name"]) not in _norm(sign + " " + " ".join(x["vo"] for x in hook)):
        errs.append("establish the town name %r in beat 1's sign or the hook narration" % b["town_name"])
    # arc
    starts, total = beat_times(beats, speed)
    names = [s for s, _ in SECTIONS]
    secs = [x.get("section") for x in beats]
    bad = [i + 1 for i, s in enumerate(secs) if s not in names]
    if bad: errs.append("beats %s: section must be one of %s" % (bad, names)); return errs
    if [names.index(s) for s in secs] != sorted(names.index(s) for s in secs):
        errs.append("sections must run in order: " + " -> ".join(names))
    for s, pct in SECTIONS:
        idx = [i for i, x in enumerate(secs) if x == s]
        if not idx: errs.append("missing section %r" % s); continue
        at = 100 * (starts[idx[0]] - LEAD) / max(1, total - LEAD)
        if s != "hook" and abs(at - pct) > SECTION_SLACK:
            errs.append("section %r starts at %.0f%% of the runtime; it should start near %d%% (move beats or change their length)" % (s, at, pct))
    if secs[-1] != "cliffhanger": errs.append("the last beat must be in the cliffhanger section")
    # ending: no moral
    for i in (n - 2, n - 1):
        m = MORAL.search(beats[i]["vo"])
        if m: errs.append("beat %d sounds like a moral (%r); end on the next danger arriving instead" % (i + 1, m.group(0)))
    # planted payoffs
    d = b["details"]
    if sorted(d) != ["A", "B", "C"]: errs.append("details must be exactly A, B and C"); return errs
    for k, x in d.items():
        p, q = x.get("plant"), x.get("payoff")
        if not (isinstance(p, int) and isinstance(q, int) and 1 <= p < q <= n):
            errs.append("detail %s: plant and payoff must be beat numbers, plant before payoff" % k); continue
        if (starts[p - 1] - LEAD) / max(1, total - LEAD) >= 0.5: errs.append("detail %s: plant it in the first half (beat %d is too late)" % (k, p))
        if secs[q - 1] not in ("twist", "cliffhanger"): errs.append("detail %s: pay it off in the twist or cliffhanger (beat %d is %s)" % (k, q, secs[q - 1]))
        if k in ("A", "C"):
            phrase = _norm(x.get("what", ""))
            for at in (p, q):
                if not phrase or phrase not in _norm(beats[at - 1]["vo"]):
                    errs.append("detail %s: quote %r word for word in beat %d's voiceover" % (k, x.get("what", ""), at))
    return errs

def bible(rule, runtime=RUNTIME, town_name="", notes="", previous=None, speed=SPEED, log=print):
    f = _fmt()
    lo, hi = runtime_lines(runtime)
    system = BIBLE.format(maxw=MAX_BEAT_WORDS, runtime=runtime, l0=lo, l1=hi, words=target_words(runtime, speed),
                          huss=HUSS_RULES.format(opener=OPENER, n=HUSS_MIN), world=WORLD.format(**f))
    user = "TOWN_RULE: %s\nRUNTIME_TARGET: %ds\nASPECT_RATIO: vertical 9:16\nTOWN_NAME: %s" % (
        rule.strip(), runtime, town_name.strip() or "(invent a fitting name)")
    if previous: user += "\n\nRevise this story bible:\n```json\n%s\n```" % json.dumps(previous, indent=1, ensure_ascii=False)
    if notes: user += "\n\nCreator notes / tweaks: %s" % notes
    b = _ask(system, user, lambda b: bible_errors(b, runtime, speed), log, "bible", BIBLE_SCHEMA)
    starts, total = beat_times(b["beats"], speed)
    for x, t in zip(b["beats"], starts): x["t"] = round(t, 1)
    b.update(runtime=runtime, est_seconds=round(total, 1))
    return b

def _ts(t): return "%d:%04.1f" % (t // 60, t % 60)

def bible_md(b):
    beats = b["beats"]
    out = ["# %s" % b["title"], "", "**Town:** %s  " % b["town_name"], "**Rule:** %s  " % b["rule"],
           "**Logline:** %s  " % b["logline"], "**Runtime:** about %s s (target %s s)" % (b.get("est_seconds"), b.get("runtime")),
           "", "## Planted details", "", "| | detail | planted | pays off | how |", "|---|---|---|---|---|"]
    for k in "ABC":
        x = b["details"][k]
        out.append("| %s | %s | beat %d (%s) | beat %d (%s) | %s |" % (k, x["what"], x["plant"], _ts(beats[x["plant"] - 1].get("t", 0)),
                                                                   x["payoff"], _ts(beats[x["payoff"] - 1].get("t", 0)), x.get("note", "")))
    out += ["", "## Beat-by-beat script", "", "| # | time | section | voiceover | on screen | camera / light |", "|---|---|---|---|---|---|"]
    for i, x in enumerate(beats, 1):
        vis = x["visual"] + (" Sign: “%s”" % x["sign"] if x.get("sign") else "")
        cam = x["camera"] + ("; " + x["light"] if x.get("light") else "")
        out.append("| %d | %s | %s | %s | %s | %s |" % (i, _ts(x.get("t", 0)), x["section"], x["vo"], vis, cam))
    return "\n".join(s.replace("\n", " ") for s in out) + "\n"

# ------------------------------------------------------------------ spec
def _from_schema(spec):
    """Cast list / pet 'none' -> renderer spec."""
    if isinstance(spec.get("cast"), list):
        spec["cast"] = {c["who"]: {k: c[k] for k in ("look", "shirt", "hair")} for c in spec["cast"]}
    if spec.get("pet") == "none": spec["pet"] = None
    return spec

def spec_errors(spec, b):
    _from_schema(spec)
    spec["mode"], spec["runtime"] = "in_this_town", b.get("runtime", RUNTIME)
    lines, beats = spec.get("lines", []), b["beats"]
    if len(lines) == len(beats):
        for l, x in zip(lines, beats): l["text"] = x["vo"]      # voiceover stays exactly as approved
    timing = set(runtime_errors([l.get("text", "") for l in lines], spec["runtime"], spec.get("speed", SPEED)))
    errs = [e for e in validate(spec) if e not in timing] + format_errors(spec, "in_this_town")
    if len(lines) != len(beats): errs.append("need exactly one line per beat (%d beats, %d lines)" % (len(beats), len(lines)))
    for i, (l, x) in enumerate(zip(lines, beats), 1):
        if l.get("text", "").strip() != x["vo"].strip(): errs.append("line %d: text must be beat %d's vo exactly: %r" % (i, i, x["vo"]))
    if lines and not lines[0].get("sign"): errs.append("line 1 needs the bible's beat 1 sign")
    if not str(spec.get("cast", {}).get("me", {}).get("look", "")).startswith("kid"):
        errs.append("cast 'me' is the kid hero: look kid_girl or kid_boy")
    return errs

def make_spec(b, notes="", log=print):
    system = SPEC.format(runtime=b.get("runtime", RUNTIME), visuals=VISUALS.format(**dict(_fmt(), schema=SCHEMA)), extras=CHAR_EXTRAS)
    user = "Approved story bible:\n```json\n%s\n```" % json.dumps(b, indent=1, ensure_ascii=False)
    if notes: user += "\n\nCreator notes: %s" % notes
    spec = _ask(system, user, lambda s: spec_errors(s, b), log, "spec", None)
    spec.update(mode="in_this_town", runtime=b.get("runtime", RUNTIME), town_name=b["town_name"])
    return spec
