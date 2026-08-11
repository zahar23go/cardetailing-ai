import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import {
  applyOverheadBoost,
  avgCheck,
  avgLoad,
  breakEvenRevenue,
  buildExpenseInsights,
  buildFinancierContextMetrics,
  computePl,
  contributionRatio,
  discountPercentRelative,
  discountRoi,
  forecastProfit,
  grossMarginPercent,
  grossProfit,
  heatmapIntensity,
  isLowMargin,
  isLowVolume,
  netMarginPercent,
  netProfit,
  percentFromPriority,
  resolveServiceCost,
  serviceDiscountPriority,
  serviceMarginPercent,
  serviceMarginRaw,
  shouldProtectHighMargin,
  sumExpenses,
  sumMaterialCost,
  sumRevenue,
} from './formulas';

const __dirname = dirname(fileURLToPath(import.meta.url));
const data = JSON.parse(readFileSync(join(__dirname, 'test-data.json'), 'utf-8'));

describe('P&L формулы', () => {
  const { transactions, expenses, expected } = data;

  it('выручка = сумма completed total_price', () => {
    expect(sumRevenue(transactions)).toBe(expected.total_revenue);
  });

  it('материалы = сумма material_cost completed', () => {
    expect(sumMaterialCost(transactions)).toBe(expected.total_material_cost);
  });

  it('расходы = сумма amount', () => {
    expect(sumExpenses(expenses)).toBe(expected.total_expenses);
  });

  it('средний чек = выручка / число записей', () => {
    expect(avgCheck(expected.total_revenue, expected.completed_count)).toBe(expected.avg_check);
  });

  it('валовая прибыль = выручка − материалы', () => {
    expect(grossProfit(expected.total_revenue, expected.total_material_cost)).toBe(expected.gross_profit);
  });

  it('валовая маржа %', () => {
    expect(grossMarginPercent(expected.total_revenue, expected.total_material_cost)).toBe(
      expected.gross_margin_percent,
    );
  });

  it('чистая прибыль = валовая − расходы', () => {
    expect(netProfit(expected.total_revenue, expected.total_material_cost, expected.total_expenses)).toBe(
      expected.net_profit,
    );
  });

  it('чистая маржа %', () => {
    expect(
      netMarginPercent(expected.total_revenue, expected.total_material_cost, expected.total_expenses),
    ).toBe(expected.net_margin_percent);
  });

  it('computePl агрегирует всё вместе', () => {
    const pl = computePl(transactions, expenses);
    expect(pl.total_revenue).toBe(expected.total_revenue);
    expect(pl.completed_appointments).toBe(expected.completed_count);
    expect(pl.avg_check).toBe(expected.avg_check);
    expect(pl.gross_profit).toBe(expected.gross_profit);
    expect(pl.net_profit).toBe(expected.net_profit);
  });
});

describe('Маржа услуг', () => {
  for (const [id, exp] of Object.entries(data.expected.service_margins) as Array<
    [string, { margin_percent: number; price: number; cost: number }]
  >) {
    it(`услуга #${id}: ((price−cost)/price)×100 = ${exp.margin_percent}%`, () => {
      expect(serviceMarginPercent(exp.price, exp.cost)).toBe(exp.margin_percent);
      expect(resolveServiceCost(exp.cost, 0)).toBe(exp.cost);
      expect(serviceMarginRaw(exp.price, exp.cost)).toBeCloseTo(exp.margin_percent / 100, 2);
    });
  }

  it('cost_price=0 → fallback на material_cost', () => {
    expect(resolveServiceCost(0, 500)).toBe(500);
  });
});

describe('Break-even и прогноз', () => {
  const { expected } = data;
  const ratio = contributionRatio(expected.total_revenue, expected.total_material_cost);

  it('contribution ratio = (выручка − материалы) / выручка', () => {
    expect(ratio).toBeCloseTo(expected.gross_profit / expected.total_revenue, 5);
  });

  it('точка безубыточности = постоянные / contribution', () => {
    expect(breakEvenRevenue(expected.total_expenses, ratio)).toBe(expected.break_even_revenue);
  });

  it('прогноз прибыли = выручка − материалы − постоянные', () => {
    expect(
      forecastProfit(expected.total_revenue, expected.total_material_cost, expected.total_expenses),
    ).toBe(expected.net_profit);
  });

  it('без выручки contribution = 0.4 по умолчанию', () => {
    expect(contributionRatio(0, 0)).toBe(0.4);
  });
});

describe('Загрузка / Happy Hours', () => {
  it('avg_load = count / weekday_occurrences', () => {
    expect(avgLoad(10, 4)).toBe(2.5);
  });

  it('heatmap intensity = count / max', () => {
    expect(heatmapIntensity(3, 6)).toBe(0.5);
    expect(heatmapIntensity(1, 0)).toBe(0);
  });

  for (const c of data.load_cases) {
    it(`load ${c.hour_load}/${c.peak_load} → скидка ${c.expected_discount}%`, () => {
      expect(discountPercentRelative(c.hour_load, c.peak_load)).toBe(c.expected_discount);
    });
  }
});

describe('ROI скидок', () => {
  for (const c of data.discount_roi_cases) {
    it(`${c.times_used}× скидка cost=${c.discount_cost} → ${c.expected_verdict}`, () => {
      const r = discountRoi(c.times_used, c.discount_cost, c.avg_check);
      expect(r.verdict).toBe(c.expected_verdict);
      if (c.expected_roi_min != null) expect(r.roi_percent).toBeGreaterThanOrEqual(c.expected_roi_min);
      if (c.expected_roi_max != null) expect(r.roi_percent).toBeLessThan(c.expected_roi_max);
    });
  }
});

describe('Приоритет скидок по услугам', () => {
  for (const c of data.priority_cases) {
    it(`priority=${c.priority}`, () => {
      const pct = percentFromPriority(c.priority);
      if (c.expected_percent != null) expect(pct).toBe(c.expected_percent);
      if (c.expected_percent_min != null) expect(pct).toBeGreaterThanOrEqual(c.expected_percent_min);
      if (c.expected_percent_max != null) expect(pct).toBeLessThanOrEqual(c.expected_percent_max);
    });
  }

  it('priority = volume_need×0.55 + margin_need×0.45', () => {
    expect(serviceDiscountPriority(0.2, 0.4)).toBeCloseTo(0.8 * 0.55 + 0.6 * 0.45, 5);
  });

  it('overhead boost усиливает %', () => {
    expect(applyOverheadBoost(15, 0.25)).toBe(20);
    expect(applyOverheadBoost(15, 0.4)).toBe(23);
    expect(applyOverheadBoost(28, 0.4)).toBe(30);
  });

  it('защита высокой маржи', () => {
    expect(shouldProtectHighMargin(0.75, false)).toBe(true);
    expect(shouldProtectHighMargin(0.75, true)).toBe(false);
    expect(isLowVolume(2, 10, 0.2)).toBe(true);
    expect(isLowMargin(0.4, 0.6)).toBe(true);
  });
});

describe('Контекст ИИ-Финансиста', () => {
  it('собирает выручку, мастеров и услуги', () => {
    const ctx = buildFinancierContextMetrics(data.transactions, {
      totalClients: 40,
      totalMasters: 2,
    });
    expect(ctx.month_revenue).toBe(data.expected.total_revenue);
    expect(ctx.completed_appointments).toBe(data.expected.completed_count);
    expect(ctx.pending_appointments).toBe(1);
    expect(ctx.avg_check).toBe(data.expected.avg_check);

    const ivan = ctx.masters.find((m) => m.name === 'Иван');
    const petr = ctx.masters.find((m) => m.name === 'Пётр');
    expect(ivan).toMatchObject(data.expected.masters['Иван']);
    expect(petr).toMatchObject(data.expected.masters['Пётр']);
  });
});

describe('Инсайты по расходам', () => {
  it('аномалия MoM, аренда, break-even, прогноз', () => {
    const insights = buildExpenseInsights({
      revenueMonth: data.expected.total_revenue,
      materialMonth: data.expected.total_material_cost,
      fixedMonth: data.expected.total_expenses,
      rentMonth: 120000,
      marketingMonth: 25000,
      prevByCategory: { marketing: 15000, consumables: 10000 },
      curByCategory: { marketing: 25000, consumables: 15000 },
    });

    expect(insights.some((i) => i.type === 'anomaly' && i.category === 'marketing')).toBe(true);
    expect(insights.some((i) => i.type === 'tip' && i.title === 'Аренда дорогая относительно выручки')).toBe(true);
    // 58500/25000 ≈ 2.3 < 5 → реклама неэффективна
    expect(insights.some((i) => i.title === 'Реклама может быть неэффективна')).toBe(true);
    expect(insights.some((i) => i.type === 'break_even')).toBe(true);
    expect(insights.some((i) => i.type === 'forecast' && i.severity === 'warn')).toBe(true);
  });
});
