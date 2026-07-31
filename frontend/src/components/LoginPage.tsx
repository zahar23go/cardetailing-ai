import React, { useState } from 'react';
import styled, { keyframes } from 'styled-components';
import { motion } from 'framer-motion';
import { useBrand } from '../design';
import { GoldButton, GhostGoldButton, GoldField } from '../design/components/BrandControls';

const orbPulse = keyframes`
  0%, 100% { transform: scale(1); filter: brightness(1) drop-shadow(0 0 8px rgba(212, 168, 75, 0.45)); }
  50% { transform: scale(1.05); filter: brightness(1.1) drop-shadow(0 0 14px rgba(224, 188, 90, 0.65)); }
`;

const shine = keyframes`
  0% { transform: translateX(-130%) skewX(-16deg); opacity: 0; }
  20% { opacity: 0.45; }
  45% { opacity: 0; }
  100% { transform: translateX(230%) skewX(-16deg); opacity: 0; }
`;

const Shell = styled.div`
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 14px;
  font-family: ${({ theme }) => theme.fonts.primary};
  background: ${({ theme }) => theme.brand.gradients.pageAtmosphere};
`;

/* Корпус телефона */
const Phone = styled(motion.div)`
  position: relative;
  width: 100%;
  max-width: 390px;
  border-radius: ${({ theme }) => theme.brand.radii.phone};
  padding: 11px;
  background: linear-gradient(145deg, #3a3a3c 0%, #1c1c1e 40%, #0a0a0a 100%);
  box-shadow: ${({ theme }) => theme.brand.shadows.phone};

  &::after {
    content: '';
    position: absolute;
    right: -2px;
    top: 140px;
    width: 3px;
    height: 64px;
    border-radius: 2px 0 0 2px;
    background: linear-gradient(180deg, #555 0%, #2a2a2a 100%);
  }
`;

const Screen = styled.div`
  position: relative;
  border-radius: 38px;
  overflow: hidden;
  background: #000;
  min-height: 720px;
  display: flex;
  flex-direction: column;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.04);
`;

const StatusBar = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 22px 0;
  height: 44px;
  position: relative;
  z-index: 5;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.02em;

  .time {
    width: 54px;
  }

  .island {
    position: absolute;
    left: 50%;
    top: 10px;
    transform: translateX(-50%);
    width: 118px;
    height: 32px;
    border-radius: 20px;
    background: #050505;
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.04);
  }

  .icons {
    display: flex;
    align-items: center;
    gap: 6px;
    width: 70px;
    justify-content: flex-end;
  }
`;

const Brand = styled.header`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 16px 10px;
  z-index: 3;

  .left {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  .mark {
    width: 48px;
    height: 22px;
    display: flex;
    align-items: center;
    flex-shrink: 0;
    filter: drop-shadow(0 0 6px rgba(212, 168, 75, 0.45));

    img {
      width: 100%;
      height: 100%;
      object-fit: contain;
      display: block;
    }
  }

  h1 {
    margin: 0;
    font-family: ${({ theme }) => theme.fonts.display};
    font-size: 12.5px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    white-space: nowrap;
    color: ${({ theme }) => theme.brand.colors.accent.solid};
  }

  .orb {
    width: 36px;
    height: 36px;
    flex-shrink: 0;
    animation: ${orbPulse} 4.2s ease-in-out infinite;

    img {
      width: 100%;
      height: 100%;
      object-fit: contain;
      display: block;
    }
  }
`;

const Hairline = styled.div`
  height: 1px;
  margin: 0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(212, 168, 75, 0.35) 30%,
    rgba(240, 217, 160, 0.55) 50%,
    rgba(212, 168, 75, 0.35) 70%,
    transparent
  );
`;

/* Авто с макета — на всю ширину экрана телефона */
const Hero = styled.div`
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  overflow: hidden;
  background: #0a0a0a;
  margin: 0;

  img.car {
    width: 100%;
    height: 100%;
    object-fit: cover;
    object-position: center 45%;
    display: block;
    transform: scale(1.02);
  }

  .vignette {
    pointer-events: none;
    position: absolute;
    inset: 0;
    background:
      linear-gradient(180deg, rgba(0, 0, 0, 0.35) 0%, transparent 18%),
      linear-gradient(180deg, transparent 55%, rgba(0, 0, 0, 0.88) 100%);
  }

  .shine {
    pointer-events: none;
    position: absolute;
    inset: 0;
    overflow: hidden;

    &::after {
      content: '';
      position: absolute;
      top: -10%;
      left: 0;
      width: 35%;
      height: 120%;
      background: linear-gradient(
        90deg,
        transparent,
        rgba(255, 240, 200, 0.08) 48%,
        rgba(255, 255, 255, 0.12) 50%,
        rgba(255, 240, 200, 0.08) 52%,
        transparent
      );
      animation: ${shine} 8s ease-in-out 1s infinite;
    }
  }
`;

const FormPad = styled(motion.div)`
  padding: 12px 18px 0;
  flex: 1;
`;

const PasswordWrap = styled.div`
  position: relative;

  input {
    padding-right: 88px;
  }

  button {
    position: absolute;
    right: 12px;
    top: 50%;
    transform: translateY(-50%);
    border: none;
    background: transparent;
    color: ${({ theme }) => theme.brand.colors.accent.solid};
    cursor: pointer;
    font-size: 12px;
    font-weight: 700;
    font-family: inherit;
  }
`;

const HomeBar = styled.div`
  width: 128px;
  height: 5px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.28);
  margin: 18px auto 10px;
`;

const SignalIcon = () => (
  <svg width="17" height="12" viewBox="0 0 17 12" fill="currentColor" aria-hidden>
    <rect x="0" y="7" width="3" height="5" rx="0.6" />
    <rect x="4.5" y="5" width="3" height="7" rx="0.6" />
    <rect x="9" y="2.5" width="3" height="9.5" rx="0.6" />
    <rect x="13.5" y="0" width="3" height="12" rx="0.6" opacity="0.35" />
  </svg>
);

const WifiIcon = () => (
  <svg width="15" height="12" viewBox="0 0 15 12" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden>
    <path d="M1 4.2c3.6-3.2 9.4-3.2 13 0" />
    <path d="M3.2 6.5c2.4-2.1 6.2-2.1 8.6 0" />
    <path d="M5.5 8.8c1.2-1 2.8-1 4 0" />
    <circle cx="7.5" cy="10.5" r="1" fill="currentColor" stroke="none" />
  </svg>
);

const BatteryIcon = () => (
  <svg width="24" height="12" viewBox="0 0 24 12" fill="none" aria-hidden>
    <rect x="0.5" y="1" width="19" height="10" rx="2.5" stroke="currentColor" strokeWidth="1.2" opacity="0.45" />
    <rect x="2" y="2.6" width="14" height="6.8" rx="1.2" fill="currentColor" />
    <path d="M21 4v4a1.6 1.6 0 0 0 0-4Z" fill="currentColor" opacity="0.45" />
  </svg>
);

interface LoginPageProps {
  onLogin?: (phone: string, password: string) => void;
  onRegister?: () => void;
  onDemo?: () => void;
}

export default function LoginPage({ onLogin, onRegister }: LoginPageProps) {
  const { brand } = useBrand();
  const [phone, setPhone] = useState('+79999999999');
  const [password, setPassword] = useState('admin123');
  const [showPassword, setShowPassword] = useState(false);

  return (
    <Shell>
      <Phone
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 110, damping: 18 }}
      >
        <Screen>
          <StatusBar>
            <span className="time">9:41</span>
            <span className="island" />
            <span className="icons">
              <SignalIcon />
              <WifiIcon />
              <BatteryIcon />
            </span>
          </StatusBar>

          <Brand>
            <div className="left">
              <span className="mark">
                <img src={`${brand.assets.logoCar}?v=5`} alt="" />
              </span>
              <h1>CAR DETAILING AI</h1>
            </div>
            <div className="orb">
              <img src={`${brand.assets.aiOrb}?v=2`} alt="" />
            </div>
          </Brand>

          <Hairline />

          <Hero>
            <img className="car" src={`${brand.assets.heroCar}?v=14`} alt="BMW X5" />
            <div className="vignette" />
            <div className="shine" />
          </Hero>

          <FormPad
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.12, duration: 0.4 }}
          >
            <GoldField $theme={brand}>
              <span>Телефон</span>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+7 (999) 999-99-99"
              />
            </GoldField>

            <GoldField $theme={brand}>
              <span>Пароль</span>
              <PasswordWrap>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
                <button type="button" onClick={() => setShowPassword((v) => !v)}>
                  {showPassword ? 'Скрыть' : 'Показать'}
                </button>
              </PasswordWrap>
            </GoldField>

            <GoldButton
              $theme={brand}
              type="button"
              style={{ marginTop: 6 }}
              whileTap={{ scale: 0.975 }}
              onClick={() => onLogin?.(phone, password)}
            >
              Войти
            </GoldButton>

            <GhostGoldButton
              $theme={brand}
              type="button"
              style={{ marginTop: 11 }}
              onClick={() => onRegister?.()}
            >
              Зарегистрироваться
            </GhostGoldButton>
          </FormPad>

          <HomeBar />
        </Screen>
      </Phone>
    </Shell>
  );
}
