import React, { useEffect, useState } from 'react';
import styled from 'styled-components';
import { GoldButton, GhostGoldButton } from './design';

const Bar = styled.div`
  position: fixed;
  left: 12px;
  right: 12px;
  bottom: 72px;
  z-index: 40;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: ${({ theme }) => theme.radii.lg};
  background: ${({ theme }) => theme.brand.colors.bg.elevated};
  border: 1px solid ${({ theme }) => theme.brand.colors.accent.border};
`;

const Copy = styled.div`
  font-size: 13px;
  line-height: 1.35;
  color: ${({ theme }) => theme.brand.colors.accent.solid};
`;

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: string }>;
};

function isStandalone(): boolean {
  const nav = window.navigator as Navigator & { standalone?: boolean };
  return window.matchMedia('(display-mode: standalone)').matches || nav.standalone === true;
}

function isIos(): boolean {
  return /iphone|ipad|ipod/i.test(window.navigator.userAgent);
}

export default function PwaInstallBanner() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [iosHint, setIosHint] = useState(false);
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    if (isStandalone()) return;
    const onPrompt = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
    };
    window.addEventListener('beforeinstallprompt', onPrompt);
    if (isIos()) setIosHint(true);
    return () => window.removeEventListener('beforeinstallprompt', onPrompt);
  }, []);

  if (hidden || isStandalone()) return null;
  if (!deferred && !iosHint) return null;

  const install = async () => {
    if (!deferred) return;
    await deferred.prompt();
    setDeferred(null);
    setHidden(true);
  };

  return (
    <Bar>
      <Copy>
        {deferred
          ? 'Установить на экран Домой — как приложение салона.'
          : 'Поделиться → На экран «Домой»'}
      </Copy>
      {deferred ? (
        <GoldButton type="button" onClick={install}>
          Установить
        </GoldButton>
      ) : (
        <GhostGoldButton type="button" onClick={() => setHidden(true)}>
          Понятно
        </GhostGoldButton>
      )}
    </Bar>
  );
}
