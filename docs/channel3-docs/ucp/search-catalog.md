> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Search the catalog

> Find products with search_catalog

**`search_catalog`** finds products across stores from a text **`query`**.

Optional: [API key](/ucp/authentication) via **`--header`** or profile **`headers.json`** for Token tier (limits, monetizable links, placements). Without a key, the CLI runs as Anonymous.

## Basic search

<CodeGroup>
  ```bash UCP CLI theme={null}
  ucp catalog search \
    --set /query='wireless headphones under $100' \
    --set '/pagination/limit=10' \
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
        "name": "search_catalog",
        "arguments": {
          "meta": null,
          "catalog": {
            "query": "wireless headphones under $100",
            "pagination": { "limit": 10 }
          }
        }
      }
    }'
  ```
</CodeGroup>

In the MCP response, open **`structuredContent`** (curl stream) or **`result`** (CLI):

* **`products`** - matches with price, variants, and store info
* **`pagination.has_next_page`** - more results available?
* **`pagination.cursor`** - send this back for the next page

## Next page

<CodeGroup>
  ```bash UCP CLI theme={null}
  ucp catalog search \
    --set /query='running shoes' \
    --set '/pagination/limit=10' \
    --set '/pagination/cursor=<paste cursor from last response>' \
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
        "name": "search_catalog",
        "arguments": {
          "meta": null,
          "catalog": {
            "query": "running shoes",
            "pagination": {
              "limit": 10,
              "cursor": "<paste cursor from last response>"
            }
          }
        }
      }
    }'
  ```
</CodeGroup>

## Filter by store (Channel3 extension)

Limit results to specific merchants:

<CodeGroup>
  ```bash UCP CLI theme={null}
  ucp catalog search \
    --input '{
      "query": "trail running shoes",
      "pagination": { "limit": 10 },
      "filters": {
        "website_ids": ["lGBj", "nike.com"]
      }
    }' \
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
        "name": "search_catalog",
        "arguments": {
          "meta": null,
          "catalog": {
            "query": "trail running shoes",
            "pagination": { "limit": 10 },
            "filters": {
              "website_ids": ["lGBj", "nike.com"]
            }
          }
        }
      }
    }'
  ```
</CodeGroup>

`website_ids` can be merchant ids or domains. Same as REST `website_ids` / `shop_ids`. More filters: [Extension reference](/ucp/catalog-global-extension).

## Placement commission data (Token tier)

Opt in with **`catalog.placements: ["affiliate"]`** and a [valid API key](/ucp/authentication). Matching variants include **`placement`** with commission percentage. Omit `placements` (or pass `[]`) and responses are unchanged.

<CodeGroup>
  ```bash UCP CLI theme={null}
  ucp catalog search \
    --header "x-api-key: $CHANNEL3_API_KEY" \
    --set /query='trail running shoes' \
    --set '/pagination/limit=10' \
    --set '/placements=["affiliate"]' \
    --format json
  ```

  ```bash curl theme={null}
  curl -sS -X POST https://ucp.trychannel3.com/mcp \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -H "x-api-key: $CHANNEL3_API_KEY" \
    -d '{
      "jsonrpc": "2.0",
      "id": 1,
      "method": "tools/call",
      "params": {
        "name": "search_catalog",
        "arguments": {
          "meta": null,
          "catalog": {
            "query": "trail running shoes",
            "pagination": { "limit": 10 },
            "placements": ["affiliate"]
          }
        }
      }
    }'
  ```
</CodeGroup>

See [Extension reference](/ucp/catalog-global-extension#catalogplacements-opt-in) for response shape.

## Fields worth saving

| Field                                 | Why                                       |
| ------------------------------------- | ----------------------------------------- |
| `products[].id`                       | Product id for lookup or get\_product     |
| `products[].variants[]`               | Per-store listings (SKUs, prices, seller) |
| `products[].variants[].seller.domain` | Which store                               |
| `messages[]`                          | Warnings (empty query, bad filter, etc.)  |

Variant **`options`** (Color, Size, …) are returned by [`get_product`](/ucp/get-product), not by search.

## What's next

<CardGroup cols={2}>
  <Card title="Lookup" icon="link" href="/ucp/lookup-catalog">
    You already have ids or URLs
  </Card>

  <Card title="Get product" icon="box" href="/ucp/get-product">
    One product by id
  </Card>
</CardGroup>
