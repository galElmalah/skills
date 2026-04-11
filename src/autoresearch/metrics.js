const METRIC_LINE_PREFIX = "METRIC";

function parseMetricLines(output) {
  const metrics = {};
  const regex = new RegExp(`^${METRIC_LINE_PREFIX}\\s+([\\w.µ-]+)=(\\S+)\\s*$`, "gm");
  let match = null;
  while ((match = regex.exec(output)) !== null) {
    const value = Number(match[2]);
    if (Number.isFinite(value)) {
      metrics[match[1]] = value;
    }
  }
  return metrics;
}

function median(values) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 1) return sorted[middle];
  return (sorted[middle - 1] + sorted[middle]) / 2;
}

function computeMad(values) {
  const med = median(values);
  if (med === null) return null;
  const deviations = values.map((value) => Math.abs(value - med));
  return median(deviations);
}

function computeConfidence(results, direction) {
  const values = results
    .map((result) => Number(result.metric))
    .filter((value) => Number.isFinite(value));
  if (values.length < 3) return null;

  const baseline = values[0];
  const mad = computeMad(values);
  if (!Number.isFinite(mad) || mad === 0) return null;

  const improvements = values.slice(1).map((value) => {
    if (direction === "higher") return value - baseline;
    return baseline - value;
  });

  if (!improvements.length) return null;
  const bestImprovement = Math.max(...improvements);
  if (!Number.isFinite(bestImprovement) || bestImprovement <= 0) return 0;
  return bestImprovement / mad;
}

module.exports = {
  computeConfidence,
  parseMetricLines
};
