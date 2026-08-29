import React from 'react';
import { motion, type HTMLMotionProps } from 'framer-motion';
import styled from 'styled-components';
import type { BrandTheme } from '../tokens';

type ThemeProp = { $theme?: BrandTheme };

/** CTA логина: те же классы, что у <Button look="gold">. Смена .btn-gold / темы меняет и кабинет, и вход. */
export const GoldButton = React.forwardRef<
  HTMLButtonElement,
  HTMLMotionProps<'button'> & ThemeProp
>(function GoldButton({ $theme: _theme, className, type = 'button', ...rest }, ref) {
  return (
    <motion.button
      ref={ref}
      type={type}
      className={['btn-gold', 'btn-gold-cta', className].filter(Boolean).join(' ')}
      {...rest}
    />
  );
});

/** Вторичная: те же классы, что у <Button look="ghost"> */
export const GhostGoldButton = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & ThemeProp
>(function GhostGoldButton({ $theme: _theme, className, type = 'button', ...rest }, ref) {
  return (
    <button
      ref={ref}
      type={type}
      className={['btn-gold-secondary', 'btn-gold-cta', className].filter(Boolean).join(' ')}
      {...rest}
    />
  );
});

/** Поле ввода — GoldField. Цвета из CSS-переменных бренда. */
export const GoldField = styled.label<{ $theme?: BrandTheme }>`
  display: block;
  margin-bottom: 12px;

  span {
    display: block;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--brand-label, ${({ $theme }) => $theme?.colors.text.label ?? '#9a8b6f'});
    margin-bottom: 7px;
  }

  input {
    width: 100%;
    box-sizing: border-box;
    padding: 14px 15px;
    border-radius: var(--radius-md, ${({ $theme }) => $theme?.radii.md ?? '10px'});
    border: 1px solid var(--brand-input-border, ${({ $theme }) => $theme?.colors.accent.border ?? 'rgba(212,168,75,0.45)'});
    background: var(--brand-input-bg, ${({ $theme }) => $theme?.colors.bg.input ?? '#1a1a1a'});
    color: var(--color-white, ${({ $theme }) => $theme?.colors.text.primary ?? '#fff'});
    font-size: 15px;
    font-family: var(--font-family, ${({ $theme }) => $theme?.fonts.ui ?? 'inherit'});
    outline: none;

    &:focus {
      border-color: var(--color-gold, ${({ $theme }) => $theme?.colors.accent.solid ?? '#d4af37'});
      box-shadow: ${({ $theme }) => $theme?.shadows.inputFocus ?? '0 0 0 2px rgba(212,168,75,0.25)'};
    }
  }
`;

/** Зарезервировано: SilverButton — появится с пресетом silver */
export const SilverButton = GoldButton;
