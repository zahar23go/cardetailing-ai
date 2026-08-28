import React from 'react';
import { Button as AntButton, type ButtonProps as AntButtonProps } from 'antd';

export type UiButtonVariant = 'gold' | 'ghost' | 'danger' | 'default';

export type ButtonProps = Omit<AntButtonProps, 'variant'> & {
  look?: UiButtonVariant;
};

/**
 * Единая кнопка. look=gold/ghost использует уже существующие .btn-gold.
 * По умолчанию — antd (иконки в таблицах не становятся на всю ширину).
 */
export function Button({ look = 'default', className, danger, ...rest }: ButtonProps) {
  const classes = [
    look === 'gold' ? 'btn-gold' : null,
    look === 'ghost' ? 'btn-gold-secondary' : null,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <AntButton
      className={classes || undefined}
      danger={danger || look === 'danger'}
      {...rest}
    />
  );
}

export default Button;
