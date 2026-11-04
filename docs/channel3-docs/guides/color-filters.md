> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Color Filters

> Filter products by color palette using hex values to find items that match a specific color scheme.

<Note>
  Color filtering is currently in **Beta**. The API surface may change.
</Note>

The `colors` filter on `POST /v1/search` accepts one or more hex color values and returns products whose dominant colors match the palette. This is useful for building color-matched shopping experiences — for example, finding furniture or clothing that complements a specific color scheme.

<iframe src="https://www.linkedin.com/embed/feed/update/urn:li:ugcPost:7465145869307322368?compact=1" height="300" frameborder="0" allowfullscreen="" title="Embedded post" />

## Basic color filter

Pass an array of `{ hex, percentage? }` objects. The `percentage` field is optional and indicates the desired proportion of that color in the product image.

<CodeGroup>
  ```typescript TypeScript theme={null}
  import Channel3 from "@channel3/sdk";

  const client = new Channel3();

  const results = await client.products.search({
    query: "sofa",
    filters: {
      colors: [{ hex: "#5D3FD3" }],
    },
  });
  ```

  ```python Python theme={null}
  from channel3_sdk import Channel3

  client = Channel3()

  results = client.products.search(
      query="sofa",
      filters={
          "colors": [{"hex": "#5D3FD3"}],
      },
  )
  ```

  ```bash cURL theme={null}
  curl -X POST https://api.trychannel3.com/v1/search \
    -H "x-api-key: $CHANNEL3_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "query": "sofa",
      "filters": { "colors": [{ "hex": "#5D3FD3" }] }
    }'
  ```
</CodeGroup>

## Multiple colors

Provide a palette of colors to find products that match the combination.

<CodeGroup>
  ```typescript TypeScript theme={null}
  const results = await client.products.search({
    query: "throw pillow",
    filters: {
      colors: [{ hex: "#1A1A2E" }, { hex: "#E2B96F" }],
    },
  });
  ```

  ```python Python theme={null}
  results = client.products.search(
      query="throw pillow",
      filters={
          "colors": [
              {"hex": "#1A1A2E"},
              {"hex": "#E2B96F"},
          ],
      },
  )
  ```
</CodeGroup>

## With percentage hints

Use `percentage` to signal how dominant each color should be in the product. Values are relative weights, not strict percentages.

```typescript TypeScript theme={null}
const results = await client.products.search({
  query: "area rug",
  filters: {
    colors: [
      { hex: "#8B4513", percentage: 60 },
      { hex: "#F5DEB3", percentage: 40 },
    ],
  },
});
```

<Cards>
  <Card title="Image Search" icon="image" href="/guides/image-search" arrow="true">
    Search by uploading an image to find visually similar products.
  </Card>

  <Card title="Search" icon="magnifying-glass" href="/guides/search" arrow="true">
    Full overview of the search endpoint and all available filters.
  </Card>
</Cards>
