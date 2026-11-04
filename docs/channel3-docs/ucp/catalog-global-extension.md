> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Extension reference

> Extra catalog fields in com.trychannel3.catalog.global

**`com.trychannel3.catalog.global`** adds Channel3-specific fields on top of standard UCP catalog: store filters, seller details, URL lookup, and our id formats.

It's listed in the [profile](https://ucp.trychannel3.com/.well-known/ucp) and works with search, lookup, and get\_product.

New here? Start with the [overview](/ucp/index) or [quickstart](/ucp/quickstart).

## Request extensions

### `catalog.urls[]` (lookup only)

`lookup_catalog` accepts store product page URLs in **`catalog.urls[]`**, as well as product ids in **`catalog.ids[]`**:

```json theme={null}
{
  "catalog": {
    "urls": ["https://www.merchant.com/products/widget-blue"]
  }
}
```

Same behavior as [`POST /v1/lookup`](/api-reference/post-v1lookup). If we can't find the URL, you get `messages[]` with `code: "not_found"`.

Put page links in **`urls[]`**, not **`ids[]`**. If a URL ends up in `ids`, we return `use_catalog_urls`.

### `catalog.filters`

Extra filters on top of UCP `categories` and `price`. Filters combine with AND; multiple values in one field combine with OR.

| Field                  | Type                                                      | Notes                                                                                                         |
| ---------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `website_ids`          | `string[]`                                                | Merchant ids (e.g. `"lGBj"`) **or** domains (e.g. `"nike.com"`). Alias: `shop_ids` for Shopify-shaped clients |
| `exclude_website_ids`  | `string[]`                                                | Same shape, inverted                                                                                          |
| `condition`            | `string[]`                                                | One or more of `"new"`, `"used"`, `"refurbished"`. `"secondhand"` is accepted and normalized to `"used"`      |
| `available`            | `boolean`                                                 | When `true` (default), only in-stock variants. When `false`, no availability filter is applied                |
| `brand_ids`            | `string[]`                                                | Restrict to specific brands                                                                                   |
| `exclude_brand_ids`    | `string[]`                                                | Inverse of `brand_ids`                                                                                        |
| `category_ids`         | `string[]`                                                | Alias for `categories` - accepts category slug strings                                                        |
| `exclude_category_ids` | `string[]`                                                | Inverse                                                                                                       |
| `gender`               | `"male" \| "female" \| "unisex"`                          | Demographic                                                                                                   |
| `age`                  | `"newborn" \| "infant" \| "toddler" \| "kids" \| "adult"` | Demographic                                                                                                   |

`price.min` and `price.max` are in **cents** (minor units). Example: `9995` means \$99.95 USD.

### `catalog.context`

The base spec defines context as buyer signals. We honor:

| Field                                     | Notes                                                               |
| ----------------------------------------- | ------------------------------------------------------------------- |
| `currency`                                | Defaults to `USD`. Used for price formatting and the `price` filter |
| `language`, `country` / `address_country` | Locale hints, used to bias content where available                  |

### `catalog.placements` (opt-in)

Set **`catalog.placements: ["affiliate"]`** to have variants carry a [`placement`](#commissions-placements) object with the commission earned on a converted sale. Requires a [Token-tier](/ucp/authentication) API key — anonymous callers (no key or invalid key) never receive commission data. Omit the field (or pass `[]`) and responses are unchanged.

```json theme={null}
{
  "catalog": {
    "query": "running shoes",
    "placements": ["affiliate"]
  }
}
```

## Response extensions

### `products[]`

Standard UCP product fields, plus Channel3 metadata. Buy and store links live on **`variants[]`** only (same as Shopify — `products[].url` is omitted).

| Field                            | Type              | Notes                               |
| -------------------------------- | ----------------- | ----------------------------------- |
| `metadata.top_features`          | `string[]`        | Channel3-curated feature highlights |
| `metadata.unique_selling_points` | `string[]`        | Single-line USP, when available     |
| `metadata.attributes`            | `[{name, value}]` | Extracted product attributes        |

### `options` and `selected` (get\_product)

Standard UCP fields for **variant selection** (color, size, etc.). Returned on **`get_product`** only — not on search or lookup.

| Field        | Notes                                                                                                                                                                                  |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `options[]`  | Selectable dimensions. Each value has `label` and an `exists` flag — whether that value exists on the product, or only on a sibling variant (e.g. a color offered only in some sizes). |
| `selected[]` | Effective selections after server-side relaxation — diff against your request to detect relaxation                                                                                     |

See [Get product](/ucp/get-product) for `catalog.selected` and `catalog.preferences`.

### `products[]`

A UCP **`products[]`** entry is a Channel3 product (one product across all stores). Per-store listings are in **`variants[]`** — when several stores sell the same product, each store's offer is its own entry in `variants[]`, so **multiple offers for one product are multiple variants**, not a nested list:

| Field              | Notes                                                                                                                               |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| `id`               | Channel3 product id. On `get_product`, when `catalog.selected` resolves to a different variant, this reflects the resolved product. |
| `title`            | Product title from the graph, not a single store's PDP title                                                                        |
| `price_range`      | Min/max **selling** price across the product's variants, in UCP minor units                                                         |
| `list_price_range` | Min/max **list** price across variants on sale, when any variant has `list_price`                                                   |
| `options[]`        | Selectable dimensions (Color, Size, …) when the product has variants — **`get_product`** only                                       |

### `variants[]` (per-store listings)

Each **variant** is one store's listing of the product:

```json theme={null}
{
  "id": "HvGOfxD:lGBj:01KJ38CXYZ9CJ8K2Y9HDYQ8DXT",
  "title": "Velociti Pace Running Shoes - 8",
  "url": "https://buy.trychannel3.com/HvGOfxD-lGBj-public_ucp?o=01KJ38CXYZ9CJ8K2Y9HDYQ8DXT",
  "price": { "amount": 9995, "currency": "USD" },
  "list_price": { "amount": 12995, "currency": "USD" },
  "availability": { "available": true },
  "seller": {
    "id": "lGBj",
    "name": "SHOEBACCA.com",
    "domain": "shoebacca.com",
    "url": "https://www.shoebacca.com"
  },
  "condition": ["new"],
  "placement": {
    "type": "affiliate",
    "commission": { "percentage": { "value": 12.5 } }
  }
}
```

| Field                     | Notes                                                                                                                                                                         |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `variants[].id`           | Variant id — `product:store:sku`                                                                                                                                              |
| `variants[].url`          | Buy redirect (`buy.trychannel3.com`). **Token**: monetized to your account; **Anonymous**: no monetization                                                                    |
| `variants[].price`        | Current selling price in UCP minor units (cents)                                                                                                                              |
| `variants[].list_price`   | Pre-discount list price in minor units, when the item is on sale (`compare_at_price` > `price` in our graph)                                                                  |
| `variants[].availability` | Standard UCP shape (`{ "available": true }`)                                                                                                                                  |
| `variants[].seller`       | The store selling this listing. Use `seller.domain` with UCP CLI `--business`                                                                                                 |
| `variants[].seller.url`   | Merchant store homepage (same role as Shopify's `seller.url`)                                                                                                                 |
| `variants[].inputs`       | When a variant matched a `catalog.ids` or `catalog.urls` entry, includes `[{id, match}]` with `match: "exact" \| "featured"`                                                  |
| `variants[].placement`    | Commission on this offer. Present only with [`catalog.placements: ["affiliate"]`](#catalogplacements-opt-in) on a Token-tier key — see [Commissions](#commissions-placements) |

### Commissions / placements

<Info>
  Placements are in **preview** and mirror Shopify's catalog `placement` shape, so agents that already read commissions from a Shopify catalog read Channel3's identically. Fields may change.
</Info>

When you opt in with [`catalog.placements: ["affiliate"]`](#catalogplacements-opt-in) on a [Token-tier](/ucp/authentication) key, monetizable variants carry a `placement`:

```json theme={null}
"placement": {
  "type": "affiliate",
  "commission": { "percentage": { "value": 12.5 } }
}
```

| Field                                   | Notes                                                                                                                        |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `placement.type`                        | `"affiliate"`                                                                                                                |
| `placement.commission.percentage.value` | Commission as a percentage number — `12.5` means 12.5% of the sale, paid on a conversion via your monetized `variants[].url` |

* **Absent ≠ zero.** A variant without `placement` has no disclosed commission (offer not monetizable, or you didn't opt in) — don't treat a missing `placement` as 0%.
* Commission is the **vendor's net share** after Channel3's cut. Actual payout depends on the merchant program and locale; treat the value as an estimate.

## Product ids

We use two id formats:

* **Product id** (e.g. `HvGOfxD`) - one product across all stores
* **Variant id** (e.g. `HvGOfxD:lGBj:01KJ38CXYZ9CJ8K2Y9HDYQ8DXT`) - one store's listing: `product:store:sku`

Both work in `catalog.ids[]` and `get_product`. `https://buy.trychannel3.com/...` links also work in `ids`.

## Messages

`messages[]` entries we emit:

| `code`             | When                                            | Action                      |
| ------------------ | ----------------------------------------------- | --------------------------- |
| `not_found`        | Lookup couldn't resolve the id or URL           | Treat as a miss             |
| `invalid_url`      | A `catalog.urls[]` entry isn't a valid HTTP URL | Fix the URL                 |
| `use_catalog_urls` | An HTTP URL appeared in `catalog.ids[]`         | Move it to `catalog.urls[]` |

## Versioning

Current version: **`2026-04-08`** (see the [profile](https://ucp.trychannel3.com/.well-known/ucp)).
