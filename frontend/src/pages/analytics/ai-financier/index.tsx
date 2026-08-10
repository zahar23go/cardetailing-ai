/**
 * ИИ Финансист — /analytics/ai-financier
 * Автономный чат, локальный state.
 */
import React, { useState } from 'react';
import { Card, Button, Input } from 'antd';
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

const SUGGESTIONS = [
  'Какая прибыль за месяц?',
  'Кто из мастеров эффективнее?',
  'Прогноз выручки на неделю',
];

export default function AiFinancierPage() {
  const [financierMessages, setFinancierMessages] = useState<{ role: 'user' | 'ai'; text: string }[]>([]);
  const [financierInput, setFinancierInput] = useState('');
  const [financierLoading, setFinancierLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);

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
    } catch (e: any) {
      setFinancierMessages((prev) => [
        ...prev,
        { role: 'ai', text: `❌ ${e.message || 'Ошибка соединения'}` },
      ]);
    }
    setFinancierLoading(false);
  };

  return (
    <>
      <div className="admin-section-head">
        <div>
          <div className="admin-overview-kicker">AI-консультант</div>
          <h3>AI Финансист</h3>
          <p className="financier-lead">
            Аналитика бизнеса, прогнозы и рекомендации
          </p>
        </div>
      </div>

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
            className="btn-gold-secondary financier-new-btn"
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
            className="btn-gold financier-send"
            onClick={() => handleFinancierQuestion()}
            loading={financierLoading}
            icon={<SendOutlined />}
          />
        </div>
      </Card>
    </>
  );
}
