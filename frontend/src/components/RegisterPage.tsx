import React, { useState } from 'react';
import styled, { keyframes } from 'styled-components';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { getBrandTheme, GoldButton, GhostGoldButton, GoldField } from '../design';

const orbPulse = keyframes`
  0%, 100% { transform: scale(1); filter: brightness(1) drop-shadow(0 0 8px rgba(212, 168, 75, 0.45)); }
  50% { transform: scale(1.05); filter: brightness(1.1) drop-shadow(0 0 14px rgba(224, 188, 90, 0.65)); }
`;

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
`;

const Screen = styled.div`
  position: relative;
  border-radius: 38px;
  overflow: hidden;
  background: ${brand.colors.bg.phone};
  min-height: 720px;
  display: flex;
  flex-direction: column;
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

const Brand = styled.header`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 0 16px 10px;

  .left {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .mark {
    width: 52px;
    height: 24px;
    display: flex;
    align-items: center;
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
    text-transform: uppercase;
    background: linear-gradient(180deg, #f0d9a0 0%, #d4a84b 50%, #a67c2d 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }

  .orb {
    width: 40px;
    height: 40px;
    animation: ${orbPulse} 4.2s ease-in-out infinite;
    filter: drop-shadow(0 0 10px rgba(212, 168, 75, 0.55));
    img {
      width: 100%;
      height: 100%;
      object-fit: contain;
    }
  }
`;

const TitleBlock = styled.div`
  padding: 4px 18px 12px;

  h2 {
    margin: 0;
    font-family: ${brand.fonts.ui};
    font-size: 16px;
    font-weight: 800;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    background: linear-gradient(180deg, #f0d9a0 0%, #d4a84b 50%, #a67c2d 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }

  p {
    margin: 6px 0 0;
    font-size: 13px;
    color: ${brand.colors.text.secondary};
    line-height: 1.4;
  }
`;

const Hairline = styled.div`
  height: 1px;
  background: ${brand.gradients.hairline};
`;

const FormPad = styled(motion.div)`
  padding: 14px 18px 0;
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

const ErrorText = styled.div`
  margin: 0 0 10px;
  font-size: 12px;
  color: #e74c3c;
`;

const HomeBar = styled.div`
  width: 128px;
  height: 5px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.28);
  margin: 8px auto 12px;
  flex-shrink: 0;
`;

interface RegisterPageProps {
  onRegistered?: (token: string, user: { id: number; phone: string; full_name: string; role: string }) => void;
}

export default function RegisterPage({ onRegistered }: RegisterPageProps) {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('+7');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setError('');
    if (!fullName.trim()) {
      setError('Укажите имя');
      return;
    }
    if (!phone.trim() || phone.trim().length < 10) {
      setError('Укажите корректный телефон');
      return;
    }
    if (password.length < 4) {
      setError('Пароль не короче 4 символов');
      return;
    }
    if (password !== password2) {
      setError('Пароли не совпадают');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone: phone.trim(),
          password,
          full_name: fullName.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(typeof data.detail === 'string' ? data.detail : 'Не удалось зарегистрироваться');
        return;
      }
      localStorage.setItem('token', data.token);
      onRegistered?.(data.token, data.user);
      navigate('/concept');
    } catch {
      setError('Нет связи с сервером. Проверьте, что backend запущен.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Shell>
      <Phone
        initial={{ opacity: 0, y: 18 }}
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

            <TitleBlock>
              <h2>Регистрация</h2>
              <p>Создайте аккаунт клиента — телефон и пароль для входа в приложение.</p>
            </TitleBlock>

            <FormPad
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.35 }}
            >
              <GoldField $theme={brand}>
                <span>Имя</span>
                <input
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Как к вам обращаться"
                  autoComplete="name"
                />
              </GoldField>

              <GoldField $theme={brand}>
                <span>Телефон</span>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+7 (999) 999-99-99"
                  autoComplete="tel"
                />
              </GoldField>

              <GoldField $theme={brand}>
                <span>Пароль</span>
                <PasswordWrap>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Минимум 4 символа"
                    autoComplete="new-password"
                  />
                  <button type="button" onClick={() => setShowPassword((v) => !v)}>
                    {showPassword ? 'Скрыть' : 'Показать'}
                  </button>
                </PasswordWrap>
              </GoldField>

              <GoldField $theme={brand}>
                <span>Повтор пароля</span>
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password2}
                  onChange={(e) => setPassword2(e.target.value)}
                  placeholder="Повторите пароль"
                  autoComplete="new-password"
                />
              </GoldField>

              {error ? <ErrorText>{error}</ErrorText> : null}

              <GoldButton
                $theme={brand}
                type="button"
                whileTap={{ scale: 0.975 }}
                onClick={submit}
                disabled={loading}
              >
                {loading ? 'Создание…' : 'Создать аккаунт'}
              </GoldButton>

              <GhostGoldButton
                $theme={brand}
                type="button"
                style={{ marginTop: 11 }}
                onClick={() => navigate('/')}
              >
                Уже есть аккаунт — Войти
              </GhostGoldButton>
            </FormPad>
          </MainStack>

          <HomeBar />
        </Screen>
      </Phone>
    </Shell>
  );
}
