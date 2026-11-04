> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Search

> Text search, filters, and pagination across the Channel3 product catalog.

The `POST /v1/search` endpoint is the core of Channel3. Pass a free-text query and get back a ranked list of products with prices, availability, images, and merchant offers.

## Basic search

<CodeGroup>
  ```typescript TypeScript theme={null}
  import Channel3 from "@channel3/sdk";

  const client = new Channel3(); // reads CHANNEL3_API_KEY from env

  const results = await client.products.search({
    query: "merino wool sweater",
  });

  console.log(results.products[0].title);
  console.log(results.products[0].offers[0].price);
  ```

  ```python Python theme={null}
  from channel3_sdk import Channel3

  client = Channel3()  # reads CHANNEL3_API_KEY from env

  results = client.products.search(query="merino wool sweater")

  print(results.products[0].title)
  print(results.products[0].offers[0].price)
  ```

  ```bash cURL theme={null}
  curl -X POST https://api.trychannel3.com/v1/search \
    -H "x-api-key: $CHANNEL3_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"query": "merino wool sweater"}'
  ```
</CodeGroup>

## Filters

Narrow results with `filters`. Every filter is optional — combine as many as you need.

<CodeGroup>
  ```typescript TypeScript theme={null}
  const results = await client.products.search({
    query: "running shoes",
    filters: {
      price:        { min_price: 50, max_price: 150 },
      availability: ["InStock", "LimitedAvailability"],
      gender:       "male",
      category:     "running-shoes",        // category slug
      brand_ids:    ["brand_id_1"],         // from /v1/brands/search
    },
    limit: 20,
  });
  ```

  ```python Python theme={null}
  results = client.products.search(
      query="running shoes",
      filters={
          "price":        {"min_price": 50, "max_price": 150},
          "availability": ["InStock", "LimitedAvailability"],
          "gender":       "male",
          "category":     "running-shoes",
          "brand_ids":    ["brand_id_1"],
      },
      limit=20,
  )
  ```
</CodeGroup>

### Popular filters

These are the filters most integrations use. See the [API reference](/api-reference/v1/search) for the complete list.

| Filter         | Type                                     | Description                                                                                                                                                                    |
| -------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `price`        | `{ min_price?, max_price? }`             | Price range in the request's currency.                                                                                                                                         |
| `availability` | `string[]`                               | One or more of `InStock`, `LimitedAvailability`, `PreOrder`, `BackOrder`, `SoldOut`, `OutOfStock`.                                                                             |
| `gender`       | `string`                                 | `male`, `female`, or `unisex`.                                                                                                                                                 |
| `category`     | `string`                                 | A category slug (e.g. `running-shoes`). See [Categories](/categories).                                                                                                         |
| `brand_ids`    | `string[]`                               | Limit to specific brands. Resolve brand IDs via [`/v1/brands/search`](/api-reference/v1/search-brands).                                                                        |
| `attributes`   | `Record<string, string[]>`               | Filter by structured attribute key/value pairs — e.g. `{ "connectivity": ["USB"] }`. Attribute keys come from category detail. See [Advanced Search](/guides/advanced-search). |
| `colors`       | `{ hex: string, percentage?: number }[]` | Filter by color palette using hex values **(Beta)**.                                                                                                                           |
| `age`          | `string`                                 | `newborn`, `infant`, `toddler`, `kids`, or `adult`.                                                                                                                            |
| `dimensions`   | `{ length?, width?, height?, weight? }`  | Filter by physical size and weight, each `{ min?, max?, unit }`. See [Dimension Filters](/guides/dimension-filters).                                                           |

## Pagination

Use `next_page_token` from the response to fetch the next page. You can page up to 500 products total.

<CodeGroup>
  ```typescript TypeScript theme={null}
  const page1 = await client.products.search({ query: "running shoes" });
  console.log("Page 1:", page1.products.length, "products");

  if (page1.next_page_token) {
    const page2 = await client.products.search({
      query: "running shoes",
      page_token: page1.next_page_token,
    });
    console.log("Page 2:", page2.products.length, "products");
  }
  ```

  ```python Python theme={null}
  page1 = client.products.search(query="running shoes")
  print(f"Page 1: {len(page1.products)} products")

  if page1.next_page_token:
      page2 = client.products.search(
          query="running shoes",
          page_token=page1.next_page_token,
      )
      print(f"Page 2: {len(page2.products)} products")
  ```
</CodeGroup>

## Search modes

`config.mode` selects the search strategy. `default` combines keyword (lexical) and semantic (vector) search and is the right choice for most use cases — the other two modes trade that balance for speed or depth.

| Mode      | What it does                                   | Use it for                                                                 |
| --------- | ---------------------------------------------- | -------------------------------------------------------------------------- |
| `default` | Lexical + semantic search.                     | Most product search. This is the default.                                  |
| `keyword` | Lexical only — skips semantic search.          | Real-time, low-latency needs like ad targeting, SKU or exact-name lookups. |
| `agentic` | An LLM plans multiple structured sub-searches. | Complex, multi-constraint queries where quality matters more than latency. |

### Low-latency keyword search

Set `mode: "keyword"` to skip semantic (vector) search and use exact keyword matching instead. This path is optimized for **super low latency** — use it when users type specific product names or SKUs, or when you need the fastest possible search response.

<CodeGroup>
  ```typescript TypeScript theme={null}
  const results = await client.products.search({
    query: "Nike Air Max 90",
    config: { mode: "keyword" },
  });
  ```

  ```python Python theme={null}
  results = client.products.search(
      query="Nike Air Max 90",
      config={"mode": "keyword"},
  )
  ```
</CodeGroup>

<Note>
  `mode: "keyword"` replaces the deprecated `keyword_search_only: true`, which
  still works and behaves identically.
</Note>

### Agentic search

Set `mode: "agentic"` when queries read like a person describing what they want rather than a keyword phrase — an LLM decomposes the query into structured sub-searches so every constraint becomes a real filter. See [Agentic Search](/guides/agentic-search) for how it works and when to use it.

<Cards>
  <Card title="Advanced Search" icon="sliders" href="/guides/advanced-search" arrow="true">
    Use structured attributes to find products by feature — e.g. "sofas with USB charging ports."
  </Card>

  <Card title="Localization" icon="globe" href="/guides/localization" arrow="true">
    Set country, language, and currency for market-specific results.
  </Card>

  <Card title="Caching" icon="database" href="/guides/caching" arrow="true">
    Cache product IDs safely while refreshing prices and availability at display time.
  </Card>
</Cards>
