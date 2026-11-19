// Image-based light for the premium pass: a small HDR "studio" built from the mood (a sky-to-ground gradient dome +
// soft emissive panels where the key, rim and fill come from + optional practical colours), prefiltered with PMREM and
// set as scene.environment. Every physical material then gets soft bounce light from the right colours (a cheap
// global-illumination look) and real reflections in its clear coat, glass and metal. Built once per mood per tab
// (cached by value), so it is a pure function of the mood and costs nothing per frame.
import { useThree } from "@react-three/fiber";
import React from "react";
import * as THREE from "three";
import type { V3 } from "../types";

export type EnvPanel = { dir: V3; color: string; power: number; size?: number };
export type EnvSpec = { sky: string; horizon: string; ground: string; panels: EnvPanel[]; intensity: number };

const cache = new Map<string, THREE.Texture>();
const DOME_FRAG = /* glsl */ `
uniform vec3 uSky; uniform vec3 uHor; uniform vec3 uGround;
varying vec3 vDir;
void main() {
  float y = normalize(vDir).y;
  vec3 c = y > 0.0 ? mix(uHor, uSky, smoothstep(0.0, 0.7, y)) : mix(uHor, uGround, smoothstep(0.0, 0.35, -y));
  gl_FragColor = vec4(c, 1.0);
}`;
const DOME_VERT = /* glsl */ `
varying vec3 vDir;
void main() { vDir = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`;

const lin = (hex: string, k = 1) => new THREE.Color(hex).multiplyScalar(k); // THREE.Color parses sRGB hex into linear

const build = (gl: THREE.WebGLRenderer, s: EnvSpec) => {
  const scene = new THREE.Scene();
  const dome = new THREE.Mesh(
    new THREE.SphereGeometry(50, 32, 16),
    new THREE.ShaderMaterial({ vertexShader: DOME_VERT, fragmentShader: DOME_FRAG, side: THREE.BackSide, depthWrite: false, uniforms: { uSky: { value: lin(s.sky) }, uHor: { value: lin(s.horizon) }, uGround: { value: lin(s.ground) } } }),
  );
  scene.add(dome);
  const geos: THREE.BufferGeometry[] = [dome.geometry];
  for (const p of s.panels) {
    const g = new THREE.CircleGeometry((p.size ?? 0.35) * 40, 24);
    geos.push(g);
    const m = new THREE.MeshBasicMaterial({ color: lin(p.color, p.power), side: THREE.DoubleSide, toneMapped: false });
    const mesh = new THREE.Mesh(g, m);
    const d = new THREE.Vector3(...p.dir).normalize();
    mesh.position.copy(d.clone().multiplyScalar(40));
    mesh.lookAt(0, 0, 0);
    scene.add(mesh);
  }
  const pm = new THREE.PMREMGenerator(gl);
  const prev = gl.getRenderTarget();
  const rt = pm.fromScene(scene, 0.03, 0.1, 100);
  gl.setRenderTarget(prev);
  pm.dispose();
  geos.forEach((g) => g.dispose());
  return rt.texture;
};

/** sets scene.environment from the spec (cached per spec); intensity 0 = off */
export const EnvLight: React.FC<{ spec: EnvSpec | null }> = ({ spec }) => {
  const { gl, scene } = useThree();
  if (!spec || spec.intensity <= 0) {
    scene.environment = null;
    return null;
  }
  const key = JSON.stringify({ ...spec, intensity: 0 });
  let tex = cache.get(key);
  if (!tex) {
    if (cache.size > 40) {
      cache.forEach((t) => t.dispose());
      cache.clear();
    }
    tex = build(gl, spec);
    cache.set(key, tex);
  }
  scene.environment = tex;
  scene.environmentIntensity = spec.intensity;
  return null;
};
