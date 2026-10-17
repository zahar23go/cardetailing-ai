/**
 * Аналитика диалогов — /analytics/dialogues
 * Объём, скорость и качество ответов ИИ-ассистентов + последние диалоги.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Card, Col, Row, Select, Spin, Tag, message } from 'antd';
import {
  CommentOutlined,
  DownOutlined,
  RightOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { apiFetch } from '../../client/api';

const { Option } = Select;

const PERIODS = [
  { value: 7, label: '7 дней' },
  { value: 30, label: '30 дней' },
  { value: 90, label: '90 дней' },
];

const ASSISTANT_LABEL: Record<string, string> = {
  detailer: 'ИИ Макс',
  financier: 'ИИ-Финансист',
  manager: 'ИИ-Управляющий',
  admin: 'ИИ-Администратор',
};

interface DailyPoint {
  date: string;
  turns: number;
  dialogs: number;
}

interface AssistantSlice {
  assistant: string;
  turns: number;
  share_pct: number;
}

interface NamedCount {
  text?: string;
  name?: string;
  count: number;
}

interface Overview {
  period_days: number;
  retention_days: number;
  dialogs: number;
  turns: number;
  users: number;
  errors: number;
  error_rate_pct: number;
  avg_response_ms: number;
  by_assistant: AssistantSlice[];
  daily: DailyPoint[];
  top_questions: NamedCount[];
  top_tools: NamedCount[];
}

interface DialogItem {
  session_id: string;
  assistant: string;
  turns: number;
  user_name: string | null;
  first_question: string | null;
  first_at: string | null;
  last_at: string | null;
  has_error: boolean;
}

interface DialogTurn {
  question: string;
  answer: string;
  tool_calls: string[];
  duration_ms: number;
  is_error: boolean;
  created_at: string | null;
}

interface DialogDetail {
  session_id: string;
  assistant: string;
  user_name: string | null;
  turns: DialogTurn[];
}

function shortDate(value: string | null) {
  if (!value) return '';
  const day = value.slice(8, 10);
  const month = value.slice(5, 7);
  return `${day}.${month}`;
}

function dateTime(value: string | null) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function seconds(ms: number) {
  if (!ms) return '—';
  return `${(ms / 1000).toFixed(1)} с`;
}

function assistantLabel(name: string) {
  return ASSISTANT_LABEL[name] || name;
}

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="ai-dialog-tooltip">
      <div className="ai-dialog-tooltip-title">{label}</div>
      {payload.map((item: any) => (
        <div key={item.dataKey}>
          {item.name}: <strong>{item.value}</strong>
        </div>
      ))}
    </div>
  );
}

export default function DialoguesAnalyticsPage() {
  const [period, setPeriod] = useState(30);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [loading, setLoading] = useState(true);
  const [dialogs, setDialogs] = useState<DialogItem[]>([]);
  const [dialogsLoading, setDialogsLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [details, setDetails] = useState<Record<string, DialogDetail>>({});
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiFetch<Overview>(`/api/ai/analytics/overview?period_days=${period}`)
      .then((data) => {
        if (!cancelled) setOverview(data);
      })
      .catch((e: unknown) => {
        if (!cancelled) message.error(e instanceof Error ? e.message : 'Не удалось загрузить метрики');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [period]);

  const loadDialogs = useCallback(() => {
    setDialogsLoading(true);
    apiFetch<{ items: DialogItem[] }>('/api/ai/analytics/dialogs?limit=20')
      .then((data) => setDialogs(data.items || []))
      .catch((e: unknown) => message.error(e instanceof Error ? e.message : 'Не удалось загрузить диалоги'))
      .finally(() => setDialogsLoading(false));
  }, []);

  useEffect(() => {
    loadDialogs();
  }, [loadDialogs]);

  const toggleDialog = async (sessionId: string) => {
    if (expanded === sessionId) {
      setExpanded(null);
      return;
    }
    setExpanded(sessionId);
    if (details[sessionId]) return;
    setDetailLoading(true);
    try {
      const data = await apiFetch<DialogDetail>(`/api/ai/analytics/dialogs/${sessionId}`);
      setDetails((prev) => ({ ...prev, [sessionId]: data }));
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Не удалось открыть диалог');
    } finally {
      setDetailLoading(false);
    }
  };

  const chartData = (overview?.daily || []).map((point) => ({
    ...point,
    label: shortDate(point.date),
  }));

  return (
    <>
      <div className="admin-section-head">
        <div>
          <div className="admin-overview-kicker">AI-аналитика</div>
          <h3>Аналитика диалогов</h3>
          <p className="financier-lead">
            Объём, скорость и качество ответов ИИ-ассистентов
          </p>
        </div>
      </div>

      <div className="ai-dialog-toolbar">
        <Select value={period} onChange={(value) => setPeriod(value)} style={{ width: 140 }}>
          {PERIODS.map((item) => (
            <Option key={item.value} value={item.value}>
              {item.label}
            </Option>
          ))}
        </Select>
        {overview ? (
          <span className="ai-dialog-retention">
            Текст переписки хранится {overview.retention_days} дн.
          </span>
        ) : null}
      </div>

      {loading || !overview ? (
        <div className="ai-dialog-loading">
          <Spin />
        </div>
      ) : (
        <>
          <Row gutter={[16, 16]}>
            <Col xs={12} md={6}>
              <Card className="admin-kpi-card" bordered={false}>
                <div className="admin-kpi-icon"><CommentOutlined /></div>
                <div className="admin-kpi-label">Диалоги</div>
                <div className="admin-kpi-value">{overview.dialogs}</div>
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card className="admin-kpi-card" bordered={false}>
                <div className="admin-kpi-icon"><ThunderboltOutlined /></div>
                <div className="admin-kpi-label">Сообщений</div>
                <div className="admin-kpi-value">{overview.turns}</div>
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card className="admin-kpi-card" bordered={false}>
                <div className="admin-kpi-icon"><TeamOutlined /></div>
                <div className="admin-kpi-label">Пользователей</div>
                <div className="admin-kpi-value">{overview.users}</div>
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card className="admin-kpi-card" bordered={false}>
                <div className="admin-kpi-icon"><WarningOutlined /></div>
                <div className="admin-kpi-label">Ошибки · ср. ответ</div>
                <div className="admin-kpi-value">
                  {overview.error_rate_pct}% · {seconds(overview.avg_response_ms)}
                </div>
              </Card>
            </Col>
          </Row>

          <Card className="admin-panel-card ai-dialog-card" bordered={false}>
            <div className="ai-dialog-card-title">Диалоги и сообщения по дням</div>
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={chartData} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                <defs>
                  <linearGradient id="turnsFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#D4AF37" stopOpacity={0.45} />
                    <stop offset="100%" stopColor="#D4AF37" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={16} />
                <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                <RechartsTooltip content={<ChartTooltip />} />
                <Area
                  type="monotone"
                  dataKey="turns"
                  name="Сообщения"
                  stroke="#D4AF37"
                  fill="url(#turnsFill)"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="dialogs"
                  name="Диалоги"
                  stroke="#8B9BB4"
                  fill="transparent"
                  strokeWidth={1.5}
                  strokeDasharray="4 3"
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>

          <Row gutter={[16, 16]}>
            <Col xs={24} md={8}>
              <Card className="admin-panel-card ai-dialog-card" bordered={false}>
                <div className="ai-dialog-card-title">Ассистенты</div>
                {overview.by_assistant.length ? (
                  overview.by_assistant.map((item) => (
                    <div key={item.assistant} className="ai-dialog-bar-row">
                      <div className="ai-dialog-bar-head">
                        <span>{assistantLabel(item.assistant)}</span>
                        <span>{item.turns} · {item.share_pct}%</span>
                      </div>
                      <div className="ai-dialog-bar">
                        <div className="ai-dialog-bar-fill" style={{ width: `${item.share_pct}%` }} />
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="ai-dialog-muted">Пока нет данных</div>
                )}
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card className="admin-panel-card ai-dialog-card" bordered={false}>
                <div className="ai-dialog-card-title">Частые вопросы</div>
                {overview.top_questions.length ? (
                  <ol className="ai-dialog-list">
                    {overview.top_questions.map((item) => (
                      <li key={item.text}>
                        <span>{item.text}</span>
                        <Tag>{item.count}</Tag>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <div className="ai-dialog-muted">Пока нет данных</div>
                )}
              </Card>
            </Col>
            <Col xs={24} md={8}>
              <Card className="admin-panel-card ai-dialog-card" bordered={false}>
                <div className="ai-dialog-card-title">Функции ассистентов</div>
                {overview.top_tools.length ? (
                  <ol className="ai-dialog-list">
                    {overview.top_tools.map((item) => (
                      <li key={item.name}>
                        <code>{item.name}</code>
                        <Tag>{item.count}</Tag>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <div className="ai-dialog-muted">Пока нет данных</div>
                )}
              </Card>
            </Col>
          </Row>

          <Card className="admin-panel-card ai-dialog-card" bordered={false}>
            <div className="ai-dialog-card-title">Последние диалоги</div>
            {dialogsLoading ? (
              <Spin />
            ) : dialogs.length ? (
              <div className="ai-dialog-items">
                {dialogs.map((item) => {
                  const isOpen = expanded === item.session_id;
                  const detail = details[item.session_id];
                  return (
                    <div key={item.session_id} className={`ai-dialog-item${isOpen ? ' is-open' : ''}`}>
                      <button
                        type="button"
                        className="ai-dialog-item-head"
                        onClick={() => toggleDialog(item.session_id)}
                      >
                        <span className="ai-dialog-item-chevron">
                          {isOpen ? <DownOutlined /> : <RightOutlined />}
                        </span>
                        <span className="ai-dialog-item-main">
                          <span className="ai-dialog-item-question">
                            {item.first_question || 'Без вопроса'}
                          </span>
                          <span className="ai-dialog-item-meta">
                            {assistantLabel(item.assistant)}
                            {item.user_name ? ` · ${item.user_name}` : ''}
                            {' · '}
                            {item.turns} сообщ.
                            {item.last_at ? ` · ${dateTime(item.last_at)}` : ''}
                          </span>
                        </span>
                        {item.has_error ? <Tag color="red">ошибка</Tag> : null}
                      </button>

                      {isOpen ? (
                        <div className="ai-dialog-transcript">
                          {detailLoading && !detail ? (
                            <Spin />
                          ) : detail ? (
                            detail.turns.map((turn, index) => (
                              <div key={index} className="ai-dialog-turn">
                                <div className="ai-dialog-turn-q">
                                  <span className="ai-dialog-turn-label">Вопрос</span>
                                  <span>{turn.question}</span>
                                </div>
                                <div className="ai-dialog-turn-a">
                                  <span className="ai-dialog-turn-label">Ответ</span>
                                  <span>{turn.answer}</span>
                                </div>
                                <div className="ai-dialog-turn-meta">
                                  {dateTime(turn.created_at)}
                                  {turn.duration_ms ? ` · ${seconds(turn.duration_ms)}` : ''}
                                  {turn.tool_calls.length ? ` · ${turn.tool_calls.join(', ')}` : ''}
                                  {turn.is_error ? ' · ошибка' : ''}
                                </div>
                              </div>
                            ))
                          ) : (
                            <div className="ai-dialog-muted">Не удалось загрузить переписку</div>
                          )}
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="ai-dialog-muted">Диалогов пока нет — ассистенты ещё не отвечали.</div>
            )}
          </Card>
        </>
      )}
    </>
  );
}
