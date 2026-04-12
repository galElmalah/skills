const fs = require("fs");
const path = require("path");
const http = require("http");
const { spawn } = require("child_process");
const { URL } = require("url");

const { buildDerivedState } = require("./state");
const { getGitRoot, runGit } = require("./git");

function contentType(filePath) {
  switch (path.extname(filePath).toLowerCase()) {
    case ".html":
      return "text/html; charset=utf-8";
    case ".json":
      return "application/json; charset=utf-8";
    case ".log":
    case ".raw":
    case ".txt":
    case ".md":
      return "text/plain; charset=utf-8";
    default:
      return "application/octet-stream";
  }
}

function safeArtifactPath(workDir, gitRoot, rawPath) {
  if (!rawPath || typeof rawPath !== "string" || path.isAbsolute(rawPath) || rawPath.includes("\0")) {
    return null;
  }
  const normalized = rawPath.replaceAll("\\", "/");
  const candidates = [
    path.resolve(workDir, normalized),
    path.resolve(gitRoot, normalized)
  ];
  return candidates.find((candidate) => candidate.startsWith(workDir) || candidate.startsWith(gitRoot)) || null;
}

function sendJson(res, status, payload) {
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store"
  });
  res.end(JSON.stringify(payload));
}

function sendFile(res, filePath) {
  fs.stat(filePath, (error, stat) => {
    if (error || !stat.isFile()) {
      res.writeHead(404);
      res.end("Not found");
      return;
    }
    res.writeHead(200, {
      "Content-Type": contentType(filePath),
      "Cache-Control": "no-store"
    });
    fs.createReadStream(filePath).pipe(res);
  });
}

function openBrowser(url) {
  const command = process.platform === "darwin" ? "open" : process.platform === "win32" ? "cmd" : "xdg-open";
  const args = process.platform === "win32" ? ["/c", "start", "", url] : [url];
  spawn(command, args, { detached: true, stdio: "ignore" }).unref();
}

function dashboardAssetPath() {
  return path.resolve(__dirname, "../../skills/autoresearch-create/assets/dashboard.html");
}

function startDashboardServer(workDir, options = {}) {
  const host = options.host || "127.0.0.1";
  const port = Number(options.port || 8765);
  const gitRoot = getGitRoot(workDir);

  const server = http.createServer((req, res) => {
    const url = new URL(req.url, `http://${req.headers.host}`);

    if (url.pathname === "/" || url.pathname === "/dashboard.html") {
      sendFile(res, dashboardAssetPath());
      return;
    }

    if (url.pathname === "/api/state") {
      try {
        const { state } = buildDerivedState(workDir);
        if (!state) {
          sendJson(res, 404, { error: "No autoresearch.jsonl found" });
          return;
        }
        sendJson(res, 200, state);
      } catch (error) {
        sendJson(res, 500, { error: error.message });
      }
      return;
    }

    if (url.pathname === "/api/artifact") {
      const filePath = safeArtifactPath(workDir, gitRoot, url.searchParams.get("path"));
      if (!filePath) {
        res.writeHead(404);
        res.end("Artifact not found");
        return;
      }
      sendFile(res, filePath);
      return;
    }

    if (url.pathname === "/api/diff-files") {
      const base = url.searchParams.get("base");
      const head = url.searchParams.get("head");
      try {
        const files = runGit(["diff", "--name-only", base, head], { cwd: gitRoot }).stdout
          .split(/\r?\n/)
          .map((line) => line.trim())
          .filter(Boolean);
        sendJson(res, 200, { files });
      } catch (error) {
        sendJson(res, 500, { error: error.message });
      }
      return;
    }

    if (url.pathname === "/api/diff") {
      const base = url.searchParams.get("base");
      const head = url.searchParams.get("head");
      const file = url.searchParams.get("file");
      try {
        const diff = runGit(["diff", "--unified=20", base, head, "--", file], { cwd: gitRoot }).stdout;
        sendJson(res, 200, { diff });
      } catch (error) {
        sendJson(res, 500, { error: error.message });
      }
      return;
    }

    res.writeHead(404);
    res.end("Not found");
  });

  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, host, () => {
      const url = `http://${host}:${port}/dashboard.html`;
      if (options.open) {
        try {
          openBrowser(url);
        } catch {
          // Browser launch failure should not fail export.
        }
      }
      resolve({ server, url });
    });
  });
}

module.exports = {
  startDashboardServer
};
