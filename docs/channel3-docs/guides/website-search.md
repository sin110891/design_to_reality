> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Website Search

> Discover and filter by the retailers (websites) whose products appear in Channel3.

Channel3 aggregates product offers from thousands of retailers. The websites API lets you browse the full list of supported retailers, and the `website_ids` filter on `POST /v1/search` lets you scope results to specific stores.

<Note>
  **What's the difference between brands and websites?**

  A **brand** makes or labels a product (Nike, Dyson). A **website** is the online store selling it (`nike.com`, `bestbuy.com`). Use `brand_ids` to filter by brand and `website_ids` to filter by retailer — they're independent. One brand's products often appear on many websites. See the [Brand](/api-reference/brand-model) and [Website](/api-reference/website-model) models.
</Note>

## Browse supported retailers

Use `GET /v0/websites` to retrieve the list of retailers available in Channel3.

<CodeGroup>
  ```typescript TypeScript theme={null}
  import Channel3 from "@channel3/sdk";

  const client = new Channel3();

  const { websites } = await client.websites.list();

  websites.forEach((site) => {
    console.log(site.id, site.name, site.domain);
  });
  ```

  ```python Python theme={null}
  from channel3_sdk import Channel3

  client = Channel3()

  result = client.websites.list()
  for site in result.websites:
      print(site.id, site.name, site.domain)
  ```

  ```bash cURL theme={null}
  curl "https://api.trychannel3.com/v0/websites" \
    -H "x-api-key: $CHANNEL3_API_KEY"
  ```
</CodeGroup>

## Filter search results by retailer

Pass one or more website IDs to the `website_ids` filter to restrict results to those retailers.

<CodeGroup>
  ```typescript TypeScript theme={null}
  const results = await client.products.search({
    query: "coffee maker",
    filters: {
      website_ids: ["walmart", "target"],
    },
  });
  ```

  ```python Python theme={null}
  results = client.products.search(
      query="coffee maker",
      filters={"website_ids": ["walmart", "target"]},
  )
  ```

  ```bash cURL theme={null}
  curl -X POST https://api.trychannel3.com/v1/search \
    -H "x-api-key: $CHANNEL3_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "query": "coffee maker",
      "filters": { "website_ids": ["walmart", "target"] }
    }'
  ```
</CodeGroup>

## Combining with other filters

Retailer filters compose with all other search filters.

```typescript TypeScript theme={null}
const results = await client.products.search({
  query: "desk lamp",
  filters: {
    website_ids: ["wayfair", "west-elm"],
    price: { max_price: 75 },
    availability: ["InStock"],
  },
});
```

<Cards>
  <Card title="Websites API" icon="globe" href="/api-reference/v0/list-websites" arrow="true">
    Full API reference for the websites endpoint.
  </Card>

  <Card title="Search" icon="magnifying-glass" href="/guides/search" arrow="true">
    Full overview of the search endpoint and all available filters.
  </Card>
</Cards>
