const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const {
  buildCustomerSummary,
  buildRegionBreakdown,
  buildAlertDigest
} = require("../src/reporting");
const {
  buildSlowTestContext,
  removeWorkspace,
  waitForSystemToSettle
} = require("./helpers/slow-fixture");

let current;

test.beforeEach(async () => {
  current = await buildSlowTestContext(33);
});

test.afterEach(async () => {
  await removeWorkspace(current.workspace);
});

test("end-to-end report writes a combined JSON artifact", async () => {
  await waitForSystemToSettle();
  const payload = {
    summary: buildCustomerSummary(current.fixtures).slice(0, 5),
    regions: buildRegionBreakdown(current.fixtures),
    alerts: buildAlertDigest(current.fixtures)
  };

  const outputPath = path.join(current.workspace, "report.json");
  await fs.writeFile(outputPath, JSON.stringify(payload, null, 2));
  const written = JSON.parse(await fs.readFile(outputPath, "utf8"));

  assert.equal(written.summary.length, 5);
  assert.equal(written.regions.length, 3);
  assert.equal(written.alerts.total, current.fixtures.alerts.length);
});
