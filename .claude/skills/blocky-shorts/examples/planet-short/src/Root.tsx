import React from "react";
import { Composition } from "remotion";
import { BLOCKY_FRAMES, BlockyTest } from "./blocky/BlockyTest";
import { SUB } from "./engine/core/frame";
import { PLANET_FRAMES, PlanetShort } from "./planet/PlanetShort";

// BlockyTest: the 10 s example Short at 30 fps (sharp, for stills and look-dev).
// BlockyTestSub: the same at SUB x fps for motion blur; render.sh averages every SUB sub-frames with ffmpeg tmix.
export const Root: React.FC = () => (
  <>
    <Composition id="BlockyTest" component={BlockyTest} durationInFrames={BLOCKY_FRAMES} fps={30} width={1080} height={1920} defaultProps={{ sub: false }} />
    <Composition id="BlockyTestSub" component={BlockyTest} durationInFrames={BLOCKY_FRAMES * SUB} fps={30 * SUB} width={1080} height={1920} defaultProps={{ sub: true }} />
    {/* The Planet That Talks Back: the 60.5 s Short (Planet = sharp, for stills; PlanetSub = motion blur) */}
    <Composition id="Planet" component={PlanetShort} durationInFrames={PLANET_FRAMES} fps={30} width={1080} height={1920} defaultProps={{ sub: false }} />
    <Composition id="PlanetSub" component={PlanetShort} durationInFrames={PLANET_FRAMES * SUB} fps={30 * SUB} width={1080} height={1920} defaultProps={{ sub: true }} />
  </>
);
