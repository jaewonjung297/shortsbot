// Procedural PBR texture sets (albedo + roughness + normal), all made here from seeded noise: no downloaded textures,
// no licences to track. Every set tiles seamlessly, is drawn once per render tab and cached by key, and is a pure
// function of its seed (identical in every tab and every render).
//   albedo is near white with variation (the material colour tints it), so one wood set serves every wood colour.
//   normal maps come from a height field (central differences, wrapped), tangent space (+z out).
import * as THREE from "three";
import { mulberry } from "./paint";

// ------------------------------------------------------------------ noise
/** periodic value noise on a cells x cells lattice (tiles over 0..1) */
const lattice = (cells: number, seed: number) => {
  const r = mulberry(seed);
  const g = new Float32Array(cells * cells).map(() => r());
  return (u: number, v: number) => {
    const x = (((u % 1) + 1) % 1) * cells, y = (((v % 1) + 1) % 1) * cells;
    const i = Math.floor(x), j = Math.floor(y);
    let fx = x - i, fy = y - j;
    fx = fx * fx * (3 - 2 * fx);
    fy = fy * fy * (3 - 2 * fy);
    const i1 = (i + 1) % cells, j1 = (j + 1) % cells;
    const a = g[j * cells + i], b = g[j * cells + i1], c = g[j1 * cells + i], d = g[j1 * cells + i1];
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy;
  };
};
/** fractal noise, 0..1, octaves of doubling lattices */
export const fbm = (cells: number, oct: number, seed: number) => {
  const ls = Array.from({ length: oct }, (_, i) => lattice(cells << i, seed + i * 101));
  return (u: number, v: number) => {
    let s = 0, a = 0.5, n = 0;
    for (const l of ls) {
      s += a * l(u, v);
      n += a;
      a *= 0.5;
    }
    return s / n;
  };
};
/** cellular (Worley) distance to the nearest feature point, tiling, ~0..1 */
const worley = (cells: number, seed: number) => {
  const r = mulberry(seed);
  const pts = Array.from({ length: cells * cells }, () => [r(), r()]);
  return (u: number, v: number) => {
    const x = (((u % 1) + 1) % 1) * cells, y = (((v % 1) + 1) % 1) * cells;
    const i = Math.floor(x), j = Math.floor(y);
    let best = 9;
    for (let dj = -1; dj <= 1; dj++)
      for (let di = -1; di <= 1; di++) {
        const ci = (i + di + cells) % cells, cj = (j + dj + cells) % cells;
        const p = pts[cj * cells + ci];
        const dx = i + di + p[0] - x, dy = j + dj + p[1] - y;
        best = Math.min(best, dx * dx + dy * dy);
      }
    return Math.sqrt(best);
  };
};

// ------------------------------------------------------------------ baking
export type Px = { c: [number, number, number]; r: number; h: number; a?: number };
export type PbrSet = { map: THREE.Texture; rough: THREE.Texture; normal: THREE.Texture; alpha?: THREE.Texture };
const sets = new Map<string, PbrSet>();
const mkTex = (c: HTMLCanvasElement, srgb: boolean) => {
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.anisotropy = 8;
  t.generateMipmaps = true;
  t.minFilter = THREE.LinearMipmapLinearFilter;
  return t;
};
/** bake a W x W set from a per-pixel function of (u, v) in 0..1; nk = normal strength */
export const bakeSet = (key: string, W: number, nk: number, px: (u: number, v: number) => Px, withAlpha = false): PbrSet => {
  const hit = sets.get(key);
  if (hit) return hit;
  const cv = [0, 1, 2, 3].map(() => {
    const c = document.createElement("canvas");
    c.width = c.height = W;
    return c;
  });
  const img = cv.map((c) => c.getContext("2d")!.createImageData(W, W));
  const H = new Float32Array(W * W);
  for (let y = 0; y < W; y++)
    for (let x = 0; x < W; x++) {
      const p = px((x + 0.5) / W, (y + 0.5) / W);
      const o = (y * W + x) * 4;
      H[y * W + x] = p.h;
      img[0].data[o] = p.c[0] * 255;
      img[0].data[o + 1] = p.c[1] * 255;
      img[0].data[o + 2] = p.c[2] * 255;
      img[0].data[o + 3] = 255;
      img[1].data[o] = img[1].data[o + 1] = img[1].data[o + 2] = Math.max(0, Math.min(1, p.r)) * 255;
      img[1].data[o + 3] = 255;
      const a = (p.a ?? 1) * 255;
      img[3].data[o] = img[3].data[o + 1] = img[3].data[o + 2] = a;
      img[3].data[o + 3] = 255;
    }
  for (let y = 0; y < W; y++)
    for (let x = 0; x < W; x++) {
      const at = (i: number, j: number) => H[((j + W) % W) * W + ((i + W) % W)];
      const dx = (at(x + 1, y) - at(x - 1, y)) * nk, dy = (at(x, y + 1) - at(x, y - 1)) * nk;
      const l = Math.hypot(dx, dy, 1);
      const o = (y * W + x) * 4;
      img[2].data[o] = (-dx / l * 0.5 + 0.5) * 255;
      img[2].data[o + 1] = (dy / l * 0.5 + 0.5) * 255; // canvas y runs down, uv v runs up
      img[2].data[o + 2] = (1 / l * 0.5 + 0.5) * 255;
      img[2].data[o + 3] = 255;
    }
  cv.forEach((c, i) => c.getContext("2d")!.putImageData(img[i], 0, 0));
  const s: PbrSet = { map: mkTex(cv[0], true), rough: mkTex(cv[1], false), normal: mkTex(cv[2], false), alpha: withAlpha ? mkTex(cv[3], false) : undefined };
  sets.set(key, s);
  return s;
};

const sm = (a: number, b: number, x: number) => {
  const t = Math.max(0, Math.min(1, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};
const grey = (v: number): [number, number, number] => [v, v, v];
const tint = (v: number, r: number, g: number, b: number): [number, number, number] => [v * r, v * g, v * b];

// ------------------------------------------------------------------ the library of surfaces
/** painted vinyl toy skin: a very fine orange peel + faint mould sparkle (normal only matters) */
export const vinylSet = () => {
  const n = fbm(32, 3, 7);
  return bakeSet("vinyl", 256, 2.2, (u, v) => ({ c: grey(1), r: 0.5, h: n(u, v) }));
};
/** planks along u: grain streaks, growth rings, seams between boards, a few knots */
export const woodSet = (boards = 4) => {
  const g = fbm(4, 4, 21), fine = fbm(64, 2, 22), k = worley(3, 23);
  return bakeSet(`wood${boards}`, 512, 3.0, (u, v) => {
    const b = Math.floor(v * boards), bv = v * boards - b;
    const off = (b * 0.37) % 1;
    const ring = 0.5 + 0.5 * Math.sin((g(u * 0.5 + off, v * 0.25) * 18 + bv * 3) * Math.PI);
    const knot = sm(0.12, 0.0, k(u + off, v));
    const seam = sm(0.025, 0.0, Math.min(bv, 1 - bv)) + sm(0.006, 0.0, Math.abs(((u + off * 2.3) % 1) - 0.5) - 0.494);
    const base = 0.95 + 0.05 * (b % 3) / 2 - 0.1 * ring - 0.08 * fine(u * 0.1, v * 4) - 0.25 * knot;
    const val = base * (1 - 0.5 * Math.min(1, seam));
    return { c: tint(val, 1, 0.96, 0.9), r: 0.42 + 0.18 * ring + 0.3 * Math.min(1, seam), h: 0.25 * ring + 0.35 * fine(u * 0.1, v * 4) - 1.2 * Math.min(1, seam) - 0.5 * knot };
  });
};
/** brushed metal: long fine streaks along u, a little speckle; low roughness */
export const metalSet = () => {
  const s = fbm(2, 3, 31), sp = fbm(128, 1, 32);
  return bakeSet("metal", 512, 1.2, (u, v) => {
    const st = s(u * 0.05, v * 30);
    return { c: grey(0.86 + 0.1 * st), r: 0.22 + 0.16 * st + 0.08 * sp(u, v), h: 0.4 * st + 0.1 * sp(u, v) };
  });
};
/** painted siding: horizontal lap boards (u across), each with a shadow line under its lip, faint grain */
export const sidingSet = () => {
  const g = fbm(4, 3, 161);
  return bakeSet("siding", 256, 3.0, (u, v) => {
    const rows = 5, r = v * rows - Math.floor(v * rows);
    const lip = sm(0.0, 0.12, r);
    const val = (0.9 + 0.06 * g(u * 0.3, v * 3)) * (0.72 + 0.28 * lip);
    return { c: grey(val), r: 0.6, h: r * 0.6 + 0.4 * (1 - lip) * 0 };
  });
};
/** concrete / plaster: two scales of mottling, pores, a few hairline cracks */
export const concreteSet = () => {
  const m = fbm(6, 4, 41), pores = worley(48, 42), cr = fbm(3, 3, 43);
  return bakeSet("concrete", 512, 2.4, (u, v) => {
    const pore = sm(0.18, 0.05, pores(u, v));
    const crack = sm(0.012, 0, Math.abs(cr(u, v) - 0.5));
    const val = 0.8 + 0.14 * m(u, v) - 0.25 * pore - 0.3 * crack;
    return { c: grey(val), r: 0.82 - 0.1 * m(u, v), h: 0.3 * m(u, v) - 0.6 * pore - 0.8 * crack };
  });
};
/** woven fabric: a plain weave + fuzz */
export const fabricSet = () => {
  const f = fbm(64, 2, 51);
  return bakeSet("fabric", 256, 2.0, (u, v) => {
    const n = 48;
    const wx = Math.sin(u * n * Math.PI * 2), wy = Math.sin(v * n * Math.PI * 2);
    const over = (Math.floor(u * n * 2) + Math.floor(v * n * 2)) % 2 ? wx : wy;
    return { c: grey(0.84 + 0.08 * over + 0.08 * f(u, v)), r: 0.92, h: 0.5 * over + 0.3 * f(u, v) };
  });
};
/** lawn seen from above: dense blade strokes in several greens with soil gaps */
export const grassSet = () => {
  const big = fbm(4, 4, 61), soil = fbm(10, 3, 62), r = mulberry(63);
  const W = 512;
  const blades = new Float32Array(W * W);
  for (let i = 0; i < 26000; i++) {
    const x0 = r() * W, y0 = r() * W, len = 5 + r() * 9, a = -Math.PI / 2 + (r() - 0.5) * 1.2, h = 0.4 + 0.6 * r();
    for (let s = 0; s < len; s++) {
      const x = Math.floor(x0 + Math.cos(a) * s + W) % W, y = Math.floor(y0 + Math.sin(a) * s + W) % W;
      blades[y * W + x] = Math.max(blades[y * W + x], h * (1 - (s / len) * 0.4));
    }
  }
  return bakeSet("grass", W, 4.0, (u, v) => {
    const b = blades[Math.floor(v * W) * W + Math.floor(u * W)];
    const gap = sm(0.62, 0.78, soil(u, v)) * (1 - b);
    const g = 0.55 + 0.45 * b, k = 0.85 + 0.25 * big(u, v);
    const c: [number, number, number] = [g * k * (0.75 + 0.3 * big(v, u)), g * k, g * k * 0.7];
    const dirt: [number, number, number] = [0.55, 0.42, 0.3];
    return { c: [c[0] * (1 - gap) + dirt[0] * gap, c[1] * (1 - gap) + dirt[1] * gap, c[2] * (1 - gap) + dirt[2] * gap], r: 0.78 + 0.15 * gap, h: b - 0.3 * gap };
  });
};
/** soil: clumps, pebbles, damp patches */
export const soilSet = () => {
  const cl = worley(24, 71), m = fbm(8, 4, 72);
  return bakeSet("soil", 512, 3.0, (u, v) => {
    const clump = 1 - sm(0.0, 0.5, cl(u, v));
    const val = 0.5 + 0.25 * clump + 0.15 * m(u, v);
    return { c: tint(val, 0.62, 0.45, 0.32), r: 0.75 + 0.2 * m(u, v), h: clump * 0.8 + 0.3 * m(u, v) };
  });
};
/** asphalt: dark binder with light aggregate, slight wear */
export const asphaltSet = () => {
  const ag = worley(90, 81), m = fbm(6, 3, 82), sp = fbm(128, 1, 83);
  return bakeSet("asphalt", 512, 2.0, (u, v) => {
    const stone = sm(0.32, 0.12, ag(u, v));
    const val = 0.22 + 0.2 * stone * sp(u, v) + 0.08 * m(u, v);
    return { c: grey(val), r: 0.8 - 0.25 * stone * 0.5, h: stone * 0.7 };
  });
};
/** brick courses with recessed mortar */
export const brickSet = () => {
  const m = fbm(8, 3, 91), b = fbm(16, 2, 92);
  return bakeSet("brick", 512, 3.5, (u, v) => {
    const rows = 8, cols = 4;
    const r = Math.floor(v * rows), rv = v * rows - r;
    const uu = u * cols + (r % 2) * 0.5, cu = uu - Math.floor(uu);
    const mortar = Math.max(sm(0.06, 0.0, Math.min(rv, 1 - rv)), sm(0.03, 0.0, Math.min(cu, 1 - cu)));
    const shade = 0.78 + 0.18 * b(Math.floor(uu) / 13, r / 7) + 0.08 * m(u, v);
    const brick = tint(shade, 1, 0.92, 0.88);
    const c: [number, number, number] = mortar > 0.5 ? grey(0.9) : brick;
    return { c, r: mortar > 0.5 ? 0.9 : 0.75, h: (1 - mortar) * 0.8 + 0.15 * m(u, v) };
  });
};
/** clay roof tiles: overlapping rounded rows (u across, v down the roof) */
export const roofSet = () => {
  const m = fbm(8, 3, 101);
  return bakeSet("roof", 512, 5.0, (u, v) => {
    const rows = 8, cols = 8;
    const r = Math.floor(v * rows), rv = v * rows - r;
    const uu = u * cols + (r % 2) * 0.5, cu = uu - Math.floor(uu);
    const arch = Math.sqrt(Math.max(0, 1 - Math.pow(2 * cu - 1, 2)));
    const lip = sm(0.0, 0.85, rv); // each tile thickens toward its lower edge, then the next row starts (a step)
    const h = arch * 0.5 + lip * 0.6;
    const shade = (0.72 + 0.2 * arch + 0.1 * m(u, v)) * (0.75 + 0.25 * rv) * (0.9 + 0.1 * ((Math.floor(uu) * 7 + r * 3) % 5) / 4);
    return { c: tint(shade, 1, 0.95, 0.92), r: 0.55 + 0.25 * (1 - arch), h };
  });
};
/** big glossy floor tiles with grout */
export const tileSet = (n = 4) => {
  const m = fbm(4, 3, 111);
  return bakeSet(`tile${n}`, 512, 3.0, (u, v) => {
    const cu = (u * n) % 1, cv = (v * n) % 1;
    const grout = Math.max(sm(0.018, 0.0, Math.min(cu, 1 - cu)), sm(0.018, 0.0, Math.min(cv, 1 - cv)));
    const checker = (Math.floor(u * n) + Math.floor(v * n)) % 2;
    const val = (checker ? 0.82 : 1.0) * (0.96 + 0.04 * m(u, v));
    return { c: grout > 0.5 ? grey(0.55) : grey(val), r: grout > 0.5 ? 0.8 : 0.08 + 0.06 * m(u, v), h: -grout };
  });
};
/** tree bark: vertical ridges and plates */
export const barkSet = () => {
  const r = fbm(3, 4, 121), c = worley(12, 122);
  return bakeSet("bark", 256, 4.0, (u, v) => {
    const ridge = Math.abs(Math.sin((u * 10 + r(u, v * 0.3) * 3) * Math.PI));
    const plate = sm(0.1, 0.4, c(u, v * 0.4));
    return { c: tint(0.6 + 0.3 * ridge * plate, 1, 0.85, 0.7), r: 0.9, h: ridge * plate };
  });
};
/** bread crumb (the inside of a slice): pores of several sizes */
export const crumbSet = () => {
  const p1 = worley(18, 131), p2 = worley(44, 132), m = fbm(6, 3, 133);
  return bakeSet("crumb", 256, 3.5, (u, v) => {
    const pore = Math.max(sm(0.22, 0.08, p1(u, v)), 0.7 * sm(0.2, 0.06, p2(u, v)));
    const val = 0.95 - 0.35 * pore + 0.05 * m(u, v);
    return { c: tint(val, 1, 0.9, 0.7), r: 0.85, h: -pore };
  });
};
/** baked crust: golden brown with blisters and flour dust */
export const crustSet = () => {
  const b = worley(14, 141), m = fbm(6, 4, 142), f = fbm(64, 1, 143);
  return bakeSet("crust", 256, 3.0, (u, v) => {
    const blister = sm(0.35, 0.05, b(u, v));
    const val = 0.62 + 0.25 * m(u, v) + 0.18 * blister;
    const flour = sm(0.7, 0.9, f(u, v)) * 0.25;
    return { c: [Math.min(1, val + flour), Math.min(1, val * 0.72 + flour), Math.min(1, val * 0.42 + flour)], r: 0.55 + 0.3 * flour, h: blister * 0.6 + 0.2 * m(u, v) };
  });
};
/** a leaf card: a pointed leaf with a midrib and veins (alpha = the leaf shape) */
export const leafSet = () =>
  bakeSet("leaf", 128, 2.5, (u, v) => {
    const x = (u - 0.5) * 2, y = v; // y 0 = stem, 1 = tip
    const w = 0.9 * Math.sin(Math.PI * Math.min(1, y * 1.05)) * (1 - 0.25 * y);
    const inside = Math.abs(x) < w && y > 0.04 ? 1 : 0;
    const rib = sm(0.06, 0, Math.abs(x));
    const vein = sm(0.08, 0, Math.abs(((Math.abs(x) * 1.2 - y * 1.6) * 5) % 1 - 0.5) - 0.45) * (Math.abs(x) < w * 0.85 ? 1 : 0);
    const val = 0.8 + 0.15 * y - 0.1 * Math.abs(x);
    return { c: tint(val + 0.15 * rib, 1, 1, 1), r: 0.55, h: rib * 0.6 + 0.3 * vein, a: inside };
  }, true);
/** rough painted wall plaster (interiors) */
export const plasterSet = () => {
  const m = fbm(10, 4, 151), s = fbm(48, 2, 152);
  return bakeSet("plaster", 256, 2.0, (u, v) => ({ c: grey(0.9 + 0.06 * m(u, v)), r: 0.85, h: 0.5 * m(u, v) + 0.3 * s(u, v) }));
};

// ------------------------------------------------------------------ materials from sets
const mats = new Map<string, THREE.MeshPhysicalMaterial>();
const reps = new Map<string, PbrSet>();
/** the same set with its own repeat (textures share the image, not the repeat) */
const repeated = (key: string, s: PbrSet, rx: number, ry: number): PbrSet => {
  const k = `${key}|${rx}|${ry}`;
  let r = reps.get(k);
  if (!r) {
    const c = (t?: THREE.Texture) => {
      if (!t) return undefined;
      const x = t.clone();
      x.repeat.set(rx, ry);
      x.needsUpdate = true;
      return x;
    };
    r = { map: c(s.map)!, rough: c(s.rough)!, normal: c(s.normal)!, alpha: c(s.alpha) };
    reps.set(k, r);
  }
  return r;
};
export type PbrOpts = { rep?: [number, number]; rough?: number; metal?: number; normal?: number; clearcoat?: number; ccRough?: number; side?: THREE.Side; emissive?: string; ei?: number; alphaTest?: number; env?: number; sheen?: number };
/** a physical material from a set, tinted by color. rough scales the roughness map (1 = as baked) */
export const pbr = (setName: string, set: () => PbrSet, color: string, o: PbrOpts = {}) => {
  const rep = o.rep ?? [1, 1];
  const key = [setName, color, rep.join("x"), o.rough ?? 1, o.metal ?? 0, o.normal ?? 1, o.clearcoat ?? 0, o.ccRough ?? 0.2, o.side ?? 0, o.emissive ?? "", o.ei ?? 0, o.alphaTest ?? 0, o.env ?? 1, o.sheen ?? 0].join("|");
  let m = mats.get(key);
  if (!m) {
    if (mats.size > 300) mats.clear();
    const s = repeated(setName, set(), rep[0], rep[1]);
    m = new THREE.MeshPhysicalMaterial({
      color,
      map: s.map,
      roughnessMap: s.rough,
      roughness: o.rough ?? 1,
      metalness: o.metal ?? 0,
      normalMap: s.normal,
      normalScale: new THREE.Vector2(o.normal ?? 1, o.normal ?? 1),
      clearcoat: o.clearcoat ?? 0,
      clearcoatRoughness: o.ccRough ?? 0.2,
      side: o.side ?? THREE.FrontSide,
      emissive: o.emissive ?? "#000000",
      emissiveIntensity: o.ei ?? 0,
      alphaMap: o.alphaTest ? s.alpha : null,
      alphaTest: o.alphaTest ?? 0,
      envMapIntensity: o.env ?? 1,
      sheen: o.sheen ?? 0,
      sheenRoughness: 0.8,
      sheenColor: new THREE.Color(color),
    });
    mats.set(key, m);
  }
  return m;
};
