/**
 * Общий чат ИИ-ассистентов админки (управляющий, администратор).
 *
 * История диалога хранится на клиенте и уходит в теле каждого запроса:
 * сервер без состояния, как у клиентского чата с ИИ Максом.
 */
import React, { useState } from 'react';
import { Card } from 'antd';
import { PlusOutlined, SendOutlined } from '@ant-design/icons';
import { Button, Input } from './ui';
import { apiFetch, newSessionId, tzOffsetMinutes } from '../pages/client/api';

export type AdminAiChatProps = {
  /** Эндпоинт чата, например /api/ai/manager */
  endpoint: string;
  kicker: string;
  title: string;
  lead: string;
  /** Подпись ассистента в пузырях ответов */
  assistantLabel: string;
  icon: React.ReactNode;
  suggestions: string[];
  emptyTitle: string;
  emptyHint: string;
  placeholder: string;
  typingText: string;
};

type ChatMsg = { role: 'user' | 'ai'; text: string };

export default function AdminAiChat({
  endpoint,
  kicker,
  title,
  lead,
  assistantLabel,
  icon,
  suggestions,
  emptyTitle,
  emptyHint,
  placeholder,
  typingText,
}: AdminAiChatProps) {
  const [sessionId, setSessionId] = useState(newSessionId);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);

  const resetDialog = () => {
    setMessages([]);
    setInput('');
    setShowSuggestions(true);
    setSessionId(newSessionId());
  };

  const ask = async (preset?: string) => {
    const question = (preset ?? input).trim();
    if (!question || loading) return;

    setShowSuggestions(false);
    setMessages((prev) => [...prev, { role: 'user', text: question }]);
    setInput('');
    setLoading(true);

    const history = messages.map((m) => ({
      role: m.role === 'user' ? 'user' : 'assistant',
      content: m.text,
    }));

    try {
      const data = await apiFetch<{ response: string }>(endpoint, {
        method: 'POST',
        body: JSON.stringify({
          messages: [...history, { role: 'user', content: question }],
          tz_offset: tzOffsetMinutes(),
          session_id: sessionId,
        }),
      });
      setMessages((prev) => [...prev, { role: 'ai', text: data.response }]);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Ошибка соединения';
      setMessages((prev) => [...prev, { role: 'ai', text: `❌ ${msg}` }]);
    }
    setLoading(false);
  };

  return (
    <>
      <div className="admin-section-head">
        <div>
          <div className="admin-overview-kicker">{kicker}</div>
          <h3>{title}</h3>
          <p className="financier-lead">{lead}</p>
        </div>
      </div>

      <Card className="admin-panel-card" bordered={false}>
        <div className="ai-chat-thread">
          {showSuggestions ? (
            <div className="ai-chat-empty">
              <div className="ai-chat-empty-icon">{icon}</div>
              <div className="ai-chat-empty-title">{emptyTitle}</div>
              <div className="ai-chat-empty-hint">{emptyHint}</div>
              <div className="ai-chat-suggests">
                {suggestions.map((q) => (
                  <button
                    key={q}
                    type="button"
                    className="ai-chat-suggest"
                    onClick={() => ask(q)}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`ai-chat-msg ${msg.role === 'user' ? 'is-user' : 'is-ai'}`}>
                <div className="ai-chat-bubble">
                  {msg.role === 'ai' && (
                    <div className="ai-chat-bubble-label">{assistantLabel}</div>
                  )}
                  <div className="ai-chat-bubble-text">{msg.text}</div>
                </div>
              </div>
            ))
          )}
          {loading && (
            <div className="ai-chat-msg is-ai">
              <div className="ai-chat-bubble">
                <div className="ai-chat-bubble-label">{assistantLabel}</div>
                <div className="ai-chat-bubble-text is-typing">{typingText}</div>
              </div>
            </div>
          )}
        </div>

        <div className="ai-chat-composer">
          <Button
            icon={<PlusOutlined />}
            look="ghost"
            className="ai-chat-new-btn"
            onClick={resetDialog}
          >
            Новый диалог
          </Button>
          <Input.TextArea
            className="input-luxury ai-chat-input"
            placeholder={placeholder}
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
            look="gold"
            className="ai-chat-send"
            icon={<SendOutlined />}
            loading={loading}
            onClick={() => ask()}
          />
        </div>
      </Card>
    </>
  );
}
