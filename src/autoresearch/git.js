const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

function runGit(args, options = {}) {
  const result = spawnSync("git", args, {
    cwd: options.cwd,
    encoding: "utf8",
    maxBuffer: 20 * 1024 * 1024
  });

  const stdout = result.stdout || "";
  const stderr = result.stderr || "";
  if (options.allowFailure) {
    return {
      code: result.status === null ? 1 : result.status,
      stdout,
      stderr
    };
  }
  if (result.status !== 0) {
    throw new Error((stderr || stdout || `git ${args.join(" ")} failed`).trim());
  }
  return {
    code: 0,
    stdout,
    stderr
  };
}

function getGitRoot(workDir) {
  return runGit(["rev-parse", "--show-toplevel"], { cwd: workDir }).stdout.trim();
}

function getHeadCommit(workDir) {
  return runGit(["rev-parse", "HEAD"], { cwd: workDir }).stdout.trim();
}

function getCurrentBranch(workDir) {
  return runGit(["branch", "--show-current"], { cwd: workDir }).stdout.trim();
}

function listChangedFilesBetween(gitRoot, fromRef, toRef, relativeWorkDir) {
  return runGit(["diff", "--name-only", fromRef, toRef, "--", relativeWorkDir], { cwd: gitRoot })
    .stdout
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function listUntrackedPaths(gitRoot, relativeWorkDir) {
  const output = runGit(
    ["status", "--porcelain", "--untracked-files=all", "--", relativeWorkDir],
    { cwd: gitRoot, allowFailure: true }
  ).stdout;
  return output
    .split(/\r?\n/)
    .map((line) => line.trimEnd())
    .filter(Boolean)
    .filter((line) => line.startsWith("?? "))
    .map((line) => line.slice(3).trim())
    .filter(Boolean);
}

function stagePath(gitRoot, relativeWorkDir) {
  runGit(["add", "-A", "--", relativeWorkDir], { cwd: gitRoot });
}

function hasStagedChanges(gitRoot, relativeWorkDir) {
  const result = runGit(["diff", "--cached", "--quiet", "--", relativeWorkDir], {
    cwd: gitRoot,
    allowFailure: true
  });
  return result.code !== 0;
}

function commitStaged(gitRoot, message) {
  return runGit(["commit", "-m", message], { cwd: gitRoot }).stdout.trim();
}

function restoreWorktree(gitRoot, relativeWorkDir) {
  runGit(["restore", "--staged", "--worktree", "--source=HEAD", "--", relativeWorkDir], {
    cwd: gitRoot,
    allowFailure: true
  });
}

function pathIsProtected(candidate, protectedPaths) {
  const normalized = candidate.split(path.sep).join("/");
  return protectedPaths.some((protectedPath) => {
    const target = protectedPath.split(path.sep).join("/");
    return normalized === target || normalized.startsWith(`${target}/`);
  });
}

function cleanupUntracked(gitRoot, untrackedPaths, protectedPaths) {
  for (const relativePath of untrackedPaths) {
    if (pathIsProtected(relativePath, protectedPaths)) continue;
    fs.rmSync(path.join(gitRoot, relativePath), { recursive: true, force: true });
  }
}

module.exports = {
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
};
