/**
 * Чат с ИИ-детейлером: консультант + оценка по фото/меткам, допродажи, слот по боксам.
 * POST /api/ai/consultant без изменений; осмотр — POST /api/ai/detailer/inspect.
 */
import React, { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Button, Input } from '../../../components/ui';
import {
  ArrowLeftOutlined,
  BulbOutlined,
  CameraOutlined,
  SendOutlined,
  UserOutlined,
} from '@ant-design/icons';
import Card from '../../../components/Card';
import Badge from '../../../components/Badge';
import {
  Car,
  DETAILER_TAGS,
  DetailerInspect,
  DetailerOffer,
  Service,
  apiFetch,
  formatCurrency,
  matchServicesFromText,
  tzOffsetMinutes,
} from '../api';

const SUGGESTIONS = [
  'Какая мойка подойдёт к ближайшему визиту?',
  'Чем полировка отличается от керамики?',
  'Подберите услугу и запишите меня',
];

type LocState = { inspect?: boolean } | null;
type ChatMsg = {
  role: 'user' | 'ai';
  text: string;
  offers?: Service[];
  inspect?: DetailerInspect;
};

export default function ClientChatPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const openInspect = Boolean((location.state as LocState)?.inspect);
  const fileRef = useRef<HTMLInputElement>(null);

  const [services, setServices] = useState<Service[]>([]);
  const [cars, setCars] = useState<Car[]>([]);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [inspecting, setInspecting] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(!openInspect);
  const [showInspect, setShowInspect] = useState(openInspect);
  const [tags, setTags] = useState<string[]>([]);
  const [notes, setNotes] = useState('');
  const [carId, setCarId] = useState<number | undefined>();
  const [files, setFiles] = useState<File[]>([]);

  useEffect(() => {
    apiFetch<{ items: Service[] }>('/api/services?skip=0&limit=200')
      .then((d) => setServices(d.items || []))
      .catch(() => undefined);
    apiFetch<{ items: Car[] }>('/api/cars?skip=0&limit=50')
      .then((d) => {
        const items = d.items || [];
        setCars(items);
        if (items[0]) setCarId(items[0].id);
      })
      .catch(() => undefined);
  }, []);

  const toggleTag = (id: string) => {
    setTags((prev) => (prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]));
  };

  const uploadPhotos = async (targetCarId: number, list: File[]) => {
    const ids: number[] = [];
    for (const file of list) {
      const body = new FormData();
      body.append('file', file);
      const saved = await apiFetch<{ id: number }>(`/api/upload/car/${targetCarId}`, {
        method: 'POST',
        body,
      });
      ids.push(saved.id);
    }
    return ids;
  };

  const inspect = async () => {
    if (inspecting) return;
    setShowSuggestions(false);
    setInspecting(true);
    const label = tags.length
      ? tags.map((id) => DETAILER_TAGS.find((t) => t.id === id)?.label || id).join(', ')
      : (notes.trim() || 'Осмотр автомобиля');
    setMessages((prev) => [...prev, { role: 'user', text: `Осмотр: ${label}` }]);
    try {
      let photoIds: number[] = [];
      if (files.length && carId) {
        photoIds = await uploadPhotos(carId, files);
      }
      const data = await apiFetch<DetailerInspect>('/api/ai/detailer/inspect', {
        method: 'POST',
        body: JSON.stringify({
          tags,
          notes: notes.trim() || null,
          car_id: carId || null,
          photo_ids: photoIds,
          tz_offset: tzOffsetMinutes(),
        }),
      });
      const text = [
        data.findings.map((f) => `${f.title}: ${f.detail}`).join('\n'),
        data.primary
          ? `Рекомендую: ${data.primary.name} · ${formatCurrency(data.primary.price)}`
          : '',
        data.slots[0]
          ? `Свободный слот: ${data.slots[0].label || data.slots[0].time} · ${data.slots[0].box_name || 'бокс'}`
          : 'Слот подберём на записи — сетка боксов пока пустая.',
      ].filter(Boolean).join('\n\n');
      setMessages((prev) => [...prev, { role: 'ai', text, inspect: data }]);
      setFiles([]);
      if (fileRef.current) fileRef.current.value = '';
    } catch (e: unknown) {
      setMessages((prev) => [
        ...prev,
        { role: 'ai', text: e instanceof Error ? e.message : 'Не удалось оценить авто' },
      ]);
    }
    setInspecting(false);
  };

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

  const bookOffer = (offer: DetailerOffer | Service, inspectData?: DetailerInspect) => {
    const serviceId = 'service_id' in offer ? offer.service_id : offer.id;
    const slot = inspectData?.slots[0];
    navigate('/client/booking', {
      state: {
        serviceId,
        inspectId: inspectData?.id,
        startTime: slot?.start_time || undefined,
        boxId: slot?.box_id || undefined,
      },
    });
  };

  const bookService = (service: Service) => {
    navigate('/client/booking', { state: { serviceId: service.id } });
  };

  const backToStart = () => {
    setMessages([]);
    setShowSuggestions(true);
    setInput('');
    setShowInspect(false);
  };

  return (
    <>
      <div className="client-section-head">
        <div>
          <h3>Детейлер</h3>
          <Badge variant="gold">Оценка, допродажи, запись</Badge>
        </div>
        <Button
          look={showInspect ? 'gold' : 'ghost'}
          icon={<CameraOutlined />}
          onClick={() => setShowInspect((v) => !v)}
        >
          Осмотр
        </Button>
      </div>

      {showInspect ? (
        <Card variant="admin" className="client-block detailer-inspect">
          <div className="detailer-inspect-title">Что видите на авто?</div>
          <div className="detailer-tags">
            {DETAILER_TAGS.map((t) => (
              <button
                key={t.id}
                type="button"
                className={`detailer-tag${tags.includes(t.id) ? ' is-on' : ''}`}
                onClick={() => toggleTag(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>
          {cars.length > 0 ? (
            <select
              className="detailer-car"
              value={carId || ''}
              onChange={(e) => setCarId(Number(e.target.value) || undefined)}
            >
              {cars.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.make} {c.model}{c.license_plate ? ` · ${c.license_plate}` : ''}
                </option>
              ))}
            </select>
          ) : (
            <div className="detailer-hint">Добавьте авто в профиле, чтобы прикрепить фото.</div>
          )}
          <Input.TextArea
            className="input-luxury"
            placeholder="Комментарий: сколы на капоте, салон после зимы…"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
          />
          <div className="detailer-files">
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              onChange={(e) => setFiles(Array.from(e.target.files || []))}
            />
            {files.length ? <span>{files.length} фото</span> : null}
          </div>
          <Button look="gold" loading={inspecting} onClick={() => inspect()}>
            Оценить и подобрать слот
          </Button>
        </Card>
      ) : null}

      <Card variant="admin" className="client-chat-panel">
        {!showSuggestions ? (
          <div className="client-chat-toolbar">
            <Button icon={<ArrowLeftOutlined />} look="gold" onClick={backToStart}>
              Назад к началу
            </Button>
          </div>
        ) : null}
        <div className="client-chat-thread">
          {showSuggestions && !messages.length ? (
            <div className="client-chat-empty">
              <div className="client-chat-empty-icon"><BulbOutlined /></div>
              <div className="client-chat-empty-title">Детейлер знает каталог и загрузку боксов</div>
              <div className="client-chat-empty-hint">
                Отметьте состояние авто или спросите про технологию — запишем на свободный слот
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
                    <div className="client-chat-bubble-label">
                      {msg.inspect ? 'AI детейлер' : 'AI консультант'}
                    </div>
                  )}
                  <div className="client-chat-bubble-text">{msg.text}</div>
                  {msg.inspect?.upsells.length ? (
                    <div className="client-chat-offers">
                      {msg.inspect.primary ? (
                        <Button
                          look="gold"
                          onClick={() => bookOffer(msg.inspect!.primary!, msg.inspect)}
                        >
                          Записаться на {msg.inspect.primary.name}
                        </Button>
                      ) : null}
                      {msg.inspect.upsells.map((u) => (
                        <Button
                          key={u.service_id}
                          look="ghost"
                          onClick={() => bookOffer(u, msg.inspect)}
                        >
                          + {u.name} · {formatCurrency(u.price)}
                        </Button>
                      ))}
                    </div>
                  ) : msg.offers?.length ? (
                    <div className="client-chat-offers">
                      {msg.offers.map((s) => (
                        <Button
                          key={s.id}
                          look="gold"
                          onClick={() => bookService(s)}
                        >
                          Записаться на {s.name}
                        </Button>
                      ))}
                    </div>
                  ) : msg.inspect?.primary ? (
                    <div className="client-chat-offers">
                      <Button
                        look="gold"
                        onClick={() => bookOffer(msg.inspect!.primary!, msg.inspect)}
                      >
                        Записаться на {msg.inspect.primary.name}
                      </Button>
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
          {loading || inspecting ? (
            <div className="client-chat-msg is-ai">
              <div className="chat-avatar chat-avatar--ai" aria-hidden>
                <BulbOutlined />
              </div>
              <div className="client-chat-bubble">
                <div className="client-chat-bubble-label">AI детейлер</div>
                <div className="client-chat-bubble-text is-typing">
                  {inspecting ? 'Сверяю каталог и свободные боксы…' : 'Подбираю ответ…'}
                </div>
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
            look="gold"
            className="client-chat-send"
            icon={<SendOutlined />}
            loading={loading}
            onClick={() => ask()}
          />
        </div>
      </Card>
    </>
  );
}
