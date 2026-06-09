export function SkeletonLine({ width = '100%', height = '14px', style = {} }) {
  return (
    <div
      className="skeleton-line"
      style={{ width, height, borderRadius: '6px', ...style }}
    />
  )
}

export function SkeletonCircle({ size = '40px', style = {} }) {
  return (
    <div
      className="skeleton-line"
      style={{ width: size, height: size, borderRadius: '50%', flexShrink: 0, ...style }}
    />
  )
}

