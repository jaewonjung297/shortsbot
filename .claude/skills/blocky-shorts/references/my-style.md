# My style: the HUSS HUSS town

The channel's own look. Use it for every Short, on top of `style.md` and the premium pass (`premium.md`).

## The universe
- **The rule:** in this town, everyone goes "HUSS HUSS". Every Short opens on that line at 0.0 s, with the town in
  frame and a face in the first second.
- A small, nosy, sunny suburb: one main street, brick and siding houses, picket fences, lawns, a few toy cars, a far
  city on the horizon. Everyone knows everyone's business.
- Stories are everyday drama (roommates, neighbours, family, small shops) retold as town events: gossip spreads,
  neighbours watch from porches, the town picks sides, and someone always shouts HUSS HUSS.

## The cast (`template/src/library/huss_cast.tsx`)
| who | role | main colour | loud silhouette | personality | default face | signature pose |
|---|---|---|---|---|---|---|
| **Mo** | narrator ("me") | teal `#18b5a8` | cream cap worn backwards with a navy brim (`acc.cap`), headset with a glowing mic, shaggy black hair, planet-ring print | deadpan; the only one who notices how weird the town is | curious | standing still, arms down, head a little turned |
| **Bea** | town gossip | hot pink `#ff3d8e` | pink hat with a gold band, tiny gold glasses, yellow shoulder bag, hair puffs, heart print | knows everything first, tells everyone second | sly | turned toward her target, one arm pointing at them |
| **Gus** | loud neighbour | sunshine orange `#ff8a1f` | goggles on the forehead, twin-tank jetpack, gold badge, red hair, freckles, star print, yellow sneakers | yells HUSS HUSS at everything, all hype | joy | both arms up in a V (raised arms: negative `out` spreads them) |
Scales: Mo 1.0, Bea 0.92, Gus 1.15.
Check silhouettes with the turnaround (`template/src/cast/TurnStill.tsx`, comp `TurnStill`, frame = cast index × 4 +
view: front, right side, back, left side). Gus's jetpack only reads from the side and back: turn him at least 3/4
in shots meant to show it. Mo's backwards cap is what reads from the side and back (the headset alone did not).
Rigid arms: a raised arm's sideways `out` flips direction (positive swings it inward over the head), and a hand cannot
reach the mouth, so gossip = pointing, not whispering. Negative body `yaw` turns a character toward screen-right
when the lens is on +z. Extras: the library `CROWD` looks re-skinned with human skin tones, never in
teal, hot pink or orange (those belong to the cast).

## Palette
- Cast colours above are reserved: one per character, never on sets or extras.
- World: sky `#2a5fd6 → #8fb6ea`, lawns `#4f8f2c` (shade `#22371c`), brick `#b2452f`, siding cream `#f4efe4` / blue
  `#8fc4e8` / butter `#f2d36b`, roofs dark brown `#5a3a2e`, picket white, road asphalt with yellow dashes.
- Accent gold `#ffd23a` for small trims (bands, badges, buckles) on everyone; it ties the cast together.

## Light per kind of scene (`library/mood.ts`, set `earth` unless noted)
| scene | light |
|---|---|
| street / lawn (default) | sunny day: key sun 42–48° from the lens's front-left, warm rim `#fff0c8` 3.2, fog `#cfe4ff` 0.007, AO on |
| gossip / secret | the whisper mood: darker, one warm shaft on the speakers, magenta rim, vignette 0.5 |
| indoor (homes, shops) | the home mood: warm lamp key, cool window fill, motes in the window shaft |
| night (town at night) | earth night: lamps and lit windows on, blue moon key, warm porch lights |
| HUSS HUSS moment | the current mood + a 0.25 s punch-in, bloom up 20 %, a dust burst at the shouter's feet |
| ending | golden hour: gold key + rim, low sun 15–25° |

## Materials
- Characters: painted vinyl with a clear coat (premium pass), faces in relief, metal on goggles, buckles and badges.
- Town: PBR brick, siding, shingles, concrete sidewalks, asphalt, grass blades, leaf canopies; toy cars in glossy
  paint. No textures from games; procedural only.

## Captions
- The proven pop-in variant (`library/PopCaptions.tsx`): white Poppins ExtraBold, thin dark outline, soft shadow,
  ≤ 2 lines, 12 % side margins, centred at ~68 % of the height.
- **HUSS HUSS** is the one exception: it pops in yellow `#ffd23a`, 1.4× size, with a small shake.

## Camera
- A cut every ~1.4 s with a push-in; group shots wide from ~7–8 m (fov 44) so all three stay inside the frame;
  close-ups for every reaction. Mo's face in the first second.
