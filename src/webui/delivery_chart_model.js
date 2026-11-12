"use strict";

(() => {
  // Per-slot totals: the chart shows how often deliveries happen in each slot of
  // the selected range. A running total only ever rises and hides the rhythm.
  function buildColumns(buckets) {
    const columns = buckets.map((bucket) => {
      const delivered = Number(bucket.delivered || 0);
      const failed = Number(bucket.failed || 0);
      const retry = Number(bucket.retry || 0);
      return { start: Number(bucket.start), delivered, failed, retry, total: delivered + failed + retry };
    });
    const peak = columns.reduce((highest, column) => Math.max(highest, column.total), 0);
    return { columns, peak };
  }

  // Round axis steps (1, 2, 5 × 10^n) with headroom above the tallest column.
  function niceAxis(peak) {
    const rawTick = Math.max(1, peak / 4);
    const scale = 10 ** Math.floor(Math.log10(rawTick));
    const normalized = rawTick / scale;
    const tickStep = Math.max(1, (normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10) * scale);
    let maximum = Math.max(tickStep, Math.ceil(peak / tickStep) * tickStep);
    if (peak > 0 && maximum === peak) maximum += tickStep;
    return { tickStep, maximum, intervals: Math.round(maximum / tickStep) };
  }

  // "30 seconds", "5 minutes", "hour", "day", "week" or "month" for "Deliveries per …".
  function slotLabel(seconds) {
    const plural = (count, unit) => (count === 1 ? unit : `${count} ${unit}s`);
    if (seconds < 60) return plural(Math.round(seconds), "second");
    if (seconds < 3_600) return plural(Math.round(seconds / 60), "minute");
    if (seconds < 86_400) return plural(Math.round(seconds / 3_600), "hour");
    if (seconds < 6 * 86_400) return plural(Math.round(seconds / 86_400), "day");
    if (seconds < 25 * 86_400) return plural(Math.round(seconds / (7 * 86_400)), "week");
    return plural(Math.round(seconds / (30 * 86_400)), "month");
  }

  function shouldAnimateRender(currentSignature, nextSignature, requested) {
    return requested === true || currentSignature !== nextSignature;
  }

  window.NowlertDeliveryChart = Object.freeze({ buildColumns, niceAxis, slotLabel, shouldAnimateRender });
})();
