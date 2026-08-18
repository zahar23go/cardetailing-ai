/**
 * Чат с ИИ-консультантом — /api/ai/consultant
 */
import React, { useState } from 'react';
import { Button, Input } from 'antd';
import { BulbOutlined, PlusOutlined, SendOutlined } from '@ant-design/icons';
import Card from '../../../components/Card';
import { apiFetch } from '../api';

const SUGGESTIONS = [
  'Какая мойка подойдёт к ближайшему визиту?',
  'Чем полировка отличается от керамики?',
  'Подберите услугу под химчистку салона',
];

export default function ClientChatPage() {
  const [messages, setMessages] = useState<{ role: 'user' | 'ai'; text: string }[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);

  const ask = async (preset?: string) => {
    const question = (preset ?? input).trim();
    if (!question || loading) return;
    setShowSuggestions(false);
    setMessages((prev) => [...prev, { role: 'user', text: question }]);
    setInput('');
    setLoading(true);
    try {
      const data = await apiFetch<{ response: string }>('/api/ai/consultant', {
        method: 'POST',
        body: JSON.stringify({ question }),
      });
      setMessages((prev) => [...prev, { role: 'ai', text: data.response }]);
    } catch (e: unknown) {
      setMessages((prev) => [
        ...prev,
        { role: 'ai', text: e instanceof Error ? e.message : 'Ошибка соединения' },
      ]);
    }
    setLoading(false);
  };

  return (
    <>
      <div className="admin-section-head">
        <div>
          <div className="admin-overview-kicker">AI-консультант</div>
          <h3>Чат с ИИ</h3>
        </div>
        <Button icon={<PlusOutlined />} className="btn-gold-secondary" onClick={() => {
          setMessages([]);
          setShowSuggestions(true);
        }}>
          Новый диалог
        </Button>
      </div>

      <Card variant="admin" className="financier-panel">
        <div className="financier-chat">
          {showSuggestions ? (
            <div className="financier-empty">
              <div className="financier-empty-icon"><BulbOutlined /></div>
              <div className="financier-empty-title">Спросите про технологию или подбор услуги</div>
              <div className="financier-empty-hint">
                Консультант знает каталог салона и поможет записаться
              </div>
              <div className="financier-suggests">
                {SUGGESTIONS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    className="financier-suggest"
                    onClick={() => ask(q)}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`financier-msg ${msg.role === 'user' ? 'is-user' : 'is-ai'}`}>
                <div className="financier-bubble">
                  {msg.role === 'ai' && (
                    <div className="financier-bubble-label">
                      <BulbOutlined /> AI консультант
                    </div>
                  )}
                  <div className="financier-bubble-text">{msg.text}</div>
                </div>
              </div>
            ))
          )}
          {loading ? (
            <div className="financier-msg is-ai">
              <div className="financier-bubble">
                <div className="financier-bubble-label"><BulbOutlined /> AI консультант</div>
                <div className="financier-bubble-text is-typing">Подбираю ответ…</div>
              </div>
            </div>
          ) : null}
        </div>
        <div className="financier-composer">
          <Input.TextArea
            className="input-luxury financier-input"
            placeholder="Вопрос о мойке, полировке, записи…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                ask();
              }
            }}
            rows={1}
            autoSize={{ minRows: 1, maxRows: 4 }}
          />
          <Button
            className="btn-gold financier-send"
            icon={<SendOutlined />}
            loading={loading}
            onClick={() => ask()}
          />
        </div>
      </Card>
    </>
  );
}
