/* ============================================================
   Badge — обёртка над CSS-системой .badge / .badge--*
   Стили: frontend/src/styles/components.css (BADGE SYSTEM)
   ============================================================ */

import React from 'react';

export type BadgeVariant =
  | 'success'
  | 'warning'
  | 'danger'
  | 'info'
  | 'neutral'
  | 'gold';

export type BadgeSize = 'sm' | 'lg';

export type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
  variant?: BadgeVariant;
  size?: BadgeSize;
  children?: React.ReactNode;
  className?: string;
};

export default function Badge({
  variant = 'neutral',
  size,
  children,
  className,
  ...rest
}: BadgeProps) {
  const classes = [
    'badge',
    `badge--${variant}`,
    size ? `badge--${size}` : null,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <span className={classes} {...rest}>
      {children}
    </span>
  );
}
