const test = require("node:test");
const assert = require("node:assert/strict");
const { buildAlertDigest } = require("../src/reporting");
const {
  buildSlowTestContext,
  removeWorkspace,
  waitForSystemToSettle
} = require("./helpers/slow-fixture");

let current;

test.beforeEach(async () => {
  current = await buildSlowTestContext(22);
});

test.afterEach(async () => {
  await removeWorkspace(current.workspace);
});

test("buildAlertDigest returns total count", async () => {
  await waitForSystemToSettle();
  const digest = buildAlertDigest(current.fixtures);
  assert.equal(digest.total, current.fixtures.alerts.length);
});

test("buildAlertDigest groups alerts by severity", async () => {
  await waitForSystemToSettle();
  const digest = buildAlertDigest(current.fixtures);
  assert.equal(digest.bySeverity.low + digest.bySeverity.medium + digest.bySeverity.high, digest.total);
});
