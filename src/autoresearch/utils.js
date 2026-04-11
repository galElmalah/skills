const fs = require("fs");
const path = require("path");

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function fileExists(filePath) {
  try {
    fs.accessSync(filePath);
    return true;
  } catch {
    return false;
  }
}

function readTextIfExists(filePath) {
  return fileExists(filePath) ? fs.readFileSync(filePath, "utf8") : null;
}

function readJsonLines(filePath) {
  const text = readTextIfExists(filePath);
  if (!text) return [];
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      try {
        return JSON.parse(line);
      } catch (error) {
        throw new Error(`Failed to parse ${path.basename(filePath)} line ${index + 1}: ${error.message}`);
      }
    });
}

function appendJsonLine(filePath, payload) {
  ensureDir(path.dirname(filePath));
  fs.appendFileSync(filePath, `${JSON.stringify(payload)}\n`);
}

function writeJson(filePath, payload) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, `${JSON.stringify(payload, null, 2)}\n`);
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function nowIso() {
  return new Date().toISOString();
}

function posixRelative(fromPath, toPath) {
  return path.relative(fromPath, toPath).split(path.sep).join("/");
}

function slugify(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48) || "session";
}

function tailText(value, maxChars) {
  const text = String(value || "");
  if (text.length <= maxChars) return text;
  return text.slice(text.length - maxChars);
}

function deletePath(targetPath) {
  fs.rmSync(targetPath, { recursive: true, force: true });
}

function formatMetricValue(value) {
  if (!Number.isFinite(value)) return "—";
  if (Math.abs(value) < 10) return value.toFixed(3);
  if (Math.abs(value) < 1000) return value.toFixed(2);
  return value.toFixed(1);
}

module.exports = {
  appendJsonLine,
  deletePath,
  ensureDir,
  fileExists,
  formatMetricValue,
  nowIso,
  posixRelative,
  readJson,
  readJsonLines,
  readTextIfExists,
  slugify,
  tailText,
  writeJson
};
