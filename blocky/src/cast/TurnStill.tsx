// TurnStill: a turnaround of the HUSS HUSS cast. Frame f shows character floor(f / 4) from view f % 4:
// front, its right side, back, its left side. Neutral pose, arms slightly out, so the silhouette reads.
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { View } from "../engine/core/View";
import { aim } from "../engine/core/rig";
import { Blocky } from "../blocky/Blocky";
import { Blob } from "../blocky/Contact";
import { World } from "../blocky/World";
import type { V3 } from "../blocky/motion";
import { base, faceH } from "../library/characters";
import { HUSS_CAST } from "../library/huss_cast";
import { moodFor } from "../library/mood";
import { GrassField } from "../library/town";

export const TURN_FRAMES = HUSS_CAST.length * 4;
const VIEWS = [0, -Math.PI / 2, Math.PI, Math.PI / 2];
const AT: [number, number] = [0, 1.6];

export const TurnStill: React.FC = () => {
  const f = Math.min(useCurrentFrame(), TURN_FRAMES - 1);
  const c = HUSS_CAST[Math.floor(f / 4)];
  const yaw = VIEWS[f % 4];
  const subj: V3 = [AT[0], (faceH(c.s) * 0.55), AT[1]];
  const lens: V3 = [AT[0] + 0.15, subj[1] + 0.35, AT[1] + 4.6];
  const cam = aim(lens, subj, 38, 0.5);
  const mood = moodFor("earth", "turn", cam);
  const pose = base(AT[0], AT[1], yaw, c.s, { outL: 0.28, outR: 0.28, armL: 0.08, armR: 0.08 });
  return (
    <AbsoluteFill style={{ background: "#6aa6f2" }}>
      <View mood={mood} cam={cam} t={0} blur={0}>
        <World />
        <GrassField x0={-2.5} x1={2.5} z0={-0.85} z1={4} n={14000} />
        <Blocky pose={pose} look={c.look} emotion={c.emotion} scale={c.s} />
        <Blob p={[AT[0], 0, AT[1]]} sx={0.95 * c.s} sz={0.7 * c.s} yaw={-yaw} op={0.55} />
      </View>
    </AbsoluteFill>
  );
};
