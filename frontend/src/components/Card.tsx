/* ============================================================
   Card — обёртка над CSS-системой .card / .card--*
   Стили: frontend/src/styles/components.css (CARD SYSTEM)
   ============================================================ */

import React from 'react';

export type CardVariant =
  | 'admin'
  | 'kpi'
  | 'stats'
  | 'preset'
  | 'luxury'
  | 'appointment'
  | 'detail';

export type CardProps = React.HTMLAttributes<HTMLDivElement> & {
  variant?: CardVariant;
  children?: React.ReactNode;
  className?: string;
};

export default function Card({
  variant = 'admin',
  children,
  className,
  ...rest
}: CardProps) {
  const classes = ['card', `card--${variant}`, className].filter(Boolean).join(' ');
  return (
    <div className={classes} {...rest}>
      {children}
    </div>
  );
}
