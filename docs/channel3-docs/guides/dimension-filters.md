> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Dimension Filters

> Filter search results by physical size and weight, in the units you choose.

The `dimensions` filter on `POST /v1/search` narrows results by an offer's physical size — `length`, `width`, `height`, and `weight`. Each field is optional; pass only the ones you care about.

Every field you include takes a `min`, a `max` (both optional and inclusive), and a required `unit`. A product matches when at least one of its offers satisfies **every** range you provide, alongside any locale, price, and availability filters on the same request.

## Basic dimension filter

Find products that fit within a size and weight envelope. Length units are `mm`, `cm`, `m`, `in`, `ft`; weight units are `mg`, `g`, `kg`, `oz`, `lb`.

<CodeGroup>
  ```typescript TypeScript theme={null}
  import Channel3 from "@channel3/sdk";

  const client = new Channel3();

  const results = await client.products.search({
    query: "carry-on suitcase",
    filters: {
      dimensions: {
        height: { max: 22, unit: "in" },
        width:  { max: 14, unit: "in" },
        weight: { max: 8,  unit: "lb" },
      },
    },
  });
  ```

  ```python Python theme={null}
  from channel3_sdk import Channel3

  client = Channel3()

  results = client.products.search(
      query="carry-on suitcase",
      filters={
          "dimensions": {
              "height": {"max": 22, "unit": "in"},
              "width":  {"max": 14, "unit": "in"},
              "weight": {"max": 8,  "unit": "lb"},
          },
      },
  )
  ```

  ```bash cURL theme={null}
  curl -X POST https://api.trychannel3.com/v1/search \
    -H "x-api-key: $CHANNEL3_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "query": "carry-on suitcase",
      "filters": {
        "dimensions": {
          "height": { "max": 22, "unit": "in" },
          "width":  { "max": 14, "unit": "in" },
          "weight": { "max": 8,  "unit": "lb" }
        }
      }
    }'
  ```
</CodeGroup>

## Units

Each field carries its own `unit`, so you can mix systems in one request — filter length in `cm` and weight in `lb` if that's what your UI collects. Values are compared with a small relative tolerance, so a listing measured in another unit still matches after conversion.

The unit you filter in also controls the response: **offer dimensions are returned in the unit used by that field's filter.** When you don't filter on a field, its response unit falls back to the [`length_unit` / `weight_unit` config](/guides/localization#dimension-units) (per-request or a client default), and when neither is set, to the unit the merchant stated.

<Note>
  Channel3 standardizes dimensions to the supported unit sets above. A merchant-stated value whose unit falls outside those sets is omitted rather than shown — so a field can be `null` in the response even when the merchant published something.
</Note>

## Reading dimensions off an offer

Every offer in a search or product-detail response now carries a `dimensions` object. Each member is either `{ number, unit }` or `null` when unknown.

```typescript TypeScript theme={null}
const offer = results.products[0].offers[0];

if (offer.dimensions?.weight) {
  console.log(`${offer.dimensions.weight.number} ${offer.dimensions.weight.unit}`);
}
```

<Note>
  An offer with no dimension data for a filtered field never matches. Note that when one merchant on a product reports a dimension, that value is shared across the product's offers — so the specific offer that matched your filter may not itself surface that dimension in the response.
</Note>

<Cards>
  <Card title="Search" icon="magnifying-glass" href="/guides/search" arrow="true">
    Full overview of the search endpoint and all available filters.
  </Card>

  <Card title="Localization" icon="globe" href="/guides/localization" arrow="true">
    Set default units, country, language, and currency on the client.
  </Card>
</Cards>
