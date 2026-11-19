// CastStill: the HUSS HUSS cast together on the town street (premium day light), for look-dev stills.
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { View } from "../engine/core/View";
import { aim } from "../engine/core/rig";
import { Blocky } from "../blocky/Blocky";
import { Blob } from "../blocky/Contact";
import { World } from "../blocky/World";
import type { V3 } from "../blocky/motion";
import { alive, blinkAt } from "../library/characters";
import { HUSS_CAST, signature } from "../library/huss_cast";
import { moodFor } from "../library/mood";
import { GrassField, Skyline, Traffic, WIND } from "../library/town";

export const CAST_FRAMES = 90;
const SPOT: Record<string, [number, number, number]> = { bea: [-0.8, 1.25, -0.45], mo: [0.0, 1.45, 0], gus: [1.12, 1.0, 0.3] };
const SUBJECT: V3 = [0.12, 0.82, 1.2];
const LENS: V3 = [0.35, 1.25, 7.9];

export const CastStill: React.FC = () => {
  const t = useCurrentFrame() / 30;
  WIND.value = t;
  const k = 1 - 0.06 * t; // slow push-in
  const cam = aim([SUBJECT[0] + (LENS[0] - SUBJECT[0]) * k, SUBJECT[1] + (LENS[1] - SUBJECT[1]) * k, SUBJECT[2] + (LENS[2] - SUBJECT[2]) * k], SUBJECT, 44, 0.56);
  const mood = moodFor("earth", "cast", aim(LENS, SUBJECT, 44, 0.5));
  return (
    <AbsoluteFill style={{ background: "#6aa6f2" }}>
      <View mood={mood} cam={cam} t={t} blur={0}>
        <World />
        <GrassField x0={-4} x1={4} z0={-0.85} z1={5} n={26000} />
        <Traffic t={t} />
        <Skyline />
        {HUSS_CAST.map((c, i) => {
          const [x, z, yaw] = SPOT[c.key];
          const a = alive({ key: c.key, look: c.look, pose: signature(c.key, x, z, yaw, c.s), emotion: c.emotion, s: c.s, blinkSeed: i + 1 }, t);
          return (
            <React.Fragment key={c.key}>
              <Blocky pose={a.pose} look={a.look} emotion={a.emotion} blink={blinkAt(t, a.blinkSeed)} scale={a.s} />
              <Blob p={[x, 0, z]} sx={0.95 * c.s} sz={0.7 * c.s} yaw={-yaw} op={0.55} />
            </React.Fragment>
          );
        })}
      </View>
    </AbsoluteFill>
  );
};
