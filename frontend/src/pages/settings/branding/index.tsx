/**
 * Брендинг — /settings/branding
 * Рендер через AdminLayout <Outlet /> (сайдбар остаётся).
 */
import React, { useEffect, useMemo, useState } from 'react';
import styled from 'styled-components';
import { message } from 'antd';
import { useBrand } from '../../../design/BrandProvider';
import { GoldButton, GhostGoldButton, GoldField } from '../../../design/components/BrandControls';
import type { BrandThemeId } from '../../../design/tokens';
import type { SurfaceMode } from '../../../design/surface';

const Wrap = styled.div`
  max-width: 980px;
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
  const {
    brand, brandId, setBrandId, themes, surfaceMode, setSurfaceMode, surfaces,
    applyRemoteBranding,
  } = useBrand();
  const [draftAccent, setDraftAccent] = useState(brand.colors.accent.solid);
  const [draftRadius, setDraftRadius] = useState(brand.radii.md);
  const [draftFont, setDraftFont] = useState(brand.fonts.ui);
  const [logoUrl, setLogoUrl] = useState<string | null | undefined>(undefined);
  const [saving, setSaving] = useState(false);
  const [uploadingLogo, setUploadingLogo] = useState(false);

  useEffect(() => {
    setDraftAccent(brand.colors.accent.solid);
    setDraftRadius(brand.radii.md);
    setDraftFont(brand.fonts.ui);
  }, [brand]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch('/api/branding', {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) return;
        const data = await res.json();
        if (cancelled) return;
        if (data.accent_solid) setDraftAccent(data.accent_solid);
        if (data.radius_md) setDraftRadius(data.radius_md);
        if (data.font_ui) setDraftFont(data.font_ui);
        if (data.base_theme) setBrandId(data.base_theme);
        if (data.surface_mode) setSurfaceMode(data.surface_mode);
        setLogoUrl(data.logo_url || null);
      } catch {
        /* остаёмся на локальных значениях */
      }
    })();
    return () => { cancelled = true; };
  }, [setBrandId, setSurfaceMode]);

  const liveBrand = useMemo(() => ({
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
  }), [brand, draftAccent, draftRadius, draftFont]);

  const saveBranding = async () => {
    setSaving(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/branding', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          accent_solid: draftAccent,
          radius_md: draftRadius,
          font_ui: draftFont,
          base_theme: brandId,
          surface_mode: surfaceMode,
          ...(logoUrl !== undefined ? { logo_url: logoUrl } : {}),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        message.error(
          typeof data.detail === 'string' ? data.detail : 'Не удалось сохранить брендинг',
        );
        return;
      }
      applyRemoteBranding(data);
      message.success('Брендинг сохранён в салоне');
    } catch {
      message.error('Нет связи с сервером');
    } finally {
      setSaving(false);
    }
  };

  const uploadLogo = async (file: File) => {
    setUploadingLogo(true);
    try {
      const token = localStorage.getItem('token');
      const body = new FormData();
      body.append('file', file);
      const res = await fetch('/api/branding/logo', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        message.error(
          typeof data.detail === 'string' ? data.detail : 'Не удалось загрузить логотип',
        );
        return;
      }
      setLogoUrl(data.logo_url || null);
      applyRemoteBranding(data);
      message.success('Логотип обновлён');
    } catch {
      message.error('Нет связи с сервером');
    } finally {
      setUploadingLogo(false);
    }
  };

  return (
    <Wrap>
      <div className="admin-section-head">
        <div>
          <div className="admin-overview-kicker">Настройки</div>
          <h3>Брендинг клиента</h3>
          <p className="text-titanium" style={{ marginTop: 4 }}>
            Режим интерфейса + пресет акцента. Стиль применяется ко всему приложению.
          </p>
        </div>
      </div>

      <Panel>
        <h2>Режим интерфейса</h2>
        <Note>
          Основной — белый контент с тёмными шапкой, меню и карточками. Второй — полный тёмный графит.
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
        <h2>Логотип салона</h2>
        <Note>
          Используется в PWA и уведомлениях салона. PNG, JPG или WEBP до 10 МБ.
          Сохраняется на сервере в тенанте.
        </Note>
        <Row>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {logoUrl ? (
              <img
                src={logoUrl}
                alt="Логотип салона"
                style={{ height: 56, maxWidth: 180, objectFit: 'contain' }}
              />
            ) : (
              <span style={{ fontSize: 13, opacity: 0.7 }}>Логотип не задан</span>
            )}
            <label
              style={{
                display: 'inline-block',
                padding: '10px 16px',
                borderRadius: 10,
                border: `1px solid ${brand.colors.accent.border}`,
                color: brand.colors.accent.solid,
                fontSize: 12,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                cursor: uploadingLogo ? 'wait' : 'pointer',
                opacity: uploadingLogo ? 0.6 : 1,
              }}
            >
              {uploadingLogo ? 'Загрузка…' : 'Загрузить логотип'}
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                style={{ display: 'none' }}
                disabled={uploadingLogo}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  e.target.value = '';
                  if (file) uploadLogo(file);
                }}
              />
            </label>
          </div>
        </Row>
      </Panel>

      <Panel>
        <h2>Ручная настройка</h2>
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
          onClick={saveBranding}
          disabled={saving}
        >
          {saving ? 'Сохранение…' : 'Сохранить в салоне'}
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
  );
}
