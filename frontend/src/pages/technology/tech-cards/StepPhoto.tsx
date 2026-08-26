/**
 * Фото шага техкарты: миниатюра в карточке, полный кадр на просмотре, клик — увеличить.
 */
import React from 'react';
import { Image } from 'antd';

type StepPhotoProps = {
  src: string;
  alt: string;
  size?: 'thumb' | 'full';
};

export default function StepPhoto({ src, alt, size = 'full' }: StepPhotoProps) {
  const isThumb = size === 'thumb';
  return (
    <div className={`tech-card-step-photo-wrap tech-card-step-photo-wrap--${size}`}>
      <Image
        src={src}
        alt={alt}
        className={`tech-card-step-photo ${isThumb ? 'tech-card-step-photo--sm' : 'tech-card-step-photo--full'}`}
        wrapperClassName="tech-card-step-photo-inner"
        width={isThumb ? 120 : '100%'}
        preview={{ mask: 'Увеличить' }}
      />
    </div>
  );
}
