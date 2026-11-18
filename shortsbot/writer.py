"""The agent: Claude invents a premise, writes the spec, fixes validation errors, then reviews rendered frames."""
import base64, json, os, re
import anthropic
from .spec import SCHEMA_DOC, template_docs, channel_docs, validate, stage_timing_table, TEMPLATES

MODEL = os.environ.get("SHORTSBOT_MODEL", "claude-sonnet-5-5")
EXAMPLE = os.path.join(os.path.dirname(__file__), "..", "examples", "blackout_car.json")

SYSTEM = """You are the writer and director of a YouTube Shorts channel that posts "What if...?" videos.
Each video is rendered by a procedural low-poly 3D engine from a JSON spec you write. A big HUD counter
escalates (time passing x10 every few seconds, or a quantity rising) while short captions explain what
happens at each stage, ending on a punchy last line.

TEMPLATES (pick the one that shows the premise best):
{templates}

EFFECT CHANNELS (what the engine can show; animate them via stage effects):
{channels}

SPEC FORMAT:
{schema}

RULES
- Premise: a single vivid, curiosity-driving hypothetical a broad audience would search for. It must be
  something the engine can SHOW with the channels above. Not about real people, politics, religion,
  tragedies or violence; no gore. Keep it family-friendly.
- Science: captions must be accurate or clearly the mainstream scientific estimate. No invented statistics.
  When something is uncertain, phrase it carefully ("within days", "scientists estimate").
- Captions: max 2 lines of <= 34 characters each, using \\n. Plain, punchy, one idea each. 1-2 per stage.
  Stage labels: 1-3 words.
- Pacing: 5-8 stages. Each stage must stay on screen >= 3 s (>= 2.2 s per caption). In time mode, stage
  starts are world_seconds that grow roughly x10-x30 each stage; the last stage should start around
  80-90% of end_world_seconds on a log scale so it gets screen time before the final caption.
- The visuals must change at almost every stage (use effects), and the final caption must land a twist or
  relatable punchline.
- Metadata: title = the premise question + one emoji (<= 70 chars). description = 2-4 sentences, then a
  question that invites comments, then 6-10 relevant hashtags including #Shorts and #whatif.
- Vary seed, start_hour, template and colour of the world between videos.
- Output ONLY the JSON object inside one ```json fenced block.
"""

def _client():
    return anthropic.Anthropic()

def _extract_json(text):
    m = re.search(r"```json\s*(\{.*\})\s*```", text, re.S) or re.search(r"(\{.*\})", text, re.S)
    if not m: raise ValueError("no JSON found in model output")
    return json.loads(m.group(1))

def _text(resp):
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")

PLATFORM_RULES = {
    "youtube": "Platform: YouTube Shorts. Set \"platform\": \"youtube\" and duration 50-60.",
    "tiktok": ("Platform: TikTok. Set \"platform\": \"tiktok\" and duration 72-85 (TikTok only pays for videos over "
               "1 minute, and retention matters more than length, so use 7-10 stages to keep something new on screen "
               "every 6-9 seconds). Write \"tiktok_caption\": one curiosity line, one question that invites comments, "
               "then 3-6 hashtags (e.g. #whatif #science #fyp-style tags are fine but keep them relevant). "
               "The creator records their own voiceover over the captions, so captions should read naturally aloud."),
}

def ideas(history, n=6, platform="tiktok", log=print):
    """Ask Claude for n fresh premise candidates for a human to pick from."""
    client = _client()
    used = "\n".join("- " + h["premise"] for h in history[-80:]) or "(none yet)"
    prompt = ("Suggest %d fresh \"What if...?\" premises for a %s channel. Each must be showable with these "
              "templates and effect channels:\n%s\n%s\n\nAlready used (avoid):\n%s\n\n"
              "Reply with ONLY a ```json block: [{\"premise\": \"What if ...?\", \"template\": \"car|window|hill\", "
              "\"why\": \"one line on why it hooks\"}]" % (n, platform, template_docs(), channel_docs(), used))
    resp = client.messages.create(model=MODEL, max_tokens=1500, messages=[{"role": "user", "content": prompt}])
    m = re.search(r"```json\s*(\[.*\])\s*```", _text(resp), re.S) or re.search(r"(\[.*\])", _text(resp), re.S)
    return json.loads(m.group(1))

def write_spec(history, log=print, max_repairs=4, premise=None, template=None, platform="youtube"):
    """Ask Claude for a new spec, loop on validation errors until it passes."""
    client = _client()
    system = SYSTEM.format(templates=template_docs(), channels=channel_docs(), schema=SCHEMA_DOC)
    recent = history[-60:]
    used = "\n".join("- %s (%s)" % (h["premise"], h["template"]) for h in recent) or "(none yet)"
    counts = {t: sum(1 for h in recent[-6:] if h["template"] == t) for t in TEMPLATES}
    prefer = min(counts, key=counts.get)
    example = open(EXAMPLE).read()
    user = ("Here is an example spec that rendered well:\n```json\n%s\n```\n\n"
            "Premises already published (do NOT repeat or closely paraphrase these):\n%s\n\n"
            "Template usage in the last 6 videos: %s. Prefer `%s` unless another template fits the premise much better.\n\n"
            "%s\n\nWrite the spec for the next video." % (example, used, counts, prefer, PLATFORM_RULES[platform]))
    if premise:
        user += "\nThe creator chose the premise: %r. Use it (you may polish the wording)." % premise
    if template:
        user += "\nUse the `%s` template." % template
    messages = [{"role": "user", "content": user}]
    for attempt in range(max_repairs + 1):
        resp = client.messages.create(model=MODEL, max_tokens=4000, system=system, messages=messages)
        text = _text(resp)
        try:
            spec = _extract_json(text); errs = validate(spec)
        except Exception as e:
            spec, errs = None, ["could not parse JSON: %s" % e]
        if not errs:
            log("writer: spec ok after %d attempt(s): %s" % (attempt + 1, spec["premise"]))
            return spec
        log("writer: attempt %d had %d problem(s): %s" % (attempt + 1, len(errs), "; ".join(errs[:4])))
        timing = ""
        if spec:
            try: timing = "\nCurrent stage timing on screen:\n" + stage_timing_table(spec)
            except Exception: pass
        messages += [{"role": "assistant", "content": text},
                     {"role": "user", "content": "The spec failed validation:\n- " + "\n- ".join(errs) + timing +
                      "\nFix every problem and return the full corrected JSON."}]
    raise RuntimeError("writer could not produce a valid spec")

CRITIC = """You are reviewing frames from a vertical "What if" Short before it is published automatically.
The image is a contact sheet: frame 1 is the hook, then one frame from the middle of each stage, then the ending.
Check: (1) is the premise visually readable at each stage, (2) do the visuals actually change between stages,
(3) is anything broken (empty/black frames, text overlapping badly, nonsensical scene), (4) are captions
accurate and family-friendly. Small stylistic quibbles are fine: approve unless there is a real problem.
Reply with ONLY a ```json block: {"approve": true|false, "issues": ["..."], "revised_spec": null | {full corrected spec}}
If you do not approve, you must supply a revised_spec that fixes the issues (e.g. stronger effects, different
template, clearer captions)."""

def review(spec, sheet_path, log=print):
    client = _client()
    img = base64.b64encode(open(sheet_path, "rb").read()).decode()
    resp = client.messages.create(model=MODEL, max_tokens=4000, system=CRITIC, messages=[{"role": "user", "content": [
        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img}},
        {"type": "text", "text": "Spec:\n```json\n%s\n```\nStage timing:\n%s" % (json.dumps(spec, ensure_ascii=False, indent=1), stage_timing_table(spec))}]}])
    out = _extract_json(_text(resp))
    log("critic: approve=%s issues=%s" % (out.get("approve"), out.get("issues")))
    return out
