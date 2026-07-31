# Design System — CarDetailing AI

## Задача босса (зафиксировано)

1. **Оставить оба дизайна** — позже клиент сможет выбирать стиль под бренд (кастомизация).
2. **Именованные UI-элементы** — `GoldButton`, `GhostGoldButton`, `GoldField`, `SilverButton` (зарезервирован).
3. **Один конфиг темы** — цвета, шрифты, скругления, градиенты, тени, ассеты.
4. **Единый стиль на всех страницах** — страницы не правят CSS вручную, берут токены.
5. **Позже** — страница брендинга на каждого клиента (tenant).

## Сохранённые пресеты

| ID | Имя | Референс | Отличие |
|----|-----|----------|---------|
| `goldMetal` | Gold Metal | `/design-refs/gold-metal.png` | Горизонтальный «металл», **тёмный** текст на кнопке |
| `goldGlow` | Gold Glow | `/design-refs/gold-glow.png` | Вертикальный градиент, **белый** текст, свечение |
| `silver` | Silver | — | Зарезервировано |

## Как разработчику применить дизайн

```ts
import { getBrandTheme, GoldButton, GhostGoldButton, GoldField } from '@/design';
// или относительный путь:
import { getBrandTheme, GoldButton } from '../design';

const brand = getBrandTheme('goldGlow'); // или 'goldMetal'

// Переключение вручную в DevTools / на релизе:
localStorage.setItem('brandTheme', 'goldMetal');
```

Дефолт задаётся в `src/design/themes/index.ts` → `ACTIVE_BRAND_THEME`.

## Структура

```
frontend/src/design/
  tokens.ts              # схема BrandTheme
  index.ts               # публичный API
  themes/
    goldMetal.ts
    goldGlow.ts
    index.ts             # реестр + getBrandTheme()
  components/
    BrandControls.tsx    # GoldButton, GhostGoldButton, GoldField, SilverButton

frontend/public/design-refs/
  gold-metal.png
  gold-glow.png
```

## Страница брендинга

Открыть: **`/branding`**

- выбор пресета `goldMetal` / `goldGlow` / `silver`
- ручная правка accent / radius / font
- превью `GoldButton` / `GoldField` / `GhostGoldButton`
- сохранение черновика в `localStorage.brandOverrides` (позже — API тенанта)
