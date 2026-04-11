const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const { getHeadCommit, getGitRoot, listChangedFilesBetween, runGit } = require("./git");
const { buildDerivedState } = require("./state");
const { formatMetricValue, slugify, writeJson } = require("./utils");

function isSessionArtifact(filePath) {
  const normalized = String(filePath || "").replaceAll("\\", "/");
  if (normalized.startsWith(".autoresearch-logs/") || normalized.startsWith(".eval-logs/")) {
    return true;
  }
  const base = path.basename(normalized);
  return base.startsWith("autoresearch.");
}

function keptExperiments(workDir) {
  const { state } = buildDerivedState(workDir);
  if (!state) throw new Error("No autoresearch session found.");
  return {
    state,
    kept: state.experiments.filter((experiment) => experiment.status === "KEPT" && experiment.candidate_commit)
  };
}

function buildFinalizeProposal(workDir, trunk = "main") {
  const gitRoot = getGitRoot(workDir);
  const { state, kept } = keptExperiments(workDir);
  if (!kept.length) {
    throw new Error("No kept experiments available to finalize.");
  }

  const base = runGit(["merge-base", "HEAD", trunk], { cwd: gitRoot }).stdout.trim();
  const finalTree = getHeadCommit(workDir);
  const groups = [];
  let previousCommit = base;
  let previousMetric = state.summary.baseline;

  for (const experiment of kept) {
    const files = listChangedFilesBetween(gitRoot, previousCommit, experiment.candidate_commit, path.relative(gitRoot, workDir) || ".")
      .filter((filePath) => !isSessionArtifact(filePath));
    const fileSet = new Set(files);
    const currentGroup = groups[groups.length - 1];
    const overlaps =
      currentGroup &&
      currentGroup.files.some((file) => fileSet.has(file));

    if (overlaps) {
      currentGroup.commits.push(experiment.commit || experiment.candidate_commit.slice(0, 7));
      currentGroup.files = Array.from(new Set([...currentGroup.files, ...files]));
      currentGroup.last_commit = experiment.candidate_commit;
      currentGroup.metric_end = experiment.result;
      currentGroup.title = currentGroup.title || experiment.title;
      currentGroup.body = `${currentGroup.body}\n${experiment.title}`;
    } else {
      groups.push({
        title: experiment.title || experiment.id,
        body: experiment.title || experiment.id,
        commits: [experiment.commit || experiment.candidate_commit.slice(0, 7)],
        files,
        metric_start: previousMetric,
        metric_end: experiment.result,
        last_commit: experiment.candidate_commit,
        slug: slugify(experiment.title || experiment.id)
      });
    }

    previousCommit = experiment.candidate_commit;
    previousMetric = experiment.result;
  }

  return {
    base,
    trunk,
    final_tree: finalTree,
    goal: `${slugify(state.objective.goal || state.objective.metric || "autoresearch")}-review`,
    groups: groups.map((group, index) => ({
      title: group.title,
      body: `${group.body}\n\nExperiments: ${group.commits.join(", ")}\nMetric: ${formatMetricValue(group.metric_start)} -> ${formatMetricValue(group.metric_end)}`,
      last_commit: group.last_commit,
      slug: group.slug || `group-${index + 1}`,
      commits: group.commits,
      files: group.files,
      metric_start: group.metric_start,
      metric_end: group.metric_end
    }))
  };
}

function writeFinalizeProposal(workDir, targetFile, trunk = "main") {
  const proposal = buildFinalizeProposal(workDir, trunk);
  writeJson(targetFile, proposal);
  return proposal;
}

function applyFinalizeProposal(workDir, groupsFile) {
  const scriptPath = path.resolve(__dirname, "../../skills/autoresearch-finalize/assets/finalize.sh");
  const result = spawnSync("bash", [scriptPath, groupsFile], {
    cwd: workDir,
    encoding: "utf8",
    maxBuffer: 20 * 1024 * 1024
  });
  if (result.status !== 0) {
    throw new Error((result.stderr || result.stdout || "Finalize failed").trim());
  }
  return result.stdout.trim();
}

module.exports = {
  applyFinalizeProposal,
  buildFinalizeProposal,
  writeFinalizeProposal
};
