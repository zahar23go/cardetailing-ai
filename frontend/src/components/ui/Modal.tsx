import React from 'react';
import { Modal as AntModal, type ModalProps as AntModalProps } from 'antd';

export type ModalProps = AntModalProps;

/**
 * Общая модалка: затемнение, закрытие по клику вне (maskClosable),
 * стили .ui-modal из ui.css. Статические confirm/info — как у antd.
 */
export function Modal({ className, maskClosable = true, centered = true, ...rest }: ModalProps) {
  return (
    <AntModal
      centered={centered}
      maskClosable={maskClosable}
      className={['ui-modal', className].filter(Boolean).join(' ')}
      {...rest}
    />
  );
}

Modal.info = AntModal.info;
Modal.success = AntModal.success;
Modal.error = AntModal.error;
Modal.warning = AntModal.warning;
Modal.confirm = AntModal.confirm;
Modal.destroyAll = AntModal.destroyAll;

export default Modal;
