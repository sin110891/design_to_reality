> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Brand Search

> Find brands in the catalog, then filter future searches by brand.

The `brand_ids` filter on `POST /v1/search` limits results to products from specific brands. Brand IDs are stable identifiers you resolve once via the brands API and then reuse.

<Note>
  **What's the difference between brands and websites?**

  A **brand** makes or labels a product (Nike, Dyson). A **website** is the online store selling it (`nike.com`, `bestbuy.com`). Use `brand_ids` to filter by brand and `website_ids` to filter by retailer — they're independent. One brand's products often appear on many websites. See the [Brand](/api-reference/brand-model) and [Website](/api-reference/website-model) models.
</Note>

## Step 1 — Resolve brand IDs

Use `GET /v1/brands/search` to find a brand by name and retrieve its ID.

<CodeGroup>
  ```typescript TypeScript theme={null}
  import Channel3 from "@channel3/sdk";

  const client = new Channel3();

  const brands = await client.brands.search({ query: "Nike" });
  const nikeId = brands.brands[0].id;
  console.log(nikeId); // e.g. "brand_nike_abc123"
  ```

  ```python Python theme={null}
  from channel3_sdk import Channel3

  client = Channel3()

  brands = client.brands.search(query="Nike")
  nike_id = brands.brands[0].id
  print(nike_id)  # e.g. "brand_nike_abc123"
  ```

  ```bash cURL theme={null}
  curl "https://api.trychannel3.com/v1/brands/search?query=Nike" \
    -H "x-api-key: $CHANNEL3_API_KEY"
  ```
</CodeGroup>

## Step 2 — Filter search results by brand

Pass the resolved ID (or IDs) to the `brand_ids` filter.

<CodeGroup>
  ```typescript TypeScript theme={null}
  const results = await client.products.search({
    query: "running shoes",
    filters: {
      brand_ids: [nikeId],
    },
  });
  ```

  ```python Python theme={null}
  results = client.products.search(
      query="running shoes",
      filters={"brand_ids": [nike_id]},
  )
  ```

  ```bash cURL theme={null}
  curl -X POST https://api.trychannel3.com/v1/search \
    -H "x-api-key: $CHANNEL3_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "query": "running shoes",
      "filters": { "brand_ids": ["brand_nike_abc123"] }
    }'
  ```
</CodeGroup>

## Filtering to multiple brands

Pass multiple IDs to include products from any of the listed brands (OR logic).

```typescript TypeScript theme={null}
const [nikeResult, adidasResult] = await Promise.all([
  client.brands.search({ query: "Nike" }),
  client.brands.search({ query: "Adidas" }),
]);

const results = await client.products.search({
  query: "running shoes",
  filters: {
    brand_ids: [nikeResult.brands[0].id, adidasResult.brands[0].id],
  },
});
```

## Browsing all brands

Use `GET /v1/brands` to list brands or `GET /v1/brands/{brand_id}` to retrieve a specific brand by its ID.

<CodeGroup>
  ```typescript TypeScript theme={null}
  // List brands (paginated)
  const allBrands = await client.brands.list({ limit: 50 });

  // Retrieve a specific brand
  const brand = await client.brands.retrieve("brand_nike_abc123");
  console.log(brand.name, brand.logo_url);
  ```

  ```python Python theme={null}
  all_brands = client.brands.list(limit=50)

  brand = client.brands.retrieve("brand_nike_abc123")
  print(brand.name, brand.logo_url)
  ```
</CodeGroup>

<Cards>
  <Card title="Brands API" icon="tag" href="/api-reference/v1/list-brands" arrow="true">
    Full API reference for the brands endpoints.
  </Card>

  <Card title="Search" icon="magnifying-glass" href="/guides/search" arrow="true">
    Full overview of the search endpoint and all available filters.
  </Card>
</Cards>
