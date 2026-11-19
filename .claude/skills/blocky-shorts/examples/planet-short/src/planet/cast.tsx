// The cast and the staging of every shot: who is in the shot, where, in which pose, with which face and prop. Pure
// functions of (shot id, t). Looks stay inside the one blocky family (references/style.md section 1): aliens = green
// or lilac skin + antennae; every character keeps one saturated colour.
import React from "react";
import * as THREE from "three";
import { KID_A, KID_B } from "../blocky/Blocky";
import type { Held, Look } from "../blocky/Blocky";
import { coneMatrix, hash, L, legDrop, lerp, SPEC, ss, U } from "../blocky/motion";
import type { Emotion, Pose, V3 } from "../blocky/motion";
import { Card, Earth, Flashlight, Jar, Sandwich } from "./props";
import { Tear } from "./fx";
import { spring } from "../engine/core/physics";
import { EARTH_IN_JAR_Y, ROOM, STORE } from "./layout";
import { SHOTS as PLAN } from "../plan.gen";

// ------------------------------------------------------------------ looks
// premium pass: louder silhouettes. Kid = space goggles + silver twin-tank jetpack + glowing sneakers; dad = hat + bag +
// a gold space badge + a wrist gadget; seller = tiny glasses + headset with a glowing mic; the crowd: bubble helmets,
// goggles, badges, sneakers in bold colour pairs.
export const DAD: Look = { skin: "#6fcf5a", shirt: "#2a7de1", pants: "#3b3f58", shoes: "#f4f4f2", sole: "#ff7a1a", hair: "#5fb84a", hairStyle: "antennae", accent: "#ffd23a", print: "ring", cheeks: "none", belt: "#2a2a3a", cuffs: "#ffd23a", kicks: "#ff7a1a", acc: { hat: ["#3a3f58", "#ffd23a"], bag: "#c87a3a", badge: "#ffd23a", wrist: "#5fe8ff" } };
export const KID: Look = { skin: "#9be36e", shirt: "#ff8a1f", pants: "#2f63c9", shoes: "#ffffff", sole: "#2fd0bd", hair: "#86d05c", hairStyle: "antennae", accent: "#ff4fa3", print: "star", cheeks: "blush", eyeScale: 1.38, belt: "#2a3a8a", cuffs: "#ffd23a", kicks: "#2fd0bd", acc: { goggles: ["#2a3a8a", "#5fe8ff"], jetpack: ["#dfe4f0", "#ff4fa3"], badge: "#ffd23a" } };
export const KID_PJ: Look = { ...KID, shirt: "#5fb8ff", pants: "#3a5ad0", print: "star", accent: "#ffd23a", belt: undefined, cuffs: "#ffffff", kicks: undefined, acc: { goggles: ["#2a3a8a", "#5fe8ff"] } };
export const SELLER: Look = { skin: "#b48cf0", shirt: "#d6283c", pants: "#2a2a3a", shoes: "#1a1a22", sole: "#ffd23a", hair: "#a07ae0", hairStyle: "antenna1", accent: "#7dffcf", print: "bow", cheeks: "none", cuffs: "#ffd23a", acc: { apron: "#2fd0bd", glasses: "#ffd23a", headset: "#2a2a3a" } };
const CROWD: Look[] = ([
  { ...DAD, skin: "#f0a040", hair: "#e09030", shirt: "#7fe3b8", accent: "#ff4fa3", print: "heart" },
  { ...KID, skin: "#5fd8ff", hair: "#4fc0e8", shirt: "#ffd23a", accent: "#ff7a1a", print: "bolt" },
  { ...SELLER, skin: "#ff8ac8", hair: "#e870b0", shirt: "#2fd0bd", accent: "#ffd23a", print: "star", hairStyle: "antennae" },
  { ...DAD, skin: "#c8e04a", hair: "#a8c03a", shirt: "#b04ae0", accent: "#7dffcf", print: "ring" },
  { ...KID, skin: "#ff9a6a", hair: "#e8805a", shirt: "#2a7de1", accent: "#ffd23a", print: "heart", hairStyle: "antenna1" },
  { ...SELLER, skin: "#7fe3b8", hair: "#5fc898", shirt: "#ff5aa0", accent: "#5fd8ff", print: "bolt", hairStyle: "antennae" },
  { ...DAD, skin: "#a08aff", hair: "#8a70f0", shirt: "#ff8a1f", accent: "#7dffcf", print: "star" },
] as Look[]).map((l, i) => ({
  ...l,
  eyeScale: 1.1,
  belt: "#2a2a3a",
  kicks: ["#ff4fa3", "#5fe8ff", "#ffd23a", "#7dffcf"][i % 4],
  acc: [{ helmet: "#bfefff" }, { goggles: ["#ff4fa3", "#ffd23a"] as [string, string] }, { badge: "#ffd23a" }, { helmet: "#ffd0f0", badge: "#7dffcf" }, { goggles: ["#2a2f48", "#7dffcf"] as [string, string] }, { helmet: "#d0ffd8" }, { badge: "#ff7a1a", wrist: "#ffd23a" }][i],
}));

export const SCALE = { dad: 1.2, kid: 1, seller: 0.7, human: 1, crowd: 1.05 };
const SINK = 0.003; // hard floors: soles barely pressed in
const GRASS_SINK = 0.012;
/** face (head centre) height above the feet for a standing character of scale s */
export const faceH = (s: number) => (L + (SPEC.torso.h + SPEC.head.gap + SPEC.head.h / 2) * U) * s;

// ------------------------------------------------------------------ pose builders
const base = (x: number, z: number, yaw: number, s: number, o: Partial<Pose> = {}, sink = SINK): Pose => ({
  x, y: (L - sink) * s, z, yaw, pitch: 0, legL: 0, legR: 0, armL: 0.06, armR: 0.06, outL: 0.05, outR: 0.05, headPitch: 0, headYaw: 0, ...o,
});
/** a walk toward yaw at v m/s from (x0, z0) at t0: rigid legs +-0.42, counter arms, a small bob */
export const walk = (x0: number, z0: number, yaw: number, t: number, t0: number, v: number, s: number, o: Partial<Pose> = {}, sink = SINK): Pose => {
  const d = v * (t - t0);
  const ph = 2 * Math.PI * 1.1 * (t - t0);
  const psi = 0.42 * Math.sin(ph);
  return {
    ...base(x0 + Math.sin(yaw) * d, z0 + Math.cos(yaw) * d, yaw, s, {}, sink),
    y: (legDrop(Math.abs(psi)) - sink) * s,
    legL: psi, legR: -psi, armL: -0.55 * psi, armR: 0.55 * psi,
    bob: -0.015 * (0.5 + 0.5 * Math.cos(2 * ph)), sway: 0.03 * Math.cos(ph), headPitch: 0.02 * Math.cos(2 * ph),
    ...o,
  };
};
/** sitting on the floor, legs forward */
const sit = (x: number, z: number, yaw: number, o: Partial<Pose> = {}): Pose => {
  const pitch = o.pitch ?? 0;
  return { ...base(x, z, yaw, 1), y: (SPEC.shoe.d * U) / 2 + 0.004, legL: Math.PI / 2 + pitch, legR: Math.PI / 2 + pitch, armL: 0.5, armR: 0.5, outL: 0.12, outR: 0.12, ...o };
};
const breathe = (t: number, seed: number) => 0.012 * Math.sin(t * 2.2 + seed);
/** anticipation + overshoot for big moves: a small dip back, then a fast move that overshoots and settles (0 -> 1) */
export const pop = (u: number) => {
  if (u <= 0) return 0;
  if (u < 0.18) return -0.14 * Math.sin((Math.PI * u) / 0.18);
  const x = Math.min(1, (u - 0.18) / 0.82) - 1;
  return 1 + 2.6 * x * x * x + 1.6 * x * x;
};
const popT = (tau: number, t0: number, dur: number) => pop((tau - t0) / dur);
/** the idle layer on every actor: breathing, a slow sway, a drifting head, arms that never freeze, wobbling antennae */
const alive = (a: Actor, t: number): Actor => {
  const s = a.blinkSeed * 1.7;
  const p = a.pose;
  const br = Math.sin(t * 2.1 + s);
  return {
    ...a,
    pose: {
      ...p,
      bob: (p.bob ?? 0) - 0.006 * (1 + br),
      sway: (p.sway ?? 0) + 0.014 * Math.sin(t * 0.9 + s),
      headPitch: p.headPitch + 0.018 * Math.sin(t * 1.3 + s * 2),
      headYaw: p.headYaw + 0.045 * Math.sin(t * 0.7 + s),
      armL: p.armL + 0.035 * Math.sin(t * 1.1 + s),
      armR: p.armR + 0.035 * Math.sin(t * 1.2 + s + 1),
      antWob: (p.antWob ?? 0) + 0.035 * Math.sin(t * 5.2 + s) + 0.015 * Math.sin(t * 8.3 + s * 3),
    },
  };
};
export const blinkAt = (t: number, seed: number) => {
  const u = (t * 0.37 + hash(seed)) % 1;
  return u < 0.028;
};
const yawTo = (from: [number, number], to: [number, number]) => Math.atan2(to[0] - from[0], to[1] - from[1]);

/** world point of something held in a hand (local offset above the grip), with the character's scale */
export const heldWorld = (p: Pose, side: "L" | "R", s: number, local: V3 = [0, 0, 0]): V3 => {
  const p0: Pose = { ...p, x: 0, y: 0, z: 0, yaw: 0, coneTilt: undefined };
  const M = new THREE.Matrix4()
    .makeTranslation(p.x, p.y, p.z)
    .multiply(new THREE.Matrix4().makeRotationY(p.yaw))
    .multiply(new THREE.Matrix4().makeScale(s, s, s))
    .multiply(coneMatrix(p0, side))
    .multiply(new THREE.Matrix4().makeTranslation(0, 0.02, 0));
  const v = new THREE.Vector3(...local).applyMatrix4(M);
  return [v.x, v.y, v.z];
};
export const facePoint = (p: Pose, s: number): V3 => {
  // head centre: hip pivot + torso + gap + half head, through yaw and pitch
  const h = (SPEC.torso.h + SPEC.head.gap + SPEC.head.h / 2) * U * s;
  return [p.x + Math.sin(p.yaw) * Math.sin(p.pitch) * h, p.y + Math.cos(p.pitch) * h, p.z + Math.cos(p.yaw) * Math.sin(p.pitch) * h];
};

// ------------------------------------------------------------------ the stage of a shot
export type Actor = { key: string; look: Look; pose: Pose; emotion: Emotion; s: number; held?: Held; chest?: React.ReactNode; blinkSeed: number; fx?: React.ReactNode };
export type Stage = {
  actors: Actor[];
  earthOnShelf?: boolean;
  tag99?: string[];
  storm?: number;
  poster?: boolean;
  /** the Earth inside the jar (home / jar shots) */
  jarEarth?: { spin: number; lights: number; hi?: boolean };
  jarGlow?: number;
  message?: number; // 0..1 rise of the glowing message in the jar
  carInJar?: boolean;
  sparkle?: V3;
  houses?: number; // S29: seconds since the shot start (the houses drop in one after another)
  car?: { p: V3; flame: number };
  /** S30: the sandwich is being torn: crumbs fly */
  crumbs?: boolean;
  /** a dust puff (the dusty Earth leaving / touching the shelf): where and when (global s) */
  puff?: { p: V3; t0: number; k: number };
  catalog?: { price: string[]; strike?: number };
  night?: boolean;
};

const EARTH_R = 0.1;
const heldEarth = (s: number, lights = 0): Held => ({ side: "R", node: <Earth p={[0, (EARTH_R + 0.02) / s, 0]} r={EARTH_R / s} lights={lights} clouds={false} dusty /> });
const jarAsChest = (lights: number) => (
  <group position={[0, -0.2, 0.2]}>
    <Jar>
      <group position={[0, EARTH_IN_JAR_Y, 0]}>
        <Earth r={EARTH_R} lights={lights} />
      </group>
    </Jar>
  </group>
);

// ------------------------------------------------------------------ tears and sweat (head space of a Blocky)
const FZ = (SPEC.head.d * U) / 2 + 0.0045; // the face decal plane
const CHIN = -((SPEC.head.h - 2 * SPEC.head.r) * U) / 2;
const EYE_Y = (0.05 - 0.15 * 0.94) * U; // the lower lid of a sad eye (eyeScale 1)
/** real tears: each entry = [start time (global s), eye side -1/1, seed] */
const tears = (t: number, list: [number, number, number][]) => (
  <>
    {list.map(([t0, side, seed], i) => (
      <Tear key={i} tau={t - t0} eye={[side * 0.21 * U + side * 0.012, EYE_Y - 0.002]} fz={FZ} chin={CHIN} r={0.016} seed={seed} />
    ))}
  </>
);
/** a sweat drop at the temple (shock) */
const sweat = (t: number, t0: number, side = 1) => <Tear tau={t - t0} eye={[side * 0.4 * U, 0.3 * U]} fz={FZ} chin={CHIN} r={0.012} seed={7} />;

// ------------------------------------------------------------------ Earth: the sandwich and the rocket car (also used by
// the effects, which need their positions at earlier emission times)
/** S30: the sandwich centre in the world at time t (shot start a): in hA's right hand */
export const sandwichAt = (a: number, t: number): V3 => {
  const tau = t - a;
  const tug = Math.sin(tau * 7) * 0.08;
  const p = base(-0.48 + tug, 1.5, Math.PI / 2 - 0.45, 1, { pitch: -0.14, armL: 1.45, armR: 1.45, outL: -0.12, outR: -0.12 }, GRASS_SINK);
  return heldWorld(p, "R", 1, [0.08, 0.06, 0.22]);
};
/** S31: ignition at the shot start, lift-off LIFT s later; before it the car shudders on its tail (nozzle on the lawn) */
export const LIFT = 0.3;
const CAR_REST_Y = 1.07 + 0.5; // the car hovers on its fire ~0.5 m above the lawn before lift-off (nose up, 0.8 scale)
export const carAt = (a: number, t: number): { p: V3; flame: number } => {
  const tau = t - a;
  const u = Math.max(0, tau - LIFT);
  const shake = tau < LIFT ? 0.012 * Math.sin(tau * 61) * Math.min(1, tau * 6) : 0.004 * Math.sin(tau * 47);
  return { p: [0.2 + shake, CAR_REST_Y + 2.9 * u * u + 0.5 * u, 1.4 + shake * 0.6], flame: Math.min(1, 0.45 + tau * 2.2) };
};

// store positions
const KID_SHELF: [number, number] = [0.15, -0.72]; // kid sitting at the bargain shelf
const DAD_SHELF: [number, number] = [-0.42, -0.72];
const DAD_COUNTER: [number, number] = [1.95, 1.0];
const SELLER_AT: [number, number] = [STORE.counter[0] + 0.6, STORE.counter[2]];
const SELLER_Y = 0.42; // he stands on a low box: his head just peeks over the counter
const seller = (t: number, o: Partial<Pose>, emotion: Emotion): Actor => {
  const p = base(SELLER_AT[0], SELLER_AT[1], -Math.PI / 2, SCALE.seller, { pitch: 0.18, headPitch: -0.12, ...o });
  return { key: "seller", look: SELLER, pose: { ...p, y: p.y + SELLER_Y, headPitch: (o.headPitch ?? 0) + breathe(t, 3) }, emotion, s: SCALE.seller, blinkSeed: 3 };
};
const kidHome = (t: number, o: Partial<Pose>, emotion: Emotion, extra: Partial<Actor> = {}): Actor => {
  const yaw = yawTo([ROOM.kid[0], ROOM.kid[2]], [ROOM.jar[0], ROOM.jar[2]]);
  return { key: "kid", look: KID_PJ, pose: base(ROOM.kid[0], ROOM.kid[2], yaw, 1, { headPitch: 0.12 + breathe(t, 1), ...o }), emotion, s: 1, blinkSeed: 1, ...extra };
};

const stageRaw = (id: string, a: number, t: number): Stage => {
  const tau = t - a;
  const kid = (pose: Pose, emotion: Emotion, extra: Partial<Actor> = {}): Actor => ({ key: "kid", look: KID, pose, emotion, s: 1, blinkSeed: 1, ...extra });
  const dad = (pose: Pose, emotion: Emotion, extra: Partial<Actor> = {}): Actor => ({ key: "dad", look: DAD, pose, emotion, s: SCALE.dad, blinkSeed: 2, ...extra });
  const human = (k: string, look: Look, pose: Pose, emotion: Emotion, extra: Partial<Actor> = {}): Actor => ({ key: k, look, pose, emotion, s: 1, blinkSeed: k.length, ...extra });
  switch (id) {
    // ---------------------------------------------------------------- the store
    case "S01":
    case "S03": {
      const t0 = id === "S01" ? 0 : -1.2;
      return {
        earthOnShelf: true,
        actors: [
          kid(walk(0.32, -2.6, 0, t, t0, 0.45, 1, { headYaw: -0.35 + 0.1 * Math.sin(t * 1.3), headPitch: -0.15 }), "happy"),
          dad(walk(-0.38, -2.85, 0, t, t0 - 0.1, 0.45, SCALE.dad, { headYaw: 0.4, headPitch: -0.1 }), "happy"),
        ],
      };
    }
    case "S02":
      return { earthOnShelf: true, actors: [kid(base(0.32, -1.68, 0.3, 1, { headPitch: -0.38 + breathe(t, 1), headYaw: -0.55 + 0.12 * ss(0.2, 0.8, tau), armR: 0.25, armL: 0.25 }), "curious")] };
    case "S04":
      return {
        earthOnShelf: true,
        actors: [
          // S04: the dad turned 0.4 toward the lens (it sits 0.86 rad to that side of his gaze)
          dad(base(-1.95, -2.3, yawTo([-1.95, -2.3], [STORE.giant[0], STORE.giant[2]]) - 0.4, SCALE.dad, { headPitch: -0.5 - 0.1 * ss(0, 0.8, tau), armL: 0.3, armR: 0.3, outL: 0.15, outR: 0.15 }), "curious"),
          kid(base(-0.55, -1.9, yawTo([-0.55, -1.9], [STORE.giant[0], STORE.giant[2]]), 1, { headPitch: -0.55 }), "happy"),
        ],
      };
    case "S05":
      return { earthOnShelf: true, actors: [kid(base(0.45, -0.4, Math.PI / 2 + 0.1, 1, { headPitch: 0.2, headYaw: -0.15 + 0.08 * Math.sin(t * 3), armR: 0.9 + 0.1 * Math.sin(t * 4), outR: 0.1 }), "joy")] };
    case "S06":
      return { earthOnShelf: true, actors: [// S06: he faces the ringed planet and points with the arm FAR from the lens (the lens is on his left)
      kid(base(0.42, -1.55, yawTo([0.42, -1.55], [STORE.ringed[0], STORE.ringed[2]]), 1, { armR: 2.45 + 0.06 * Math.sin(t * 5), outR: 0.12, armL: 0.3, headPitch: -0.42, headYaw: 0.1 }), "joy")] };
    case "S07":
    case "S09":
      return { earthOnShelf: true, storm: id === "S09" ? 1 : 0, actors: [] };
    case "S08":
      return { earthOnShelf: true, actors: [dad(base(1.9, -2.15, 0.45, SCALE.dad, { headPitch: -0.05, armL: lerp(0.3, 1.6, popT(tau, 0, 0.7)), armR: lerp(0.3, 1.6, popT(tau, 0, 0.7)), outL: 0.5, outR: 0.5, ant: lerp(0, 1, popT(tau, 0.05, 0.65)), pitch: -0.06 * popT(tau, 0, 0.7) }), "shock")] };
    case "S10": {
      const yaw = yawTo([0.8, -1.9], [STORE.jupiter[0], STORE.jupiter[2]]);
      return { earthOnShelf: true, storm: 1, actors: [kid(base(0.8, -1.9, yaw, 1, { headPitch: -0.2 + 0.05 * Math.sin(t * 9), pitch: -0.04, armL: 0.6, armR: 0.6, outL: 0.25, outR: 0.25 }), "joy")] };
    }
    case "S11":
    case "S12":
    case "S13":
    case "S14": {
      const lean = id === "S11" ? ss(0, 0.6, tau) : 1;
      return {
        earthOnShelf: true,
        actors: [
          kid(sit(KID_SHELF[0], KID_SHELF[1], -Math.PI / 2 + 0.15, { pitch: 0.18 * lean, headPitch: 0.25 * lean + breathe(t, 1), armR: 0.9 * lean, outR: 0.05 }), "curious"),
          dad(base(0.5, -1.05, -Math.PI / 2 + 0.5, SCALE.dad, { headPitch: 0.35, armL: 0.1, armR: 0.1 }), "happy"),
        ],
      };
    }
    case "S15": {
      const lift = popT(tau, 0, 0.75);
      const p = base(DAD_SHELF[0], DAD_SHELF[1], -0.65, SCALE.dad, { pitch: 0.25 * (1 - lift), armR: lerp(0.4, 1.25, lift), outR: 0.05, headPitch: lerp(0.5, 0.3, lift) });
      return { earthOnShelf: false, puff: { p: [STORE.earth[0], STORE.earth[1] - 0.06, STORE.earth[2]], t0: a + 0.12, k: 0.35 }, actors: [dad(p, "curious", { held: heldEarth(SCALE.dad) }), kid(sit(0.55, -0.33, -0.9, { headPitch: -0.3 }), "happy")] };
    }
    case "S16":
    case "S19":
    case "S20": {
      const shock = id === "S20";
      const p = base(DAD_COUNTER[0], DAD_COUNTER[1], Math.PI / 2, SCALE.dad, {
        armR: 1.25, outR: 0.05, headPitch: id === "S19" ? 0.35 : shock ? -0.05 : 0.0, headYaw: id === "S16" ? lerp(0.5, 0.1, ss(0.3, 1.0, tau)) : shock ? 0.35 : 0,
        armL: shock ? lerp(0.1, 1.3, popT(tau, 0, 0.7)) : id === "S16" ? 0.55 + 0.35 * Math.max(0, Math.sin(tau * 5)) : 0.1, outL: shock ? 0.55 : id === "S16" ? 0.45 : 0.05, ant: shock ? lerp(0, 1, popT(tau, 0, 0.7)) : 0,
      });
      return {
        earthOnShelf: false,
        actors: [
          dad(p, shock ? "shock" : "curious", { held: heldEarth(SCALE.dad, id === "S19" ? 0.9 : 0), fx: shock ? sweat(t, a + 0.1, -1) : undefined }),
          seller(t, { pitch: 0.25, headPitch: -0.1 }, "sly"),
        ],
      };
    }
    case "S17":
    case "S18": {
      const lean = id === "S17" ? ss(0, 0.8, tau) : 1;
      return {
        earthOnShelf: false,
        actors: [
          seller(t, id === "S18" ? { pitch: 0.45, headPitch: -0.3, armR: 2.05 + 0.05 * Math.sin(tau * 7), outR: -0.2, armL: 0.4, headYaw: 0.25 } : { pitch: 0.4 * lean, headPitch: -0.25 * lean, armL: 1.0 + 0.08 * Math.sin(tau * 11), armR: 1.0 + 0.08 * Math.sin(tau * 11 + 2), outL: -0.28, outR: -0.28 }, "sly"),
          dad(base(DAD_COUNTER[0], DAD_COUNTER[1], Math.PI / 2, SCALE.dad, { armR: 1.25, outR: 0.05, pitch: 0.08 * lean }), "curious", { held: heldEarth(SCALE.dad) }),
        ],
      };
    }
    case "S21": {
      const down = ss(0, 0.6, tau);
      const placed = tau > 0.75;
      // a step back from the shelf and a smaller bend, so the lens inside the shelf can hold his face (~1 m away)
      const p = base(DAD_SHELF[0] + 0.27, DAD_SHELF[1], -Math.PI / 2, SCALE.dad, { pitch: 0.25 * down, armR: lerp(1.25, 0.95, down), headPitch: 0.3 });
      return { earthOnShelf: placed, puff: { p: [STORE.earth[0], STORE.earth[1] - 0.06, STORE.earth[2]], t0: a + 0.75, k: 0.3 }, actors: [dad(p, "sad", { ...(placed ? {} : { held: heldEarth(SCALE.dad) }), fx: tears(t, [[a - 0.25, 1, 1], [a + 0.55, -1, 2]]) }), kid(sit(0.55, -0.33, -0.9, { headPitch: -0.2 }), "sad")] };
    }
    case "S22":
      return {
        earthOnShelf: true,
        actors: [dad(base(DAD_SHELF[0], DAD_SHELF[1], 0.35, SCALE.dad, { headYaw: 0.28 * Math.sin(tau * 7.5), armL: 1.2, outL: -0.3, armR: lerp(0.2, 2.1, popT(tau, 0, 0.7)), outR: 0.08 * Math.sin(tau * 10), ant: -0.4 }), "sad", { fx: tears(t, [[a - 0.35, 1, 3], [a + 0.15, -1, 4]]) })],
      };
    case "S23":
      return {
        earthOnShelf: false,
        actors: [kid(base(-0.1, -0.45, 0.35, 1, { armL: 1.05, armR: 1.05, outL: -0.18, outR: -0.18, headPitch: 0.18 + breathe(t, 1), sway: 0.05 * Math.sin(t * 3) }), "love", { chest: <Earth p={[0, -0.05, 0.13]} r={EARTH_R} dusty clouds={false} /> })],
      };
    case "S24": {
      const up = popT(tau, 0, 1.0); // <= ~4 rad/s, or 4 blur samples ghost
      const p = base(-0.1, -0.45, 0.35, 1, { armR: lerp(1.0, 2.75, up), outR: 0.05, armL: lerp(1.0, 2.6, up), outL: 0.18, headPitch: -0.35 * up });
      return { earthOnShelf: false, sparkle: heldWorld(p, "R", 1, [0, 0.12, 0]), actors: [kid(p, "love", { held: heldEarth(1) })] };
    }
    case "S25":
    case "S26": {
      const t0 = id === "S25" ? a : a - 1.0;
      return {
        earthOnShelf: false,
        actors: [
          kid(walk(0.4, 1.6, -Math.PI / 2, t, t0, 0.55, 1, { armL: 1.0, armR: 1.0, outL: -0.18, outR: -0.18, headPitch: 0.15 }), "love", { chest: jarAsChest(0.2) }),
          dad(walk(1.15, 2.0, -Math.PI / 2, t, t0, 0.55, SCALE.dad, { headYaw: -0.2 }), "happy"),
        ],
      };
    }
    // ---------------------------------------------------------------- home + jar
    case "S27":
      return { jarEarth: { spin: t * 0.4, lights: 0.25 }, jarGlow: 0.6, actors: [kidHome(t, { pitch: 0.12 }, "happy")] };
    case "S28":
      return { jarEarth: { spin: t * 0.4, lights: 0.5 }, jarGlow: 0.6, actors: [] };
    case "S32":
      return { jarEarth: { spin: t * 0.4, lights: 0.4 }, jarGlow: 0.7, carInJar: true, actors: [kidHome(t, { pitch: 0.15, headYaw: 0.25 * ss(0, 0.5, tau), sway: 0.12 * ss(0, 0.5, tau) }, "curious")] };
    case "S33":
    case "S34":
    case "S35": {
      const chin = id === "S34";
      return {
        jarEarth: { spin: t * 0.3, lights: 0.8 }, jarGlow: 1,
        actors: [kidHome(t, chin ? { pitch: 0.22, armL: 2.1, armR: 2.1, outL: -0.22, outR: -0.22, headPitch: 0.1 } : { pitch: 0.08 }, "happy")],
      };
    }
    case "S36":
      return { jarEarth: { spin: 2.2 + t * 0.2, lights: 0.6 + 0.4 * (0.5 + 0.5 * Math.sin(t * 6)) }, jarGlow: 1, actors: [] };
    case "S38":
      return { jarEarth: { spin: 2.4 + t * 0.15, lights: 1 }, jarGlow: 1.2, message: ss(0, 0.8, tau), actors: [] };
    case "S39":
      return { jarEarth: { spin: 2.4 + t * 0.15, lights: 1 }, jarGlow: 1.2, message: 1, actors: [kidHome(t, { pitch: -0.05 * popT(tau, 0, 0.7), headPitch: -0.05, ant: lerp(0, 1, popT(tau, 0, 0.7)), armL: lerp(0.1, 0.9, popT(tau, 0, 0.7)), armR: lerp(0.1, 0.9, popT(tau, 0, 0.7)), outL: 0.4, outR: 0.4 }, "shock")] };
    case "S40":
      return { jarEarth: { spin: 2.4 + t * 0.15, lights: 1 }, jarGlow: 1.2, message: 1, actors: [kidHome(t, { pitch: 0.1 }, tau < 0.3 ? "curious" : "joy")] };
    case "S41": {
      const up = popT(tau, 0, 1.0);
      return {
        jarEarth: { spin: 2.4 + t * 0.15, lights: 1 }, jarGlow: 1.2,
        actors: [kidHome(t, { pitch: 0.12, armR: lerp(0.3, 2.05, up), outR: 0.1 }, "joy", { held: { side: "R", node: <group position={[0, 0.1, 0.02]}><Card text="HI!" /></group> } })],
      };
    }
    case "S48":
      return {
        jarEarth: { spin: 2.4 + t * 0.15, lights: 1, hi: true }, jarGlow: 1.3,
        actors: [{ ...kidHome(t, { pitch: 0.3, headPitch: 0.15, armL: 1.6, armR: 1.4, outL: -0.1, outR: 0.2 }, "love"), pose: { ...kidHome(t, {}, "love").pose, x: ROOM.kid[0] + 0.06, z: ROOM.kid[2] - 0.04, pitch: 0.3, headPitch: 0.15, armL: 1.6, armR: 1.4, outL: -0.1, outR: 0.2, headYaw: -0.2 } }],
      };
    case "S49":
      return { jarEarth: { spin: 2.4 + t * 0.15, lights: 1, hi: true }, jarGlow: 1.3, actors: [] };
    // ---------------------------------------------------------------- down on Earth
    case "S29":
      return { houses: tau, actors: [human("hA", KID_A, base(0.25, 2.7, -0.5, 1, { headPitch: -0.2, headYaw: -0.4 + 0.5 * ss(0.2, 0.9, tau), armL: 0.5, armR: 0.5, outL: 0.3, outR: 0.3 }, GRASS_SINK), "joy")] };
    case "S30": {
      const tug = Math.sin(tau * 7) * 0.08;
      return {
        crumbs: true,
        actors: [
          human("hA", KID_A, base(-0.48 + tug, 1.5, Math.PI / 2 - 0.45, 1, { pitch: -0.14, armL: 1.45, armR: 1.45, outL: -0.12, outR: -0.12 }, GRASS_SINK), "sly", { held: { side: "R", node: <group position={[0.08, 0.02, 0.22]} rotation={[0, Math.PI / 2, 0]}><Sandwich squash={0.3 + 0.2 * Math.sin(tau * 7)} pull={Math.sin(tau * 7)} /></group> } }),
          human("hB", KID_B, base(0.48 + tug, 1.5, -Math.PI / 2 + 0.45, 1, { pitch: -0.14, armL: 1.45, armR: 1.45, outL: -0.12, outR: -0.12 }, GRASS_SINK), "shock"),
        ],
      };
    }
    case "S31": {
      const c = carAt(a, t);
      return {
        car: c,
        actors: [human("hA", KID_A, base(-1.3, 2.6, 0.6, 1, { headPitch: -0.6 * ss(0, 0.6, tau), armL: 0.6, armR: 2.5, outR: 0.2 }, GRASS_SINK), "shock"), human("hB", KID_B, base(2.3, 1.9, -1.2, 1, { headPitch: -0.6 * ss(0.1, 0.7, tau), armL: 2.6, armR: 2.6, outL: 0.4, outR: 0.4 }, GRASS_SINK), "joy")],
      };
    }
    case "S37":
      return {
        night: true,
        actors: [
          human("hA", KID_A, base(-0.85, 1.6, 0.25, 1, { armR: 2.9, outR: 0.05, headPitch: -0.5 }, GRASS_SINK), "happy", { held: { side: "R", node: <group rotation={[-0.1, 0, 0]}><Flashlight /></group> } }),
          human("hB", KID_B, base(0.05, 1.95, 0, 1, { armR: 2.95, outR: 0.0, armL: 2.6, outL: 0.3, headPitch: -0.5 }, GRASS_SINK), "joy", { held: { side: "R", node: <Flashlight /> } }),
          human("hC", { ...KID_A, shirt: "#7fe3b8", hair: "#2b1912", print: "heart", accent: "#ff5aa0" }, base(0.9, 1.5, -0.3, 1, { armR: 2.85, outR: 0.1, headPitch: -0.45 }, GRASS_SINK), "happy", { held: { side: "R", node: <group rotation={[0.1, 0, 0]}><Flashlight /></group> } }),
        ],
      };
    // ---------------------------------------------------------------- the store, the next day
    case "S42":
    case "S43":
      return { earthOnShelf: false, tag99: ["99¢"], catalog: { price: ["99¢"] }, actors: [seller(t, { pitch: 0.28, headPitch: 0.45, armL: 0.7, armR: 0.7 + 0.15 * Math.sin(tau * 5), outL: 0.1, outR: 0.1 }, "curious")] };
    case "S44":
      return { earthOnShelf: false, tag99: ["99¢"], catalog: { price: ["99¢"] }, actors: [{ ...seller(t, { pitch: -0.05, headPitch: -0.1, armL: lerp(0.4, 1.6, popT(tau, 0, 0.7)), armR: lerp(0.4, 1.6, popT(tau, 0, 0.7)), outL: 0.6, outR: 0.6, ant: lerp(0, 1, popT(tau, 0.05, 0.65)) }, "shock"), fx: sweat(t, a + 0.15, 1) }] };
    case "S45": {
      const flipped = tau > 0.35;
      return { earthOnShelf: false, tag99: flipped ? ["PRICELESS"] : ["99¢"], catalog: { price: ["99¢"], strike: 0 }, actors: [] };
    }
    case "S46": {
      const crowd: Actor[] = CROWD.map((look, i) => {
        const x = -4.6 + (i % 4) * 0.75 + 0.2 * hash(i * 3.3), z = 0.9 + Math.floor(i / 4) * 0.9 + (i % 2) * 0.35;
        const jump = Math.max(0, Math.sin((tau + hash(i)) * 9)) * 0.08;
        const p = base(x, z, Math.PI / 2 - 0.15 + 0.3 * hash(i * 5.1), SCALE.crowd, { armR: 2.2 + 0.2 * Math.sin(tau * 8 + i), outR: 0.1, headPitch: -0.25, ant: 0.8 });
        return { key: `c${i}`, look, pose: { ...p, y: p.y + jump }, emotion: (i % 3 === 0 ? "love" : "joy") as Emotion, s: SCALE.crowd, blinkSeed: 10 + i };
      });
      return { earthOnShelf: false, tag99: ["PRICELESS"], poster: true, catalog: { price: ["99¢"], strike: 0 }, actors: [...crowd, seller(t, { headPitch: -0.1, armL: 1.5, armR: 1.5, outL: 0.5, outR: 0.5, ant: 1 }, "shock")] };
    }
    case "S47":
      return { actors: [] };
  }
  return { actors: [] };
};

// background customers in the store (not in the crowd shot, not in the next-day inserts)
const SET_OF: Record<string, string> = Object.fromEntries(PLAN.map((x) => [x.id, x.set]));
const customers = (t: number): Actor[] => {
  const mk = (k: string, look: Look, x: number, z: number, to: [number, number], o: Partial<Pose>): Actor => ({
    key: k, look, s: SCALE.crowd, blinkSeed: 20 + k.length, emotion: "happy" as Emotion,
    pose: base(x, z, yawTo([x, z], to), SCALE.crowd, o),
  });
  return [
    mk("cu1", CROWD[0], -3.4, -2.2, [STORE.giant[0], STORE.giant[2]], { armR: 1.9 + 0.1 * Math.sin(t * 2), outR: 0.1, headPitch: -0.35 }),
    mk("cu2", CROWD[1], 3.45, -2.25, [STORE.saturn[0], STORE.saturn[2]], { armL: 0.4, armR: 0.4, outL: -0.2, outR: -0.2, headPitch: -0.15 }),
    mk("cu3", CROWD[3], -4.7, -1.5, [-6, -1.5], { armR: 1.2 + 0.2 * Math.sin(t * 1.5), headPitch: 0.1 }),
  ];
};
const withExtras = (id: string, a: number, t: number): Stage => {
  const st = stageRaw(id, a, t);
  const set = SET_OF[id];
  const extra = (set === "store" || set === "store2") && id !== "S46" ? customers(t) : [];
  return { ...st, actors: [...st.actors, ...extra].map((x) => alive(x, t)) };
};
// Secondary motion (premium pass): antennae, the dad's bag and the kid's jetpack trail every move of the body, overshoot
// and settle, as damped springs (engine/core/physics.ts). The drivers are sampled from the actor's OWN pose function
// over the last SEC_WIN s at 60 Hz (linear in between) and the springs are stepped at 240 Hz from rest: frame N is the
// same in every render. Drivers: fore-aft = lean + head nod + travel along the facing + vertical motion; sideways =
// sway + head turn + body turn + travel across; bag = travel + bounce.
const SEC_WIN = 1.4, SEC_HZ = 60;
type Drv = [number, number, number, number];
const driversOf = (p: Pose): Drv => {
  const fwd = p.x * Math.sin(p.yaw) + p.z * Math.cos(p.yaw), side = p.x * Math.cos(p.yaw) - p.z * Math.sin(p.yaw);
  const up = p.y + (p.bob ?? 0);
  return [
    p.pitch + p.headPitch + 2.2 * fwd + 3.0 * up,
    (p.sway ?? 0) + 0.8 * p.headYaw + 0.6 * p.yaw + 2.2 * side,
    2.4 * fwd + 6.0 * up + 0.8 * p.pitch,
    p.pitch + 4.0 * up,
  ];
};
const secondary = (id: string, a: number, t: number, actors: Actor[]): Actor[] => {
  const n = Math.round(SEC_WIN * SEC_HZ);
  const t0 = t - SEC_WIN;
  const tracks = new Map<string, Drv[]>();
  for (let k = 0; k <= n; k++) {
    const st = k === n ? { actors } : withExtras(id, a, t0 + k / SEC_HZ);
    for (const x of st.actors) {
      let tr = tracks.get(x.key);
      if (!tr) {
        tr = [];
        tracks.set(x.key, tr);
      }
      tr[k] = driversOf(x.pose);
    }
  }
  return actors.map((x) => {
    const tr = tracks.get(x.key)!;
    const now = tr[n];
    const at = (j: number) => (tt: number) => {
      const f = Math.min(n, Math.max(0, (tt - t0) * SEC_HZ));
      const i = Math.min(n - 1, Math.floor(f));
      const A = tr[i] ?? now, B = tr[i + 1] ?? now;
      return A[j] + (B[j] - A[j]) * (f - i);
    };
    const lagOf = (j: number, hz: number, z: number) => spring(at(j), t, hz, z, SEC_WIN)[0] - now[j];
    const c = (v: number, m: number) => Math.max(-m, Math.min(m, v));
    return {
      ...x,
      pose: {
        ...x.pose,
        antSec: [c(-lagOf(0, 2.4, 0.16) * 1.1, 0.7), c(-lagOf(1, 2.4, 0.16) * 1.1, 0.7)] as [number, number],
        bagSec: c(-lagOf(2, 1.6, 0.14) * 0.9, 0.6),
        packSec: c(-lagOf(3, 3.0, 0.25) * 0.5, 0.3),
      },
    };
  });
};
export const stageOf = (id: string, a: number, t: number): Stage => {
  const st = withExtras(id, a, t);
  return { ...st, actors: secondary(id, a, t, st.actors) };
};
