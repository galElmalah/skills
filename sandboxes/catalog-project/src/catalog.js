function cloneMetadata(product) {
  return JSON.parse(JSON.stringify(product.metadata));
}

function scoreTokenAgainstProduct(token, product) {
  const metadata = cloneMetadata(product);
  const haystack = [
    product.name,
    product.category,
    product.tags.join(" "),
    metadata.keywords.join(" "),
    metadata.owner
  ]
    .join(" ")
    .toLowerCase();

  if (!haystack.includes(token)) {
    return 0;
  }

  let score = 1;
  for (const keyword of metadata.keywords) {
    if (keyword.includes(token)) {
      score += 4;
    }
  }

  if (product.name.toLowerCase().includes(token)) {
    score += 3;
  }

  return score + metadata.score / 100;
}

function searchCatalog(products, query) {
  const tokens = query.toLowerCase().split(/\s+/).filter(Boolean);
  let workingSet = products.slice();

  for (const token of tokens) {
    const matches = [];

    for (const product of workingSet) {
      const score = scoreTokenAgainstProduct(token, product);
      if (score > 0) {
        matches.push({
          product,
          score,
          snapshot: cloneMetadata(product)
        });
      }
    }

    matches.sort((left, right) => {
      if (right.score !== left.score) {
        return right.score - left.score;
      }
      return left.product.name.localeCompare(right.product.name);
    });

    workingSet = matches.map((entry) => ({
      ...entry.product,
      metadata: entry.snapshot
    }));
  }

  return workingSet.slice(0, 40);
}

function buildTrendingList(products, events) {
  const rows = [];

  for (const product of products) {
    let views = 0;
    let purchases = 0;

    for (const event of events) {
      if (event.productId !== product.id) {
        continue;
      }

      if (event.type === "view") {
        views += event.weight;
      } else if (event.type === "purchase") {
        purchases += event.weight * 2;
      }
    }

    rows.push({
      productId: product.id,
      score: views + purchases,
      category: product.category
    });
  }

  rows.sort((left, right) => right.score - left.score);
  return rows;
}

function buildCategoryRevenue(products, orders) {
  const rows = [];

  for (const product of products) {
    let revenue = 0;

    for (const order of orders) {
      for (const lineItem of order.lineItems) {
        if (lineItem.productId === product.id) {
          revenue += lineItem.total;
        }
      }
    }

    rows.push({
      category: product.category,
      productId: product.id,
      revenue
    });
  }

  rows.sort((left, right) => right.revenue - left.revenue);

  const merged = [];
  for (const row of rows) {
    const existing = merged.find((entry) => entry.category === row.category);
    if (existing) {
      existing.revenue += row.revenue;
      existing.products += 1;
    } else {
      merged.push({
        category: row.category,
        revenue: row.revenue,
        products: 1
      });
    }
  }

  merged.sort((left, right) => right.revenue - left.revenue);
  return merged;
}

function rankRecommendations(products, query, events, orders) {
  const searchMatches = searchCatalog(products, query);
  const trending = buildTrendingList(products, events);
  const categoryRevenue = buildCategoryRevenue(products, orders);

  return searchMatches
    .map((product) => {
      const trendingRow = trending.find((entry) => entry.productId === product.id);
      const revenueRow = categoryRevenue.find((entry) => entry.category === product.category);

      let bundleCount = 0;
      for (const order of orders) {
        const containsCurrent = order.lineItems.some((lineItem) => lineItem.productId === product.id);
        if (!containsCurrent) {
          continue;
        }

        for (const lineItem of order.lineItems) {
          if (lineItem.productId !== product.id) {
            bundleCount += 1;
          }
        }
      }

      return {
        id: product.id,
        name: product.name,
        score:
          (trendingRow ? trendingRow.score : 0) +
          (revenueRow ? revenueRow.revenue / Math.max(revenueRow.products, 1) : 0) / 10 +
          bundleCount
      };
    })
    .sort((left, right) => right.score - left.score)
    .slice(0, 15);
}

module.exports = {
  searchCatalog,
  buildTrendingList,
  buildCategoryRevenue,
  rankRecommendations
};
