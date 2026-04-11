#!/usr/bin/env node
const http = require("http");
const fs = require("fs");
const path = require("path");
const { execFile } = require("child_process");
const { URL } = require("url");

const host = process.env.DASHBOARD_HOST || "127.0.0.1";
const port = Number(process.env.DASHBOARD_PORT || 8765);
const root = path.resolve(process.env.DASHBOARD_ROOT || ".");

const types = {
  ".html": "text/html; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".svg": "image/svg+xml"
};

function safePath(urlPath) {
  const raw = urlPath === "/" ? "/dashboard.html" : urlPath;
  const filePath = path.resolve(root, "." + raw);
  if (!filePath.startsWith(root)) return null;
  return filePath;
}

function sendJson(res, status, payload) {
  res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  res.end(JSON.stringify(payload));
}

function isSafeRef(value) {
  return typeof value === "string" && /^[A-Za-z0-9._/-]+$/.test(value);
}

function isSafeFile(value) {
  return typeof value === "string" && value.length > 0 && !path.isAbsolute(value) && !value.includes("\0");
}

function git(args, callback) {
  execFile("git", args, { cwd: root, maxBuffer: 10 * 1024 * 1024 }, callback);
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

  const filePath = safePath(url.pathname);

  if (!filePath) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }

  fs.stat(filePath, (err, stat) => {
    if (err || !stat.isFile()) {
      res.writeHead(404);
      res.end("Not found");
      return;
    }

    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { "Content-Type": types[ext] || "application/octet-stream" });
    fs.createReadStream(filePath).pipe(res);
  });
});

server.listen(port, host, () => {
  console.log(`[dashboard] serving ${root}`);
  console.log(`[dashboard] open http://${host}:${port}/dashboard.html`);
});
