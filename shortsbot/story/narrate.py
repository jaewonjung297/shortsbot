"""Kokoro TTS narration and estimated per-word caption timings."""
import json, os, re, subprocess, urllib.request
import numpy as np
from .spec import SPEED

SR = 24000
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FILES = ["kokoro-v1.0.int8.onnx", "voices-v1.0.bin"]
TTS_SPEED = 1.15   # fastest clean Kokoro speed; faster narration is time-stretched with ffmpeg

def model_dir():
    d = os.environ.get("KOKORO_DIR", os.path.expanduser("~/.cache/kokoro"))
    os.makedirs(d, exist_ok=True)
    for f in FILES:
        p = os.path.join(d, f)
        if not os.path.exists(p):
            print("downloading", f)
            urllib.request.urlretrieve(MODEL_URL + f, p + ".part"); os.replace(p + ".part", p)
    return d

# spoken respellings for words the TTS mispronounces; captions keep the original text
SAY = {
    "Airbnb": "Air B and B", "Venmo": "Ven mo", "IKEA": "eye kee uh",
    "AITA": "Am I the A-hole", "AIO": "Am I overreacting", "WIBTA": "Would I be the A-hole",
    "TIFU": "Today I messed up", "BF": "boyfriend", "GF": "girlfriend", "MIL": "mother-in-law",
    "FIL": "father-in-law", "SIL": "sister-in-law", "BIL": "brother-in-law", "DM": "D M", "DMs": "D Ms",
}
_SAY_RE = re.compile(r"\b(%s)\b" % "|".join(sorted(map(re.escape, SAY), key=len, reverse=True)), re.I)
_SAY_LOWER = {k.lower(): v for k, v in SAY.items()}

def spoken(text):
    return _SAY_RE.sub(lambda m: _SAY_LOWER[m.group(1).lower()], text)

def _trim(x, thr=0.012):
    env = np.convolve(np.abs(x), np.ones(240) / 240, mode="same")
    idx = np.where(env > thr)[0]
    if not len(idx): return x
    return x[max(0, idx[0] - 600): min(len(x), idx[-1] + 1200)]

def _stretch(x, tempo):
    """Speed up audio without changing pitch (ffmpeg atempo)."""
    if abs(tempo - 1) < 0.01: return x
    p = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0",
                        "-af", "atempo=%.4f" % tempo, "-f", "f32le", "pipe:1"], input=x.astype(np.float32).tobytes(),
                       capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32)

HUSS_CLIP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "huss_huss.wav")
CLIP_PAD = 0.05            # silence on each side of the clip, seconds

def _is_huss(word): return re.sub(r"[^a-z]", "", word.lower()) == "huss"

def segments(words):
    """Split a line's words into runs: ("tts", words) and ("clip", words) for each HUSS HUSS pair."""
    out, cur, j = [], [], 0
    while j < len(words):
        if j + 1 < len(words) and _is_huss(words[j]) and _is_huss(words[j + 1]):
            if cur: out.append(("tts", cur)); cur = []
            out.append(("clip", words[j:j + 2])); j += 2
        else:
            cur.append(words[j]); j += 1
    if cur: out.append(("tts", cur))
    return out

def load_clip():
    """The HUSS HUSS sound at SR (path from $HUSS_CLIP, default assets/huss_huss.wav; empty disables it)."""
    path = os.environ.get("HUSS_CLIP", HUSS_CLIP)
    if not path: return None
    if not os.path.exists(path): raise FileNotFoundError("HUSS_CLIP not found: %s" % path)
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"],
                       capture_output=True, check=True)
    return np.frombuffer(p.stdout, dtype=np.float32).copy()

def _rms(x):
    env = np.convolve(np.abs(x), np.ones(240) / 240, mode="same")
    act = x[env > 0.2 * env.max()] if len(x) else x
    return float(np.sqrt(np.mean(act ** 2))) if len(act) else 0.0

def _weights(words):
    w = []
    for j, wd in enumerate(words):
        core = re.sub(r"[^A-Za-z0-9']", "", wd)
        syl = max(1, len(re.findall(r"[aeiouy]+", core.lower())))
        v = 0.6 + syl + len(core) * 0.08
        if j < len(words) - 1:
            if wd[-1] == ",": v += 0.9
            elif wd[-1] in ".?!": v += 1.6
        w.append(v)
    return np.array(w)

def narrate(spec, outdir, log=print):
    import soundfile as sf
    from kokoro_onnx import Kokoro
    d = model_dir()
    k = Kokoro(os.path.join(d, FILES[0]), os.path.join(d, FILES[1]))
    voice = spec.get("voice", "af_heart")
    if voice not in k.get_voices(): voice = "af_heart"
    speed = float(spec.get("speed", SPEED))
    clip = load_clip()
    audio, lines, t = [np.zeros(int(0.35 * SR))], [], 0.35
    n = len(spec["lines"])
    def tts(text):
        samples, _ = k.create(spoken(text), voice=voice, speed=min(speed, TTS_SPEED), lang="en-us")
        return _trim(_stretch(np.asarray(samples, dtype=np.float32), speed / min(speed, TTS_SPEED)))
    for i, L in enumerate(spec["lines"]):
        words = L["text"].split()
        segs = segments(words) if clip is not None else [("tts", words)]
        speakable = lambda ws: re.search(r"[A-Za-z0-9]", " ".join(ws))
        parts = [(kind, ws, tts(" ".join(ws)) if kind == "tts" and speakable(ws) else np.zeros(0)) for kind, ws in segs]
        level = _rms(np.concatenate([x for kind, _, x in parts if kind == "tts"] or [np.zeros(1)]))
        pieces, timed = [], []
        pos = 0.0
        for kind, ws, x in parts:
            if kind == "clip":
                c = clip * (min(3.0, level / _rms(clip)) if level > 0 and _rms(clip) > 0 else 1.0)
                pad = np.zeros(int(CLIP_PAD * SR))
                x = np.concatenate([pad if pieces else np.zeros(0), c, pad])
                a0 = pos + (CLIP_PAD if pieces else 0.0); half = len(c) / SR / len(ws)
                timed += [(w, a0 + j * half, a0 + (j + 1) * half) for j, w in enumerate(ws)]
            else:
                d = len(x) / SR; ww = _weights(ws)
                cum = np.concatenate([[0], np.cumsum(ww)]) / ww.sum() * max(0.0, d - 0.08) + min(0.03, d)
                timed += [(w, pos + cum[j], pos + cum[j + 1]) for j, w in enumerate(ws)]
            pieces.append(x); pos += len(x) / SR
        x = np.concatenate(pieces)
        dur = len(x) / SR
        hold = 1.2 if L["scene"] == "phone" else 0.0          # extra hold on text-message shots
        gap = (0.38 if i < n - 1 else 1.6) + hold
        lines.append(dict(i=i, start=round(t, 3), end=round(t + dur, 3), shot_end=round(t + dur + gap, 3),
                          words=[dict(w=w, a=round(t + a, 3), b=round(t + b, 3)) for w, a, b in timed]))
        audio += [x, np.zeros(int(gap * SR))]
        t += dur + gap
        log("narrate: %2d/%d %4.1fs %s" % (i + 1, n, dur, L["text"][:60]))
    sf.write(os.path.join(outdir, "narration.wav"), np.concatenate(audio), SR)
    tl = dict(total=round(t, 3), lines=lines)
    json.dump(tl, open(os.path.join(outdir, "timeline.json"), "w"), indent=1)
    log("narrate: total %.1fs" % t)
    return tl
