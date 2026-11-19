"""Kokoro TTS narration and estimated per-word caption timings."""
import json, os, re, urllib.request
import numpy as np

SR = 24000
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FILES = ["kokoro-v1.0.int8.onnx", "voices-v1.0.bin"]

def model_dir():
    d = os.environ.get("KOKORO_DIR", os.path.expanduser("~/.cache/kokoro"))
    os.makedirs(d, exist_ok=True)
    for f in FILES:
        p = os.path.join(d, f)
        if not os.path.exists(p):
            print("downloading", f)
            urllib.request.urlretrieve(MODEL_URL + f, p + ".part"); os.replace(p + ".part", p)
    return d

def _trim(x, thr=0.012):
    env = np.convolve(np.abs(x), np.ones(240) / 240, mode="same")
    idx = np.where(env > thr)[0]
    if not len(idx): return x
    return x[max(0, idx[0] - 600): min(len(x), idx[-1] + 1200)]

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
    speed = float(spec.get("speed", 1.05))
    audio, lines, t = [np.zeros(int(0.35 * SR))], [], 0.35
    n = len(spec["lines"])
    for i, L in enumerate(spec["lines"]):
        samples, _ = k.create(L["text"], voice=voice, speed=speed, lang="en-us")
        x = _trim(np.asarray(samples, dtype=np.float32))
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
