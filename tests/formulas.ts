/**
 * Чистые формулы финансов / ИИ-Финансиста (зеркало backend/app/finance_formulas.py).
 * Используются в юнит-тестах tests/formulas.test.ts.
 */

export type Tx = {
  total_price?: number;
  material_cost?: number;
  status?: string;
  service_id?: number;
  service_name?: string;
  master_id?: number;
  master_name?: string;
};

export type Expense = {
  amount?: number;
  category?: string;
};

export function sumRevenue(transactions: Tx[], completedOnly = true): number {
  let total = 0;
  for (const t of transactions) {
    if (completedOnly && (t.status ?? 'completed') !== 'completed') continue;
    total += Number(t.total_price ?? 0);
  }
  return round2(total);
}

export function avgCheck(revenue: number, completedCount: number): number {
  if (completedCount <= 0) return 0;
  return round2(revenue / completedCount);
}

export function sumMaterialCost(transactions: Tx[], completedOnly = true): number {
  let total = 0;
  for (const t of transactions) {
    if (completedOnly && (t.status ?? 'completed') !== 'completed') continue;
    total += Number(t.material_cost ?? 0);
  }
  return round2(total);
}

export function sumExpenses(expenses: Expense[]): number {
  return round2(expenses.reduce((s, e) => s + Number(e.amount ?? 0), 0));
}

export function grossProfit(revenue: number, materialCost: number): number {
  return round2(revenue - materialCost);
}

export function grossMarginPercent(revenue: number, materialCost: number): number {
  if (revenue <= 0) return 0;
  return round1(((revenue - materialCost) / revenue) * 100);
}

export function netProfit(revenue: number, materialCost: number, expenses: number): number {
  return round2(revenue - materialCost - expenses);
}

export function netMarginPercent(revenue: number, materialCost: number, expenses: number): number {
  if (revenue <= 0) return 0;
  return round1(netProfit(revenue, materialCost, expenses) / revenue * 100);
}

export function serviceMarginPercent(price: number, cost: number): number {
  if (price <= 0) return 0;
  return round1(((price - cost) / price) * 100);
}

export function serviceMarginRaw(price: number, cost: number): number {
  if (price <= 0) return 0;
  return Math.max(0, Math.min(1, (price - cost) / price));
}

export function resolveServiceCost(costPrice?: number | null, materialCost?: number | null): number {
  const cp = Number(costPrice ?? 0);
  if (cp > 0) return cp;
  return Number(materialCost ?? 0);
}

export function computePl(transactions: Tx[], expenses: Expense[]) {
  const completed = transactions.filter((t) => (t.status ?? 'completed') === 'completed');
  const revenue = sumRevenue(completed, false);
  const materials = sumMaterialCost(completed, false);
  const fixed = sumExpenses(expenses);
  const count = completed.length;

  const byService = new Map<number, {
    service_id: number;
    service_name: string;
    total_revenue: number;
    total_material_cost: number;
    appointment_count: number;
  }>();

  for (const t of completed) {
    if (t.service_id == null) continue;
    const cur = byService.get(t.service_id) ?? {
      service_id: t.service_id,
      service_name: t.service_name ?? `Услуга #${t.service_id}`,
      total_revenue: 0,
      total_material_cost: 0,
      appointment_count: 0,
    };
    cur.total_revenue += Number(t.total_price ?? 0);
    cur.total_material_cost += Number(t.material_cost ?? 0);
    cur.appointment_count += 1;
    byService.set(t.service_id, cur);
  }

  const service_margins = [...byService.values()].map((s) => {
    const gp = s.total_revenue - s.total_material_cost;
    const mp = s.total_revenue ? round1((gp / s.total_revenue) * 100) : 0;
    return {
      ...s,
      total_revenue: round2(s.total_revenue),
      total_material_cost: round2(s.total_material_cost),
      gross_profit: round2(gp),
      margin_percent: mp,
    };
  }).sort((a, b) => b.appointment_count - a.appointment_count);

  return {
    total_revenue: revenue,
    completed_appointments: count,
    avg_check: avgCheck(revenue, count),
    total_material_cost: materials,
    total_expenses: fixed,
    gross_profit: grossProfit(revenue, materials),
    gross_margin_percent: grossMarginPercent(revenue, materials),
    net_profit: netProfit(revenue, materials, fixed),
    net_margin_percent: netMarginPercent(revenue, materials, fixed),
    service_margins,
  };
}

export function contributionRatio(revenue: number, materialCost: number, fallback = 0.4): number {
  if (revenue <= 0) return fallback;
  return (revenue - materialCost) / revenue;
}

export function breakEvenRevenue(fixedCosts: number, contribRatio: number): number {
  if (contribRatio <= 0) return 0;
  return round2(fixedCosts / contribRatio);
}

export function forecastProfit(revenue: number, materialCost: number, fixedCosts: number): number {
  return round2(revenue - materialCost - fixedCosts);
}

export function avgLoad(count: number, weekdayOccurrences: number): number {
  return count / Math.max(weekdayOccurrences, 1);
}

export function heatmapIntensity(count: number, maxCount: number): number {
  if (maxCount <= 0) return 0;
  return count / maxCount;
}

/** Happy Hours % относительно пика группы. */
export function discountPercentRelative(hourLoad: number, peakLoad: number): number {
  if (peakLoad <= 0) return 25;
  const ratio = hourLoad / peakLoad;
  if (ratio >= 0.55) return 0;
  if (ratio >= 0.35) return 10;
  if (ratio >= 0.2) return 15;
  if (hourLoad <= 0 || ratio < 0.12) return 25;
  return 20;
}

export function discountRoi(
  timesUsed: number,
  discountCost: number,
  avgCheckValue: number,
  liftFactor = 0.6,
) {
  const extra = avgCheckValue ? round2(timesUsed * avgCheckValue * liftFactor) : 0;
  let roiPct: number;
  if (discountCost > 0) {
    roiPct = round1(((extra - discountCost) / discountCost) * 100);
  } else {
    roiPct = timesUsed > 0 ? 100 : 0;
  }
  const verdict = roiPct >= 20 ? 'держать' : roiPct >= 0 ? 'пересмотреть' : 'отключить';
  return { estimated_extra_revenue: extra, roi_percent: roiPct, verdict };
}

export function percentFromPriority(priority: number): number {
  if (priority >= 0.7) {
    const t = Math.min(1, (priority - 0.7) / 0.3);
    return Math.round(20 + t * 10);
  }
  if (priority >= 0.45) {
    const t = (priority - 0.45) / 0.25;
    return Math.round(10 + t * 10);
  }
  return 0;
}

export function serviceDiscountPriority(popularity: number, marginRaw: number): number {
  return (1 - popularity) * 0.55 + (1 - marginRaw) * 0.45;
}

export function overheadPressure(fixedMonth: number, revenueMonth: number): number {
  return fixedMonth / Math.max(revenueMonth, 1);
}

export function applyOverheadBoost(suggested: number, pressure: number): number {
  if (pressure >= 0.35) return Math.min(30, suggested + 8);
  if (pressure >= 0.2) return Math.min(30, suggested + 5);
  return suggested;
}

export const HIGH_MARGIN_PROTECT = 0.7;

export function shouldProtectHighMargin(marginRaw: number, isLowVolume: boolean): boolean {
  return marginRaw >= HIGH_MARGIN_PROTECT && !isLowVolume;
}

export function isLowVolume(bookings: number, maxBookings: number, popularity: number): boolean {
  return bookings <= Math.max(1, Math.floor(maxBookings * 0.45)) || popularity <= 0.45;
}

export function isLowMargin(marginRaw: number, marginMedian: number): boolean {
  return marginRaw <= marginMedian || marginRaw < 0.55;
}

export function categorySharePercent(amount: number, total: number): number {
  if (total <= 0) return 0;
  return round1((amount / total) * 100);
}

export function rentShareWarn(rentMonth: number, revenueMonth: number, threshold = 25): boolean {
  if (revenueMonth <= 0 || rentMonth <= 0) return false;
  return (rentMonth / revenueMonth) * 100 >= threshold;
}

export function marketingRoiProxy(revenueMonth: number, marketingMonth: number): number | null {
  if (marketingMonth <= 0) return null;
  return revenueMonth / marketingMonth;
}

export function buildExpenseInsights(input: {
  revenueMonth: number;
  materialMonth: number;
  fixedMonth: number;
  rentMonth?: number;
  marketingMonth?: number;
  prevByCategory?: Record<string, number>;
  curByCategory?: Record<string, number>;
}) {
  const insights: Array<Record<string, unknown>> = [];
  const {
    revenueMonth,
    materialMonth,
    fixedMonth,
    rentMonth = 0,
    marketingMonth = 0,
    prevByCategory,
    curByCategory,
  } = input;

  if (prevByCategory && curByCategory) {
    for (const [cat, prevV] of Object.entries(prevByCategory)) {
      const curV = curByCategory[cat] ?? 0;
      if (prevV > 0 && curV > prevV * 1.3) {
        const growth = ((curV - prevV) / prevV) * 100;
        insights.push({
          type: 'anomaly',
          severity: growth >= 40 ? 'critical' : 'warn',
          growth_percent: round1(growth),
          category: cat,
        });
      }
    }
  }

  if (rentShareWarn(rentMonth, revenueMonth)) {
    insights.push({
      type: 'tip',
      severity: 'warn',
      title: 'Аренда дорогая относительно выручки',
      share_percent: round1((rentMonth / revenueMonth) * 100),
    });
  }

  const roi = marketingRoiProxy(revenueMonth, marketingMonth);
  if (roi != null) {
    if (roi < 5) {
      insights.push({ type: 'tip', severity: 'warn', title: 'Реклама может быть неэффективна', roi_proxy: round1(roi) });
    } else if (roi >= 10) {
      insights.push({ type: 'tip', severity: 'info', title: 'Реклама работает', roi_proxy: round1(roi) });
    }
  }

  const ratio = contributionRatio(revenueMonth, materialMonth);
  insights.push({
    type: 'break_even',
    severity: 'info',
    break_even_revenue: breakEvenRevenue(fixedMonth, ratio),
  });
  const fp = forecastProfit(revenueMonth, materialMonth, fixedMonth);
  insights.push({
    type: 'forecast',
    severity: fp >= 0 ? 'info' : 'warn',
    forecast_profit: fp,
  });
  return insights;
}

export function buildFinancierContextMetrics(
  transactions: Tx[],
  opts: { totalClients?: number; totalMasters?: number } = {},
) {
  const completed = transactions.filter((t) => t.status === 'completed');
  const pending = transactions.filter((t) => t.status === 'pending');
  const revenue = sumRevenue(completed, false);

  const masters = new Map<number, { name: string; completed: number; revenue: number }>();
  for (const t of completed) {
    if (!t.master_id) continue;
    const cur = masters.get(t.master_id) ?? {
      name: t.master_name ?? `мастер #${t.master_id}`,
      completed: 0,
      revenue: 0,
    };
    cur.completed += 1;
    cur.revenue += Number(t.total_price ?? 0);
    masters.set(t.master_id, cur);
  }

  const services = new Map<number, { name: string; count: number }>();
  for (const t of transactions) {
    if (!t.service_id) continue;
    const cur = services.get(t.service_id) ?? {
      name: t.service_name ?? `услуга #${t.service_id}`,
      count: 0,
    };
    cur.count += 1;
    services.set(t.service_id, cur);
  }

  return {
    total_clients: opts.totalClients ?? 0,
    total_masters: opts.totalMasters ?? 0,
    total_appointments: transactions.length,
    completed_appointments: completed.length,
    pending_appointments: pending.length,
    month_revenue: revenue,
    avg_check: avgCheck(revenue, completed.length),
    masters: [...masters.values()].sort((a, b) => b.completed - a.completed),
    services: [...services.values()].sort((a, b) => b.count - a.count),
  };
}

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

function round1(n: number): number {
  return Math.round(n * 10) / 10;
}
