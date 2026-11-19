// The lens of every shot (references/style.md section 5): a subject point, a lens offset from it (or a fixed lens
// position), fov, where the subject sits in the frame (fraction from the top), a small roll drift, and a constant
// push-in of PUSH x the lens distance per second. Times come from the word-anchored plan (plan.gen.ts).
import type { Cam } from "../engine/core/View";
import { aim } from "../engine/core/rig";
import { lerp } from "../blocky/motion";
import type { V3 } from "../blocky/motion";
import { SHOTS as PLAN, FPS } from "../plan.gen";
import { facePoint, heldWorld, stageOf } from "./cast";
import type { Stage } from "./cast";
import { EARTH_IN_JAR_Y, ROOM, STORE } from "./layout";

export const PUSH = 0.09;
type Lens = { subj: V3 | ((st: Stage, t: number) => V3); off?: V3; pos?: V3; fov: number; face: number; roll?: [number, number]; push?: number };

const faceOf = (key: string, dy = 0) => (st: Stage): V3 => {
  const a = st.actors.find((x) => x.key === key);
  if (!a) return [0, 1.2, 0];
  const f = facePoint(a.pose, a.s);
  return [f[0], f[1] + dy, f[2]];
};
const held = (key: string) => (st: Stage): V3 => {
  const a = st.actors.find((x) => x.key === key);
  return a ? heldWorld(a.pose, "R", a.s, [0, 0.12, 0]) : [0, 1, 0];
};
const mid = (p: V3, q: V3, u = 0.5): V3 => [lerp(p[0], q[0], u), lerp(p[1], q[1], u), lerp(p[2], q[2], u)];
const JAR_EARTH: V3 = [ROOM.jar[0], ROOM.jar[1] + EARTH_IN_JAR_Y, ROOM.jar[2]];
const TAG99: V3 = [-0.965, 0.17, -0.72];

export const LENS: Record<string, Lens> = {
  // the store
  S01: { subj: (st) => mid(faceOf("kid")(st), faceOf("dad")(st), 0.35), off: [0.7, 0.3, 3.9], fov: 52, face: 0.36, roll: [0, 1.5] },
  S02: { subj: faceOf("kid"), off: [0.45, -0.12, 1.25], fov: 50, face: 0.42, roll: [0, -1.5] },
  S03: { subj: [0, 0.9, -1.8], pos: [2.4, 3.3, 3.4], fov: 58, face: 0.52, roll: [0, -1], push: 0.07 },
  // S04: low, from behind the giant planet (its edge in the foreground) into the dad's face as he looks up
  S04: { subj: faceOf("dad"), pos: [-1.55, 1.15, -4.05], fov: 54, face: 0.42, roll: [-1, 1] },
  // S05: from inside the shelf, behind the chrome planet, out at the kid's face (he faces the planet)
  S05: { subj: faceOf("kid"), pos: [1.4, 1.02, -0.5], fov: 64, face: 0.42, roll: [0, 1.5] },
  // S06: from the right shelf's front, facing the pointing kid, the ringed planet above
  // S06: from the far end of the aisle (past the shelf) back at his face, the ringed planet up between them
  S06: { subj: (st) => mid(faceOf("kid")(st), STORE.ringed, 0.35), pos: [0.75, 1.0, -2.95], fov: 60, face: 0.48, roll: [0, -1.2] },
  // S07: the tag sits above the caption band (the caption covered it)
  S07: { subj: [STORE.saturn[0], 0.5, STORE.saturn[2] + 0.4], off: [-0.7, 0.55, 2.0], fov: 54, face: 0.5, roll: [0, 1.2] },
  S08: { subj: faceOf("dad"), off: [0.72, 0.02, 1.62], fov: 50, face: 0.42, roll: [0, -2] },
  S09: { subj: [STORE.jupiter[0], 0.95, STORE.jupiter[2] + 0.35], off: [0.4, 0.2, 1.45], fov: 50, face: 0.45, roll: [0, 1.5] },
  S10: { subj: faceOf("kid"), pos: [0.75, 1.36, -3.12], fov: 58, face: 0.42, roll: [0, -1.5] },
  // S11: from inside the bargain shelf (Earth in the foreground) out at the kid peering in
  S11: { subj: faceOf("kid"), pos: [-1.38, 0.48, -0.5], fov: 60, face: 0.42, roll: [0, 1.2] },
  // S12: from beyond the kid's feet (they were in the lens)
  S12: { subj: mid(STORE.earth, TAG99, 0.55), pos: [-0.5, 0.3, -1.2], fov: 50, face: 0.5, roll: [0, -1] },
  S13: { subj: [-0.55, 0.55, -0.85], pos: [1.0, 2.35, 0.95], fov: 55, face: 0.5, roll: [0, 1] },
  S14: { subj: TAG99, off: [0.45, 0.12, 0.35], fov: 42, face: 0.55, roll: [0, -1] },
  S15: { subj: (st) => mid(faceOf("dad")(st), held("dad")(st), 0.5), off: [-0.4, 0.05, 2.1], fov: 52, face: 0.45, roll: [0, 1.5] },
  // S16 / S20: reverse shot over the seller's shoulder, straight into the dad's face (the side lens showed only his head's side)
  S16: { subj: faceOf("dad"), pos: [3.75, 1.6, 0.55], fov: 50, face: 0.42, roll: [0, -1.5] },
  S17: { subj: faceOf("seller"), pos: [1.45, 1.6, 1.8], fov: 50, face: 0.42, roll: [0, 1.2] },
  S18: { subj: faceOf("seller"), off: [-1.15, 0.05, 0.5], fov: 50, face: 0.42, roll: [0, -1.5] },
  // S19: from the seller's side, the Earth in front of the dad's face (from the dad's side his arm blocked it)
  S19: { subj: held("dad"), off: [0.55, 0.1, -0.2], fov: 46, face: 0.55, roll: [0, 1] },
  S20: { subj: faceOf("dad"), pos: [3.5, 1.58, 0.68], fov: 50, face: 0.42, roll: [0, 2] },
  // S21: from INSIDE the shelf, between two rows of planets, looking out at the dad's face as he reaches in (beside him
  // the lens saw only his arm and back)
  S21: { subj: faceOf("dad", -0.12), pos: [-1.42, 1.06, -0.55], fov: 64, face: 0.42, roll: [0, -1] },
  S22: { subj: faceOf("dad"), off: [0.45, 0.0, 1.65], fov: 50, face: 0.42, roll: [0, 1.5] },
  S23: { subj: faceOf("kid", -0.08), off: [0.4, -0.02, 1.35], fov: 52, face: 0.4, roll: [0, -1.5] },
  // S24: a fixed aim point above his face (aiming at the rising Earth made the lens jerk with it)
  S24: { subj: [-0.1, 1.5, -0.45], off: [0.5, -0.3, 2.2], fov: 56, face: 0.42, roll: [-1, 1] },
  S25: { subj: (st) => mid(faceOf("kid")(st), faceOf("dad")(st), 0.5), off: [0.9, 0.9, 3.9], fov: 56, face: 0.48, roll: [0, -1] },
  S26: { subj: faceOf("kid", -0.22), off: [-1.15, 0.12, 0.62], fov: 50, face: 0.45, roll: [0, 1.5] },
  // home + jar
  S27: { subj: (st) => mid(faceOf("kid")(st), JAR_EARTH, 0.5), pos: [1.5, 1.3, -1.5], fov: 52, face: 0.45, roll: [0, 1.2] }, // found by search: face 3/4 to the lens, jar in front, both inside +-12.5 deg
  S28: { subj: JAR_EARTH, off: [-0.12, 0.08, 0.58], fov: 44, face: 0.5, roll: [0, -1] },
  S32: { subj: faceOf("kid"), pos: [0.32, 1.27, -1.68], fov: 50, face: 0.42, roll: [0, -2] },
  S33: { subj: [0, 1.0, -1.5], pos: [1.65, 1.75, 1.9], fov: 56, face: 0.5, roll: [0, 1], push: 0.07 },
  S34: { subj: faceOf("kid"), pos: [0.36, 1.18, -1.66], fov: 48, face: 0.42, roll: [0, 1.5] },
  S35: { subj: (st) => mid(faceOf("kid")(st), JAR_EARTH, 0.4), pos: [-0.15, 1.36, -3.2], fov: 50, face: 0.48, roll: [0, -1] },
  S36: { subj: JAR_EARTH, off: [0.12, 0.05, 0.5], fov: 42, face: 0.5, roll: [0, 1.5] },
  S38: { subj: [JAR_EARTH[0], JAR_EARTH[1] + 0.14, JAR_EARTH[2]], off: [-0.12, 0.12, 1.15], fov: 48, face: 0.48, roll: [0, -1] },
  S39: { subj: faceOf("kid"), pos: [0.3, 1.28, -1.66], fov: 48, face: 0.42, roll: [0, -1.5] },
  S40: { subj: faceOf("kid"), pos: [0.4, 1.22, -1.55], fov: 50, face: 0.42, roll: [0, 1.5] },
  // S41: the jar-side lens of S27 (sees his face and the card's front); a fixed aim, no jerk with the moving card
  S41: { subj: faceOf("kid"), pos: [1.5, 1.32, -1.5], fov: 52, face: 0.5, roll: [0, -1] },
  S48: { subj: (st) => mid(faceOf("kid")(st), JAR_EARTH, 0.5), pos: [1.45, 1.32, -1.4], fov: 50, face: 0.45, roll: [0, 1.5] },
  S49: { subj: JAR_EARTH, off: [0.0, 0.05, 0.52], fov: 42, face: 0.5, roll: [0, -1], push: 0.11 },
  // down on Earth
  S29: { subj: [0.4, 0.9, 1.8], pos: [-2.3, 0.65, 5.6], fov: 56, face: 0.5, roll: [0, 1.5] },
  S30: { subj: [0, 1.05, 1.5], off: [0.45, 0.3, 3.4], fov: 52, face: 0.42, roll: [0, -1.5] },
  S31: { subj: (st) => (st.car ? [st.car.p[0], st.car.p[1] + 0.5, st.car.p[2]] : [0, 1, 1.4]), pos: [0.6, 0.4, 5.6], fov: 60, face: 0.45, roll: [-1, 1.5] },
  S37: { subj: [0, 1.45, 1.7], pos: [0.4, 0.55, 5.2], fov: 56, face: 0.55, roll: [0, 1] },
  // the store, the next day
  S42: { subj: faceOf("seller", -0.15), pos: [1.65, 1.62, 2.1], fov: 50, face: 0.45, roll: [0, -1.2] },
  S43: { subj: [STORE.counter[0] + 0.15, 1.0, STORE.counter[2] + 0.17], off: [-0.42, 0.55, 0.0], fov: 46, face: 0.5, roll: [0, 1] },
  S44: { subj: faceOf("seller"), pos: [2.0, 1.32, 1.8], fov: 48, face: 0.42, roll: [0, 2] },
  S45: { subj: TAG99, off: [0.7, 0.18, 0.35], fov: 48, face: 0.5, roll: [0, -1.5] },
  S46: { subj: [-3.4, 1.3, 1.7], pos: [-0.9, 1.7, 2.2], fov: 54, face: 0.5, roll: [0, 1] },
  S47: { subj: [0.5, 1.7, 1.0], pos: [-2.6, 1.9, 7.8], fov: 56, face: 0.5, roll: [0, -1.5], push: 0.07 },
};

export const PLAN_SHOTS = PLAN;
/** shot index of OUTPUT frame n (all motion-blur sub-frames of n stay in one shot) */
export const shotIndexAt = (n: number) => {
  let i = 0;
  for (let k = 0; k < PLAN.length; k++) if (n >= Math.round(PLAN[k].t * FPS)) i = k;
  return i;
};
export const camAt = (i: number, t: number, st: Stage): Cam => {
  const s = PLAN[i];
  const L = LENS[s.id];
  const tau = t - s.t;
  // the subject is evaluated at the shot start for fixed-subject lenses, and live for moving ones
  const subj = typeof L.subj === "function" ? L.subj(st, t) : L.subj;
  const k = 1 - (L.push ?? PUSH) * tau;
  let pos: V3;
  if (L.pos) {
    const s0 = typeof L.subj === "function" ? L.subj(stageOf(s.id, s.t, s.t), s.t) : L.subj;
    pos = [s0[0] + (L.pos[0] - s0[0]) * k, s0[1] + (L.pos[1] - s0[1]) * k, s0[2] + (L.pos[2] - s0[2]) * k];
  } else {
    const o = L.off ?? [0, 0, 2];
    pos = [subj[0] + o[0] * k, subj[1] + o[1] * k, subj[2] + o[2] * k];
  }
  const c = aim(pos, subj, L.fov, L.face);
  const r = L.roll ?? [0, 1];
  return { ...c, roll: lerp(r[0], r[1], tau / Math.max(0.1, s.end - s.t)) };
};
