> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# About the catalog

> The three catalog tools and how requests are shaped

**`ucp.trychannel3.com`** is one catalog across many online stores. It uses the same product data as the Channel3 REST API.

## Three tools

| Tool             | Use it when you want to...                              |
| ---------------- | ------------------------------------------------------- |
| `search_catalog` | Find products from a text query                         |
| `lookup_catalog` | Load products you already know by id or store URL       |
| `get_product`    | Load one product by id, with optional variant selection |

## How to shape a request

Every tool takes the same outer shape:

```json theme={null}
{
  "meta": null,
  "catalog": { }
}
```

* **`catalog`** — your query (`query`, `ids`, `urls`, `id`, `selected`, `preferences`, `pagination`, filters, `context` for currency or country)
* **`meta`** — pass `null` on Channel3 today ([details](/ucp/about-profiles#what-is-meta))

The answer lives in **`structuredContent`**: `products`, `pagination`, and sometimes `messages`.

## Channel3 extras

Base UCP gives you title, price, variants, and store domain. For filters by store, richer seller info, and URL lookup, use extension **`com.trychannel3.catalog.global`**. Details: [Extension reference](/ucp/catalog-global-extension).

## Same as REST

| Tool                         | REST equivalent                                                |
| ---------------------------- | -------------------------------------------------------------- |
| `search_catalog`             | `POST /v1/search`                                              |
| `lookup_catalog` with `ids`  | `POST /v1/lookup`                                              |
| `lookup_catalog` with `urls` | `POST /v1/lookup` (URL)                                        |
| `get_product`                | `GET /v1/products/{id}` (`option_<name>=<label>` query params) |

## What's next

<CardGroup cols={2}>
  <Card title="Search" icon="search" href="/ucp/search-catalog">
    Text search and filters
  </Card>

  <Card title="Lookup" icon="link" href="/ucp/lookup-catalog">
    By id or store URL
  </Card>

  <Card title="Get product" icon="box" href="/ucp/get-product">
    One product by id, with variant selection
  </Card>
</CardGroup>
