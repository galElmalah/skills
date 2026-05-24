function buildCustomerSummary(fixtures) {
  const buckets = new Map();

  for (const invoice of fixtures.invoices) {
    const current = buckets.get(invoice.customerId) || {
      customerId: invoice.customerId,
      invoices: 0,
      total: 0,
      failedInvoices: 0
    };

    current.invoices += 1;
    current.total += invoice.total;
    if (invoice.status === "failed") {
      current.failedInvoices += 1;
    }

    buckets.set(invoice.customerId, current);
  }

  return Array.from(buckets.values()).sort((left, right) => right.total - left.total);
}

function buildRegionBreakdown(fixtures) {
  const totals = new Map();

  for (const customer of fixtures.customers) {
    const region = customer.region;
    const current = totals.get(region) || { region, customers: 0, invoices: 0 };
    current.customers += 1;
    totals.set(region, current);
  }

  for (const invoice of fixtures.invoices) {
    const region = fixtures.customerById.get(invoice.customerId).region;
    const current = totals.get(region);
    current.invoices += 1;
  }

  return Array.from(totals.values()).sort((left, right) => left.region.localeCompare(right.region));
}

function buildAlertDigest(fixtures) {
  return fixtures.alerts.reduce(
    (digest, alert) => {
      digest.total += 1;
      digest.bySeverity[alert.severity] = (digest.bySeverity[alert.severity] || 0) + 1;
      return digest;
    },
    { total: 0, bySeverity: {} }
  );
}

module.exports = {
  buildCustomerSummary,
  buildRegionBreakdown,
  buildAlertDigest
};
