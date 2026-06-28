import React from 'react';
import useLowPowerMode from '../hooks/useLowPowerMode';

const NoiseOverlay = () => {
  const lowPower = useLowPowerMode();

  // The full-viewport SVG feTurbulence filter with mix-blend-mode: overlay
  // forces the browser to re-blend the entire screen every frame — a top cause
  // of mobile jank/hang. Skip the whole overlay on mobile/touch/reduced-motion.
  if (lowPower) return null;

  return (
    <>
      {/* Dynamic Fluid Mesh Background */}
      <div className="app-bg-mesh" />

      {/* SVG Noise Texture for Glassmorphism 2.0 */}
      <svg
        className="pointer-events-none fixed inset-0 z-50 h-full w-full opacity-[0.03] mix-blend-overlay"
        style={{ pointerEvents: 'none', position: 'fixed', inset: 0, zIndex: 9999, width: '100%', height: '100%', opacity: 0.03, mixBlendMode: 'overlay' }}
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
