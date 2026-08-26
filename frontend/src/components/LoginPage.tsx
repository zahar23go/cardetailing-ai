import React, { useState } from 'react';
import styled, { keyframes } from 'styled-components';
import { motion } from 'framer-motion';
import { getBrandTheme, GoldButton, GhostGoldButton, GoldField } from '../design';

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

/* Бренд + формы с шаблона Gold Metal (другой пресет) */
const brand = getBrandTheme('goldMetal');

const Shell = styled.div`
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 14px;
  font-family: ${brand.fonts.ui};
  background: ${brand.gradients.pageAtmosphere};
`;

const Phone = styled(motion.div)`
  position: relative;
  width: 100%;
  max-width: 390px;
  border-radius: ${brand.radii.phone};
  padding: 11px;
  background: linear-gradient(145deg, #3a3a3c 0%, #1c1c1e 40%, #0a0a0a 100%);
  box-shadow: ${brand.shadows.phone};

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
  background: ${brand.colors.bg.phone};
  min-height: 720px;
  display: flex;
  flex-direction: column;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.04);
`;

const MainStack = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  width: 100%;
  min-height: 0;
  padding: 8px 0 4px;
`;

/* Формула бренда как на главном экране */
const Brand = styled.header`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 0 16px 10px;
  z-index: 3;

  .left {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
  }

  .mark {
    width: 52px;
    height: 24px;
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

  .name {
    margin: 0;
    font-family: ${brand.fonts.ui};
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 0.05em;
    line-height: 1.1;
    text-transform: uppercase;
    white-space: nowrap;
    background: linear-gradient(180deg, #f0d9a0 0%, #d4a84b 50%, #a67c2d 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }

  .orb {
    width: 40px;
    height: 40px;
    flex-shrink: 0;
    animation: ${orbPulse} 4.2s ease-in-out infinite;
    filter: drop-shadow(0 0 10px rgba(212, 168, 75, 0.55));

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
  background: ${brand.gradients.hairline};
`;

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
  flex: 0 0 auto;
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
    color: ${brand.colors.accent.solid};
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
  margin: 8px auto 12px;
  flex-shrink: 0;
`;

const Accounts = styled.div`
  margin-top: 12px;

  .caption {
    margin: 0 0 7px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: ${brand.colors.text.label};
  }

  select {
    width: 100%;
    box-sizing: border-box;
    padding: 12px 14px;
    border-radius: ${brand.radii.md};
    border: 1px solid ${brand.colors.accent.border};
    background: ${brand.colors.bg.input};
    color: ${brand.colors.text.primary};
    font-size: 13px;
    font-family: inherit;
    outline: none;
    cursor: pointer;
    appearance: auto;

    &:focus {
      border-color: ${brand.colors.accent.solid};
      box-shadow: ${brand.shadows.inputFocus};
    }
  }
`;

const DEMO_ACCOUNTS = [
  { role: 'Админ', name: 'Супер администратор', phone: '+79999999999', password: 'admin123' },
  { role: 'Клиент', name: 'Иван Петров', phone: '79501234501', password: 'password123' },
  { role: 'Клиент', name: 'Мария Соколова', phone: '79501234502', password: 'password123' },
  { role: 'Клиент', name: 'Алексей Кузнецов', phone: '79501234503', password: 'password123' },
  { role: 'Клиент', name: 'Елена Новикова', phone: '79501234504', password: 'password123' },
  { role: 'Клиент', name: 'Дмитрий Волков', phone: '79501234505', password: 'password123' },
  { role: 'Клиент', name: 'Ольга Белова', phone: '79501234506', password: 'password123' },
  { role: 'Клиент', name: 'Сергей Морозов', phone: '79501234507', password: 'password123' },
  { role: 'Мастер', name: 'Андрей Смирнов', phone: '79501234550', password: 'password123' },
  { role: 'Мастер', name: 'Максим Орлов', phone: '79501234551', password: 'password123' },
] as const;

interface LoginPageProps {
  onLogin?: (phone: string, password: string) => void;
  onRegister?: () => void;
  onDemo?: () => void;
}

export default function LoginPage({ onLogin, onRegister }: LoginPageProps) {
  const [phone, setPhone] = useState('+79999999999');
  const [password, setPassword] = useState('admin123');
  const [showPassword, setShowPassword] = useState(false);

  const fillAccount = (acc: typeof DEMO_ACCOUNTS[number]) => {
    setPhone(acc.phone);
    setPassword(acc.password);
  };

  return (
    <Shell>
      <Phone
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ type: 'spring', stiffness: 110, damping: 18 }}
      >
        <Screen>
          <MainStack>
            <Brand>
              <div className="left">
                <span className="mark">
                  <img src={`${brand.assets.logoCar}?v=21`} alt="" />
                </span>
                <h1 className="name">CAR DETAILING AI</h1>
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
              <form
                autoComplete="on"
                onSubmit={(e) => {
                  e.preventDefault();
                  onLogin?.(phone, password);
                }}
              >
                <GoldField $theme={brand}>
                  <span>Телефон</span>
                  <input
                    type="tel"
                    name="username"
                    autoComplete="username"
                    list="login-phones"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+7 (999) 999-99-99"
                  />
                  <datalist id="login-phones">
                    {DEMO_ACCOUNTS.map((acc) => (
                      <option key={acc.phone} value={acc.phone}>
                        {acc.role}: {acc.name}
                      </option>
                    ))}
                  </datalist>
                </GoldField>

                <GoldField $theme={brand}>
                  <span>Пароль</span>
                  <PasswordWrap>
                    <input
                      type={showPassword ? 'text' : 'password'}
                      name="password"
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                    />
                    <button type="button" onClick={() => setShowPassword((v) => !v)}>
                      {showPassword ? 'Скрыть' : 'Показать'}
                    </button>
                  </PasswordWrap>
                </GoldField>

                <Accounts>
                  <p className="caption">Телефоны и пароли</p>
                  <select
                    aria-label="Выбрать кабинет"
                    value={DEMO_ACCOUNTS.some((acc) => acc.phone === phone) ? phone : ''}
                    onChange={(e) => {
                      const acc = DEMO_ACCOUNTS.find((item) => item.phone === e.target.value);
                      if (acc) fillAccount(acc);
                    }}
                  >
                    <option value="" disabled>
                      Выберите кабинет…
                    </option>
                    {DEMO_ACCOUNTS.map((acc) => (
                      <option key={acc.phone} value={acc.phone}>
                        {acc.role} · {acc.phone} · {acc.password}
                      </option>
                    ))}
                  </select>
                </Accounts>

                <GoldButton
                  $theme={brand}
                  type="submit"
                  style={{ marginTop: 6 }}
                  whileTap={{ scale: 0.975 }}
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
              </form>
            </FormPad>
          </MainStack>

          <HomeBar />
        </Screen>
      </Phone>
    </Shell>
  );
}
