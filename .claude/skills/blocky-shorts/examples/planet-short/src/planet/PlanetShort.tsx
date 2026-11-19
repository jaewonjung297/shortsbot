// "The Planet That Talks Back": 60.5 s, 49 word-anchored shots with hard cuts (plan/SHOTS.md), pop-in white captions
// at 68 % of the height (PopCaptions). PlanetSub renders SUB sub-frames per output frame for motion blur (render.sh
// averages them). The shot is chosen by the OUTPUT frame, time by the sub-frame; captions are keyed to the output frame.
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import * as THREE from "three";
import { subFrame, useFonts } from "../engine/core/frame";
import { makeChunks } from "../engine/core/captions";
import { View } from "../engine/core/View";
import { Blocky } from "../blocky/Blocky";
import { Blob } from "../blocky/Contact";
import { geoOf, plastic } from "../blocky/mat";
import { World } from "../blocky/World";
import type { V3 } from "../blocky/motion";
import { DURATION, LAST_WORD_END, WORDS } from "../plan.gen";
import { blinkAt, carAt, LIFT, sandwichAt, stageOf } from "./cast";
import { Debris, Dust, Glints, SmokeTrail, Sparks } from "./fx";
import { GrassField, Skyline, Traffic, WIND } from "./town";
import type { Stage } from "./cast";
import { isEnding, moodFor } from "./mood";
import { Catalog, Message, RocketCar } from "./props";
import { Earth } from "./planets";
import { PopCaptions } from "./PopCaptions";
import { EARTH_IN_JAR_Y, Outside, PopHouse, Room, ROOM, Store, STORE } from "./sets";
import { camAt, PLAN_SHOTS, shotIndexAt } from "./shots";

export const PLANET_FRAMES = DURATION;
const CHUNKS = makeChunks(WORDS, LAST_WORD_END + 0.35);

const Sparkles: React.FC<{ p: V3; t: number }> = ({ p, t }) => (
  <>
    {Array.from({ length: 9 }, (_, i) => {
      const a = (i / 9) * Math.PI * 2 + t * 1.5;
      const r = 0.16 + 0.04 * Math.sin(t * 5 + i);
      const s = 0.5 + 0.5 * Math.sin(t * 9 + i * 1.7);
      return (
        <mesh key={i} geometry={geoOf("spark", () => new THREE.OctahedronGeometry(0.018, 0))} material={plastic("#fff2a0", { emissive: "#fff2a0", ei: 3.5 })} position={[p[0] + Math.cos(a) * r, p[1] + 0.05 + Math.sin(a) * r * 0.8, p[2] + Math.sin(a) * 0.05]} scale={0.6 + s} rotation={[t * 3, t * 2, 0]} />
      );
    })}
  </>
);

// S30: crumbs torn off the sandwich in bursts, flying and landing in the grass (they stay)
const Crumbs: React.FC<{ a: number; t: number }> = ({ a, t }) => {
  const out: React.ReactNode[] = [];
  for (let k = 0; ; k++) {
    const te = a + 0.08 + k * 0.15;
    if (te > t) break;
    out.push(<Debris key={k} t={t} t0={te} p={sandwichAt(a, te)} n={5} seed={k + 300} color="#f0c890" crumb k={0.55} ground={0.01} cone={1.2} />);
  }
  return <>{out}</>;
};
// S31: the launch: rocket fire on the car, a smoke trail from the nozzle (a ground cloud at lift-off), sparks and
// embers, a dust ring + soil chips at lift-off, a scorched glowing patch on the lawn
const CAR_ROT = new THREE.Euler(0, 0.4, Math.PI / 2);
const nozzleOf = (p: V3): { pos: V3; dir: V3 } => {
  const M = new THREE.Matrix4().compose(new THREE.Vector3(...p), new THREE.Quaternion().setFromEuler(CAR_ROT), new THREE.Vector3(0.8, 0.8, 0.8));
  const n = new THREE.Vector3(-1.45, 0.42, 0).applyMatrix4(M);
  const d = new THREE.Vector3(-1, 0, 0).applyEuler(CAR_ROT).normalize();
  return { pos: [n.x, n.y, n.z], dir: [d.x, d.y, d.z] };
};
const Launch: React.FC<{ id: string; t: number; car: { p: V3; flame: number } }> = ({ id, t, car }) => {
  const a = PLAN_SHOTS.find((x) => x.id === id)!.t;
  const at = (te: number) => nozzleOf(carAt(a, te).p);
  const pad: V3 = [0.2, 0.0, 1.4];
  const heat = Math.max(0, 1 - Math.max(0, t - a - LIFT) * 0.8);
  return (
    <>
      <RocketCar p={car.p} rot={[CAR_ROT.x, CAR_ROT.y, CAR_ROT.z]} flame={car.flame} s={0.8} t={t} />
      <SmokeTrail t={t} t0={a - 0.25} pos={(te) => at(te).pos} dir={at(t).dir} k={1.1} ground={0.02} />
      <Sparks t={t} t0={a - 0.2} pos={(te) => at(te).pos} dir={at(t).dir} k={1} ground={0.01} />
      <Dust t={t} t0={a + LIFT} p={[pad[0], 0.03, pad[2]]} k={1.7} seed={41} n={26} color={[0.82, 0.76, 0.66]} />
      <Debris t={t} t0={a + LIFT} p={[pad[0], 0.05, pad[2]]} n={14} seed={77} color="#5a3a22" k={1.4} ground={0.004} />
      <mesh geometry={geoOf("scorch", () => new THREE.CircleGeometry(0.55, 32))} material={plastic("#1a120c", { transparent: true, opacity: 0.75, rough: 1, cc: 0 })} position={[pad[0], 0.006, pad[2]]} rotation={[-Math.PI / 2, 0, 0]} renderOrder={2} />
      <mesh geometry={geoOf("scorchGlow", () => new THREE.CircleGeometry(0.3, 32))} material={plastic("#ff6a20", { transparent: true, opacity: 0.8 * heat, emissive: "#ff5a10", ei: 2.5 * heat, cc: 0 })} position={[pad[0], 0.008, pad[2]]} rotation={[-Math.PI / 2, 0, 0]} renderOrder={2} />
    </>
  );
};

// the whisper scene (S17-S22): one warm shaft on the speakers
const WHISPER_SPOT: Record<string, V3> = { S17: [3.2, 0, 1.0], S18: [3.2, 0, 1.0], S19: [2.4, 0, 1.0], S20: [2.4, 0, 1.0], S21: [-0.2, 0, -0.72], S22: [-0.42, 0, -0.72] };
const SetFor: React.FC<{ set: string; id: string; st: Stage; t: number }> = ({ set, id, st, t }) => {
  if (set === "store" || set === "store2")
    return (
      <>
        <Store t={t} earth={(st.earthOnShelf ?? true) ? <Earth r={0.1} spin={t * 0.2} dusty clouds={false} /> : null} tag99={st.tag99} poster={st.poster} storm={st.storm} whisper={WHISPER_SPOT[id] ?? null} gold={isEnding(id)} />
        {st.catalog ? <Catalog p={[STORE.counter[0] + 0.15, 0.985, STORE.counter[2]]} yaw={-Math.PI / 2} price={st.catalog.price} strike={st.catalog.strike} /> : null}
      </>
    );
  if (set === "home" || set === "jar") {
    const je = st.jarEarth ?? { spin: t * 0.3, lights: 0.4 };
    const J = ROOM.jar;
    return (
      <>
        <Room t={t} gold={isEnding(id)} jarGlow={st.jarGlow ?? 0.6} lamp={isEnding(id) ? 1.6 : 1} earth={<Earth r={0.1} spin={je.spin} cloudSpin={je.spin * 1.4 + t * 0.25} lights={je.lights} hi={je.hi} glow={1.3} />} />
        {st.message !== undefined ? <Message p={[J[0], J[1] + EARTH_IN_JAR_Y + 0.1 + 0.2 * st.message, J[2] + 0.02]} text={["IS ANYONE", "OUT THERE?"]} w={0.3} op={st.message} /> : null}
        {st.carInJar ? <RocketCar p={[J[0] + Math.cos(t * 1.4) * 0.125, J[1] + EARTH_IN_JAR_Y + 0.06, J[2] + Math.sin(t * 1.4) * 0.125]} rot={[0.3, -t * 1.4, 0.4]} s={0.03} flame={0.8} t={t} light={0.15} /> : null}
      </>
    );
  }
  if (set === "earth") {
    WIND.value = t;
    return (
      <>
        <World night={st.night} />
        <GrassField x0={-5} x1={5} z0={-0.85} z1={6.6} n={34000} />
        <Traffic t={t} night={st.night} />
        <Skyline night={st.night} />
        {st.houses !== undefined
          ? ([[-1.4, 1.0, "#f2d36b", "#7a3b2e", 0, 0], [1.9, 0.6, "#8fc4e8", "#3c4a66", 0.25, 1], [0.4, -0.3, "#f4efe4", "#b2452f", 0.45, 0], [3.0, 2.0, "#c8664a", "#5a3a2e", 0.6, 1], [-2.8, 2.4, "#b9e0a8", "#7a3b2e", 0.75, 0]] as [number, number, string, string, number, number][]).map(([x, z, w, r, d, br], i) => (
              <PopHouse key={i} p={[x, 0, z]} tau={st.houses!} t0={d * 0.62} wall={w} roof={r} s={0.85} yaw={0.3 * i} seed={i + 1} brick={!!br} />
            ))
          : null}
        {st.crumbs ? <Crumbs a={PLAN_SHOTS.find((x) => x.id === id)!.t} t={t} /> : null}
        {st.car ? <Launch id={id} t={t} car={st.car} /> : null}
      </>
    );
  }
  return <Outside t={t} />;
};

export const PlanetShort: React.FC<{ sub?: boolean }> = ({ sub = false }) => {
  const fonts = useFonts();
  const g = useCurrentFrame();
  const n0 = sub ? Math.floor(g / 4) : g;
  const i = shotIndexAt(n0);
  const { n, fp } = sub ? subFrame(g, 4, 0.35) : { n: g, fp: g };
  const t = fp / 30;
  const s = PLAN_SHOTS[i];
  const st = stageOf(s.id, s.t, t);
  const cam = camAt(i, t, st);
  const mood = moodFor(s.set, s.id, camAt(i, s.t, stageOf(s.id, s.t, s.t)), st.night);
  if (!fonts) return <AbsoluteFill style={{ background: "#160f48" }} />;
  return (
    <AbsoluteFill style={{ background: "#160f48" }}>
      <View mood={mood} cam={cam} t={t} blur={0}>
        <SetFor set={s.set} id={s.id} st={st} t={t} />
        {st.actors.map((a) => (
          <React.Fragment key={a.key}>
            <Blocky pose={a.pose} look={a.look} emotion={a.emotion} blink={a.emotion !== "love" && blinkAt(t, a.blinkSeed)} held={a.held} chest={a.chest} scale={a.s} fx={a.fx} />
            <Blob p={[a.pose.x, 0, a.pose.z]} sx={0.95 * a.s} sz={0.7 * a.s} yaw={-a.pose.yaw} op={a.pose.y > 0.9 ? 0.3 : 0.6} />
          </React.Fragment>
        ))}
        {st.sparkle ? <><Sparkles p={st.sparkle} t={t} /><Glints p={st.sparkle} t={t} /></> : null}
        {st.puff ? <Dust t={t} t0={st.puff.t0} p={st.puff.p} k={st.puff.k} seed={11} n={14} color={[0.8, 0.74, 0.66]} /> : null}
      </View>
      <PopCaptions chunks={CHUNKS} t={n / 30} until={LAST_WORD_END + 0.35} />
    </AbsoluteFill>
  );
};
