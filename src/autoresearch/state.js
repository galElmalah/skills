const path = require("path");

const { computeConfidence } = require("./metrics");
const { ensureDir, fileExists, nowIso, posixRelative, readJsonLines } = require("./utils");

const SESSION_FILE_NAMES = [
  "autoresearch.jsonl",
  "autoresearch.md",
  "autoresearch.sh",
  "autoresearch.checks.sh",
  "autoresearch.ideas.md"
];

function sessionPaths(workDir) {
  return {
    workDir,
    jsonl: path.join(workDir, "autoresearch.jsonl"),
    markdown: path.join(workDir, "autoresearch.md"),
    benchmark: path.join(workDir, "autoresearch.sh"),
    checks: path.join(workDir, "autoresearch.checks.sh"),
    ideas: path.join(workDir, "autoresearch.ideas.md"),
    logsDir: path.join(workDir, ".autoresearch-logs")
  };
}

function ensureSessionDirs(workDir) {
  ensureDir(sessionPaths(workDir).logsDir);
}

function loadEntries(workDir) {
  return readJsonLines(sessionPaths(workDir).jsonl);
}

function latestConfig(entries) {
  const configs = entries.filter((entry) => entry.type === "config");
  return configs.length ? configs[configs.length - 1] : null;
}

function latestSegment(entries) {
  const config = latestConfig(entries);
  return config ? Number(config.segment || 1) : 1;
}

function nextRunNumber(entries) {
  const maxRun = entries.reduce((value, entry) => {
    const run = Number(entry.run || 0);
    return Number.isFinite(run) && run > value ? run : value;
  }, 0);
  return maxRun + 1;
}

function formatStatus(status) {
  switch (status) {
    case "keep":
      return "KEPT";
    case "discard":
      return "DISCARDED";
    case "crash":
      return "CRASHED";
    case "checks_failed":
      return "CHECKS FAILED";
    default:
      return String(status || "UNKNOWN").toUpperCase();
  }
}

function buildLogPaths(record) {
  return [
    record.stream_output_path,
    record.raw_output_path,
    record.final_output_path,
    record.checks_output_path,
    record.result_path
  ].filter(Boolean);
}

function mapResultRecord(record) {
  return {
    id: record.id,
    title: record.description,
    hypothesis: record.asi && typeof record.asi.hypothesis === "string" ? record.asi.hypothesis : "",
    lesson: record.asi && typeof record.asi.lesson === "string" ? record.asi.lesson : "",
    reason:
      (record.asi && typeof record.asi.rollback_reason === "string" && record.asi.rollback_reason) ||
      record.description,
    comparison_to_champion:
      record.asi && typeof record.asi.comparison_to_champion === "string"
        ? record.asi.comparison_to_champion
        : "",
    status: formatStatus(record.status),
    result: record.metric,
    metrics: record.metrics || {},
    duration_ms: record.duration_ms || null,
    files_touched: record.files_touched || [],
    log_paths: buildLogPaths(record),
    stream_output_path: record.stream_output_path || null,
    raw_output_path: record.raw_output_path || null,
    final_output_path: record.final_output_path || null,
    checks_output_path: record.checks_output_path || null,
    parent_commit: record.parent_commit || null,
    candidate_commit: record.candidate_commit || null,
    commit: record.commit || null,
    timestamp: record.timestamp || record.finished_at || record.started_at || nowIso(),
    confidence: record.confidence ?? null,
    command: record.command || null,
    verification_result: record.checks_pass === true ? "pass" : record.checks_pass === false ? "fail" : "",
    verification_command: record.verification_command || "",
    summary_path: record.result_path || null
  };
}

function mapBaselineRecord(record) {
  return {
    id: record.id,
    status: "BASELINE",
    result: record.metric,
    duration_ms: record.duration_ms || null,
    log_paths: buildLogPaths(record),
    stream_output_path: record.stream_output_path || null,
    raw_output_path: record.raw_output_path || null,
    final_output_path: record.final_output_path || null,
    checks_output_path: record.checks_output_path || null
  };
}

function buildDerivedState(workDir) {
  const entries = loadEntries(workDir);
  const config = latestConfig(entries);
  if (!config) {
    return {
      entries,
      state: null
    };
  }

  const currentSegment = latestSegment(entries);
  const segmentEntries = entries.filter((entry) => Number(entry.segment || currentSegment) === currentSegment);
  const startedById = new Map();
  const results = [];

  for (const entry of segmentEntries) {
    if (entry.type === "run_started") startedById.set(entry.id, entry);
    if (entry.type === "run_result") {
      results.push(entry);
      startedById.delete(entry.id);
    }
  }

  const activeExperiment = startedById.size
    ? {
        ...Array.from(startedById.values()).pop(),
        status: "IN PROGRESS",
        result: null,
        duration_ms: null,
        log_paths: buildLogPaths(Array.from(startedById.values()).pop())
      }
    : null;

  const baseline = results.length ? results[0] : null;
  const postBaseline = results.slice(1);
  const direction = config.direction === "higher" ? "max" : "min";

  let champion = baseline;
  for (const result of results.slice(1)) {
    if (result.status !== "keep") continue;
    if (!champion) {
      champion = result;
      continue;
    }
    if (direction === "max") {
      if (Number(result.metric) > Number(champion.metric)) champion = result;
    } else if (Number(result.metric) < Number(champion.metric)) {
      champion = result;
    }
  }

  const confidence = computeConfidence(results, config.direction === "higher" ? "higher" : "lower");
  const totalDurationMs = results.reduce((sum, result) => sum + Number(result.duration_ms || 0), 0);
  const experiments = postBaseline.map((record) => ({
    ...mapResultRecord(record),
    confidence: record.confidence ?? confidence
  }));

  const state = {
    objective: {
      goal: config.goal || config.name,
      metric: config.metric_name,
      direction,
      cheap_eval_command: config.command || "./autoresearch.sh",
      verification_command: config.verification_command || "",
      verification_policy: config.verification_policy || "none",
      full_eval_command: config.holdout_command || "",
      runtime_budget: config.runtime_budget || "",
      max_iterations: config.max_iterations ?? null
    },
    summary: {
      baseline: baseline ? baseline.metric : null,
      champion_commit: champion ? champion.commit || champion.candidate_commit || champion.parent_commit || "" : "",
      champion_score: champion ? champion.metric : null,
      experiments_run: results.length,
      kept: postBaseline.filter((result) => result.status === "keep").length,
      discarded: postBaseline.filter((result) => result.status === "discard").length,
      crashed: postBaseline.filter((result) => result.status === "crash").length,
      checks_failed: postBaseline.filter((result) => result.status === "checks_failed").length,
      iterations: results.length,
      total_duration_ms: totalDurationMs,
      confidence
    },
    active_experiment: activeExperiment
      ? {
          id: activeExperiment.id,
          title: activeExperiment.description || activeExperiment.id,
          status: "IN PROGRESS",
          command: activeExperiment.command,
          stream_output_path: activeExperiment.stream_output_path || null,
          raw_output_path: activeExperiment.raw_output_path || null,
          final_output_path: activeExperiment.final_output_path || null,
          checks_output_path: activeExperiment.checks_output_path || null,
          log_paths: buildLogPaths(activeExperiment)
        }
      : null,
    baseline_runs: baseline ? [mapBaselineRecord(baseline)] : [],
    experiments
  };

  return {
    entries,
    state
  };
}

function relativeSessionArtifacts(workDir, gitRoot) {
  const base = posixRelative(gitRoot, workDir);
  const values = {};
  for (const name of SESSION_FILE_NAMES) {
    values[name] = base === "" ? name : `${base}/${name}`;
  }
  values[".autoresearch-logs"] = base === "" ? ".autoresearch-logs" : `${base}/.autoresearch-logs`;
  values[".eval-logs"] = base === "" ? ".eval-logs" : `${base}/.eval-logs`;
  return values;
}

module.exports = {
  buildDerivedState,
  ensureSessionDirs,
  latestSegment,
  loadEntries,
  nextRunNumber,
  relativeSessionArtifacts,
  sessionPaths
};
