import React, { useId } from 'react';

/** Золотой силуэт спорткара — как на пресетах center/right (goldGlow / goldMetal) */
export function GoldCarLogo({
  width = 48,
  height = 22,
  className,
}: {
  width?: number;
  height?: number;
  className?: string;
}) {
  const uid = useId().replace(/:/g, '');
  const strokeId = `goldCarStroke-${uid}`;
  const fillId = `goldCarFill-${uid}`;

  return (
    <svg
      className={className}
      width={width}
      height={height}
      viewBox="0 0 96 40"
      fill="none"
      aria-hidden
    >
      <defs>
        <linearGradient id={strokeId} x1="4" y1="8" x2="90" y2="32">
          <stop stopColor="#F5E0A8" />
          <stop offset="0.45" stopColor="#D4A84B" />
          <stop offset="1" stopColor="#A67C2D" />
        </linearGradient>
        <linearGradient id={fillId} x1="10" y1="12" x2="86" y2="36">
          <stop stopColor="#D4A84B" stopOpacity="0.22" />
          <stop offset="1" stopColor="#D4A84B" stopOpacity="0.05" />
        </linearGradient>
      </defs>

      <path
        d="M6 24c3.5-7 10-11.5 20-13L32 5h28l7 6c9 1.2 17 5 21 12.5l2 5.5H4.5L6 24Z"
        fill={`url(#${fillId})`}
        stroke={`url(#${strokeId})`}
        strokeWidth="2"
        strokeLinejoin="round"
      />

      <path
        d="M34 6.2 37.5 11.2h23L57.5 6.2"
        stroke={`url(#${strokeId})`}
        strokeWidth="1.4"
        strokeLinejoin="round"
        opacity="0.85"
      />

      <path d="M14 18.5h66M11 23h72" stroke={`url(#${strokeId})`} strokeWidth="1.1" opacity="0.45" />

      <circle cx="24" cy="29.5" r="5" stroke={`url(#${strokeId})`} strokeWidth="1.8" fill="#050505" />
      <circle cx="70" cy="29.5" r="5" stroke={`url(#${strokeId})`} strokeWidth="1.8" fill="#050505" />
      <circle cx="24" cy="29.5" r="1.7" fill="#E0BC5A" />
      <circle cx="70" cy="29.5" r="1.7" fill="#E0BC5A" />

      <ellipse cx="10" cy="22.5" rx="2.2" ry="1.6" fill="#F0D9A0" />
    </svg>
  );
}

export default GoldCarLogo;
