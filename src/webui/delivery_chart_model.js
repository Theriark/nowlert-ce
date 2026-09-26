"use strict";

(() => {
  function buildCumulativeSeries(buckets, bucketSeconds) {
    let total = 0;
    const points = [];
    buckets.forEach((bucket, index) => {
      const delta = Number(bucket.delivered || 0) + Number(bucket.failed || 0) + Number(bucket.retry || 0);
      if (delta <= 0) return;
      total += delta;
      points.push({
        index,
        time: Number(bucket.start) + bucketSeconds / 2,
        value: total,
        delta,
      });
    });
    return { points, total };
  }

  function buildStepPath(points, xAt, yAt, startX, endX) {
    let path = `M ${startX} ${yAt(0)}`;
    for (const point of points) path += ` H ${xAt(point.time)} V ${yAt(point.value)}`;
    return `${path} H ${endX}`;
  }

  function pulseDelay(time, start, seconds, duration) {
    const progress = Math.max(0, Math.min(1, (time - start) / seconds));
    return Math.round(progress * duration);
  }

  function shouldAnimateRender(currentSignature, nextSignature, requested) {
    return requested === true || currentSignature !== nextSignature;
  }

  window.NowlertDeliveryChart = Object.freeze({ buildCumulativeSeries, buildStepPath, pulseDelay, shouldAnimateRender });
})();
