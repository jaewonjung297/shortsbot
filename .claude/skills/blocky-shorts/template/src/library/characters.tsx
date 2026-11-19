// Reusable characters of the blocky family (from "The Planet That Talks Back"): the alien looks (DAD with hat + bag, KID
// with big eyes + goggles + twin-tank jetpack + glowing sneakers, KID_PJ, SELLER small with apron + tiny glasses, a CROWD of 7), the template's humans
// (KID_A, KID_B in blocky/Blocky.tsx), and the motion kit every Short needs:
//   base / walk / sit   pose builders (pure functions of t)
//   alive(actor, t)     the idle layer: breathing, sway, head + arm drift, antenna wobble (never stand still)
//   pop / popT          anticipation + overshoot for big moves (keep >= 0.7 s for a big arm move: <= ~4 rad/s)
//   heldWorld / facePoint  where a held prop / a face is in the world (aim lenses at them, check framing)
//   secondaryMotion     (1.2) baked spring physics for antennae, bags, jetpacks
//   tears / sweat       (1.2) real drops for Actor.fx (form, run with a wet streak, drip)
// Stage a story with these (see examples/planet-short/src/planet/cast.tsx).
import React from "react";
import { spring } from "../engine/core/physics";
import { Tear } from "./fx";
import * as THREE from "three";
import type { Held, Look } from "../blocky/Blocky";
import { coneMatrix, hash, L, legDrop, SPEC, U } from "../blocky/motion";
import type { Emotion, Pose, V3 } from "../blocky/motion";

/** fx = children in the actor's head space (tears, sweat: see tears() / sweat() below; pass to <Blocky fx>) */
export type Actor = { key: string; look: Look; pose: Pose; emotion: Emotion; s: number; held?: Held; chest?: React.ReactNode; blinkSeed: number; fx?: React.ReactNode };

// ------------------------------------------------------------------ looks
export const DAD: Look = { skin: "#6fcf5a", shirt: "#2a7de1", pants: "#3b3f58", shoes: "#f4f4f2", sole: "#ff7a1a", hair: "#5fb84a", hairStyle: "antennae", accent: "#ffd23a", print: "ring", cheeks: "none", belt: "#2a2a3a", cuffs: "#ffd23a", kicks: "#ff7a1a", acc: { hat: ["#3a3f58", "#ffd23a"], bag: "#c87a3a", badge: "#ffd23a", wrist: "#5fe8ff" } };
export const KID: Look = { skin: "#9be36e", shirt: "#ff8a1f", pants: "#2f63c9", shoes: "#ffffff", sole: "#2fd0bd", hair: "#86d05c", hairStyle: "antennae", accent: "#ff4fa3", print: "star", cheeks: "blush", eyeScale: 1.38, belt: "#2a3a8a", cuffs: "#ffd23a", kicks: "#2fd0bd", acc: { goggles: ["#2a3a8a", "#5fe8ff"], jetpack: ["#dfe4f0", "#ff4fa3"], badge: "#ffd23a" } };
export const KID_PJ: Look = { ...KID, shirt: "#5fb8ff", pants: "#3a5ad0", print: "star", accent: "#ffd23a", belt: undefined, cuffs: "#ffffff", kicks: undefined, acc: { goggles: ["#2a3a8a", "#5fe8ff"] } };
export const SELLER: Look = { skin: "#b48cf0", shirt: "#d6283c", pants: "#2a2a3a", shoes: "#1a1a22", sole: "#ffd23a", hair: "#a07ae0", hairStyle: "antenna1", accent: "#7dffcf", print: "bow", cheeks: "none", cuffs: "#ffd23a", acc: { apron: "#2fd0bd", glasses: "#ffd23a", headset: "#2a2a3a" } };
export const CROWD: Look[] = ([
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
export const SINK = 0.003; // hard floors: soles barely pressed in
export const GRASS_SINK = 0.012;
/** face (head centre) height above the feet for a standing character of scale s */
export const faceH = (s: number) => (L + (SPEC.torso.h + SPEC.head.gap + SPEC.head.h / 2) * U) * s;

// ------------------------------------------------------------------ pose builders
export const base = (x: number, z: number, yaw: number, s: number, o: Partial<Pose> = {}, sink = SINK): Pose => ({
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
export const sit = (x: number, z: number, yaw: number, o: Partial<Pose> = {}): Pose => {
  const pitch = o.pitch ?? 0;
  return { ...base(x, z, yaw, 1), y: (SPEC.shoe.d * U) / 2 + 0.004, legL: Math.PI / 2 + pitch, legR: Math.PI / 2 + pitch, armL: 0.5, armR: 0.5, outL: 0.12, outR: 0.12, ...o };
};
export const breathe = (t: number, seed: number) => 0.012 * Math.sin(t * 2.2 + seed);
/** anticipation + overshoot for big moves: a small dip back, then a fast move that overshoots and settles (0 -> 1) */
export const pop = (u: number) => {
  if (u <= 0) return 0;
  if (u < 0.18) return -0.14 * Math.sin((Math.PI * u) / 0.18);
  const x = Math.min(1, (u - 0.18) / 0.82) - 1;
  return 1 + 2.6 * x * x * x + 1.6 * x * x;
};
export const popT = (tau: number, t0: number, dur: number) => pop((tau - t0) / dur);
/** the idle layer on every actor: breathing, a slow sway, a drifting head, arms that never freeze, wobbling antennae */
export const alive = (a: Actor, t: number): Actor => {
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
export const yawTo = (from: [number, number], to: [number, number]) => Math.atan2(to[0] - from[0], to[1] - from[1]);

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


// ------------------------------------------------------------------ premium pass (1.2): secondary motion, tears, sweat
/**
 * Secondary motion: antennae, a hanging bag and a jetpack trail every move of the body, overshoot and settle, as damped
 * springs. sample(tau) must return the stage's actors at time tau (your pure staging function, alive() applied);
 * they are sampled at 60 Hz over the last `win` s and each spring is re-simulated from rest at 240 Hz, so frame N is
 * the same in every render. Returns the actors at t with pose.antSec / bagSec / packSec filled in.
 */
export const secondaryMotion = (sample: (tau: number) => Actor[], t: number, now: Actor[], win = 1.4, hz = 60): Actor[] => {
  type Drv = [number, number, number, number];
  const driversOf = (p: Pose): Drv => {
    const fwd = p.x * Math.sin(p.yaw) + p.z * Math.cos(p.yaw), side = p.x * Math.cos(p.yaw) - p.z * Math.sin(p.yaw);
    const up = p.y + (p.bob ?? 0);
    return [p.pitch + p.headPitch + 2.2 * fwd + 3.0 * up, (p.sway ?? 0) + 0.8 * p.headYaw + 0.6 * p.yaw + 2.2 * side, 2.4 * fwd + 6.0 * up + 0.8 * p.pitch, p.pitch + 4.0 * up];
  };
  const n = Math.round(win * hz), t0 = t - win;
  const tracks = new Map<string, Drv[]>();
  for (let k = 0; k <= n; k++) {
    const actors = k === n ? now : sample(t0 + k / hz);
    for (const x of actors) {
      const tr = tracks.get(x.key) ?? [];
      tr[k] = driversOf(x.pose);
      tracks.set(x.key, tr);
    }
  }
  const c = (v: number, m: number) => Math.max(-m, Math.min(m, v));
  return now.map((x) => {
    const tr = tracks.get(x.key)!;
    const cur = tr[n];
    const at = (j: number) => (tt: number) => {
      const f = Math.min(n, Math.max(0, (tt - t0) * hz));
      const i = Math.min(n - 1, Math.floor(f));
      const A = tr[i] ?? cur, B = tr[i + 1] ?? cur;
      return A[j] + (B[j] - A[j]) * (f - i);
    };
    const lagOf = (j: number, f: number, z: number) => spring(at(j), t, f, z, win)[0] - cur[j];
    return { ...x, pose: { ...x.pose, antSec: [c(-lagOf(0, 2.4, 0.16) * 1.1, 0.7), c(-lagOf(1, 2.4, 0.16) * 1.1, 0.7)] as [number, number], bagSec: c(-lagOf(2, 1.6, 0.14) * 0.9, 0.6), packSec: c(-lagOf(3, 3.0, 0.25) * 0.5, 0.3) } };
  });
};
const FZ = (SPEC.head.d * U) / 2 + 0.0045; // the face decal plane (head space)
const CHIN = -((SPEC.head.h - 2 * SPEC.head.r) * U) / 2;
const EYE_Y = (0.05 - 0.15 * 0.94) * U; // the lower lid of a sad eye (eyeScale 1)
/** real tears for Actor.fx: each = [start time (global s), eye side -1 / 1, seed]; start one before the cut */
export const tears = (t: number, list: [number, number, number][]) => (
  <>
    {list.map(([t0, side, seed], i) => (
      <Tear key={i} tau={t - t0} eye={[side * 0.21 * U + side * 0.012, EYE_Y - 0.002]} fz={FZ} chin={CHIN} r={0.016} seed={seed} />
    ))}
  </>
);
/** a sweat drop at the temple (shock) for Actor.fx */
export const sweat = (t: number, t0: number, side = 1) => <Tear tau={t - t0} eye={[side * 0.4 * U, 0.3 * U]} fz={FZ} chin={CHIN} r={0.012} seed={7} />;
