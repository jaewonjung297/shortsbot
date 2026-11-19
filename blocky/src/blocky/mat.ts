// Smooth plastic materials (MeshStandardMaterial, low metalness, soft specular): the blocky look has no toon ramp and
// no ink. Bounded caches keyed by value strings (never by Object3D.id), so every tab builds identical objects.
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import { vinylSet } from "../engine/mat/pbr";

// Premium pass: every plastic is a painted vinyl toy surface: MeshPhysicalMaterial with a clear coat (a second,
// sharper highlight that reflects the scene's environment map) and a very fine orange-peel micro normal. Matte parts
// (rough >= 0.7) get only a thin coat. bump = a height map (embossed decals: the face).
const mats = new Map<string, THREE.MeshPhysicalMaterial>();
export type PlasticOpts = { rough?: number; flat?: boolean; map?: THREE.Texture; alphaMap?: THREE.Texture; transparent?: boolean; opacity?: number; decal?: boolean; side?: THREE.Side; emissive?: string; ei?: number; bump?: THREE.Texture; bs?: number; cc?: number; metal?: number };
let micro: THREE.Texture | null = null;
const microTex = () => {
  if (!micro) {
    micro = vinylSet().normal.clone();
    micro.repeat.set(3, 3);
    micro.needsUpdate = true;
  }
  return micro;
};
const MICRO = new THREE.Vector2(0.18, 0.18);
export const plastic = (color: string, o: PlasticOpts = {}) => {
  const key = [color, o.rough ?? 0.5, o.flat ? 1 : 0, o.map?.uuid ?? "", o.alphaMap?.uuid ?? "", o.transparent ? 1 : 0, o.opacity ?? 1, o.decal ? 1 : 0, o.side ?? 0, o.emissive ?? "", o.ei ?? 0, o.bump?.uuid ?? "", o.bs ?? 0, o.cc ?? -1, o.metal ?? 0].join("|");
  let m = mats.get(key);
  if (!m) {
    if (mats.size > 400) mats.clear();
    const rough = o.rough ?? 0.5;
    m = new THREE.MeshPhysicalMaterial({
      color,
      roughness: rough,
      metalness: o.metal ?? 0,
      clearcoat: o.cc ?? (rough < 0.7 ? 0.55 : 0.12),
      clearcoatRoughness: 0.18 + 0.25 * rough,
      normalMap: o.bump || o.flat ? null : microTex(),
      normalScale: MICRO,
      bumpMap: o.bump ?? null,
      bumpScale: o.bs ?? 1,
      flatShading: o.flat ?? false,
      map: o.map ?? null,
      alphaMap: o.alphaMap ?? null,
      transparent: o.transparent || o.decal || false,
      opacity: o.opacity ?? 1,
      depthWrite: !(o.transparent || o.decal),
      side: o.side ?? THREE.FrontSide,
      emissive: o.emissive ?? "#000000",
      emissiveIntensity: o.ei ?? 0,
    });
    if (o.decal) {
      // decals sit >= 4 mm proud AND pull forward in depth: never z-fight with the surface under them
      m.polygonOffset = true;
      m.polygonOffsetFactor = -2;
      m.polygonOffsetUnits = -2;
    }
    mats.set(key, m);
  }
  return m;
};

const geos = new Map<string, THREE.BufferGeometry>();
export const geoOf = (key: string, make: () => THREE.BufferGeometry) => {
  let g = geos.get(key);
  if (!g) {
    if (geos.size > 400) geos.clear();
    g = make();
    geos.set(key, g);
  }
  return g;
};
/** a box with softly rounded edges (plastic parts catch a highlight on the edge) */
export const rbox = (w: number, h: number, d: number, r: number) =>
  geoOf(`rb${w.toFixed(4)}|${h.toFixed(4)}|${d.toFixed(4)}|${r.toFixed(4)}`, () => new RoundedBoxGeometry(w, h, d, 3, Math.min(r, w / 2 - 1e-4, h / 2 - 1e-4, d / 2 - 1e-4)));

const texs = new Map<string, THREE.CanvasTexture>();
/** a cached canvas texture (drawn once per key) */
export const canvasTexture = (key: string, w: number, h: number, draw: (g: CanvasRenderingContext2D, w: number, h: number) => void, srgb = true) => {
  let t = texs.get(key);
  if (!t) {
    if (texs.size > 120) texs.clear();
    const c = document.createElement("canvas");
    c.width = w;
    c.height = h;
    draw(c.getContext("2d")!, w, h);
    t = new THREE.CanvasTexture(c);
    t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    t.anisotropy = 8;
    t.generateMipmaps = true;
    t.minFilter = THREE.LinearMipmapLinearFilter;
    texs.set(key, t);
  }
  return t;
};
