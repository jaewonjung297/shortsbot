# Changelog

## 1.2 (community) · the premium pass: real physics, PBR materials, cinematic game light
Built on the same 60 s Short: short_v3 (1.1 look) → a 12 s motion test → short_v4, v5, v6.
- **Rules:** `references/premium.md` (new: light, materials, characters, physics, tears, fire, the town, cost,
  checks), `references/pitfalls.md` round 3, `SKILL.md` (workflow steps 6 and 11, three new rules).
- **Engine:** clear-coated vinyl on every plastic + micro normal (`blocky/mat.ts`); per-mood image-based light
  (`core/envmap.tsx`, mood `env`); SSAO in the post chain (`ao`); depth fog per mood; procedural PBR sets
  (`mat/pbr.ts`); deterministic physics (`core/physics.ts`).
- **Characters:** faces in relief (shadow + highlight + bump), two-segment glowing antennae with spring lag, goggles,
  twin-tank jetpack, space badge, wrist gadget, sneakers, headset, bubble helmet; a swinging bag; the library looks
  updated; `secondaryMotion()`, `tears()`, `sweat()` in `library/characters.tsx` (was `.ts`).
- **Library:** `fx.tsx` (volumetric shafts, motes, soft particles, dust, debris, tears, rocket fire, smoke trail,
  sparks, glints), `town.tsx` (grass blades, leaf crowns, toy cars, far city, lit windows); sets with real materials
  and light shafts; the real sandwich; the dropping house with bounce + dust; the rocket car with real fire.
- **Tools:** `template/tools/region_flicker.py`.
- **Example:** `examples/planet-short/` updated to the short_v6 code.

## 1.1.1 · release fixes (all included in 1.2, plus `setMoodShots()` in `library/mood.ts`)
- Python: `render.sh` and `tools/stills.sh` find a working Python 3 with numpy themselves (new `tools/pick_python.sh`:
  python3, python, `py -3`), so the Windows Store `python3` stub is skipped without setting `PYTHON`.
- Safety: the scripts call `npx --no-install` (a missing `npm ci` fails instead of fetching packages); `render.sh` and
  `stills.sh` check their arguments (version, name, frame range, tag) before using them.
- Docs: first-run downloads (Chrome Headless Shell, the Whisper model), the pip line, Remotion's own license (not MIT;
  a company license above 3 employees), `LICENSE` and `THIRD_PARTY_NOTICES.md` also inside `template/`.
- `tools/shot_sheet.py` and `tools/critic.py` say what is missing when there is no `src/plan.gen.ts`.
- Line endings: every text file uses LF.

## 1.1 · lessons and library from a 60 s voiced Short
Built while making "The Planet That Talks Back" (60.5 s, 49 shots, voiced): 4 test renders, 3 full versions.
- **Rules:** `references/pitfalls.md` round 2 (voice timing, lenses and framing, passing through, motion, look,
  process); `references/style.md` §8 the premium pass + the proven caption variant; `references/render.md` versions,
  tools, sound, Windows; `SKILL.md` workflow steps 2, 5, 7, 9, 10, 11 and the rules.
- **Library** (`template/src/library/`): characters (aliens with accessories + the pose / idle / overshoot kit), planets,
  props, sets (store, room, space), scene moods, pop-in captions.
- **Template upgrades:** `Blocky.tsx` (eye scale, catch-lights, antennae with wobble, hat, bag, apron, glasses, rocket
  backpack, belts, cuffs, held and chest props, new emotions sly / love / curious), `motion.ts` (ant, antWob),
  `captions.tsx` (y position), `render.sh` (NAME prefix, keeps the sub-frame render, refuses any existing version),
  `tools/stills.sh` (refuses a used tag), new `tools/compare.sh`, `tools/shot_sheet.py`, `tools/critic.py`,
  `vo/transcribe.py`. The 10 s example still passes its checks.
- **Example:** `examples/planet-short/` (the whole Short's code + `planet_check.ts`).

## 1.0 · the original skill
The 10 s template, its references and scripts (62 files).
