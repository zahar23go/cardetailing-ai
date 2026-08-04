import React from 'react';
import styled from 'styled-components';
import { useNavigate } from 'react-router-dom';
import { useBrand } from '../design';
import { GoldButton, GhostGoldButton } from '../design/components/BrandControls';

const Shell = styled.div`
  min-height: 100vh;
  min-height: 100dvh;
  background: ${({ theme }) => theme.brand.gradients.pageAtmosphere};
  color: ${({ theme }) => theme.colors.text.primary};
  font-family: ${({ theme }) => theme.fonts.primary};
  padding: 28px 16px 48px;
`;

const Wrap = styled.div`
  max-width: 920px;
  margin: 0 auto;
`;

const Top = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 28px;

  h1 {
    margin: 0;
    font-family: ${({ theme }) => theme.fonts.display};
    font-size: 22px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: ${({ theme }) => theme.brand.colors.accent.solid};
  }

  p {
    margin: 8px 0 0;
    max-width: 520px;
    color: ${({ theme }) => theme.colors.text.secondary};
    font-size: 14px;
    line-height: 1.45;
  }
`;

const Actions = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 14px;
  margin-bottom: 24px;
`;

const Card = styled.button`
  text-align: left;
  border: 1px solid ${({ theme }) => theme.brand.colors.accent.border};
  background: ${({ theme }) => theme.brand.colors.bg.elevated};
  border-radius: ${({ theme }) => theme.radii.lg};
  padding: 16px;
  cursor: pointer;
  color: inherit;
  font-family: inherit;
  transition: border-color 0.2s ease, transform 0.15s ease;

  &:hover {
    border-color: ${({ theme }) => theme.brand.colors.accent.solid};
    transform: translateY(-1px);
  }

  .title {
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-size: 13px;
    color: ${({ theme }) => theme.brand.colors.accent.solid};
  }

  .desc {
    margin-top: 8px;
    font-size: 13px;
    color: ${({ theme }) => theme.colors.text.secondary};
    line-height: 1.4;
  }
`;

const Panel = styled.section`
  border: 1px solid ${({ theme }) => theme.brand.colors.accent.border};
  border-radius: ${({ theme }) => theme.radii.lg};
  background: ${({ theme }) => theme.brand.colors.bg.phone};
  padding: 16px;
  overflow: hidden;

  h2 {
    margin: 0 0 12px;
    font-size: 13px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: ${({ theme }) => theme.brand.colors.text.label};
  }
`;

const PdfFrame = styled.iframe`
  width: 100%;
  height: min(72vh, 820px);
  border: 0;
  border-radius: 12px;
  background: #111;
`;

const SCREENS = [
  {
    title: 'Главный экран',
    desc: 'Макет клиента П3.1 — авто, запись, AI Детейлер',
    path: '/main',
  },
  {
    title: 'Вход',
    desc: 'Экран логина с телефоном и паролем',
    path: '/',
  },
  {
    title: 'Регистрация',
    desc: 'Создание аккаунта нового клиента',
    path: '/register',
  },
  {
    title: 'Брендинг',
    desc: 'Пресеты goldMetal / goldGlow / silver',
    path: '/settings/branding',
  },
];

interface ConceptPageProps {
  onLogout?: () => void;
  isAuthenticated?: boolean;
}

export default function ConceptPage({ onLogout, isAuthenticated }: ConceptPageProps) {
  const navigate = useNavigate();
  const { brand } = useBrand();

  return (
    <Shell>
      <Wrap>
        <Top>
          <div>
            <h1>Смотреть концепцию</h1>
            <p>
              Документ CARDET и превью экранов приложения. Отсюда можно открыть любой макет
              без тупика на главной.
            </p>
          </div>
          <Actions>
            <GoldButton
              $theme={brand}
              type="button"
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate('/main')}
              style={{ width: 'auto', minWidth: 180, padding: '0 18px' }}
            >
              Главный экран
            </GoldButton>
            {isAuthenticated ? (
              <GhostGoldButton
                $theme={brand}
                type="button"
                onClick={() => onLogout?.()}
                style={{ width: 'auto', minWidth: 140, padding: '0 16px' }}
              >
                Выйти
              </GhostGoldButton>
            ) : (
              <GhostGoldButton
                $theme={brand}
                type="button"
                onClick={() => navigate('/')}
                style={{ width: 'auto', minWidth: 140, padding: '0 16px' }}
              >
                Ко входу
              </GhostGoldButton>
            )}
          </Actions>
        </Top>

        <Grid>
          {SCREENS.map((s) => (
            <Card key={s.path} type="button" onClick={() => navigate(s.path)}>
              <div className="title">{s.title}</div>
              <div className="desc">{s.desc}</div>
            </Card>
          ))}
        </Grid>

        <Panel>
          <h2>Концепция проекта (PDF)</h2>
          <PdfFrame title="Концепция CARDET" src="/docs/concept.pdf" />
        </Panel>
      </Wrap>
    </Shell>
  );
}
