const crypto = require("node:crypto");
const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function buildFixtures(seed = 1) {
  const customers = [];
  const invoices = [];
  const alerts = [];
  const customerById = new Map();
  const regions = ["us", "eu", "apac"];

  for (let index = 0; index < 120; index += 1) {
    const customer = {
      id: `customer-${seed}-${index}`,
      region: regions[index % regions.length],
      tier: index % 3 === 0 ? "enterprise" : "starter"
    };
    customers.push(customer);
    customerById.set(customer.id, customer);
  }

  for (let index = 0; index < 900; index += 1) {
    const customerId = customers[index % customers.length].id;
    invoices.push({
      id: `invoice-${seed}-${index}`,
      customerId,
      total: 50 + ((seed * 17 + index * 13) % 800),
      status: index % 9 === 0 ? "failed" : "paid"
    });
  }

  for (let index = 0; index < 320; index += 1) {
    alerts.push({
      id: `alert-${seed}-${index}`,
      severity: ["low", "medium", "high"][index % 3]
    });
  }

  return {
    customers,
    invoices,
    alerts,
    customerById
  };
}

function burnCpu(seed) {
  for (let index = 0; index < 36; index += 1) {
    crypto.pbkdf2Sync(`fixture-${seed}-${index}`, "tests-project", 4200, 32, "sha256");
  }
}

async function createWorkspace(fixtures, seed) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), `tests-project-${seed}-`));
  const payload = JSON.stringify(
    {
      customers: fixtures.customers,
      invoices: fixtures.invoices,
      alerts: fixtures.alerts
    },
    null,
    2
  );

  await fs.writeFile(path.join(directory, "fixtures.json"), payload);
  await fs.writeFile(path.join(directory, "alerts.json"), JSON.stringify(fixtures.alerts));
  await sleep(95);
  return directory;
}

async function removeWorkspace(directory) {
  await fs.rm(directory, { recursive: true, force: true });
}

async function buildSlowTestContext(seed = 1) {
  burnCpu(seed);
  const fixtures = buildFixtures(seed);
  const workspace = await createWorkspace(fixtures, seed);
  await sleep(120);
  return { fixtures, workspace };
}

async function waitForSystemToSettle() {
  await sleep(90);
}

module.exports = {
  buildSlowTestContext,
  removeWorkspace,
  waitForSystemToSettle
};
