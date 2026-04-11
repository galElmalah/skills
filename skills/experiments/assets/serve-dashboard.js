#!/usr/bin/env node
const http = require("http");
const fs = require("fs");
const path = require("path");
const { execFile, execFileSync } = require("child_process");
const { URL } = require("url");

const host = process.env.DASHBOARD_HOST || "127.0.0.1";
const port = Number(process.env.DASHBOARD_PORT || 8765);
const root = path.resolve(process.env.DASHBOARD_ROOT || ".");
const gitRoot = discoverGitRoot(root);

const types = {
  ".html": "text/html; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".log": "text/plain; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".raw": "text/plain; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".svg": "image/svg+xml"
};

function discoverGitRoot(cwd) {
  try {
    return execFileSync("git", ["rev-parse", "--show-toplevel"], {
      cwd,
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"]
    }).trim();
  } catch {
    return null;
  }
}

function isWithinRoot(filePath, base) {
  return Boolean(base) && (filePath === base || filePath.startsWith(base + path.sep));
}

function safeStaticPath(urlPath) {
  const raw = urlPath === "/" ? "/dashboard.html" : urlPath;
  const filePath = path.resolve(root, "." + raw);
  if (!isWithinRoot(filePath, root)) return null;
  return filePath;
}

function safeArtifactPath(rawPath) {
  if (!isSafeFile(rawPath)) return null;

  const normalized = rawPath.replaceAll("\\", "/").replace(/^\/+/, "");
  const candidates = [];
  const pushCandidate = (base, relativePath) => {
    if (!base || !relativePath) return;
    const candidate = path.resolve(base, relativePath);
    if (!isWithinRoot(candidate, root) && !isWithinRoot(candidate, gitRoot)) return;
    candidates.push(candidate);
  };

  pushCandidate(root, normalized);
  pushCandidate(gitRoot, normalized);

  const rootName = path.basename(root);
  if (normalized.startsWith(`${rootName}/`)) {
    const stripped = normalized.slice(rootName.length + 1);
    pushCandidate(root, stripped);
    pushCandidate(gitRoot, stripped);
  }

  return candidates.find((candidate) => fs.existsSync(candidate)) || null;
}

function sendJson(res, status, payload) {
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store"
  });
  res.end(JSON.stringify(payload));
}

function sendFile(res, filePath) {
  fs.stat(filePath, (err, stat) => {
    if (err || !stat.isFile()) {
      res.writeHead(404);
      res.end("Not found");
      return;
    }

    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, {
      "Content-Type": types[ext] || "application/octet-stream",
      "Cache-Control": "no-store"
    });
    fs.createReadStream(filePath).pipe(res);
  });
}

function isSafeRef(value) {
  return typeof value === "string" && /^[A-Za-z0-9._/-]+$/.test(value);
}

function isSafeFile(value) {
  return typeof value === "string" && value.length > 0 && !path.isAbsolute(value) && !value.includes("\0");
}

function git(args, callback) {
  execFile("git", args, { cwd: gitRoot || root, maxBuffer: 10 * 1024 * 1024 }, callback);
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  if (url.pathname === "/api/diff-files") {
    const base = url.searchParams.get("base");
    const head = url.searchParams.get("head");
    if (!isSafeRef(base) || !isSafeRef(head)) {
      sendJson(res, 400, { error: "Invalid base/head commit reference" });
      return;
    }
    git(["diff", "--name-only", base, head], (err, stdout, stderr) => {
      if (err) {
        sendJson(res, 500, { error: stderr.trim() || err.message });
        return;
      }
      const files = stdout.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
      sendJson(res, 200, { files });
    });
    return;
  }

  if (url.pathname === "/api/diff") {
    const base = url.searchParams.get("base");
    const head = url.searchParams.get("head");
    const file = url.searchParams.get("file");
    if (!isSafeRef(base) || !isSafeRef(head) || !isSafeFile(file)) {
      sendJson(res, 400, { error: "Invalid diff request" });
      return;
    }
    git(["diff", "--unified=20", base, head, "--", file], (err, stdout, stderr) => {
      if (err) {
        sendJson(res, 500, { error: stderr.trim() || err.message });
        return;
      }
      sendJson(res, 200, { diff: stdout });
    });
    return;
  }

  if (url.pathname === "/api/artifact") {
    const artifactPath = url.searchParams.get("path");
    const filePath = safeArtifactPath(artifactPath);
    if (!filePath) {
      res.writeHead(404);
      res.end("Artifact not found");
      return;
    }
    sendFile(res, filePath);
    return;
  }

  const filePath = safeStaticPath(url.pathname);

  if (!filePath) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }

  sendFile(res, filePath);
});

server.listen(port, host, () => {
  console.log(`[dashboard] serving ${root}`);
  console.log(`[dashboard] open http://${host}:${port}/dashboard.html`);
});
