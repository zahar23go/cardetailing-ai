import styled from 'styled-components';
import { motion } from 'framer-motion';
import type { BrandTheme } from '../tokens';

/** Основная CTA — GoldButton */
export const GoldButton = styled(motion.button)<{ $theme: BrandTheme }>`
  width: 100%;
  border: none;
  border-radius: ${({ $theme }) => $theme.radii.lg};
  padding: 16px;
  font-family: ${({ $theme }) => $theme.fonts.display};
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: ${({ $theme }) => $theme.colors.text.onAccent};
  cursor: pointer;
  background: ${({ $theme }) => $theme.gradients.goldButton};
  box-shadow: ${({ $theme }) => $theme.shadows.goldButton};
`;

/** Вторичная — GhostGoldButton (контур) */
export const GhostGoldButton = styled.button<{ $theme: BrandTheme }>`
  width: 100%;
  border: 1px solid ${({ $theme }) => $theme.colors.accent.border};
  background: transparent;
  color: ${({ $theme }) => $theme.colors.accent.soft};
  border-radius: ${({ $theme }) => $theme.radii.lg};
  padding: 13px;
  font-family: ${({ $theme }) => $theme.fonts.ui};
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
`;

/** Поле ввода — GoldField */
export const GoldField = styled.label<{ $theme: BrandTheme }>`
  display: block;
  margin-bottom: 12px;

  span {
    display: block;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: ${({ $theme }) => $theme.colors.text.label};
    margin-bottom: 7px;
  }

  input {
    width: 100%;
    box-sizing: border-box;
    padding: 14px 15px;
    border-radius: ${({ $theme }) => $theme.radii.md};
    border: 1px solid ${({ $theme }) => $theme.colors.accent.border};
    background: ${({ $theme }) => $theme.colors.bg.input};
    color: ${({ $theme }) => $theme.colors.text.primary};
    font-size: 15px;
    font-family: ${({ $theme }) => $theme.fonts.ui};
    outline: none;

    &:focus {
      border-color: ${({ $theme }) => $theme.colors.accent.solid};
      box-shadow: ${({ $theme }) => $theme.shadows.inputFocus};
    }
  }
`;

/** Зарезервировано: SilverButton — появится с пресетом silver */
export const SilverButton = styled(GoldButton)`
  /* временно наследует GoldButton; при появлении silver-темы переопределить градиент */
`;
