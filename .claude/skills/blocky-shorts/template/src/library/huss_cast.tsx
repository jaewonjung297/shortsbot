// The HUSS HUSS town cast: three original townspeople, one silhouette, one main colour and one loud accessory each.
// Style sheet: references/my-style.md in the blocky-shorts skill.
import type { Emotion, Pose } from "../blocky/motion";
import type { Look } from "../blocky/Blocky";
import { base } from "./characters";

export type CastMember = { key: string; name: string; role: string; look: Look; s: number; emotion: Emotion };

/** MO, the narrator ("me"): teal, a cream cap with a navy brim worn backwards over a headset with a glowing mic. Deadpan, the only one who notices how weird the town is. */
export const MO: Look = {
  skin: "#e8b48a", shirt: "#18b5a8", pants: "#2b3550", shoes: "#f4f4f2", sole: "#18b5a8", hair: "#2a1d18", hairStyle: "shaggy",
  accent: "#fff1c4", print: "ring", cheeks: "none", eyeScale: 1.08, belt: "#20263a", cuffs: "#0e7f76", kicks: "#5fe8ff",
  acc: { headset: "#1d2230", cap: ["#fff1c4", "#22305a"] },
};

/** BEA, the town gossip: hot pink, a hat with a gold band and a swinging shoulder bag. Knows everything first, tells everyone second. */
export const BEA: Look = {
  skin: "#b8794e", shirt: "#ff3d8e", pants: "#5a3fc8", shoes: "#ffffff", sole: "#ff3d8e", hair: "#1e1410", hairStyle: "puffs",
  accent: "#ffd23a", print: "heart", cheeks: "blush", eyeScale: 1.15, belt: "#3a2a6a", cuffs: "#ffd23a",
  acc: { hat: ["#ff3d8e", "#ffd23a"], bag: "#ffd23a", glasses: "#ffd23a" },
};

/** GUS, the loud neighbour: sunshine orange, goggles on his forehead and a twin-tank jetpack. Yells HUSS HUSS at everything. */
export const GUS: Look = {
  skin: "#f1c393", shirt: "#ff8a1f", pants: "#2f63c9", shoes: "#1a1a22", sole: "#ffd23a", hair: "#c8452a", hairStyle: "shaggy",
  accent: "#ffd23a", print: "star", cheeks: "freckles", belt: "#2a2a3a", cuffs: "#ffd23a", kicks: "#ffd23a",
  acc: { goggles: ["#2a2f48", "#7dffcf"], jetpack: ["#dfe4f0", "#ff3d3d"], badge: "#ffd23a" },
};

export const HUSS_CAST: CastMember[] = [
  { key: "mo", name: "Mo", role: "narrator", look: MO, s: 1, emotion: "curious" },
  { key: "bea", name: "Bea", role: "gossip", look: BEA, s: 0.92, emotion: "sly" },
  { key: "gus", name: "Gus", role: "loud neighbour", look: GUS, s: 1.15, emotion: "joy" },
];

/** signature poses (s = scale): Mo stands deadpan, Bea points at whoever she is gossiping about, Gus throws both arms up in a V for HUSS HUSS */
export const signature = (key: string, x: number, z: number, yaw: number, s: number): Pose => {
  if (key === "mo") return base(x, z, yaw, s, { armL: 0.02, armR: 0.02, outL: 0.1, outR: 0.1, headYaw: 0.08 });
  if (key === "bea") return base(x, z, yaw, s, { armL: 1.45, outL: 0.05, armR: 0.1, outR: 0.12, headYaw: 0.25, headPitch: 0.03 });
  return base(x, z, yaw, s, { armL: 2.75, armR: 2.75, outL: -0.3, outR: -0.3, headPitch: -0.1 });
};
