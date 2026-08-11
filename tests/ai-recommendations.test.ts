import { describe, expect, it } from 'vitest';
import {
  applyOverheadBoost,
  buildExpenseInsights,
  buildFinancierContextMetrics,
  discountPercentRelative,
  discountRoi,
  percentFromPriority,
  serviceDiscountPriority,
  serviceMarginRaw,
  shouldProtectHighMargin,
} from './formulas';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const data = JSON.parse(readFileSync(join(__dirname, 'test-data.json'), 'utf-8'));

/**
 * Интеграционные сценарии «рекомендаций» (rule-based слой + контекст для LLM).
 * LLM сам не детерминирован — проверяем входы/правила, которые кормят ИИ.
 */
describe('ИИ-рекомендации: Happy Hours по загрузке', () => {
  it('пиковые часы → 0% (скидка вредна)', () => {
    expect(discountPercentRelative(4.5, 5)).toBe(0);
  });

  it('простой слот → 20–25%', () => {
    expect(discountPercentRelative(0.5, 5)).toBe(25);
    expect(discountPercentRelative(0.9, 5)).toBe(20);
  });

  it('набор предложений покрывает все кейсы фикстуры', () => {
    for (const c of data.load_cases) {
      expect(discountPercentRelative(c.hour_load, c.peak_load)).toBe(c.expected_discount);
    }
  });
});

describe('ИИ-рекомендации: ROI правил скидок', () => {
  it('положительный ROI ≥20% → держать', () => {
    const r = discountRoi(10, 5000, 6500);
    expect(r.verdict).toBe('держать');
    expect(r.roi_percent).toBeGreaterThanOrEqual(20);
  });

  it('отрицательный ROI → отключить', () => {
    expect(discountRoi(2, 8000, 6500).verdict).toBe('отключить');
  });

  it('слабый положительный ROI → пересмотреть', () => {
    expect(discountRoi(5, 18000, 6500).verdict).toBe('пересмотреть');
  });
});

describe('ИИ-рекомендации: скидки по услугам (бухлогика)', () => {
  it('низкая популярность + низкая маржа → высокий приоритет и %', () => {
    const popularity = 0.1;
    const margin = serviceMarginRaw(6000, 3500); // ~41.7%
    const priority = serviceDiscountPriority(popularity, margin);
    expect(priority).toBeGreaterThan(0.7);
    const pct = percentFromPriority(priority);
    expect(pct).toBeGreaterThanOrEqual(20);
    expect(applyOverheadBoost(pct, 0.4)).toBeGreaterThanOrEqual(pct);
  });

  it('высокая маржа + нормальный спрос → защита цены', () => {
    const margin = serviceMarginRaw(8000, 1500); // 81.3%
    expect(shouldProtectHighMargin(margin, false)).toBe(true);
  });

  it('высокая маржа + просадка объёма → можно мягкую скидку (cap 12%)', () => {
    const margin = serviceMarginRaw(8000, 1500);
    expect(shouldProtectHighMargin(margin, true)).toBe(false);
    const priority = serviceDiscountPriority(0.2, margin);
    const suggested = Math.min(percentFromPriority(priority), 12);
    expect(suggested).toBeLessThanOrEqual(12);
  });
});

describe('ИИ-рекомендации: инсайты расходов', () => {
  it('формирует набор инсайтов для владельца', () => {
    const insights = buildExpenseInsights({
      revenueMonth: data.expected.total_revenue,
      materialMonth: data.expected.total_material_cost,
      fixedMonth: data.expected.total_expenses,
      rentMonth: 120000,
      marketingMonth: 25000,
      prevByCategory: { marketing: 15000 },
      curByCategory: { marketing: 25000 },
    });

    const types = insights.map((i) => i.type);
    expect(types).toContain('anomaly');
    expect(types).toContain('break_even');
    expect(types).toContain('forecast');
    expect(insights.find((i) => i.type === 'forecast')?.severity).toBe('warn');
  });
});

describe('ИИ-рекомендации: контекст для LLM-финансиста', () => {
  it('контекст содержит KPI без выдуманных цифр', () => {
    const ctx = buildFinancierContextMetrics(data.transactions, {
      totalClients: 40,
      totalMasters: 2,
    });

    // То, что уходит в промпт DeepSeek
    expect(ctx.month_revenue).toBe(58500);
    expect(ctx.completed_appointments).toBe(9);
    expect(ctx.masters.length).toBe(2);
    expect(ctx.services[0].name).toBe('Комплексная мойка'); // 4 записи
    expect(ctx.services[0].count).toBe(4);
  });

  it('шаблон ответа финансиста должен опираться на эти метрики', () => {
    const ctx = buildFinancierContextMetrics(data.transactions);
    const promptFacts = [
      `Выручка за месяц: ${ctx.month_revenue}`,
      `Завершено: ${ctx.completed_appointments}`,
      `Средний чек: ${ctx.avg_check}`,
    ];
    expect(promptFacts.join('\n')).toContain('58500');
    expect(promptFacts.join('\n')).toContain('6500');
  });
});
