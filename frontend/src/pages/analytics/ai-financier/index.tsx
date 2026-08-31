/**
 * ИИ Финансист — /analytics/ai-financier
 * Сводка сезон/погода + причина → действие → эффект ₽. Чат POST /api/ai/financier без изменений.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Spin } from 'antd';
import { Button, Input } from '../../../components/ui';
import { BulbOutlined, PlusOutlined, SendOutlined } from '@ant-design/icons';

const API_BASE = '';

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Ошибка ${res.status}`);
  }
  return res.json();
}

function formatRub(val: number) {
  return `${Number(val || 0).toLocaleString('ru-RU')} ₽`;
}

const KIND_LABEL: Record<string, string> = {
  weather: 'Погода',
  season: 'Сезон',
  load: 'Загрузка',
  box: 'Бокс',
  pnl: 'P&L',
};

const SUGGESTIONS = [
  'Какая прибыль за месяц?',
  'Кто из мастеров эффективнее?',
  'Что делать с погодой на неделю?',
];

interface WeatherDay {
  date: string;
  t_max: number;
  t_min: number;
  precip_mm: number;
}

interface FinancierRec {
  id: string;
  cause: string;
  action: string;
  effect_rub: number;
  horizon: string;
  kind: string;
}

interface FinancierBrief {
  city: string;
  source: string;
  season: string;
  season_label: string;
  season_demand: string;
  outlook: string;
  days: WeatherDay[];
  recommendations: FinancierRec[];
}

export default function AiFinancierPage() {
  const navigate = useNavigate();
  const [financierMessages, setFinancierMessages] = useState<{ role: 'user' | 'ai'; text: string }[]>([]);
  const [financierInput, setFinancierInput] = useState('');
  const [financierLoading, setFinancierLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [brief, setBrief] = useState<FinancierBrief | null>(null);
  const [briefLoading, setBriefLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setBriefLoading(true);
    apiFetch<FinancierBrief>('/api/ai/financier/brief')
      .then((data) => {
        if (!cancelled) setBrief(data);
      })
      .catch(() => {
        if (!cancelled) setBrief(null);
      })
      .finally(() => {
        if (!cancelled) setBriefLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const handleNewDialog = () => {
    setFinancierMessages([]);
    setShowSuggestions(true);
  };

  const handleFinancierQuestion = async (preset?: string) => {
    const question = (preset ?? financierInput).trim();
    if (!question || financierLoading) return;
    setShowSuggestions(false);
    setFinancierMessages((prev) => [...prev, { role: 'user', text: question }]);
    setFinancierInput('');
    setFinancierLoading(true);
    try {
      const data = await apiFetch<{ response: string }>('/api/ai/financier', {
        method: 'POST',
        body: JSON.stringify({ question }),
      });
      setFinancierMessages((prev) => [...prev, { role: 'ai', text: data.response }]);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Ошибка соединения';
      setFinancierMessages((prev) => [
        ...prev,
        { role: 'ai', text: `❌ ${msg}` },
      ]);
    }
    setFinancierLoading(false);
  };

  const applyRec = (kind: string) => {
    if (kind === 'box') navigate('/upload/boxes');
    else if (kind === 'pnl') navigate('/analytics/finances');
    else navigate('/discounts');
  };

  const askAboutRec = (rec: FinancierRec) => {
    handleFinancierQuestion(
      `Разбери рекомендацию. Причина: ${rec.cause} Действие: ${rec.action} Эффект: ${formatRub(rec.effect_rub)}.`,
    );
  };

  return (
    <>
      <div className="admin-section-head">
        <div>
          <div className="admin-overview-kicker">AI-консультант</div>
          <h3>AI Финансист</h3>
          <p className="financier-lead">
            Сезон, погода и действие в ₽ — не только чат
          </p>
        </div>
      </div>

      <Card className="admin-panel-card financier-brief-panel" bordered={false}>
        {briefLoading ? (
          <Spin />
        ) : brief ? (
          <>
            <div className="financier-brief-head">
              <div>
                <div className="financier-brief-kicker">
                  {brief.city} · {brief.season_label}
                  {brief.source === 'season-only' ? ' · календарь' : ''}
                </div>
                <div className="financier-brief-outlook">{brief.outlook}</div>
                <div className="financier-brief-demand">{brief.season_demand}</div>
              </div>
            </div>
            {brief.days.length ? (
              <div className="financier-weather-row">
                {brief.days.slice(0, 5).map((d) => (
                  <div key={d.date} className="financier-weather-day">
                    <span>{d.date.slice(8, 10)}.{d.date.slice(5, 7)}</span>
                    <strong>{Math.round(d.t_max)}°</strong>
                    <em>{d.precip_mm >= 1 ? `${Math.round(d.precip_mm)} мм` : 'сухо'}</em>
                  </div>
                ))}
              </div>
            ) : null}
            <div className="financier-rec-grid">
              {brief.recommendations.map((rec) => (
                <div key={rec.id} className="financier-rec-wrap">
                  <button
                    type="button"
                    className="financier-rec-card"
                    onClick={() => askAboutRec(rec)}
                  >
                    <div className="financier-rec-meta">
                      <span>{KIND_LABEL[rec.kind] || rec.kind}</span>
                      <span>{rec.horizon}</span>
                    </div>
                    <div className="financier-rec-row">
                      <span>Причина</span>
                      <p>{rec.cause}</p>
                    </div>
                    <div className="financier-rec-row">
                      <span>Действие</span>
                      <p>{rec.action}</p>
                    </div>
                    <div className="financier-rec-effect">{formatRub(rec.effect_rub)}</div>
                  </button>
                  <Button
                    size="small"
                    look="gold"
                    onClick={() => applyRec(rec.kind)}
                  >
                    Применить рекомендацию
                  </Button>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="financier-brief-demand">
            Сводка недоступна — чат финансиста ниже работает как раньше.
          </div>
        )}
      </Card>

      <Card className="admin-panel-card financier-panel" bordered={false}>
        <div className="financier-chat">
          {showSuggestions ? (
            <div className="financier-empty">
              <div className="financier-empty-icon">
                <BulbOutlined />
              </div>
              <div className="financier-empty-title">Задайте вопрос о финансах вашего бизнеса</div>
              <div className="financier-empty-hint">
                Данные салона: выручка, мастера, загрузка, затраты — в одном ответе
              </div>
              <div className="financier-suggests">
                {SUGGESTIONS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    className="financier-suggest"
                    onClick={() => handleFinancierQuestion(q)}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            financierMessages.map((msg, i) => (
              <div
                key={i}
                className={`financier-msg ${msg.role === 'user' ? 'is-user' : 'is-ai'}`}
              >
                <div className="financier-bubble">
                  {msg.role === 'ai' && (
                    <div className="financier-bubble-label">
                      <BulbOutlined /> AI Финансист
                    </div>
                  )}
                  <div className="financier-bubble-text">{msg.text}</div>
                </div>
              </div>
            ))
          )}
          {financierLoading && (
            <div className="financier-msg is-ai">
              <div className="financier-bubble">
                <div className="financier-bubble-label">
                  <BulbOutlined /> AI Финансист
                </div>
                <div className="financier-bubble-text is-typing">Анализирую данные салона…</div>
              </div>
            </div>
          )}
        </div>

        <div className="financier-composer">
          <Button
            icon={<PlusOutlined />}
            look="ghost" className="financier-new-btn"
            onClick={handleNewDialog}
          >
            + Новый диалог
          </Button>
          <Input.TextArea
            className="input-luxury financier-input"
            placeholder="Спросите AI-финансиста…"
            value={financierInput}
            onChange={(e) => setFinancierInput(e.target.value)}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleFinancierQuestion();
              }
            }}
            rows={1}
            autoSize={{ minRows: 1, maxRows: 4 }}
          />
          <Button
            look="gold" className="financier-send"
            onClick={() => handleFinancierQuestion()}
            loading={financierLoading}
            icon={<SendOutlined />}
          />
        </div>
      </Card>
    </>
  );
}
