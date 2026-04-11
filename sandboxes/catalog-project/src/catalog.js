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
  const scoreByProductId = Object.create(null);

  for (const event of events) {
    if (event.type === "view") {
      scoreByProductId[event.productId] = (scoreByProductId[event.productId] || 0) + event.weight;
    } else if (event.type === "purchase") {
      scoreByProductId[event.productId] = (scoreByProductId[event.productId] || 0) + event.weight * 2;
    }
  }

  const rows = products.map((product) => ({
    productId: product.id,
    score: scoreByProductId[product.id] || 0,
    category: product.category
  }));

  rows.sort((left, right) => right.score - left.score);
  return rows;
}

function buildCategoryRevenue(products, orders) {
  const revenueByCategory = Object.create(null);
  const productCountByCategory = Object.create(null);
  const categoryOrder = [];

  for (const product of products) {
    if (productCountByCategory[product.category] === undefined) {
      productCountByCategory[product.category] = 0;
      revenueByCategory[product.category] = 0;
      categoryOrder.push(product.category);
    }
    productCountByCategory[product.category] += 1;
  }

  for (const order of orders) {
    for (const lineItem of order.lineItems) {
      revenueByCategory[lineItem.category] += lineItem.total;
    }
  }

  const merged = categoryOrder.map((category) => ({
    category,
    revenue: revenueByCategory[category],
    products: productCountByCategory[category]
  }));

  merged.sort((left, right) => right.revenue - left.revenue);
  return merged;
}

function buildBundleCounts(orders) {
  const bundleCountByProductId = Object.create(null);

  for (const order of orders) {
    const lineItemCountByProductId = Object.create(null);

    for (const lineItem of order.lineItems) {
      lineItemCountByProductId[lineItem.productId] =
        (lineItemCountByProductId[lineItem.productId] || 0) + 1;
    }

    const lineItemCount = order.lineItems.length;
    for (const productId of Object.keys(lineItemCountByProductId)) {
      bundleCountByProductId[productId] =
        (bundleCountByProductId[productId] || 0) +
        (lineItemCount - lineItemCountByProductId[productId]);
    }
  }

  return bundleCountByProductId;
}

function rankRecommendations(products, query, events, orders) {
  const searchMatches = searchCatalog(products, query);
  const trending = buildTrendingList(products, events);
  const categoryRevenue = buildCategoryRevenue(products, orders);
  const bundleCounts = buildBundleCounts(orders);
  const trendingByProductId = Object.create(null);
  const revenueByCategory = Object.create(null);

  for (const entry of trending) {
    trendingByProductId[entry.productId] = entry;
  }

  for (const entry of categoryRevenue) {
    revenueByCategory[entry.category] = entry;
  }

  return searchMatches
    .map((product) => {
      const trendingRow = trendingByProductId[product.id];
      const revenueRow = revenueByCategory[product.category];
      const bundleCount = bundleCounts[product.id] || 0;

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
