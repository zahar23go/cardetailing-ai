# Design System — CarDetailing AI

## Зафиксированный визуальный стиль (эталон)

**Запомнить и не менять без явного запроса:**

### Логотип / бренд-формула
- **Золотой контур спорткара в профиль** (низкий силуэт, капот / крыша / колёсные арки).
- Файл: `/images/logo-formula-sport.png` (также `header-car-logo.png`).
- Рядом текст **CAR DETAILING AI** — uppercase, золотой градиент:
  `linear-gradient(180deg, #f0d9a0 0%, #d4a84b 50%, #a67c2d 100%)` + `background-clip: text`.
- Справа в шапке — **AI orb** (`/images/ai-orb.png`), не фото профиля.
- **Не использовать** фото-силуэт седана / SVG-заглушки вместо этого логотипа.

### Экран входа / регистрации (phone UI)
- Корпус телефона, тёмный фон, Champagne Gold `#D4A84B`.
- **Без** статус-бара (9:41 / антенна / Wi‑Fi / батарея).
- Основной блок (бренд + авто + форма) **по центру** экрана телефона.
- Кнопки: только **Войти** + **Зарегистрироваться** (без «Смотреть концепцию»).
- Поля: `GoldField`, CTA: `GoldButton`, вторичная: `GhostGoldButton`.
- Логин/регистрация опираются на пресет **`goldMetal`** (металл, тёмный текст на кнопке).

### Палитра и атмосфера
- Фон: чёрный / графит, атмосфера `pageAtmosphere` из темы.
- Акцент: Champagne Gold `#D4A84B` / `#E0BC5A` / `#F0D9A0`.
- Шрифты UI: Manrope; display (кнопки): Cinzel где задано темой.

---

## Задача босса (зафиксировано)

1. **Оставить оба дизайна** — позже клиент сможет выбирать стиль под бренд (кастомизация).
2. **Именованные UI-элементы** — `GoldButton`, `GhostGoldButton`, `GoldField`, `SilverButton` (зарезервирован).
3. **Один конфиг темы** — цвета, шрифты, скругления, градиенты, тени, ассеты.
4. **Единый стиль на всех страницах** — страницы не правят CSS вручную, берут токены.
5. **Страница брендинга** — `/branding` (пресеты + ручные overrides).

## Сохранённые пресеты

| ID | Имя | Референс | Отличие |
|----|-----|----------|---------|
| `goldMetal` | Gold Metal | `/design-refs/gold-metal.png` | Горизонтальный «металл», **тёмный** текст на кнопке — **эталон для логина** |
| `goldGlow` | Gold Glow | `/design-refs/gold-glow.png` | Вертикальный градиент, **белый** текст, свечение |
| `silver` | Silver | — | Зарезервировано |

## Как разработчику применить дизайн

```ts
import { getBrandTheme, GoldButton, GhostGoldButton, GoldField } from '../design';

const brand = getBrandTheme('goldMetal'); // эталон входа
// логотип:
<img src={brand.assets.logoCar} alt="" /> // → /images/logo-formula-sport.png
```

Дефолт: `src/design/themes/index.ts` → `ACTIVE_BRAND_THEME`.

## Структура

```
frontend/src/design/
  tokens.ts
  index.ts
  themes/goldMetal.ts | goldGlow.ts | silver.ts | index.ts
  components/BrandControls.tsx | GoldCarLogo.tsx

frontend/public/images/
  logo-formula-sport.png   ← эталон логотипа (золотой спорткар)
  header-car-logo.png      ← копия эталона
  login-car.png | ai-orb.png

frontend/public/design-refs/
  gold-metal.png | gold-glow.png
```

## Страница брендинга

Открыть: **`/branding`**

- выбор пресета `goldMetal` / `goldGlow` / `silver`
- ручная правка accent / radius / font
- превью компонентов
- `localStorage.brandOverrides` (позже — API тенанта)
