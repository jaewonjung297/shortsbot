# Example: "The Planet That Talks Back" (60.5 s, voiced)

In a planet store in space, aliens shop for planets. An alien dad and his kid find a dusty Earth on the bottom shelf for
99¢; a sneaky little seller whispers "It comes with humans"; the kid takes Earth home in a glass jar, the humans send a
message, the kid writes back, and Earth becomes the most wanted planet in the universe. 49 shots, each starting on a
word of the voice-over.

Use it in a project made from `template/` (it imports `src/blocky/`, `src/engine/`, and mirrors `src/library/`):
copy `src/planet/` and `src/plan.gen.ts` into `src/`, register the compositions as in `src/Root.tsx`, copy
`plan/plan_src.py` (replace its SHOTS with your story) and `tools/planet_check*`.

| file | what |
|---|---|
| `src/planet/cast.tsx` | looks + the staging of all 49 shots (`stageOf`), pure functions of t |
| `src/planet/shots.ts` | the lens of every shot (`LENS`) and `camAt` |
| `src/planet/sets.tsx`, `props.tsx`, `planets.tsx`, `layout.ts`, `PopCaptions.tsx` | the same as `template/src/library/` |
| `src/planet/mood.ts` | the library's moods with this Short's whisper (S17-S22) and ending (S46-S49) shots built in |
| `src/planet/PlanetShort.tsx` | the composition (`Planet`, `PlanetSub` for motion blur) |
| `plan/plan_src.py`, `plan/SHOTS.md`, `src/plan.gen.ts` | the word-anchored plan and its output |
| `tools/planet_check.ts`, `tools/planet_checks.sh` | numeric checks: LENS_IN, BLOCKED, OVERLAP, FRAMING, FACING (furniture lists per set inside) |

Final numbers (short_v3): 48 cuts all on their word frames, still frames 5.4 %, nothing static, captions ≥ 10.7 % from the
edges, voice at −14 LUFS, 0 numeric issues. The voice-over audio is not included.
