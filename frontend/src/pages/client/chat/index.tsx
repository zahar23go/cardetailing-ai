/**
 * Чат с ИИ-консультантом — /api/ai/consultant
 * Кнопка «Записаться на {услугу}» ведёт на /client/booking с предзаполненной услугой.
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Input } from 'antd';
import { ArrowLeftOutlined, BulbOutlined, SendOutlined, UserOutlined } from '@ant-design/icons';
import Card from '../../../components/Card';
import Badge from '../../../components/Badge';
import { Service, apiFetch, matchServicesFromText } from '../api';

const SUGGESTIONS = [
  'Какая мойка подойдёт к ближайшему визиту?',
  'Чем полировка отличается от керамики?',
  'Подберите услугу и запишите меня',
];

type ChatMsg = { role: 'user' | 'ai'; text: string; offers?: Service[] };

export default function ClientChatPage() {
  const navigate = useNavigate();
  const [services, setServices] = useState<Service[]>([]);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);

  useEffect(() => {
    apiFetch<{ items: Service[] }>('/api/services?skip=0&limit=200')
      .then((d) => setServices(d.items || []))
      .catch(() => undefined);
  }, []);

  const ask = async (preset?: string) => {
    const question = (preset ?? input).trim();
    if (!question || loading) return;
    setShowSuggestions(false);
    setMessages((prev) => [...prev, { role: 'user', text: question }]);
    setInput('');
    setLoading(true);
    const catalog = services.length
      ? services
      : ((await apiFetch<{ items: Service[] }>('/api/services?skip=0&limit=200')).items || []);
    if (!services.length && catalog.length) setServices(catalog);
    try {
      const data = await apiFetch<{ response: string }>('/api/ai/consultant', {
        method: 'POST',
        body: JSON.stringify({ question }),
      });
      const offers = matchServicesFromText(`${question} ${data.response}`, catalog);
      setMessages((prev) => [...prev, { role: 'ai', text: data.response, offers }]);
    } catch (e: unknown) {
      setMessages((prev) => [
        ...prev,
        { role: 'ai', text: e instanceof Error ? e.message : 'Ошибка соединения' },
      ]);
    }
    setLoading(false);
  };

  const bookService = (service: Service) => {
    navigate('/client/booking', { state: { serviceId: service.id } });
  };

  const backToStart = () => {
    setMessages([]);
    setShowSuggestions(true);
    setInput('');
  };

  return (
    <>
      <div className="client-section-head">
        <div>
          <h3>Чат с ИИ</h3>
          <Badge variant="gold">AI-консультант</Badge>
        </div>
      </div>

      <Card variant="admin" className="client-chat-panel">
        {!showSuggestions ? (
          <div className="client-chat-toolbar">
            <Button
              icon={<ArrowLeftOutlined />}
              className="btn-gold"
              onClick={backToStart}
            >
              Назад к началу
            </Button>
          </div>
        ) : null}
        <div className="client-chat-thread">
          {showSuggestions ? (
            <div className="client-chat-empty">
              <div className="client-chat-empty-icon"><BulbOutlined /></div>
              <div className="client-chat-empty-title">Спросите про технологию или подбор услуги</div>
              <div className="client-chat-empty-hint">
                Консультант знает каталог и предложит записаться кнопкой в чате
              </div>
              <div className="client-chat-suggests">
                {SUGGESTIONS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    className="client-chat-suggest"
                    onClick={() => ask(q)}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`client-chat-msg ${msg.role === 'user' ? 'is-user' : 'is-ai'}`}>
                {msg.role === 'ai' ? (
                  <div className="chat-avatar chat-avatar--ai" aria-hidden>
                    <BulbOutlined />
                  </div>
                ) : null}
                <div className="client-chat-bubble">
                  {msg.role === 'ai' && (
                    <div className="client-chat-bubble-label">AI консультант</div>
                  )}
                  <div className="client-chat-bubble-text">{msg.text}</div>
                  {msg.offers?.length ? (
                    <div className="client-chat-offers">
                      {msg.offers.map((s) => (
                        <Button
                          key={s.id}
                          className="btn-gold"
                          onClick={() => bookService(s)}
                        >
                          Записаться на {s.name}
                        </Button>
                      ))}
                    </div>
                  ) : null}
                </div>
                {msg.role === 'user' ? (
                  <div className="chat-avatar chat-avatar--user" aria-hidden>
                    <UserOutlined />
                  </div>
                ) : null}
              </div>
            ))
          )}
          {loading ? (
            <div className="client-chat-msg is-ai">
              <div className="chat-avatar chat-avatar--ai" aria-hidden>
                <BulbOutlined />
              </div>
              <div className="client-chat-bubble">
                <div className="client-chat-bubble-label">AI консультант</div>
                <div className="client-chat-bubble-text is-typing">Подбираю ответ…</div>
              </div>
            </div>
          ) : null}
        </div>
        <div className="client-chat-composer">
          <Input.TextArea
            className="input-luxury client-chat-input"
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
            className="btn-gold client-chat-send"
            icon={<SendOutlined />}
            loading={loading}
            onClick={() => ask()}
          />
        </div>
      </Card>
    </>
  );
}
