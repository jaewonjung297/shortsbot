// Numeric checks for "The Planet That Talks Back" (numbers before eyes, like the skill's framing_check.ts): every 2nd
// output frame, evaluate the real staging (cast.tsx) and lenses (shots.ts) and test
//   LENS_IN   - the lens inside a character or a piece of furniture
//   BLOCKED   - the line from the lens to the subject passes through another character or object
//   OVERLAP   - two characters pass through each other, or a character stands inside furniture
//   FRAMING   - the subject (and, in face shots, the whole face) leaves the frame (2 % margin)
// Characters are vertical cylinders (radius 0.36 x scale, feet to hat/antennae); furniture is boxes / cylinders from
// layout.ts. Run: bash tools/planet_checks.sh  (exit 1 if anything FAILs).
import * as THREE from "three";
import { faceH, facePoint, stageOf } from "../src/planet/cast";
import type { Actor } from "../src/planet/cast";
import { STORE, ROOM } from "../src/planet/layout";
import { camAt, LENS, PLAN_SHOTS } from "../src/planet/shots";
import type { V3 } from "../src/blocky/motion";

const FPS = 30;
const W = 1080, H = 1920;
type Cyl = { name: string; x: number; z: number; r: number; y0: number; y1: number };
type Box = { name: string; x0: number; x1: number; z0: number; z1: number; y0: number; y1: number };

const STORE_BOXES: Box[] = [
  { name: "left shelf", x0: -1.5, x1: -1.0, z0: -2.6, z1: 0, y0: 0, y1: 1.92 },
  { name: "right shelf", x0: 1.0, x1: 1.5, z0: -2.6, z1: 0, y0: 0, y1: 1.92 },
  { name: "counter", x0: STORE.counter[0] - 0.35, x1: STORE.counter[0] + 0.35, z0: STORE.counter[2] - 1.0, z1: STORE.counter[2] + 1.0, y0: 0, y1: 0.98 },
  { name: "seller box", x0: STORE.counter[0] + 0.25, x1: STORE.counter[0] + 0.95, z0: STORE.counter[2] - 0.35, z1: STORE.counter[2] + 0.35, y0: 0, y1: 0.42 },
];
const STORE_CYLS: Cyl[] = [
  { name: "island", x: STORE.island[0], z: STORE.island[2], r: 0.42, y0: 0, y1: 1.0 },
  { name: "giant podium+planet", x: STORE.giant[0], z: STORE.giant[2], r: 0.8, y0: 0, y1: 2.25 },
  { name: "saturn podium+planet", x: STORE.saturn[0], z: STORE.saturn[2], r: 0.6, y0: 0, y1: 1.75 },
  { name: "jupiter podium+planet", x: STORE.jupiter[0], z: STORE.jupiter[2], r: 0.6, y0: 0, y1: 1.72 },
];
const ROOM_BOXES: Box[] = [
  { name: "sill", x0: -0.8, x1: 0.8, z0: -1.84, z1: -1.5, y0: 0, y1: 0.89 },
  { name: "bed", x0: -2.35, x1: -1.35, z0: -1.65, z1: 0.4, y0: 0, y1: 0.67 },
  { name: "desk", x0: 1.6, x1: 2.3, z0: 0.35, z1: 0.85, y0: 0, y1: 1.3 },
];
const ROOM_CYLS: Cyl[] = [{ name: "jar", x: ROOM.jar[0], z: ROOM.jar[2], r: 0.16, y0: ROOM.jar[1], y1: ROOM.jar[1] + 0.42 }];
/** lenses that sit inside furniture on purpose (frame-in-frame) */
const LENS_INSIDE_OK = new Set(["S05", "S11", "S21"]);
/** wide shots: the subject is an area, people in front of it are fine */
const WIDE = new Set(["S03", "S13", "S25", "S29", "S33", "S37", "S46", "S47"]);
/** inserts / object shots: no face is expected */
const NO_FACE = new Set(["S07", "S09", "S12", "S14", "S19", "S28", "S29", "S30", "S31", "S36", "S37", "S38", "S43", "S45", "S47", "S49", "S03", "S13", "S25", "S33", "S46"]);

const actorCyl = (a: Actor): Cyl => {
  const p = a.pose;
  const sitting = p.y < 0.35 * a.s;
  const fwd = sitting ? 0.22 : 0;
  return { name: a.key, x: p.x + Math.sin(p.yaw) * fwd, z: p.z + Math.cos(p.yaw) * fwd, r: (sitting ? 0.42 : 0.36) * a.s, y0: p.y - 0.55 * a.s, y1: p.y - 0.55 * a.s + faceH(a.s) + 0.32 * a.s };
};
const inCyl = (q: V3, c: Cyl, pad = 0) => Math.hypot(q[0] - c.x, q[2] - c.z) < c.r + pad && q[1] > c.y0 - pad && q[1] < c.y1 + pad;
const inBox = (q: V3, b: Box, pad = 0) => q[0] > b.x0 - pad && q[0] < b.x1 + pad && q[2] > b.z0 - pad && q[2] < b.z1 + pad && q[1] > b.y0 - pad && q[1] < b.y1 + pad;

const camera = new THREE.PerspectiveCamera(50, W / H, 0.02, 600);
const project = (cam: ReturnType<typeof camAt>, q: V3) => {
  camera.fov = cam.fov;
  camera.position.set(...cam.pos);
  const dir = new THREE.Vector3(...cam.look).sub(camera.position).normalize();
  camera.up.copy(new THREE.Vector3(0, 1, 0).applyAxisAngle(dir, ((cam.roll ?? 0) * Math.PI) / 180));
  camera.lookAt(...cam.look);
  camera.updateProjectionMatrix();
  camera.updateMatrixWorld();
  const v = new THREE.Vector3(...q).project(camera);
  const behind = new THREE.Vector3(...q).sub(camera.position).dot(dir) < 0;
  return { x: (v.x + 1) / 2, y: (1 - v.y) / 2, behind };
};

type Issue = { shot: string; kind: string; what: string; frames: number[] };
const issues = new Map<string, Issue>();
const add = (shot: string, kind: string, what: string, f: number) => {
  const k = `${shot}|${kind}|${what}`;
  const it = issues.get(k) ?? { shot, kind, what, frames: [] };
  it.frames.push(f);
  issues.set(k, it);
};

const last = PLAN_SHOTS[PLAN_SHOTS.length - 1].end;
for (let f = 0; f < Math.round(last * FPS); f += 2) {
  const t = f / FPS;
  let i = 0;
  for (let k = 0; k < PLAN_SHOTS.length; k++) if (f >= Math.round(PLAN_SHOTS[k].t * FPS)) i = k;
  const s = PLAN_SHOTS[i];
  const st = stageOf(s.id, s.t, t);
  const cam = camAt(i, t, st);
  const lens = LENS[s.id];
  const subj: V3 = typeof lens.subj === "function" ? lens.subj(st, t) : lens.subj;
  const set = s.set;
  const boxes = set === "store" || set === "store2" ? STORE_BOXES : set === "home" || set === "jar" ? ROOM_BOXES : [];
  const cyls = set === "store" || set === "store2" ? STORE_CYLS : set === "home" || set === "jar" ? ROOM_CYLS : [];
  const actors = st.actors.map((a) => ({ a, c: actorCyl(a), face: facePoint(a.pose, a.s) }));
  // the subject's own actor: the one whose face (or body) is nearest the subject point
  const own = actors.filter((x) => Math.hypot(x.face[0] - subj[0], x.face[2] - subj[2]) < 0.45 && subj[1] > x.c.y0 - 0.2 && subj[1] < x.c.y1 + 0.3).map((x) => x.a.key);

  // LENS_IN
  for (const x of actors) if (inCyl(cam.pos, x.c, 0.04)) add(s.id, "LENS_IN", x.a.key, f);
  if (!LENS_INSIDE_OK.has(s.id)) {
    for (const b of boxes) if (inBox(cam.pos, b, 0.02)) add(s.id, "LENS_IN", b.name, f);
    for (const c of cyls) if (inCyl(cam.pos, c, 0.02)) add(s.id, "LENS_IN", c.name, f);
  }
  // BLOCKED: sample the lens -> subject segment, stop 0.22 m short of the subject
  const d = Math.hypot(subj[0] - cam.pos[0], subj[1] - cam.pos[1], subj[2] - cam.pos[2]);
  const n = Math.max(2, Math.ceil(d / 0.02));
  const hit = new Set<string>();
  for (let k = 1; k < n; k++) {
    const u = k / n;
    if (d * (1 - u) < 0.22) break;
    const q: V3 = [cam.pos[0] + (subj[0] - cam.pos[0]) * u, cam.pos[1] + (subj[1] - cam.pos[1]) * u, cam.pos[2] + (subj[2] - cam.pos[2]) * u];
    for (const x of actors) if (!own.includes(x.a.key) && !WIDE.has(s.id) && inCyl(q, x.c, -0.04)) hit.add(x.a.key);
    if (!LENS_INSIDE_OK.has(s.id)) {
      for (const b of boxes) if (inBox(q, b, -0.02)) hit.add(b.name);
      for (const c of cyls) if (inCyl(q, c, -0.02) && Math.hypot(subj[0] - c.x, subj[2] - c.z) > c.r + 0.05) hit.add(c.name);
    }
  }
  for (const h of hit) add(s.id, "BLOCKED", h, f);
  // OVERLAP: actor vs actor, actor vs furniture
  for (let p = 0; p < actors.length; p++) {
    for (let q = p + 1; q < actors.length; q++) {
      const A = actors[p].c, B = actors[q].c;
      if (Math.hypot(A.x - B.x, A.z - B.z) < (A.r + B.r) * 0.72) add(s.id, "OVERLAP", `${A.name} x ${B.name}`, f);
    }
    const A = actors[p].c;
    for (const b of boxes) {
      if (b.name === "seller box" && actors[p].a.key === "seller") continue;
      const cx = Math.min(Math.max(A.x, b.x0), b.x1), cz = Math.min(Math.max(A.z, b.z0), b.z1);
      if (Math.hypot(A.x - cx, A.z - cz) < A.r * 0.55) add(s.id, "OVERLAP", `${A.name} x ${b.name}`, f);
    }
    for (const c of cyls) if (Math.hypot(A.x - c.x, A.z - c.z) < (A.r + c.r) * 0.75) add(s.id, "OVERLAP", `${A.name} x ${c.name}`, f);
  }
  // FRAMING: the subject point, and for face shots the whole head
  const ps = project(cam, subj);
  if (ps.behind || ps.x < 0.02 || ps.x > 0.98 || ps.y < 0.02 || ps.y > 0.98) add(s.id, "FRAMING", "subject out of frame", f);
  for (const x of actors) {
    if (!own.includes(x.a.key) || NO_FACE.has(s.id)) continue;
    // FACING: the face must turn toward the lens (no back or side of the head in a face shot)
    const fy = x.a.pose.yaw + x.a.pose.headYaw;
    const tx = cam.pos[0] - x.face[0], tz = cam.pos[2] - x.face[2], tl = Math.hypot(tx, tz) || 1;
    if ((Math.sin(fy) * tx + Math.cos(fy) * tz) / tl < 0.3) add(s.id, "FACING", `${x.a.key}'s face turned away`, f);
    const hs = 0.17 * x.a.s;
    for (const q of [[x.face[0], x.face[1] + hs, x.face[2]], [x.face[0], x.face[1] - hs, x.face[2]]] as V3[]) {
      const pq = project(cam, q);
      if (pq.behind || pq.y < 0.0 || pq.y > 1.0) add(s.id, "FRAMING", `${x.a.key}'s head cut`, f);
    }
  }
}

const rows = [...issues.values()].filter((x) => x.frames.length >= 2); // >= 2 samples = at least ~2 frames
rows.sort((a, b) => a.frames[0] - b.frames[0]);
for (const r of rows) {
  const span = `${r.frames[0]}-${r.frames[r.frames.length - 1]}`;
  console.log(`FAIL ${r.shot.padEnd(4)} ${r.kind.padEnd(8)} ${r.what.padEnd(30)} frames ${span} (${r.frames.length} samples)`);
}
const shots = new Set(rows.map((r) => r.shot));
const sampled = Math.ceil(Math.round(last * FPS) / 2);
console.log(`checked ${PLAN_SHOTS.length} shots on ${sampled} sampled frames (every 2nd frame)`);
console.log(`${rows.length} issues in ${shots.size} shots${shots.size ? ": " + [...shots].join(" ") : ""}`);
if (rows.length) process.exitCode = 1;
