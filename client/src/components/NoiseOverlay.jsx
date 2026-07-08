import React from 'react';
import useLowPowerMode from '../hooks/useLowPowerMode';

const NoiseOverlay = () => {
  const lowPower = useLowPowerMode();

  // The full-viewport SVG feTurbulence filter with mix-blend-mode: overlay
  // re-blends the entire screen every frame — skip it for reduced-motion users.
  if (lowPower) return null;

  return (
    <>
      {/* Dynamic Fluid Mesh Background */}
      <div className="app-bg-mesh" />

      {/* SVG Noise Texture for Glassmorphism 2.0 */}
      <svg
        className="noise-overlay"
        /* opacity + blend live in index.css (.noise-overlay) so the mobile GPU
           tier can swap the whole-screen blend for plain alpha. */
        style={{ pointerEvents: 'none', position: 'fixed', inset: 0, zIndex: 9999, width: '100%', height: '100%' }}
      >
        <filter id="noiseFilter">
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.8"
            numOctaves="3"
            stitchTiles="stitch"
          />
        </filter>
        <rect width="100%" height="100%" filter="url(#noiseFilter)" />
      </svg>
    </>
  );
};

export default NoiseOverlay;
