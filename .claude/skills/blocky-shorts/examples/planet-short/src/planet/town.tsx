// Earth, premium pass: the living town around the template suburb (blocky/World.tsx). Everything moves only as a pure
// function of t: one shared wind uniform (WIND.value = t, set by the set every frame) drives grass blades and leaves in
// their vertex shaders; cars drive along the road at constant speeds; the skyline's windows are a fixed pattern.
//   GrassField  - thousands of instanced blades (tapered, two-tone, swaying, rooted in the lawn)
//   LeafCanopy  - a tree crown of instanced leaf cards (alpha-cut leaf texture) around a dark core, rustling
//   ToyCar      - a generic little car (no brand): clear-coated paint, glass, tyres with rims, lights
//   Skyline     - a far city: towers with lit windows behind the hills (the humans "built cities")
//   houseGlass  - window glass that reflects the sky, with a warm lit room behind it
import React from "react";
import * as THREE from "three";
import { geoOf, plastic, rbox } from "../blocky/mat";
import type { V3 } from "../blocky/motion";
import { canvasTexture } from "../blocky/mat";
import { h01 } from "../engine/core/physics";
import { leafSet, metalSet, pbr } from "../engine/mat/pbr";

export const WIND = { value: 0 };

/** a standard material whose vertices sway in the wind: weight = local height (blades) or 1 (leaves) */
const swayCache = new Map<string, THREE.MeshStandardMaterial>();
const sway = (key: string, make: () => THREE.MeshStandardMaterial, amp: number, byHeight: boolean) => {
  let m = swayCache.get(key);
  if (!m) {
    m = make();
    m.onBeforeCompile = (sh) => {
      sh.uniforms.uWind = WIND;
      sh.vertexShader = sh.vertexShader
        .replace("#include <common>", "#include <common>\nuniform float uWind;")
        .replace(
          "#include <begin_vertex>",
          `#include <begin_vertex>
          vec3 ip = vec3(instanceMatrix[3][0], instanceMatrix[3][1], instanceMatrix[3][2]);
          float wgt = ${byHeight ? "clamp(position.y, 0.0, 1.0) * clamp(position.y, 0.0, 1.0)" : "1.0"};
          float ph = uWind * 1.7 + ip.x * 0.9 + ip.z * 0.6;
          float gust = 0.6 + 0.4 * sin(uWind * 0.45 + ip.x * 0.15);
          transformed.x += ${amp.toFixed(3)} * wgt * gust * (sin(ph) + 0.35 * sin(ph * 2.7 + 1.3));
          transformed.z += ${(amp * 0.6).toFixed(3)} * wgt * gust * sin(ph * 1.3 + 0.7);`,
        );
    };
    m.customProgramCacheKey = () => key;
    swayCache.set(key, m);
  }
  return m;
};

// ------------------------------------------------------------------ grass blades
const bladeGeo = () =>
  geoOf("blade", () => {
    // a tapered, slightly bent blade 1 m tall (scaled per instance), colour darker at the root
    const g = new THREE.BufferGeometry();
    const P = [-0.5, 0, 0, 0.5, 0, 0, -0.32, 0.5, 0.04, 0.32, 0.5, 0.04, 0, 1, 0.12];
    const C = [0.45, 0.5, 0.45, 0.45, 0.5, 0.45, 0.8, 0.85, 0.8, 0.8, 0.85, 0.8, 1, 1, 0.95];
    g.setAttribute("position", new THREE.Float32BufferAttribute(P, 3));
    g.setAttribute("color", new THREE.Float32BufferAttribute(C, 3));
    g.setIndex([0, 1, 2, 1, 3, 2, 2, 3, 4]);
    g.computeVertexNormals();
    return g;
  });
const grassFields = new Map<string, THREE.InstancedMesh>();
/** blades over the rectangle [x0,x1] x [z0,z1] (avoid: circles [x, z, r] kept clear, e.g. under feet) */
export const GrassField: React.FC<{ x0: number; x1: number; z0: number; z1: number; n: number; seed?: number; h?: [number, number] }> = ({ x0, x1, z0, z1, n, seed = 1, h = [0.05, 0.13] }) => {
  const key = `${x0}|${x1}|${z0}|${z1}|${n}|${seed}`;
  let mesh = grassFields.get(key);
  if (!mesh) {
    const mat = sway("grassBlade", () => new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.55, side: THREE.DoubleSide }), 0.025, true);
    mesh = new THREE.InstancedMesh(bladeGeo(), mat, n);
    const M = new THREE.Matrix4(), q = new THREE.Quaternion(), c = new THREE.Color();
    const greens = ["#4f9a2c", "#5aa834", "#3f8a26", "#6ab83c", "#7a9a2a"];
    for (let i = 0; i < n; i++) {
      const s = seed * 100000 + i;
      const x = x0 + (x1 - x0) * h01(s), z = z0 + (z1 - z0) * h01(s + 1);
      const hh = h[0] + (h[1] - h[0]) * h01(s + 2) ** 1.5;
      q.setFromEuler(new THREE.Euler((h01(s + 3) - 0.5) * 0.5, h01(s + 4) * Math.PI * 2, (h01(s + 5) - 0.5) * 0.5));
      M.compose(new THREE.Vector3(x, 0, z), q, new THREE.Vector3(0.014 + 0.01 * h01(s + 6), hh, 1));
      mesh.setMatrixAt(i, M);
      c.set(greens[Math.floor(h01(s + 7) * greens.length)]).multiplyScalar(0.85 + 0.3 * h01(s + 8));
      mesh.setColorAt(i, c);
    }
    mesh.instanceMatrix.needsUpdate = true;
    mesh.receiveShadow = true;
    mesh.frustumCulled = false;
    mesh.userData.outline = false;
    grassFields.set(key, mesh);
  }
  return <primitive object={mesh} />;
};

// ------------------------------------------------------------------ leaves
const canopies = new Map<string, THREE.InstancedMesh>();
/** a crown of n leaf cards on a sphere of radius r at p (seeded), colour pair */
export const LeafCanopy: React.FC<{ p: V3; r: number; n?: number; seed?: number; colors?: [string, string, string] }> = ({ p, r, n = 420, seed = 1, colors = ["#3f8c2c", "#5aa83a", "#2f7a26"] }) => {
  const key = `${p.join(",")}|${r}|${n}|${seed}`;
  let mesh = canopies.get(key);
  if (!mesh) {
    const L = leafSet();
    const mat = sway("leafCard", () => new THREE.MeshStandardMaterial({ map: L.map, normalMap: L.normal, alphaMap: L.alpha, alphaTest: 0.5, side: THREE.DoubleSide, roughness: 0.55 }), 0.035, false);
    const geo = geoOf("leafCard", () => {
      const g = new THREE.PlaneGeometry(0.2, 0.26);
      g.translate(0, 0.13, 0);
      return g;
    });
    mesh = new THREE.InstancedMesh(geo, mat, n);
    const M = new THREE.Matrix4(), c = new THREE.Color();
    for (let i = 0; i < n; i++) {
      const s = seed * 10000 + i;
      // clumped points on a squashed sphere (crowns are rounder on top)
      const u = h01(s) * 2 - 1, th = h01(s + 1) * Math.PI * 2, rr = r * (0.82 + 0.18 * h01(s + 2));
      const sq = Math.sqrt(1 - u * u);
      const pos = new THREE.Vector3(p[0] + Math.cos(th) * sq * rr, p[1] + u * rr * 0.85, p[2] + Math.sin(th) * sq * rr);
      const out = new THREE.Vector3(Math.cos(th) * sq, u, Math.sin(th) * sq).normalize();
      const look = new THREE.Matrix4().lookAt(new THREE.Vector3(0, 0, 0), out, new THREE.Vector3(0, 1, 0));
      const q = new THREE.Quaternion().setFromRotationMatrix(look).multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(-1.2 + 0.6 * h01(s + 3), 0, h01(s + 4) * Math.PI * 2)));
      const sc = 0.8 + 0.5 * h01(s + 5);
      M.compose(pos, q, new THREE.Vector3(sc, sc, sc));
      mesh.setMatrixAt(i, M);
      c.set(colors[Math.floor(h01(s + 6) * 3)]).multiplyScalar(0.8 + 0.35 * h01(s + 7));
      mesh.setColorAt(i, c);
    }
    mesh.instanceMatrix.needsUpdate = true;
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.frustumCulled = false;
    canopies.set(key, mesh);
  }
  return (
    <>
      <mesh geometry={geoOf("crownCore", () => new THREE.IcosahedronGeometry(1, 2))} material={plastic(colors[2], { rough: 0.9, cc: 0 })} position={p} scale={[r * 0.82, r * 0.72, r * 0.82]} castShadow receiveShadow />
      <primitive object={mesh} />
    </>
  );
};

// ------------------------------------------------------------------ cars
/** a generic little car along +x (its front), on the ground at p; spin = wheel angle */
export const ToyCar: React.FC<{ p: V3; yaw?: number; color: string; spin?: number; lights?: number; s?: number }> = ({ p, yaw = 0, color, spin = 0, lights = 0.4, s = 1 }) => {
  const paint = plastic(color, { rough: 0.3, cc: 1 });
  const glass = plastic("#1a2a3a", { rough: 0.04, cc: 1, metal: 0.4 });
  const chrome = pbr("metal", metalSet, "#e8ecf4", { metal: 1, rough: 0.5 });
  return (
    <group position={p} rotation={[0, yaw, 0]} scale={s}>
      <mesh geometry={rbox(1.9, 0.5, 0.95, 0.14)} material={paint} position={[0, 0.45, 0]} castShadow receiveShadow />
      <mesh geometry={rbox(1.05, 0.42, 0.86, 0.16)} material={paint} position={[-0.12, 0.86, 0]} castShadow />
      <mesh geometry={rbox(0.98, 0.32, 0.88, 0.12)} material={glass} position={[-0.12, 0.88, 0]} />
      <mesh geometry={rbox(0.12, 0.12, 0.9, 0.04)} material={chrome} position={[0.96, 0.32, 0]} />
      <mesh geometry={rbox(0.12, 0.12, 0.9, 0.04)} material={chrome} position={[-0.96, 0.32, 0]} />
      {[-1, 1].map((z) => (
        <group key={z}>
          <mesh geometry={geoOf("headL", () => new THREE.SphereGeometry(0.07, 12, 8))} material={plastic("#fff6d8", { emissive: "#fff2c0", ei: 0.5 + 3 * lights })} position={[0.95, 0.5, z * 0.3]} />
          <mesh geometry={rbox(0.04, 0.08, 0.16, 0.02)} material={plastic("#ff2a2a", { emissive: "#ff2a2a", ei: 0.4 + 2 * lights })} position={[-0.96, 0.5, z * 0.33]} />
        </group>
      ))}
      {[[-0.6, -0.46], [-0.6, 0.46], [0.6, -0.46], [0.6, 0.46]].map(([x, z], i) => (
        <group key={i} position={[x, 0.24, z]} rotation={[Math.PI / 2, 0, 0]}>
          <group rotation={[0, -spin, 0]}>
            <mesh geometry={geoOf("tyre", () => new THREE.TorusGeometry(0.17, 0.075, 12, 24))} material={plastic("#1e1e22", { rough: 0.85, cc: 0 })} rotation={[Math.PI / 2, 0, 0]} castShadow />
            <mesh geometry={geoOf("rim", () => new THREE.CylinderGeometry(0.13, 0.13, 0.12, 6))} material={chrome} />
          </group>
        </group>
      ))}
    </group>
  );
};
/** cars driving along the road (x), wrapping around: lane z, speed v (m/s), offset */
export const Traffic: React.FC<{ t: number; night?: boolean }> = ({ t, night = false }) => (
  <>
    {([[-5.0, 3.2, 0, "#2a7de1", 1], [-7.3, -2.6, 13, "#ffd23a", -1], [-5.0, 3.2, 28, "#e3242b", 1], [-7.3, -2.6, 40, "#7fe3b8", -1]] as [number, number, number, string, number][]).map(([z, v, off, c, dir], i) => {
      const x = (((v * t + off + 40) % 80) + 80) % 80 - 40;
      return <ToyCar key={i} p={[x, -0.1, z]} yaw={dir > 0 ? 0 : Math.PI} color={c} spin={(Math.abs(v) * t) / 0.24} lights={night ? 1 : 0.1} />;
    })}
  </>
);

// ------------------------------------------------------------------ the far city
const towerTex = (night: boolean) => {
  const t = canvasTexture(`tower|${night ? 1 : 0}`, 128, 256, (g, W, H) => {
    g.fillStyle = night ? "#20263a" : "#7f8ea6";
    g.fillRect(0, 0, W, H);
    let s = 11;
    const r = () => ((s = (s * 16807) % 2147483647) / 2147483647);
    for (let y = 6; y < H - 6; y += 12)
      for (let x = 6; x < W - 6; x += 12) {
        const on = r() < (night ? 0.55 : 0.0);
        g.fillStyle = on ? ["#ffd890", "#fff2c0", "#ffc070"][Math.floor(r() * 3)] : night ? "#323a54" : r() < 0.3 ? "#dfe8f4" : "#4a5a74";
        g.fillRect(x, y, 7, 8);
      }
  });
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
};
export const Skyline: React.FC<{ night?: boolean }> = ({ night = false }) => (
  <group position={[0, 0, -120]}>
    {Array.from({ length: 22 }, (_, i) => {
      const x = -110 + i * 10.5 + 4 * h01(i + 3);
      const h = 12 + 22 * h01(i + 7) ** 1.6;
      const w = 6 + 4 * h01(i + 9);
      const tex = towerTex(night);
      return (
        <mesh key={i} geometry={geoOf(`tower${w.toFixed(1)}|${h.toFixed(1)}`, () => new THREE.BoxGeometry(w, h, w))} material={plastic("#ffffff", { map: tex, rough: 0.4, emissive: night ? "#ffffff" : undefined, ei: night ? 0.9 : 0, cc: 0.8 })} position={[x, h / 2 - 2, -8 * h01(i + 11)]} />
      );
    })}
  </group>
);

// ------------------------------------------------------------------ window glass with a lit room behind
const roomTex = () =>
  canvasTexture("litRoom", 128, 128, (g, W) => {
    const gr = g.createRadialGradient(W * 0.5, W * 0.35, 4, W * 0.5, W * 0.5, W * 0.8);
    gr.addColorStop(0, "#fff0c8");
    gr.addColorStop(0.5, "#ffb860");
    gr.addColorStop(1, "#6a3a20");
    g.fillStyle = gr;
    g.fillRect(0, 0, W, W);
    // a curtain on each side and a lamp
    g.fillStyle = "rgba(200,60,60,0.85)";
    g.fillRect(0, 0, W * 0.18, W);
    g.fillRect(W * 0.82, 0, W * 0.18, W);
    g.fillStyle = "#ffffff";
    g.beginPath();
    g.arc(W * 0.5, W * 0.3, W * 0.06, 0, Math.PI * 2);
    g.fill();
  });
/** a window pane w x h at the origin facing +z: reflective glass in front of a warm lit room (lit: 0..1) */
export const LitWindow: React.FC<{ w: number; h: number; lit: number }> = ({ w, h, lit }) => (
  <group>
    <mesh geometry={geoOf(`litRoom${w}|${h}`, () => new THREE.PlaneGeometry(w, h))} material={plastic("#ffffff", { map: roomTex(), emissive: "#ffffff", ei: 0.15 + 1.1 * lit, rough: 1, cc: 0 })} position={[0, 0, -0.06]} />
    <mesh geometry={geoOf(`pane${w}|${h}`, () => new THREE.PlaneGeometry(w, h))} material={plastic("#a8d0f0", { transparent: true, opacity: 0.38, rough: 0.03, cc: 1, metal: 0.3 })} position={[0, 0, 0.0]} renderOrder={3} />
  </group>
);
