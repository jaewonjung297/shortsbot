# The premium pass: a modern sandbox-game look with real-life physics, materials and light

Version 1.2 (community). Everything here was built and tested on the 60 s worked example (`examples/planet-short/`):
short_v3 (the 1.1 look) → short_v4 / v5 / v6 (this pass). Still our own blocky toy world: rigid parts, decal faces,
saturated colours; what changes is how real it behaves and how it is lit. All of it is deterministic (Remotion renders
frames alone, in any order, in several tabs) and all textures are procedural (no downloads, no licences to track).

## 1. Light (engine level, every scene)

| piece | where | numbers that worked |
|---|---|---|
| image-based light per mood: a small HDR studio (sky → ground gradient + soft panels where key, rim and fill come from + extra coloured panels), PMREM, `scene.environment` | `template/src/engine/core/envmap.tsx`, mood `env: { k, hemiK, extra }` | k 0.4–0.6; hemisphere scaled by hemiK 0.5 when it is on; store: neon-coloured horizon panels so the glossy floor and clear coats reflect colour |
| screen-space ambient occlusion: half-res, 14 samples, fixed per-pixel rotation (same every frame), depth-aware 5×5 blur, multiplied into the colour pass before bloom | `engine/post/pipeline.ts`, post `ao: { enabled, radius, strength }` | radius 0.32–0.4 m (scaled by distance), strength 0.7–0.75 |
| depth fog per mood | mood `fog: [colour, density]` | store 0.03, whisper 0.05, night room 0.04, Earth day 0.007 (more turns the far city into flat haze) |
| volumetric shafts: additive open cones, soft view-angle edges, drifting density noise, fade along the length, **fade near the lens** | `library/fx.tsx` `VolumeBeam` | op 0.3–0.7; lamps r0 0.17 → r 0.95; through a window r0 ≈ the window radius |
| dust motes in the light | `fx.tsx` `Motes` | 70–110 per set, 9–12 mm |
| emissives that light their surroundings | a point light next to every strong emitter (lamps, fire, jar) | fire: 4 × flicker, distance 6 m |

Keep each scene's mood: bright store, dark whisper (one warm shaft on the speakers, the aisle lamps dimmed), blue
night room (moonbeam + light pool on the floor), golden ending (the same rigs in gold, dimmer shafts).

## 2. Materials

- **Characters = painted vinyl toys:** every `plastic()` is a `MeshPhysicalMaterial` with a clear coat (0.55; matte
  parts 0.12) and a very fine orange-peel micro normal (scale 0.18). Metal accessories `metal: 0.8–0.9`.
- **World = procedural PBR sets** (`engine/mat/pbr.ts`: albedo + roughness + normal from one height field): wood,
  siding, brushed metal, concrete, plaster, fabric (with sheen), grass, soil, asphalt, brick, roof tiles, floor tiles,
  bark, bread crumb, crust, leaf. `pbr(name, set, colour, { rep, clearcoat, normal, metal, sheen })`.
- **Albedo near white**: the material colour carries the colour; a baked albedo around 0.6 turns every tint brown.
- **Repeat per real size**: walls 0.4–0.6 m per tile (coarser reads as stucco); bricks 12.5 cm; boards 20 cm.
- **Glass** that reflects the environment, with a warm lit room plane behind it (windows), or a clear-coated pane.
- **Painted parts stay paint**: a coloured shelf side in tinted wood went dark maroon under the store light; lacquered
  paint (clear coat 1) pops like a toy. Real wood on boards, floors, doors, counters.

## 3. Characters that jump out

- **One loud silhouette each**: the kid = space goggles on the forehead + twin-tank silver jetpack + glowing sneakers +
  a space badge; the dad = hat + swinging bag + gold badge + wrist gadget; the seller = tiny glasses + headset with a
  glowing mic; the crowd = bubble helmets, goggles, badges, sneakers in bold pairs. (`Look.acc` + `Look.kicks`.)
- **Glowing antennae**: two segments with a ring, emissive tips (ei 1.5) so bloom catches them.
- **Expressions in relief**: the features are drawn once, composed on the decal with a soft drop shadow (down-right,
  away from the key) and a thin top-left highlight, and a blurred height map of the same shapes is the decal's bump
  map (bs 3, clear coat ~0.3, roughness ~0.45: 0.9 caught hot spots, see pitfalls round 3). Cheeks stay flat paint. They still change with the story (the emotion picks the face).

## 4. Physics (deterministic)

`engine/core/physics.ts`:

- `spring(drive, t, hz, zeta, win)`: re-simulates a damped spring from rest `win` s before t at a fixed 1/240 s step.
  The lag behind the driver is the secondary motion. Drivers are sampled from the actor's OWN pose function at 60 Hz
  over the window (one stage evaluation per sample for all actors): antennae (fore-aft + sideways, 2.4 Hz, ζ 0.16),
  the bag (1.6 Hz, ζ 0.14), the jetpack (3 Hz, ζ 0.25). Clamp the result (±0.7 rad).
- `bounce(tau, h0, { e, squashK, vmin })`: closed-form drop with restitution: lands, bounces low, settles; squash on
  every impact (scaled by impact speed, ≤ 0.35, recovers in ~0.15 s); returns the impacts for dust.
- `wobble(t, t0, a, hz, decay)`: the damped jiggle after landing.
- `burst(...)`: particles with linear drag + gravity in closed form, a ground plane where they stop. Dust (gk −0.04:
  it floats and rises), debris and crumbs (gk 1: they land and STAY), sparks (fast, gravity), embers (slow, rising).
- Randomness only from `h01(seed)`, never `Math.random`; nothing carried from one frame to the next.
- Contact: feet on the ground (sink 3 mm hard floors, 12 mm grass: instanced blades cover the soles), held props in
  the hand's frame, crumbs and chips on the ground plane, the rocket car hovering on its fire before lift-off (standing
  on its nozzle hid the flame in the ground).

## 5. Small effects at full detail

- **Tears** (`fx.tsx` `Tear`, head space): 0.5 s forming at the lower lid (grows, trembles) → runs down with gravity and
  stick-slip → leaves a wet glossy streak (segments, clear coat) → over the chin edge it detaches and falls, fading.
  Drop = transmission 1, IOR 1.33, clear coat 1 + a tiny hot highlight up-left. Radius 16 mm on a 0.27 m head: smaller
  does not read on a phone. Two tears, staggered 0.5–0.8 s, one per eye; one starts before the cut.
- **Sweat**: the same drop from the temple on shock.
- **Sparkles**: four-point star glints that twinkle and drift down (`Glints`), on top of the old sparkles.
- **Glow**: emissive tips and screens + bloom; sprites capped at 160 px.

## 6. The humans' world

- Lawn = PBR grass + 34,000 instanced blades (tapered, two-tone, rooted, swaying in the wind shader) around the action.
- Trees = bark + crowns of instanced alpha-cut leaf cards (240–520 per crown) around a dark core, rustling in the same
  wind (`WIND.value = t`, one uniform for the whole set).
- Houses: brick / siding / clay roof tiles, glass windows with lit rooms behind (brighter at night), metal knobs.
- A living town: toy cars driving the road at constant speeds (wheels turn with the distance), lamps that light up at
  night, a far city behind the hills with a window grid (lit at night).
- Props real but toy-like: the sandwich = crust + crumb slices, frilly lettuce, tomato slices with seeds, ham, cheese
  with holes; crumbs fly in bursts while it is torn and stay in the grass.
- The rocket: three noise-flame layers (white-hot core added, orange and red layers **alpha-blended**: additive fire
  washes out to white over a day sky), flicker < 12 Hz (no strobing), a heat light, a smoke trail emitted along the
  car's real path (warm when young, grey later, a ground cloud at lift-off), sparks + embers, a lift-off dust ring +
  soil chips, a glowing scorch on the lawn.

## 7. Cost (phone-first)

The premium pass took a sub-frame from ~23 ms to ~51 ms (4 sub-frames per frame: the 60 s film renders in ~4 min on
the test GPU). Instancing (grass, leaves), one env map per mood (cached), half-res AO and point sprites keep it
there. Planar mirror reflections and screen-space reflections were not needed: the env map in the clear coats reads
as reflections on a phone.

## 8. Checks for this pass

- `tools/critic.py` as before (sync, static, edges, sound) + `tools/region_flicker.py <video> f0 f1 x y w h` on every
  fire / lightning / glow region (FAIL = strobing).
- Shot sheet + 20 frames: look for **haze over faces** (motes / shafts in front of the lens), washed-out faces in gold
  light, dark tinted wood, fire hidden in the ground, objects floating (falling objects mid-air are fine: check the
  frames around them).
