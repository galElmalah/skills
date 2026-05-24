const test = require("node:test");
const assert = require("node:assert/strict");
const {
  buildCustomerSummary,
  buildRegionBreakdown
} = require("../src/reporting");
const {
  buildSlowTestContext,
  removeWorkspace,
  waitForSystemToSettle
} = require("./helpers/slow-fixture");

let current;

test.beforeEach(async () => {
  current = await buildSlowTestContext(11);
});

test.afterEach(async () => {
  await removeWorkspace(current.workspace);
});

test("buildCustomerSummary sorts customers by total descending", async () => {
  await waitForSystemToSettle();
  const rows = buildCustomerSummary(current.fixtures);
  assert.equal(rows.length, current.fixtures.customers.length);
  assert.ok(rows[0].total >= rows[1].total);
});

test("buildCustomerSummary counts failed invoices", async () => {
  await waitForSystemToSettle();
  const rows = buildCustomerSummary(current.fixtures);
  const failedCount = rows.reduce((sum, row) => sum + row.failedInvoices, 0);
  assert.ok(failedCount > 0);
});

test("buildRegionBreakdown counts customers and invoices", async () => {
  await waitForSystemToSettle();
  const rows = buildRegionBreakdown(current.fixtures);
  assert.equal(rows.length, 3);
  assert.equal(rows.reduce((sum, row) => sum + row.customers, 0), current.fixtures.customers.length);
  assert.equal(rows.reduce((sum, row) => sum + row.invoices, 0), current.fixtures.invoices.length);
});
