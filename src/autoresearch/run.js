const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const { parseMetricLines } = require("./metrics");
const { getHeadCommit, getGitRoot } = require("./git");
const { appendJsonLine, ensureDir, formatMetricValue, nowIso, posixRelative, tailText, writeJson } = require("./utils");
const { buildDerivedState, ensureSessionDirs, latestSegment, nextRunNumber, sessionPaths } = require("./state");

function runShell(command, cwd, timeoutMs) {
  const startedAt = Date.now();
  const result = spawnSync("bash", ["-lc", command], {
    cwd,
    encoding: "utf8",
    timeout: timeoutMs,
    maxBuffer: 20 * 1024 * 1024
  });

  const durationMs = Date.now() - startedAt;
  const stdout = result.stdout || "";
  const stderr = result.stderr || "";
  const output = `${stdout}${stderr ? (stdout ? "\n" : "") + stderr : ""}`;
  const timedOut = Boolean(result.error && result.error.code === "ETIMEDOUT");
  const exitCode = typeof result.status === "number" ? result.status : timedOut ? 124 : 1;

  return {
    command,
    cwd,
    durationMs,
    exitCode,
    output,
    timedOut,
    passed: exitCode === 0 && !timedOut,
    metrics: parseMetricLines(output),
    startedAt: new Date(startedAt).toISOString(),
    finishedAt: nowIso()
  };
}

function defaultCommand(workDir, state) {
  const paths = sessionPaths(workDir);
  if (fs.existsSync(paths.benchmark)) return "bash ./autoresearch.sh";
  if (state && state.objective && state.objective.cheap_eval_command) {
    return state.objective.cheap_eval_command;
  }
  throw new Error("No benchmark command configured. Create autoresearch.sh or pass --command.");
}

function defaultChecksCommand(workDir, state) {
  const paths = sessionPaths(workDir);
  if (state && state.objective && state.objective.verification_command) {
    return state.objective.verification_command;
  }
  if (fs.existsSync(paths.checks)) return "bash ./autoresearch.checks.sh";
  return "";
}

function nextRunId(entries) {
  const runNumber = nextRunNumber(entries);
  return `EXP-${String(runNumber).padStart(3, "0")}`;
}

function selectPrimaryMetric(metricName, metrics) {
  if (metricName && Object.prototype.hasOwnProperty.call(metrics, metricName)) {
    return metrics[metricName];
  }
  const keys = Object.keys(metrics);
  if (!keys.length) return null;
  return metrics[keys[0]];
}

function runExperiment(workDir, options = {}) {
  ensureSessionDirs(workDir);
  const { entries, state } = buildDerivedState(workDir);
  if (!state) {
    throw new Error("No autoresearch session initialized. Run `autoresearch init` first.");
  }

  if (state.active_experiment && !options.allowConcurrent) {
    throw new Error(`Run ${state.active_experiment.id} is still active. Log it before starting another run.`);
  }

  const segment = latestSegment(entries);
  const id = nextRunId(entries);
  const runDir = path.join(sessionPaths(workDir).logsDir, id);
  ensureDir(runDir);

  const benchmarkLogPath = path.join(runDir, "benchmark.log");
  const benchmarkSummaryPath = path.join(runDir, "benchmark-summary.txt");
  const resultPath = path.join(runDir, "result.json");
  const checksLogPath = path.join(runDir, "checks.log");
  const command = options.command || defaultCommand(workDir, state);

  const gitRoot = getGitRoot(workDir);
  const relativeWorkDir = posixRelative(gitRoot, workDir) || ".";
  const parentCommit = getHeadCommit(workDir);
  const runStarted = {
    type: "run_started",
    segment,
    run: nextRunNumber(entries),
    id,
    command,
    started_at: nowIso(),
    parent_commit: parentCommit,
    stream_output_path: posixRelative(workDir, benchmarkLogPath),
    raw_output_path: posixRelative(workDir, benchmarkLogPath),
    final_output_path: posixRelative(workDir, benchmarkSummaryPath),
    result_path: posixRelative(workDir, resultPath),
    checks_output_path: posixRelative(workDir, checksLogPath)
  };
  appendJsonLine(sessionPaths(workDir).jsonl, runStarted);

  const runResult = runShell(command, workDir, Number(options.timeoutSeconds || 600) * 1000);
  fs.writeFileSync(benchmarkLogPath, runResult.output);

  const checksCommand = defaultChecksCommand(workDir, state);
  let checksResult = null;
  if (runResult.passed && checksCommand && state.objective.verification_policy !== "none") {
    checksResult = runShell(checksCommand, workDir, Number(options.checksTimeoutSeconds || 300) * 1000);
    fs.writeFileSync(checksLogPath, checksResult.output);
  }

  const metric = selectPrimaryMetric(state.objective.metric, runResult.metrics);
  const payload = {
    id,
    run: runStarted.run,
    segment,
    command,
    verification_command: checksCommand,
    parent_commit: parentCommit,
    metric,
    metrics: runResult.metrics,
    duration_ms: runResult.durationMs,
    exit_code: runResult.exitCode,
    timed_out: runResult.timedOut,
    passed: runResult.passed,
    output_tail: tailText(runResult.output, 4000),
    started_at: runResult.startedAt,
    finished_at: runResult.finishedAt,
    stream_output_path: runStarted.stream_output_path,
    raw_output_path: runStarted.raw_output_path,
    final_output_path: runStarted.final_output_path,
    result_path: runStarted.result_path,
    checks_output_path: checksCommand ? runStarted.checks_output_path : null,
    checks: checksResult
      ? {
          exit_code: checksResult.exitCode,
          timed_out: checksResult.timedOut,
          passed: checksResult.passed,
          output_tail: tailText(checksResult.output, 4000),
          duration_ms: checksResult.durationMs
        }
      : null,
    relative_workdir: relativeWorkDir
  };

  writeJson(resultPath, payload);
  const summaryLines = [
    `Run ${id}`,
    `Command: ${command}`,
    `Duration: ${runResult.durationMs}ms`,
    `Exit code: ${runResult.exitCode}`,
    `Primary metric (${state.objective.metric}): ${metric === null ? "missing" : formatMetricValue(metric)}`,
    checksResult
      ? `Checks: ${checksResult.passed ? "pass" : checksResult.timedOut ? "timed out" : "failed"}`
      : "Checks: not run"
  ];
  fs.writeFileSync(benchmarkSummaryPath, `${summaryLines.join("\n")}\n`);

  return payload;
}

module.exports = {
  runExperiment
};
