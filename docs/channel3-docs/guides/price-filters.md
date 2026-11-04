> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Price Filters

> Filter search results by price range to surface products within a budget.

The `price` filter on `POST /v1/search` accepts a `min_price` and/or `max_price` in the currency of the request (default: USD). Either bound is optional — set only one to create an open-ended range.

<Note>
  A product passes the price filter if **any** of its offers falls within the range — not every offer has to match. Search results still return all offers for each product, so you may see prices above `max_price` or below `min_price` alongside an offer that qualified. To show only in-range prices in your UI, filter `product.offers` client-side.
</Note>

## Basic price range

<CodeGroup>
  ```typescript TypeScript theme={null}
  import Channel3 from "@channel3/sdk";

  const client = new Channel3();

  const results = await client.products.search({
    query: "running shoes",
    filters: {
      price: { min_price: 50, max_price: 150 },
    },
  });
  ```

  ```python Python theme={null}
  from channel3_sdk import Channel3

  client = Channel3()

  results = client.products.search(
      query="running shoes",
      filters={
          "price": {"min_price": 50, "max_price": 150},
      },
  )
  ```

  ```bash cURL theme={null}
  curl -X POST https://api.trychannel3.com/v1/search \
    -H "x-api-key: $CHANNEL3_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "query": "running shoes",
      "filters": { "price": { "min_price": 50, "max_price": 150 } }
    }'
  ```
</CodeGroup>

## Under a price ceiling

Set only `max_price` to find products below a given price.

<CodeGroup>
  ```typescript TypeScript theme={null}
  const results = await client.products.search({
    query: "office chair",
    filters: {
      price: { max_price: 200 },
    },
  });
  ```

  ```python Python theme={null}
  results = client.products.search(
      query="office chair",
      filters={"price": {"max_price": 200}},
  )
  ```
</CodeGroup>

## Currency

Pass a `currency` parameter alongside the price filter to search in a non-USD currency. Prices in the response will be returned in the same currency.

<CodeGroup>
  ```typescript TypeScript theme={null}
  const results = await client.products.search({
    query: "leather sofa",
    currency: "GBP",
    filters: {
      price: { max_price: 800 },
    },
  });
  ```

  ```python Python theme={null}
  results = client.products.search(
      query="leather sofa",
      currency="GBP",
      filters={"price": {"max_price": 800}},
  )
  ```
</CodeGroup>

## Combining with other filters

Price filters compose freely with all other filters.

```typescript TypeScript theme={null}
const results = await client.products.search({
  query: "sneakers",
  filters: {
    price:        { min_price: 80, max_price: 200 },
    brand_ids:    ["brand_nike"],
    availability: ["InStock"],
  },
});
```

<Cards>
  <Card title="Search" icon="magnifying-glass" href="/guides/search" arrow="true">
    Full overview of the search endpoint and all available filters.
  </Card>

  <Card title="Brand Search" icon="tag" href="/guides/brand-search" arrow="true">
    Resolve brand IDs to use with the brand\_ids filter.
  </Card>
</Cards>
