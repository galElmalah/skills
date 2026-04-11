const fs = require("fs");
const path = require("path");

const {
  cleanupUntracked,
  commitStaged,
  getCurrentBranch,
  getGitRoot,
  getHeadCommit,
  hasStagedChanges,
  listChangedFilesBetween,
  listUntrackedPaths,
  restoreWorktree,
  runGit,
  stagePath
} = require("./git");
const { computeConfidence } = require("./metrics");
const { runExperiment } = require("./run");
const { buildDerivedState, latestSegment, loadEntries, relativeSessionArtifacts, sessionPaths } = require("./state");
const { appendJsonLine, ensureDir, fileExists, nowIso, posixRelative, readJson, slugify } = require("./utils");
const { startDashboardServer } = require("./dashboard");
const { applyFinalizeProposal, buildFinalizeProposal, writeFinalizeProposal } = require("./finalize");

function parseArgs(argv) {
  const result = { _: [] };
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (!value.startsWith("--")) {
      result._.push(value);
      continue;
    }
    const key = value.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith("--")) {
      result[key] = true;
      continue;
    }
    result[key] = next;
    index += 1;
  }
  return result;
}

function resolveWorkDir(flags) {
  const candidate = path.resolve(flags.workdir || process.cwd());
  return fs.existsSync(candidate) ? fs.realpathSync(candidate) : candidate;
}

function requireValue(flags, key, description) {
  if (!flags[key]) {
    throw new Error(`Missing --${key}${description ? ` (${description})` : ""}.`);
  }
  return flags[key];
}

function normalizeDirection(value) {
  if (value === "higher" || value === "max") return "higher";
  return "lower";
}

function isSessionArtifact(relativePath, protectedPaths) {
  const normalized = relativePath.split(path.sep).join("/");
  return protectedPaths.some((protectedPath) => {
    const target = protectedPath.split(path.sep).join("/");
    return normalized === target || normalized.startsWith(`${target}/`);
  });
}

function filterCandidateFiles(files, protectedPaths) {
  return files.filter((filePath) => !isSessionArtifact(filePath, protectedPaths));
}

function initSession(flags) {
  const workDir = resolveWorkDir(flags);
  ensureDir(workDir);
  const jsonlPath = sessionPaths(workDir).jsonl;
  const entries = loadEntries(workDir);
  const segment = entries.filter((entry) => entry.type === "config").length + 1;

  const gitRoot = getGitRoot(workDir);
  const branch = getCurrentBranch(workDir);
  if (!branch) {
    throw new Error("Detached HEAD. Switch to a branch before initializing autoresearch.");
  }

  const config = {
    type: "config",
    segment,
    timestamp: nowIso(),
    workdir: workDir,
    name: requireValue(flags, "name", "human-readable session name"),
    goal: flags.goal || flags.name,
    metric_name: requireValue(flags, "metric", "primary metric name"),
    metric_unit: flags.unit || "",
    direction: normalizeDirection(flags.direction),
    command: flags.command || "./autoresearch.sh",
    verification_command: flags["verify-command"] || "",
    verification_policy: flags["verification-policy"] || (flags["verify-command"] ? "required_before_keep" : "none"),
    holdout_command: flags["holdout-command"] || "",
    runtime_budget: flags["runtime-budget"] || "",
    max_iterations: flags["max-iterations"] ? Number(flags["max-iterations"]) : null,
    git_root: gitRoot,
    git_branch: branch
  };

  appendJsonLine(jsonlPath, config);
  process.stdout.write(`Initialized autoresearch "${config.name}" in ${workDir}\n`);
}

function statusSession(flags) {
  const workDir = resolveWorkDir(flags);
  const { state } = buildDerivedState(workDir);
  if (!state) {
    throw new Error(`No autoresearch session found in ${workDir}.`);
  }
  if (flags.json) {
    process.stdout.write(`${JSON.stringify(state, null, 2)}\n`);
    return;
  }
  const lines = [
    `Goal: ${state.objective.goal}`,
    `Metric: ${state.objective.metric} (${state.objective.direction})`,
    `Baseline: ${state.summary.baseline ?? "—"}`,
    `Champion: ${state.summary.champion_score ?? "—"}`,
    `Iterations: ${state.summary.iterations}`,
    `Kept / discarded: ${state.summary.kept} / ${state.summary.discarded}`
  ];
  if (state.active_experiment) {
    lines.push(`Active: ${state.active_experiment.id} (${state.active_experiment.command})`);
  }
  process.stdout.write(`${lines.join("\n")}\n`);
}

function logExperiment(flags) {
  const workDir = resolveWorkDir(flags);
  const paths = sessionPaths(workDir);
  const entries = loadEntries(workDir);
  const segment = latestSegment(entries);
  const runId = flags["run-id"] || (() => {
    const { state } = buildDerivedState(workDir);
    return state && state.active_experiment ? state.active_experiment.id : "";
  })();

  if (!runId) {
    throw new Error("No active run found. Pass --run-id explicitly.");
  }

  const resultPath = path.join(paths.logsDir, runId, "result.json");
  if (!fileExists(resultPath)) {
    throw new Error(`No run result found for ${runId}. Expected ${resultPath}.`);
  }

  const result = readJson(resultPath);
  const status = flags.status || (!result.passed ? "crash" : result.checks && result.checks.passed === false ? "checks_failed" : "discard");
  const description = requireValue(flags, "description", "decision description");
  const asi = flags["asi-json"] ? JSON.parse(flags["asi-json"]) : {};
  const gitRoot = getGitRoot(workDir);
  const relativeWorkDir = posixRelative(gitRoot, workDir) || ".";
  const protectedPaths = Object.values(relativeSessionArtifacts(workDir, gitRoot));

  if (status === "keep" && result.checks && result.checks.passed === false) {
    throw new Error("Cannot keep this run because autoresearch checks failed.");
  }

  let filesTouched = [];
  try {
    filesTouched = listChangedFilesBetween(gitRoot, "HEAD", "HEAD", relativeWorkDir);
  } catch {
    filesTouched = [];
  }
  const untrackedBefore = listUntrackedPaths(gitRoot, relativeWorkDir);

  let candidateCommit = null;
  let commit = null;
  if (status === "keep") {
    stagePath(gitRoot, relativeWorkDir);
    runGit(
      [
        "reset",
        "HEAD",
        "--",
        relativeSessionArtifacts(workDir, gitRoot)[".autoresearch-logs"],
        relativeSessionArtifacts(workDir, gitRoot)[".eval-logs"]
      ],
      { cwd: gitRoot, allowFailure: true }
    );
    if (hasStagedChanges(gitRoot, relativeWorkDir)) {
      const trailer = JSON.stringify({
        status,
        [buildDerivedState(workDir).state.objective.metric]: result.metric,
        ...(result.metrics || {})
      });
      const commitMessage = `${description}\n\nResult: ${trailer}`;
      commitStaged(gitRoot, commitMessage);
      candidateCommit = getHeadCommit(workDir);
      commit = candidateCommit.slice(0, 7);
      filesTouched = filterCandidateFiles(
        listChangedFilesBetween(gitRoot, result.parent_commit, candidateCommit, relativeWorkDir),
        protectedPaths
      );
    } else {
      candidateCommit = getHeadCommit(workDir);
      commit = candidateCommit.slice(0, 7);
    }
  } else {
    restoreWorktree(gitRoot, relativeWorkDir);
    cleanupUntracked(gitRoot, untrackedBefore, protectedPaths);
  }

  const existingResults = entries
    .filter((entry) => entry.type === "run_result" && Number(entry.segment || 0) === segment)
    .map((entry) => ({ metric: Number(entry.metric) }))
    .filter((entry) => Number.isFinite(entry.metric));
  const confidence = computeConfidence(
    existingResults.concat(Number.isFinite(result.metric) ? [{ metric: result.metric }] : []),
    buildDerivedState(workDir).state.objective.direction === "max" ? "higher" : "lower"
  );

  const record = {
    type: "run_result",
    segment,
    run: result.run,
    id: runId,
    status,
    description,
    timestamp: nowIso(),
    started_at: result.started_at,
    finished_at: result.finished_at,
    command: result.command,
    verification_command: result.verification_command,
    metric: result.metric,
    metrics: result.metrics,
    duration_ms: result.duration_ms,
    exit_code: result.exit_code,
    timed_out: result.timed_out,
    checks_pass: result.checks ? result.checks.passed : null,
    checks_timed_out: result.checks ? result.checks.timed_out : false,
    stream_output_path: result.stream_output_path,
    raw_output_path: result.raw_output_path,
    final_output_path: result.final_output_path,
    checks_output_path: result.checks_output_path,
    result_path: result.result_path,
    parent_commit: result.parent_commit,
    candidate_commit: candidateCommit,
    commit,
    confidence,
    files_touched: filesTouched,
    asi
  };
  appendJsonLine(paths.jsonl, record);

  process.stdout.write(
    `Logged ${runId} as ${status}. Primary metric: ${result.metric ?? "missing"}${candidateCommit ? `, commit ${candidateCommit.slice(0, 7)}` : ""}\n`
  );
}

async function exportSession(flags) {
  const workDir = resolveWorkDir(flags);
  const { state } = buildDerivedState(workDir);
  if (!state) {
    throw new Error(`No autoresearch session found in ${workDir}.`);
  }
  const { url } = await startDashboardServer(workDir, {
    host: flags.host,
    port: flags.port,
    open: Boolean(flags.open)
  });
  process.stdout.write(`Dashboard available at ${url}\n`);
  return new Promise(() => {});
}

function clearSession(flags) {
  const workDir = resolveWorkDir(flags);
  const paths = sessionPaths(workDir);
  for (const filePath of [paths.jsonl, paths.markdown, paths.benchmark, paths.checks, paths.ideas]) {
    if (fileExists(filePath)) {
      fs.rmSync(filePath, { force: true });
    }
  }
  if (fileExists(paths.logsDir)) {
    fs.rmSync(paths.logsDir, { recursive: true, force: true });
  }
  process.stdout.write(`Cleared autoresearch session in ${workDir}\n`);
}

function finalizeSession(flags) {
  const workDir = resolveWorkDir(flags);
  const action = flags._[1] || "propose";
  if (action === "propose") {
    const proposal = buildFinalizeProposal(workDir, flags.trunk || "main");
    if (flags["write-groups"]) {
      writeFinalizeProposal(workDir, path.resolve(flags["write-groups"]), flags.trunk || "main");
    }
    process.stdout.write(`${JSON.stringify(proposal, null, 2)}\n`);
    return;
  }
  if (action === "apply") {
    const groupsFile = requireValue(flags, "groups", "path to a groups.json file");
    const output = applyFinalizeProposal(workDir, path.resolve(groupsFile));
    process.stdout.write(`${output}\n`);
    return;
  }
  throw new Error(`Unknown finalize action: ${action}`);
}

function printHelp() {
  process.stdout.write(
    [
      "Usage: autoresearch <command> [options]",
      "",
      "Commands:",
      "  init --name NAME --metric METRIC [--direction lower|higher]",
      "  run [--command CMD] [--timeout-seconds N] [--checks-timeout-seconds N]",
      "  log --status keep|discard|crash|checks_failed --description TEXT [--run-id EXP-001]",
      "  status [--json]",
      "  export [--host HOST] [--port PORT] [--open]",
      "  clear",
      "  finalize propose [--write-groups FILE]",
      "  finalize apply --groups FILE"
    ].join("\n") + "\n"
  );
}

function printCommandHelp(command) {
  const helpText = {
    init: "Usage: autoresearch init --name NAME --metric METRIC [--direction lower|higher] [--command CMD] [--verify-command CMD]",
    run: "Usage: autoresearch run [--workdir DIR] [--command CMD] [--timeout-seconds N] [--checks-timeout-seconds N]",
    log: "Usage: autoresearch log --status keep|discard|crash|checks_failed --description TEXT [--run-id EXP-001] [--asi-json JSON]",
    status: "Usage: autoresearch status [--workdir DIR] [--json]",
    export: "Usage: autoresearch export [--workdir DIR] [--host HOST] [--port PORT] [--open]",
    clear: "Usage: autoresearch clear [--workdir DIR]",
    finalize: "Usage: autoresearch finalize propose [--write-groups FILE] | autoresearch finalize apply --groups FILE"
  };

  if (!helpText[command]) {
    printHelp();
    return;
  }

  process.stdout.write(`${helpText[command]}\n`);
}

async function runCli(argv) {
  const flags = parseArgs(argv);
  const command = flags._[0];

  if (!command || command === "help" || command === "--help") {
    printHelp();
    return;
  }

  if (flags.help) {
    printCommandHelp(command);
    return;
  }

  switch (command) {
    case "init":
      initSession(flags);
      return;
    case "run": {
      const payload = runExperiment(resolveWorkDir(flags), flags);
      process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
      return;
    }
    case "log":
      logExperiment(flags);
      return;
    case "status":
      statusSession(flags);
      return;
    case "export":
      await exportSession(flags);
      return;
    case "clear":
      clearSession(flags);
      return;
    case "finalize":
      finalizeSession(flags);
      return;
    default:
      throw new Error(`Unknown command: ${command}`);
  }
}

module.exports = {
  runCli
};
