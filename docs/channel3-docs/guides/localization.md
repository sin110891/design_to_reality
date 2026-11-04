> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Localization

> Set country, language, and currency to localize search results and product detail for your target market.

Set `country`, `language`, and `currency` on search and product-detail requests to return offers priced and available for a specific market. Channel3 supports locales across Europe, the UK, Canada, Australia, and more.

## Per-request locale

Pass locale fields on each search call:

<CodeGroup>
  ```typescript TypeScript theme={null}
  const results = await client.products.search({
    query: "trainers",
    country: "GB",
    language: "en",
    currency: "GBP",
  });
  ```

  ```python Python theme={null}
  results = client.products.search(
      query="trainers",
      country="GB",
      language="en",
      currency="GBP",
  )
  ```

  ```bash cURL theme={null}
  curl -X POST https://api.trychannel3.com/v1/search \
    -H "x-api-key: $CHANNEL3_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "query": "trainers",
      "country": "GB",
      "language": "en",
      "currency": "GBP"
    }'
  ```
</CodeGroup>

## Default locale on the client

Set a default once on the client and it applies to every search and product-detail call. Per-request values override the client default.

<CodeGroup>
  ```typescript TypeScript theme={null}
  import Channel3 from "@channel3/sdk";

  const client = new Channel3({
    country: "GB",
    currency: "GBP",
  });

  // Uses GB / GBP
  await client.products.search({ query: "raincoat" });

  // Override per-call
  await client.products.search({
    query: "raincoat",
    config: { country: "DE", currency: "EUR" },
  });
  ```

  ```python Python theme={null}
  from channel3_sdk import Channel3

  client = Channel3(country="GB", currency="GBP")

  client.products.search(query="raincoat")

  client.products.search(
      query="raincoat",
      config={"country": "DE", "currency": "EUR"},
  )
  ```
</CodeGroup>

You can also set defaults via environment variables: `CHANNEL3_LANGUAGE`, `CHANNEL3_COUNTRY`, `CHANNEL3_CURRENCY`.

## Dimension units

`length_unit` and `weight_unit` choose the units product dimensions come back in. Like locale, you can set them once on the client — as constructor options or via the `CHANNEL3_LENGTH_UNIT` / `CHANNEL3_WEIGHT_UNIT` environment variables — and override them per call.

<CodeGroup>
  ```typescript TypeScript theme={null}
  const client = new Channel3({
    lengthUnit: "cm",
    weightUnit: "kg",
  });

  // Dimensions come back in cm / kg
  await client.products.search({ query: "coffee table" });

  // Override per-call
  await client.products.search({
    query: "coffee table",
    config: { length_unit: "in", weight_unit: "lb" },
  });
  ```

  ```python Python theme={null}
  client = Channel3(length_unit="cm", weight_unit="kg")

  client.products.search(query="coffee table")

  client.products.search(
      query="coffee table",
      config={"length_unit": "in", "weight_unit": "lb"},
  )
  ```
</CodeGroup>

On [`GET /v1/products/{product_id}`](/api-reference/v1/product-detail), pass `length_unit` / `weight_unit` as query parameters instead.

<Note>
  Precedence for the response unit of a field: a [dimension filter's](/guides/dimension-filters) own `unit` wins, then the per-request `config` value, then the client default; when none is set, dimensions are returned in the unit the merchant stated. Length units are `mm`, `cm`, `m`, `in`, `ft`; weight units are `mg`, `g`, `kg`, `oz`, `lb`.
</Note>

<Note>
  When only `country` is set, the server infers `currency` (e.g. `GB` → `GBP`) and `language` (e.g. `GB` → `en`). When all three are unset, defaults to `en` / `US` / `USD`.
</Note>

## Supported markets

Channel3 is expanding international coverage based on developer demand. Pass any of the values below as `country`, `currency`, or `language` on search and product-detail requests.

### Countries

| Code | Market                                                                             |
| ---- | ---------------------------------------------------------------------------------- |
| `US` | United States                                                                      |
| `CA` | Canada                                                                             |
| `GB` | United Kingdom                                                                     |
| `IE` | Ireland                                                                            |
| `AU` | Australia                                                                          |
| `DE` | Germany                                                                            |
| `AT` | Austria                                                                            |
| `FR` | France                                                                             |
| `BE` | Belgium                                                                            |
| `IT` | Italy                                                                              |
| `ES` | Spain                                                                              |
| `NL` | Netherlands                                                                        |
| `SE` | Sweden                                                                             |
| `FI` | Finland                                                                            |
| `PT` | Portugal                                                                           |
| `CZ` | Czech Republic                                                                     |
| `GR` | Greece                                                                             |
| `RO` | Romania                                                                            |
| `EU` | Europe (pan-region; use with `currency: EUR` when you don't need a single country) |

### Currencies

`USD`, `CAD`, `AUD`, `GBP`, `EUR`, `SEK`, `CZK`, `RON`

When you set `country` only, the API infers `currency` (for example `GB` → `GBP`). When all three locale fields are unset, defaults are `en` / `US` / `USD`.

### Languages

`en`, `de`, `fr`, `it`, `es`, `nl`, `sv`, `fi`, `pt`, `cs`, `el`, `ro`

<Note>
  Coverage outside the U.S. is still growing. If you need a geography we don't support yet, [contact us](mailto:support@trychannel3.com) or ask in [Discord](https://discord.gg/6J6MjctXrH).
</Note>

<Cards>
  <Card title="Search" icon="magnifying-glass" href="/guides/search" arrow="true">
    Full overview of the search endpoint, filters, and pagination.
  </Card>

  <Card title="Caching" icon="database" href="/guides/caching" arrow="true">
    Cache product IDs safely while refreshing prices and availability at display time.
  </Card>
</Cards>
