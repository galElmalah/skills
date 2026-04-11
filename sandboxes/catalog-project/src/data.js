function createProducts(count) {
  const categories = ["databases", "payments", "monitoring", "storage", "security", "support"];
  const products = [];

  for (let index = 0; index < count; index += 1) {
    const category = categories[index % categories.length];
    products.push({
      id: `product-${index}`,
      sku: `SKU-${String(index).padStart(5, "0")}`,
      name: `${category} toolkit ${index % 37}`,
      category,
      price: 25 + ((index * 13) % 170),
      tags: [
        category,
        index % 2 === 0 ? "cloud" : "on-prem",
        index % 3 === 0 ? "enterprise" : "starter",
        index % 5 === 0 ? "analytics" : "core"
      ],
      metadata: {
        score: (index * 17) % 100,
        region: ["us", "eu", "apac"][index % 3],
        owner: `team-${index % 12}`,
        keywords: [
          category,
          `bundle-${index % 11}`,
          `series-${index % 19}`,
          index % 4 === 0 ? "search" : "routing"
        ]
      }
    });
  }

  return products;
}

function createEvents(count, products) {
  const events = [];

  for (let index = 0; index < count; index += 1) {
    const product = products[index % products.length];
    events.push({
      eventId: `event-${index}`,
      productId: product.id,
      type: ["view", "view", "cart", "purchase"][index % 4],
      userId: `user-${index % 1500}`,
      weight: 1 + (index % 6),
      region: product.metadata.region
    });
  }

  return events;
}

function createOrders(count, products) {
  const orders = [];

  for (let index = 0; index < count; index += 1) {
    const lineItems = [];
    const size = 2 + (index % 4);

    for (let offset = 0; offset < size; offset += 1) {
      const product = products[(index * 7 + offset * 13) % products.length];
      lineItems.push({
        productId: product.id,
        category: product.category,
        total: product.price * (1 + ((index + offset) % 3))
      });
    }

    orders.push({
      orderId: `order-${index}`,
      customerId: `customer-${index % 900}`,
      lineItems
    });
  }

  return orders;
}

module.exports = {
  createProducts,
  createEvents,
  createOrders
};
