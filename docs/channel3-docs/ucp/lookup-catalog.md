> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Lookup catalog

> Load products by ID or by a store product page URL

**`lookup_catalog`** turns ids or URLs into full product records.

* **`catalog.ids`** - Channel3 product ids (or variant ids)
* **`catalog.urls`** - links to a product page on a store's website

Don't put `https://...` links in `ids`. Use `urls` for those.

Examples below use **UCP CLI** and **curl**. See [quickstart](/ucp/quickstart) to install the CLI.

## By product ID

<CodeGroup>
  ```bash UCP CLI theme={null}
  ucp catalog lookup \
    --input '{"ids":["HvGOfxD","cp_def456"]}' \
    --format json
  ```

  ```bash curl theme={null}
  curl -sS -X POST https://ucp.trychannel3.com/mcp \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d '{
      "jsonrpc": "2.0",
      "id": 1,
      "method": "tools/call",
      "params": {
        "name": "lookup_catalog",
        "arguments": {
          "meta": null,
          "catalog": {
            "ids": ["HvGOfxD", "cp_def456"]
          }
        }
      }
    }'
  ```
</CodeGroup>

You get one product per ID when we have it. Missing ids show up in `messages` but won't fail the whole request.

## By product URL

<CodeGroup>
  ```bash UCP CLI theme={null}
  ucp catalog lookup \
    --input '{"urls":["https://merchant.example.com/products/some-shoe"]}' \
    --format json
  ```

  ```bash curl theme={null}
  curl -sS -X POST https://ucp.trychannel3.com/mcp \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d '{
      "jsonrpc": "2.0",
      "id": 1,
      "method": "tools/call",
      "params": {
        "name": "lookup_catalog",
        "arguments": {
          "meta": null,
          "catalog": {
            "urls": [
              "https://merchant.example.com/products/some-shoe"
            ]
          }
        }
      }
    }'
  ```
</CodeGroup>

We match the URL to our index and return the product with **every store's offer as a separate entry in `variants[]`** (same as `POST /v1/lookup`). Multiple sellers for one product means multiple variants — see [Extension reference](/ucp/catalog-global-extension#variants-per-store-listings).

For interactive variant selection (`selected`, `preferences`), use [`get_product`](/ucp/get-product) instead.

<Warning>
  If you put a URL in **`catalog.ids`**, you'll get a message telling you to use
  **`catalog.urls`** instead.
</Warning>

## Both at once

You can send `ids` and `urls` in one request if your agent has a mix.

<CodeGroup>
  ```bash UCP CLI theme={null}
  ucp catalog lookup \
    --input '{"ids":["HvGOfxD"],"urls":["https://merchant.example.com/products/some-shoe"]}' \
    --format json
  ```

  ```bash curl theme={null}
  curl -sS -X POST https://ucp.trychannel3.com/mcp \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d '{
      "jsonrpc": "2.0",
      "id": 1,
      "method": "tools/call",
      "params": {
        "name": "lookup_catalog",
        "arguments": {
          "meta": null,
          "catalog": {
            "ids": ["HvGOfxD"],
            "urls": ["https://merchant.example.com/products/some-shoe"]
          }
        }
      }
    }'
  ```
</CodeGroup>

## What's next

<Card title="Get one product" icon="box" href="/ucp/get-product">
  When you only need a single ID
</Card>
