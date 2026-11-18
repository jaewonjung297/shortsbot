"""Procedural soundtrack driven by the same timeline/channels as the picture."""
import math
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile
from .timeline import Timeline
from .engine import environment

SR = 48000

def _f(kind, f, order=2): return butter(order, f, kind, fs=SR, output='sos')

def build_audio(spec, out_wav, seed=4):
    tl = Timeline(spec)
    dur = tl.dur
    N = int(SR * dur); t = np.arange(N) / SR
    rng = np.random.default_rng(seed)
    L = np.zeros(N); R = np.zeros(N)
    tpl = spec["template"]

    # control-rate channels (20 Hz) -> audio rate
    ct = np.arange(0, dur + 0.05, 0.05)
    envs = [environment(tl, float(x)) for x in ct]
    def ctl(key): return np.interp(t, ct, np.array([e[key] for e in envs]))
    power, day, rain, snow, smoke = ctl("power"), ctl("day"), ctl("rain"), ctl("snow"), ctl("smoke")
    water, shake, wind, veg, traffic = ctl("water"), ctl("shake"), ctl("wind"), ctl("vegetation"), ctl("traffic")

    def bp(x, lo, hi): return sosfilt(_f('bandpass', [lo, hi]), x)
    def lp(x, f): return sosfilt(_f('lowpass', f), x)
    def hp(x, f): return sosfilt(_f('highpass', f), x)
    def add(sig, pan=0.0, gain=1.0):
        nonlocal L, R
        L += sig * gain * math.cos((pan + 1) * math.pi / 4) * 1.414
        R += sig * gain * math.sin((pan + 1) * math.pi / 4) * 1.414
    def place(sig, start, pan=0.0, gain=1.0):
        i = int(start * SR)
        if i >= N or i + len(sig) <= 0: return
        j = min(N, i + len(sig)); s = np.zeros(N); s[max(0, i):j] = sig[max(0, -i):j - i]; add(s, pan, gain)
    noise = lambda: rng.standard_normal(N)

    ev = tl.ev
    # ---- ambience before/while the world is "normal"
    city = power * np.clip(1 - day * 0.3, 0, 1)
    if tpl == "car":
        add(lp(noise(), 180) * city * 0.9 + bp(noise(), 300, 1500) * 0.12 * city, 0, 0.45)
        run = power * traffic
        f_eng = 32 * (0.4 + 0.6 * run)
        ph = 2 * np.pi * np.cumsum(f_eng) / SR
        eng = (np.sin(ph) * 0.6 + np.sin(2 * ph) * 0.35 + np.sin(3 * ph + 0.4) * 0.2) * (0.75 + 0.25 * np.sin(2 * np.pi * 13.3 * t))
        add(lp(eng, 400) * np.clip(run * 1.2, 0, 1) ** 2, 0, 0.3)
        for tp in (0.05, 0.95, 1.85):
            n = int(0.32 * SR); tt = np.arange(n) / SR
            pg = (np.sin(2 * np.pi * 1318 * tt) * (tt < 0.12) + np.sin(2 * np.pi * 1760 * tt) * (tt >= 0.1)) * np.exp(-tt * 9)
            place(pg * 0.2, tp, 0.35)
    elif tpl == "window":
        add(lp(noise(), 120) * 0.35 * city + bp(noise(), 400, 2000) * 0.05 * city, 0, 0.4)
        add(np.sin(2 * np.pi * 60 * t) * 0.012 * power + np.sin(2 * np.pi * 120 * t) * 0.006 * power, 0)
    else:
        add(lp(noise(), 150) * 0.15 * city, 0, 0.4)
    # ---- event sound
    snaps_power = tl.t_power_off is not None and abs(tl.t_power_off - ev) < 0.1
    if snaps_power:
        n = int(1.1 * SR); tt = np.arange(n) / SR
        f = 320 * np.exp(-tt * 3.4) + 30
        place(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.4), ev, 0, 0.55)
        place(lp(rng.standard_normal(int(0.4 * SR)), 140) * np.exp(-np.arange(int(0.4 * SR)) / SR * 14), ev, 0, 1.3)
    else:
        n = int(2.5 * SR); tt = np.arange(n) / SR
        fb = 60 * np.exp(-tt * 3) + 35
        place(np.sin(2 * np.pi * np.cumsum(fb) / SR) * np.exp(-tt * 1.6), ev, 0, 0.6)
        place(bp(rng.standard_normal(n), 300, 4000) * np.exp(-tt * 2.5) * np.clip(tt / 0.05, 0, 1), ev, 0, 0.15)
    if tl.t_power_off is not None and not snaps_power:
        n = int(0.9 * SR); tt = np.arange(n) / SR
        f = 260 * np.exp(-tt * 3.4) + 30
        place(np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 2.6), tl.t_power_off, 0, 0.45)
    # ---- environmental beds
    started = np.clip((t - ev - 0.3) / 2.0, 0, 1)
    wamp = (0.07 + 0.35 * wind) * (0.3 + 0.7 * started) * (1.0 if tpl != "window" else 0.5)
    for pan, fr in ((-0.7, 0.11), (0.7, 0.09)):
        add(bp(noise(), 180, 900) * (0.6 + 0.4 * np.sin(2 * np.pi * fr * t + pan)) * wamp, pan)
    add(bp(noise(), 900, 7000) * rain * (0.55 if tpl == "window" else 0.8), 0.2, 0.22)
    add(lp(noise(), 300) * rain * 0.3, -0.2, 0.3)
    # thunder
    for k in range(40):
        tp = rng.uniform(ev, dur - 2); i = int(tp * SR)
        if rain[i] < 0.55 or rng.random() > 0.35: continue
        n = int(2.2 * SR); tt = np.arange(n) / SR
        place(lp(rng.standard_normal(n), 220) * np.exp(-tt * 1.8) * np.clip(tt / 0.08, 0, 1), tp, rng.uniform(-0.6, 0.6), 0.9 * rain[i])
    # earthquake rumble + cracks
    add(lp(noise(), 70) * shake * 1.6, 0, 0.6)
    for k in range(80):
        tp = rng.uniform(ev, dur - 1); i = int(tp * SR)
        if shake[i] < 0.3 or rng.random() > shake[i]: continue
        n = int(0.15 * SR); tt = np.arange(n) / SR
        place(hp(rng.standard_normal(n), 800) * np.exp(-tt * 40), tp, rng.uniform(-0.8, 0.8), 0.25)
    # fire crackle
    crk = (rng.random(N) > 0.9994).astype(float) * rng.uniform(0.3, 1.0, N)
    add(hp(crk, 1500) * smoke * 2.0, 0.3, 0.5)
    add(lp(noise(), 400) * smoke * 0.25, -0.3, 0.4)
    # water lapping
    lap = lp(noise(), 500) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.35 * t) ** 2)
    add(lap * np.clip(water * 3, 0, 1) * 0.35, 0.4)
    # crickets at night, birds by day
    night = 1 - day
    crick = night * started * (1 - rain) * (1 - snow) * (0.4 + 0.6 * veg if tpl != "hill" else 1.0) * (1 - smoke)
    gate = (np.sin(2 * np.pi * 28 * t) > 0.2) * (np.sin(2 * np.pi * 1.7 * t) > 0.35)
    add(np.sin(2 * np.pi * 4650 * t) * gate * crick, 0.5, 0.022)
    gate2 = (np.sin(2 * np.pi * 31 * t) > 0.3) * (np.sin(2 * np.pi * 1.3 * t + 2) > 0.5)
    add(np.sin(2 * np.pi * 4300 * t) * gate2 * crick, -0.6, 0.016)
    for k in range(260):
        tp = rng.uniform(0, dur - 0.5); i = int(tp * SR)
        dens = day[i] * (0.15 + 0.9 * veg[i] + (0.4 if tpl == "hill" else 0)) * (1 - rain[i]) * (1 - snow[i]) * (1 - smoke[i])
        if rng.random() > dens * 0.6: continue
        n = int(rng.uniform(0.06, 0.16) * SR); tt = np.arange(n) / SR
        f0 = rng.uniform(2600, 4800); fm = rng.uniform(600, 1600) * np.sin(2 * np.pi * rng.uniform(15, 40) * tt)
        sig = np.sin(2 * np.pi * np.cumsum(f0 + fm - tt * rng.uniform(-8000, 8000)) / SR) * np.sin(np.pi * tt / tt[-1]) ** 2
        for r in range(int(rng.integers(1, 4))):
            place(sig * 0.05, tp + r * rng.uniform(0.12, 0.2), rng.uniform(-0.9, 0.9))
    # ---- accelerating ticks
    tick = tl.t0; i = 0
    tick_end = tl.t0 + (dur - tl.t0) * 0.45
    while tick < tick_end:
        n = int(0.03 * SR); tt = np.arange(n) / SR
        c = hp(rng.standard_normal(n), 3000) * np.exp(-tt * 260) + np.sin(2 * np.pi * (1800 if i % 2 else 1500) * tt) * np.exp(-tt * 180) * 0.5
        place(c, tick, 0.15 if i % 2 else -0.15, 0.10 * np.clip((tick_end - tick) / 6, 0, 1))
        rate = min(14, 1.6 * 1.25 ** ((tick - tl.t0) / 2.0)); tick += 1 / rate; i += 1
    # ---- tension drone
    f_dr = 55 * 2 ** (np.clip((t - tl.t0) / (dur - tl.t0), 0, 1) * 7 / 12)
    phd = 2 * np.pi * np.cumsum(f_dr) / SR
    dr = np.sin(phd) + 0.5 * np.sin(phd * 1.5 + 0.3) + 0.35 * np.sin(phd * 2.003) + 0.25 * np.sin(phd * 3.01)
    add(lp(dr, 700) * np.clip((t - ev - 1) / 6, 0, 1) * (0.5 + 0.5 * np.clip((t - ev) / (dur - ev), 0, 1)), 0, 0.09)
    # ---- stage hits + final hit
    notes = [523.25, 587.33, 659.25, 783.99, 880.0, 987.77, 1046.5, 1174.7, 1318.5]
    hits = [s["at"] for s in tl.stages[1:]] + [tl.final_at]
    for k, th in enumerate(hits):
        rs = int(1.2 * SR); tt = np.arange(rs) / SR
        place(bp(rng.standard_normal(rs), 800, 6000) * (tt / 1.2) ** 3, th - 1.2, 0, 0.09)
        n = int(1.6 * SR); tt = np.arange(n) / SR
        fb = 70 * np.exp(-tt * 6) + 42
        place(np.sin(2 * np.pi * np.cumsum(fb) / SR) * np.exp(-tt * 3.2) * np.clip(tt / 0.005, 0, 1), th, 0, 0.4 if k < len(hits) - 1 else 0.6)
        bf = notes[min(k, len(notes) - 1)]
        bell = (np.sin(2 * np.pi * bf * tt) + 0.4 * np.sin(2 * np.pi * bf * 2.76 * tt) + 0.2 * np.sin(2 * np.pi * bf * 5.4 * tt)) * np.exp(-tt * 2.2)
        place(bell, th, 0.2, 0.06)
    fade = np.clip((dur - t) / 0.6, 0, 1) * np.clip(t / 0.05, 0, 1)
    mix = np.stack([L * fade, R * fade], 1)
    mix = np.tanh(mix * 1.2) / np.tanh(1.2)
    mix = mix / (np.max(np.abs(mix)) + 1e-9) * 0.89
    wavfile.write(out_wav, SR, (mix * 32767).astype(np.int16))
    return out_wav
