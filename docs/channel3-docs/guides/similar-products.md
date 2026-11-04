> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Similar Products

> Given a product, find similar alternatives.

Given a `product_id`, `products.find_similar` returns the closest neighbors. Add `filters` to narrow results by gender, brand, category, or price.

<CodeGroup>
  ```typescript TypeScript theme={null}
  import Channel3 from "@channel3/sdk";

  const client = new Channel3();

  const similar = await client.products.find_similar({
    product_id: "2yh8WH5",
    limit: 10,
    filters: {
      gender: "female",
      price: { max_price: 200 },
    },
  });

  console.log(similar.products.map((p) => p.title));
  ```

  ```python Python theme={null}
  from channel3_sdk import Channel3

  client = Channel3()

  similar = client.products.find_similar(
      product_id="2yh8WH5",
      limit=10,
      filters={
          "gender": "female",
          "price": {"max_price": 200},
      },
  )
  print([p.title for p in similar.products])
  ```

  ```bash cURL theme={null}
  curl -X POST https://api.trychannel3.com/v1/similar \
    -H "x-api-key: $CHANNEL3_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"product_id": "2yh8WH5", "limit": 10, "filters": {"gender": "female", "price": {"max_price": 200}}}'
  ```
</CodeGroup>

## Creative uses of `/similar`

* **"Shop the look"** — for a shirt result, filter the similar call to `pants` and `shoes` categories to suggest a full outfit.
* **Couple's shopping** — exclude the source product's gender to surface his-and-hers alternatives.
* **Budget finder** — set a price ceiling based on the source product's price to surface similar but cheaper items.
* **Shop for the whole family** — add an `age` filter (`kids`, `toddler`) to find children's versions of an item.

<Cards>
  <Card title="Image Search" icon="image" href="/guides/image-search" arrow="true">
    Search by image URL or base64 upload to find visually matching products.
  </Card>

  <Card title="Advanced Search" icon="sliders" href="/guides/advanced-search" arrow="true">
    Combine similar-product results with structured attribute filters.
  </Card>
</Cards>
