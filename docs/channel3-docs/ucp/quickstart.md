> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Quickstart

> Connect to the Channel3 catalog and run your first search

In a few minutes you'll connect to **`ucp.trychannel3.com`** and search for products. No API key needed.

Put your query in **`catalog`**. Curl examples also include **`"meta": null`** ([why](/ucp/about-profiles#what-is-meta)); the UCP CLI fills that in for you.

## Install UCP CLI

Channel3's catalog works with [**`@shopify/ucp-cli`**](https://github.com/Shopify/ucp-cli) — Shopify's reference CLI for [UCP](https://ucp.dev/). Examples in this section show the same call as **UCP CLI** and **curl** so you can copy either one.

<Info>
  Channel3 is **catalog-only** (search, lookup, get product). Cart, checkout,
  and order commands in the CLI apply to other UCP merchants, not this endpoint.
</Info>

<Info>
  Without an API key, CLI catalog commands use the **Anonymous** tier. Pass
  **`--header "x-api-key: $CHANNEL3_API_KEY"`** per command, or add
  [`headers.json`](/ucp/authentication) on your profile, for Token-tier rate
  limits and monetized buy links.
</Info>

```bash theme={null}
npm install -g @shopify/ucp-cli
# or: npx @shopify/ucp-cli <command>
```

Prefer **curl** only? Skip install and use the curl tabs below.

## You'll need

* **UCP CLI** (installed above) or `curl`
* Optional: [API key](https://trychannel3.com/dashboard) for Token tier: higher limits, monetized buy links, and optional `placement` commission data ([authentication](/ucp/authentication))

Your agent runtime should point at **`https://ucp.trychannel3.com/mcp`** (Streamable HTTP MCP).

## 1. Read the profile

<CodeGroup>
  ```bash UCP CLI theme={null}
  ucp discover --business https://ucp.trychannel3.com --format json
  ```

  ```bash curl theme={null}
  curl -sS https://ucp.trychannel3.com/.well-known/ucp | jq .
  ```
</CodeGroup>

This JSON lists the catalog tools and the MCP URL.

## 2. Start an MCP session

<CodeGroup>
  ```bash UCP CLI theme={null}
  # The CLI starts MCP sessions automatically on catalog commands.
  ucp doctor
  ```

  ```bash curl theme={null}
  curl -sS -X POST https://ucp.trychannel3.com/mcp \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"my-agent","version":"1.0"}}}'
  ```
</CodeGroup>

You should get a response that mentions `channel3-catalog`.

## 3. Set your CLI profile

Point your local profile at the Channel3 catalog (discovery uses `/.well-known/ucp` on this host):

```bash theme={null}
ucp profile init --name channel3 --catalog https://ucp.trychannel3.com --activate
ucp profile show channel3 --format json
```

Confirm `meta.defaults.catalog` is `https://ucp.trychannel3.com`. If the profile already exists, add `--force` to re-point it (otherwise `init` is a no-op).

After that, catalog commands can omit `--business` — they use `meta.defaults.catalog` from the profile.

Override per shell if needed:

```bash theme={null}
export UCP_DEFAULT_CATALOG=https://ucp.trychannel3.com
```

<Note>
  Profile setup is **CLI-only**. Curl examples in this guide call
  `ucp.trychannel3.com` directly — no local profile needed.
</Note>

## 4. List tools

<CodeGroup>
  ```bash UCP CLI theme={null}
  ucp catalog search --input-schema --format json
  ```

  ```bash curl theme={null}
  curl -sS -X POST https://ucp.trychannel3.com/mcp \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
  ```
</CodeGroup>

The curl `tools/list` returns all three tools: `search_catalog`, `lookup_catalog`, and `get_product`. The UCP CLI `--input-schema` shows the input schema for one tool (`search_catalog` here) — run `ucp discover` to see every negotiated tool.

## 5. Search

<CodeGroup>
  ```bash UCP CLI theme={null}
  ucp catalog search \
    --set /query='running shoes' \
    --set '/pagination/limit=5' \
    --format json
  ```

  ```bash curl theme={null}
  curl -sS -X POST https://ucp.trychannel3.com/mcp \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d '{
      "jsonrpc": "2.0",
      "id": 3,
      "method": "tools/call",
      "params": {
        "name": "search_catalog",
        "arguments": {
          "meta": null,
          "catalog": {
            "query": "running shoes",
            "pagination": { "limit": 5 }
          }
        }
      }
    }'
  ```
</CodeGroup>

In the response, open **`structuredContent`** (curl) or **`result`** (CLI):

* **`products`** - the matches (title, price, store, variants)
* **`pagination.cursor`** - copy this into the next request for page 2
* **`pagination.has_next_page`** - `true` if there are more results

## 6. Search with your API key

For production traffic, [create a key](https://trychannel3.com/dashboard) and send it on every catalog call. Channel3 accepts **`x-api-key`** or **`Authorization: Bearer <key>`**.

```bash theme={null}
export CHANNEL3_API_KEY="ch3_live_..."
```

<CodeGroup>
  ```bash UCP CLI theme={null}
  ucp catalog search \
    --header "x-api-key: $CHANNEL3_API_KEY" \
    --set /query='running shoes' \
    --set '/pagination/limit=5' \
    --format json
  ```

  ```bash curl theme={null}
  curl -sS -D - -o /tmp/ucp-search.json -X POST https://ucp.trychannel3.com/mcp \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -H "x-api-key: $CHANNEL3_API_KEY" \
    -d '{
      "jsonrpc": "2.0",
      "id": 4,
      "method": "tools/call",
      "params": {
        "name": "search_catalog",
        "arguments": {
          "meta": null,
          "catalog": {
            "query": "running shoes",
            "pagination": { "limit": 5 }
          }
        }
      }
    }'
  ```
</CodeGroup>

Confirm Token tier in the response headers:

```
x-ucp-auth-tier: token
```

Your buy links should be monetized to your account. Compare with step 5 without a key (no monetization).

### Placement commission data (optional)

The API key alone attributes **buy links** to your account. To also receive **`variants[].placement`** commission percentages, opt in with **`catalog.placements: ["affiliate"]`**. Without a Token-tier key, placements are never returned even if you pass the field.

<CodeGroup>
  ```bash UCP CLI theme={null}
  ucp catalog search \
    --header "x-api-key: $CHANNEL3_API_KEY" \
    --set /query='running shoes' \
    --set '/pagination/limit=5' \
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
      "id": 5,
      "method": "tools/call",
      "params": {
        "name": "search_catalog",
        "arguments": {
          "meta": null,
          "catalog": {
            "query": "running shoes",
            "pagination": { "limit": 5 },
            "placements": ["affiliate"]
          }
        }
      }
    }'
  ```
</CodeGroup>

On monetizable offers, matching variants include **`placement`** with the commission rate (e.g. `12.5` = 12.5%). Omitted `placement` means no disclosed commission for that offer — not zero. See [Extension reference](/ucp/catalog-global-extension#catalogplacements-opt-in).

<Accordion title="Skip --header on every command (CLI only)">
  Add **`~/.ucp/profiles/channel3/headers.json`** so the key is sent automatically:

  ```json theme={null}
  {
    "default": {},
    "businesses": {
      "https://ucp.trychannel3.com": {
        "x-api-key": "${CHANNEL3_API_KEY}"
      }
    }
  }
  ```

  Keep `CHANNEL3_API_KEY` in your shell environment. See [Authentication](/ucp/authentication) for placements and more detail.
</Accordion>

## What's next

<CardGroup cols={2}>
  <Card title="Authentication" icon="key" href="/ucp/authentication">
    Placements, persistent headers, Bearer auth
  </Card>

  <Card title="Search in depth" icon="search" href="/ucp/search-catalog">
    Filters and pagination
  </Card>

  <Card title="Look up a store URL" icon="link" href="/ucp/lookup-catalog">
    Turn a product page link into catalog data
  </Card>

  <Card title="Rate limits" icon="shield" href="/ucp/auth-and-rate-limiting">
    Anonymous vs API key
  </Card>
</CardGroup>
