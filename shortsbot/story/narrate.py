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
    audio, lines, t = [np.zeros(int(0.35 * SR))], [], 0.35
    n = len(spec["lines"])
    for i, L in enumerate(spec["lines"]):
        samples, _ = k.create(spoken(L["text"]), voice=voice, speed=min(speed, TTS_SPEED), lang="en-us")
        x = _trim(_stretch(np.asarray(samples, dtype=np.float32), speed / min(speed, TTS_SPEED)))
        dur = len(x) / SR
        words = L["text"].split(); ww = _weights(words)
        cum = np.concatenate([[0], np.cumsum(ww)]) / ww.sum() * (dur - 0.08) + 0.03
        hold = 1.2 if L["scene"] == "phone" else 0.0          # extra hold on text-message shots
        gap = (0.38 if i < n - 1 else 1.6) + hold
        lines.append(dict(i=i, start=round(t, 3), end=round(t + dur, 3), shot_end=round(t + dur + gap, 3),
                          words=[dict(w=words[j], a=round(t + cum[j], 3), b=round(t + cum[j + 1], 3)) for j in range(len(words))]))
        audio += [x, np.zeros(int(gap * SR))]
        t += dur + gap
        log("narrate: %2d/%d %4.1fs %s" % (i + 1, n, dur, L["text"][:60]))
    sf.write(os.path.join(outdir, "narration.wav"), np.concatenate(audio), SR)
    tl = dict(total=round(t, 3), lines=lines)
    json.dump(tl, open(os.path.join(outdir, "timeline.json"), "w"), indent=1)
    log("narrate: total %.1fs" % t)
    return tl
