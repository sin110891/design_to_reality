> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Caching Best Practices

> How to cache Channel3 data effectively without serving stale results.

<Note>
  The recommended path for most integrations is **real-time product discovery** via the [`/search`](/v1/search) endpoint. The guidance below is for use cases where product IDs are stored and revisited later, such as:

  * **Persisted carts or "saved for later" collections** — users bookmark products and return to them hours or days later
  * **Hand-curated shopping experiences** — developers select specific products for display, typically originally discovered via [`/search`](/v1/search) or [`/lookup`](/v1/lookup)
</Note>

## Cache IDs, not data

Product IDs and category slugs are stable identifiers — cache them freely and for as long as you like. Everything else on a product object (prices, availability, images, descriptions, offers, variants) should be treated as **unstable**. These fields can change at any time as merchants update their catalogs. Retrieve fresh product snapshots at load time with the **free** [`GET /v1/products/{product_id}`](/v1/products/\{product_id}).

**Do:**

* Store `product.id` from search results and reuse it later

**Don't:**

* Cache prices, availability, or offer URLs and serve them to users without refreshing
* Assume image URLs or product descriptions are permanent
* Cache offer URLs — these are short-lived and must be fetched fresh before presenting to users

## Refresh at load time

When you need to display a product to a user, fetch the latest data with [`GET /v1/products/{product_id}`](/v1/products/\{product_id}) rather than relying on a cached snapshot. This ensures prices, stock status, and buy links are current.

<CodeGroup>
  ```typescript TypeScript theme={null}
  // At search time — cache the IDs
  const results = await client.products.search({ query: "running shoes" });
  const productIds = results.products.map((p) => p.id);
  // store productIds in your database or session

  // At display time — fetch fresh data
  const product = await client.products.retrieve(productId);
  ```

  ```python Python theme={null}
  # At search time — cache the IDs
  results = client.products.search(query="running shoes")
  product_ids = [p.id for p in results.products]
  # store product_ids in your database or session

  # At display time — fetch fresh data
  product = client.products.retrieve(product_id)
  ```
</CodeGroup>

## Short-lived caches are fine

Caches with a short TTL (a few minutes to a few hours) on full product objects for presentational data (images, title) is reasonable for use cases that require it. Just avoid caching product data for many hours or days — pricing and availability can shift quickly, and we often update our data model to include new features and info.

| Data                                         | Cache strategy                         |
| -------------------------------------------- | -------------------------------------- |
| Product IDs, category slugs                  | Cache indefinitely                     |
| Product details (title, description, images) | Short TTL or refresh on display        |
| Prices, availability, offers                 | Always refresh before showing to users |

<Cards>
  <Card title="Search" icon="magnifying-glass" href="/guides/search" arrow="true">
    Full overview of the search endpoint, filters, and pagination.
  </Card>

  <Card title="Localization" icon="globe" href="/guides/localization" arrow="true">
    Set country, language, and currency for market-specific results.
  </Card>
</Cards>
