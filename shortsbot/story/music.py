"""Soft piano bed + swooshes on cuts + booms on dramatic lines, ducked under the narration."""
import os
import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000

def mix_audio(spec, timeline, outdir):
    import soundfile as sf
    dur = timeline["total"]; N = int(dur * SR); t = np.arange(N) / SR
    rng = np.random.default_rng(2)
    mus = np.zeros(N)
    def note(f, start, length, amp):
        i = int(start * SR); n = min(int(length * SR), N - i)
        if n <= 0: return
        tt = np.arange(n) / SR
        env = np.exp(-tt * 1.6) * np.clip(tt / 0.008, 0, 1)
        sig = np.sin(2*np.pi*f*tt) + 0.45*np.sin(2*np.pi*2*f*tt)*np.exp(-tt*3) + 0.2*np.sin(2*np.pi*3*f*tt)*np.exp(-tt*5)
        mus[i:i+n] += sig * env * amp
    mid = lambda m: 440 * 2 ** ((m - 69) / 12)
    prog = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
    k, tt0 = 0, 0.0
    while tt0 < dur:
        ch = prog[(k // 4) % 4]
        if k % 4 == 0:
            note(mid(ch[0] - 12), tt0, 3.0, 0.22)
            for m in ch: note(mid(m), tt0, 3.0, 0.08)
        note(mid([ch[0] + 12, ch[1] + 12, ch[2] + 12, ch[1] + 12][k % 4]), tt0, 1.4, 0.09)
        tt0 += 0.75; k += 1
    mus = sosfilt(butter(2, 5000, 'lowpass', fs=SR, output='sos'), mus)
    pad = sum(np.sin(2*np.pi*mid(m)*t + 0.3*np.sin(2*np.pi*0.2*t)) for m in (45, 52, 57))
    mus += sosfilt(butter(2, 900, 'lowpass', fs=SR, output='sos'), pad) * 0.025
    fx = np.zeros(N); gate = np.ones(N)
    starts = [0.0] + [ln["shot_end"] for ln in timeline["lines"][:-1]]
    for idx, s in enumerate(starts):
        line = spec["lines"][idx]; lfx = line.get("fx", [])
        if idx > 0:
            n = int(0.3 * SR); tt = np.arange(n) / SR
            w = sosfilt(butter(2, [800, 6000], 'bandpass', fs=SR, output='sos'), rng.standard_normal(n)) * np.sin(np.pi * tt / 0.3) ** 2
            i = int(max(0, s - 0.12) * SR); m = max(0, min(n, N - i)); fx[i:i+m] += w[:m] * 0.05
        if "shake" in lfx or "redflash" in lfx or "punch" in lfx and idx > 2:
            n = int(1.5 * SR); tt = np.arange(n) / SR
            boom = np.sin(2*np.pi*np.cumsum(60*np.exp(-tt*5)+38)/SR) * np.exp(-tt*2.5)
            i = int(s * SR); m = max(0, min(n, N - i)); fx[i:i+m] += boom[:m] * 0.6
        if "dark" in lfx or "shake" in lfx:
            gate[(t >= s) & (t < timeline["lines"][idx]["shot_end"])] = 0.15
        if line["scene"] == "phone":   # message pings
            msgs = line.get("messages", [])
            span = timeline["lines"][idx]["shot_end"] - s
            for j in range(len(msgs)):
                at = s + (0.05 + 0.85 * j / max(1, len(msgs))) * span
                n = int(0.25 * SR); tt = np.arange(n) / SR
                ping = np.sin(2*np.pi*(1568 if msgs[j]["from"] == "them" else 1175)*tt) * np.exp(-tt*14)
                i = int(at * SR); m = max(0, min(n, N - i)); fx[i:i+m] += ping[:m] * 0.15
    gate = np.convolve(gate, np.ones(4800) / 4800, mode="same")
    mus *= gate
    v, sr = sf.read(os.path.join(outdir, "narration.wav"))
    v = np.interp(np.arange(N) / SR, np.arange(len(v)) / sr, v)
    venv = np.convolve(np.abs(v), np.ones(4800) / 4800, mode="same")
    duck = 1 - 0.55 * np.clip(venv / (venv.max() * 0.25 + 1e-9), 0, 1)
    mix = v + mus * duck * 0.55 + fx
    mix *= np.clip((dur - t) / 0.8, 0, 1)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.9
    path = os.path.join(outdir, "mix.wav")
    sf.write(path, np.stack([mix, mix], 1), SR)
    return path
