import React, { useMemo, useState } from 'react';
import styled from 'styled-components';
import { useNavigate } from 'react-router-dom';
import { useBrand } from '../design/BrandProvider';
import { GoldButton, GhostGoldButton, GoldField } from '../design/components/BrandControls';
import type { BrandThemeId } from '../design/tokens';
import type { SurfaceMode } from '../design/surface';

const Shell = styled.div`
  min-height: 100vh;
  min-height: 100dvh;
  background: ${({ theme }) => theme.colors.bg.primary};
  color: ${({ theme }) => theme.colors.text.primary};
  font-family: ${({ theme }) => theme.fonts.primary};
  padding: 24px 16px 48px;
`;

const Wrap = styled.div`
  max-width: 980px;
  margin: 0 auto;
`;

const Top = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
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
    margin: 6px 0 0;
    color: ${({ theme }) => theme.colors.text.secondary};
    font-size: 14px;
  }
`;

const Back = styled.button`
  flex-shrink: 0;
  border: 1px solid ${({ theme }) => theme.brand.colors.accent.border};
  background: linear-gradient(180deg, #f0d9a0 0%, #d4a84b 55%, #a67c2d 100%);
  color: #1a1610;
  border-radius: ${({ theme }) => theme.radii.md};
  padding: 10px 18px;
  cursor: pointer;
  font-family: inherit;
  font-weight: 700;
  font-size: 14px;
  box-shadow: 0 4px 14px rgba(212, 168, 75, 0.25);

  &:hover {
    filter: brightness(1.05);
  }
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
  margin-bottom: 28px;
`;

const Card = styled.button<{ $active?: boolean }>`
  text-align: left;
  border: 1px solid
    ${({ theme, $active }) =>
      $active ? theme.brand.colors.accent.solid : theme.brand.colors.accent.border};
  background: ${({ theme }) => theme.brand.colors.bg.elevated};
  border-radius: ${({ theme }) => theme.radii.lg};
  padding: 12px;
  cursor: pointer;
  color: inherit;
  box-shadow: ${({ $active, theme }) =>
    $active ? `0 0 0 2px ${theme.brand.colors.accent.muted}` : 'none'};

  img {
    width: 100%;
    aspect-ratio: 9 / 16;
    object-fit: cover;
    object-position: top center;
    border-radius: 12px;
    display: block;
    background: #000;
    margin-bottom: 10px;
  }

  .name {
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-size: 13px;
    color: ${({ theme }) => theme.brand.colors.accent.solid};
  }

  .id {
    margin-top: 4px;
    font-size: 12px;
    color: ${({ theme }) => theme.colors.text.secondary};
  }
`;

const ModeCard = styled.button<{ $active?: boolean; $mode: SurfaceMode }>`
  text-align: left;
  border: 2px solid
    ${({ theme, $active }) =>
      $active ? theme.brand.colors.accent.solid : theme.colors.border.primary};
  background: ${({ theme }) => theme.colors.bg.elevated};
  border-radius: ${({ theme }) => theme.radii.lg};
  padding: 16px;
  cursor: pointer;
  color: inherit;
  box-shadow: ${({ $active, theme }) =>
    $active ? `0 0 0 3px ${theme.brand.colors.accent.muted}` : theme.surface.shadowCard};

  .swatch {
    height: 72px;
    border-radius: 10px;
    margin-bottom: 12px;
    border: 1px solid ${({ theme }) => theme.colors.border.primary};
    background: ${({ $mode }) =>
      $mode === 'light'
        ? 'linear-gradient(90deg, #0B0D10 28%, #FFFFFF 28%), #FFFFFF'
        : 'linear-gradient(135deg, #1A1D23 40%, #282C34 40%), #282C34'};
    position: relative;
    overflow: hidden;
  }

  .swatch::after {
    content: '';
    position: absolute;
    right: 12px;
    bottom: 12px;
    width: 36px;
    height: 20px;
    border-radius: 6px;
    background: #d4af37;
  }

  .name {
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-size: 13px;
    color: ${({ theme }) => theme.brand.colors.accent.solid};
  }

  .desc {
    margin-top: 6px;
    font-size: 13px;
    color: ${({ theme }) => theme.colors.text.secondary};
    line-height: 1.4;
  }

  .badge {
    display: inline-block;
    margin-top: 10px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: ${({ $mode }) => ($mode === 'light' ? '#1A1D23' : '#F0F2F5')};
    background: ${({ $mode }) => ($mode === 'light' ? '#D4AF37' : '#3B4049')};
    padding: 4px 8px;
    border-radius: 999px;
  }
`;

const Panel = styled.section`
  border: 1px solid ${({ theme }) => theme.brand.colors.accent.border};
  border-radius: ${({ theme }) => theme.radii.lg};
  background: ${({ theme }) => theme.colors.bg.elevated};
  padding: 20px;
  margin-bottom: 20px;

  h2 {
    margin: 0 0 14px;
    font-size: 14px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: ${({ theme }) => theme.brand.colors.text.label};
  }
`;

const Row = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
`;

const FieldEdit = styled.label`
  display: block;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.brand.colors.text.label};

  input {
    margin-top: 6px;
    width: 100%;
    box-sizing: border-box;
    padding: 10px 12px;
    border-radius: ${({ theme }) => theme.radii.md};
    border: 1px solid ${({ theme }) => theme.brand.colors.accent.border};
    background: ${({ theme }) => theme.brand.colors.bg.input};
    color: ${({ theme }) => theme.colors.text.primary};
    font-family: inherit;
  }
`;

const Preview = styled.div`
  max-width: 360px;
`;

const Note = styled.p`
  margin: 0 0 16px;
  font-size: 13px;
  color: ${({ theme }) => theme.colors.text.secondary};
  line-height: 1.45;
`;

export default function BrandingPage() {
  const navigate = useNavigate();
  const { brand, brandId, setBrandId, themes, surfaceMode, setSurfaceMode, surfaces } = useBrand();
  const [draftAccent, setDraftAccent] = useState(brand.colors.accent.solid);
  const [draftRadius, setDraftRadius] = useState(brand.radii.md);
  const [draftFont, setDraftFont] = useState(brand.fonts.ui);

  // sync when preset changes
  React.useEffect(() => {
    setDraftAccent(brand.colors.accent.solid);
    setDraftRadius(brand.radii.md);
    setDraftFont(brand.fonts.ui);
  }, [brand]);

  const liveBrand = useMemo(() => {
    return {
      ...brand,
      colors: {
        ...brand.colors,
        accent: {
          ...brand.colors.accent,
          solid: draftAccent,
          soft: draftAccent,
          label: draftAccent,
        },
        text: {
          ...brand.colors.text,
          label: draftAccent,
        },
      },
      radii: {
        ...brand.radii,
        md: draftRadius,
        lg: draftRadius,
      },
      fonts: {
        ...brand.fonts,
        ui: draftFont,
      },
    };
  }, [brand, draftAccent, draftRadius, draftFont]);

  const saveManual = () => {
    const overrides = {
      accentSolid: draftAccent,
      radiusMd: draftRadius,
      fontUi: draftFont,
      baseTheme: brandId,
      surfaceMode,
    };
    localStorage.setItem('brandOverrides', JSON.stringify(overrides));
    document.documentElement.style.setProperty('--color-gold', draftAccent);
    document.documentElement.style.setProperty('--nd-primary', draftAccent);
    document.documentElement.style.setProperty('--radius-md', draftRadius);
    document.documentElement.style.setProperty('--font-family', draftFont);
    alert('Черновик бренда сохранён локально (brandOverrides). На проде это уйдёт в API тенанта.');
  };

  return (
    <Shell>
      <Wrap>
        <Top>
          <div>
            <h1>Брендинг клиента</h1>
            <p>Режим интерфейса + пресет акцента. Стиль применяется ко всему приложению.</p>
          </div>
          <Back
            type="button"
            onClick={() => {
              if (window.history.length > 1) navigate(-1);
              else navigate('/overview');
            }}
          >
            ← Назад
          </Back>
        </Top>

        <Panel>
          <h2>Режим интерфейса</h2>
          <Note>
            Основной — белый контент с тёмными шапкой, меню и карточками (как на скрине). Второй — полный тёмный графит.
          </Note>
          <Grid>
            {(Object.keys(surfaces) as SurfaceMode[]).map((mode) => {
              const s = surfaces[mode];
              return (
                <ModeCard
                  key={mode}
                  type="button"
                  $mode={mode}
                  $active={surfaceMode === mode}
                  onClick={() => setSurfaceMode(mode)}
                >
                  <div className="swatch" />
                  <div className="name">{s.label}</div>
                  <div className="desc">{s.description}</div>
                  <span className="badge">{mode === 'light' ? 'Основной' : 'Второй'}</span>
                </ModeCard>
              );
            })}
          </Grid>
        </Panel>

        <Panel>
          <h2>Пресеты дизайна</h2>
          <Note>
            Оба gold-варианта сохранены для кастомизации под бренд. Silver — заготовка второго металла.
          </Note>
          <Grid>
            {(Object.keys(themes) as BrandThemeId[]).map((id) => {
              const t = themes[id];
              return (
                <Card
                  key={id}
                  type="button"
                  $active={brandId === id}
                  onClick={() => setBrandId(id)}
                >
                  <img src={t.preview} alt={t.label} />
                  <div className="name">{t.label}</div>
                  <div className="id">{t.id}</div>
                </Card>
              );
            })}
          </Grid>
        </Panel>

        <Panel>
          <h2>Ручная настройка (релиз / клиент)</h2>
          <Row>
            <FieldEdit>
              Accent / Gold
              <input
                type="color"
                value={/^#([0-9a-f]{6})$/i.test(draftAccent) ? draftAccent : '#D4A84B'}
                onChange={(e) => setDraftAccent(e.target.value)}
              />
            </FieldEdit>
            <FieldEdit>
              Скругление (radius.md)
              <input value={draftRadius} onChange={(e) => setDraftRadius(e.target.value)} />
            </FieldEdit>
            <FieldEdit>
              Шрифт UI
              <input value={draftFont} onChange={(e) => setDraftFont(e.target.value)} />
            </FieldEdit>
          </Row>
          <GoldButton
            $theme={liveBrand}
            type="button"
            whileTap={{ scale: 0.98 }}
            onClick={saveManual}
          >
            Сохранить настройки
          </GoldButton>
        </Panel>

        <Panel>
          <h2>Превью компонентов</h2>
          <Preview>
            <GoldField $theme={liveBrand}>
              <span>Телефон</span>
              <input defaultValue="+79999999999" readOnly />
            </GoldField>
            <GoldField $theme={liveBrand}>
              <span>Пароль</span>
              <input type="password" defaultValue="********" readOnly />
            </GoldField>
            <GoldButton $theme={liveBrand} type="button" style={{ marginBottom: 12 }}>
              Войти
            </GoldButton>
            <GhostGoldButton $theme={liveBrand} type="button">
              Зарегистрироваться
            </GhostGoldButton>
          </Preview>
        </Panel>
      </Wrap>
    </Shell>
  );
}
