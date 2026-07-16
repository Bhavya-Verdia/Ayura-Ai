import React from 'react';
import useLowPowerMode from '../hooks/useLowPowerMode';

/* Grain tile: feTurbulence rendered ONCE into a 220px repeating texture.
   Never mount a full-viewport <svg><feTurbulence> for grain — at Retina DPR
   the live filter rasters a screen-sized noise field on the main thread, and
   any invalidation re-runs it (whole-screen flicker under GPU pressure).
   Same pattern as .vital-noise-field in index.css. */
const NOISE_TILE =
  "data:image/svg+xml,%3Csvg viewBox='0 0 220 220' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E";

const NoiseOverlay = () => {
  const lowPower = useLowPowerMode();

  // Decorative grain — skip it for reduced-motion users.
  if (lowPower) return null;

  return (
    <>
      {/* Dynamic Fluid Mesh Background */}
      <div className="app-bg-mesh" />

      {/* Grain over content for Glassmorphism 2.0 (opacity in index.css) */}
      <div
        className="noise-overlay"
        aria-hidden="true"
        style={{
          pointerEvents: 'none',
          position: 'fixed',
          inset: 0,
          zIndex: 9999,
          backgroundImage: `url("${NOISE_TILE}")`,
        }}
      />
    </>
  );
};

export default NoiseOverlay;
