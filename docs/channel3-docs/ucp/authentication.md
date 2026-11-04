> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Authenticate your agent

> Use a Channel3 API key for Token-tier catalog access, rate limits, and monetizable links

You can use the catalog **with no login** (Anonymous tier). Without a key, requests run as Anonymous: lower rate limits and no monetization.

For production, add a **Channel3 API key** for the **Token** tier: higher rate limits, monetization on `variants[].url` buy links, and optional [`placement`](/ucp/catalog-global-extension#commissions-placements) commission data when you opt in.

## 1. Create a key

1. Go to the [dashboard](https://trychannel3.com/dashboard).
2. Create an API key.
3. Keep it out of git:

```bash theme={null}
export CHANNEL3_API_KEY="ch3_live_..."
```

## 2. Send it on every MCP request

Channel3 accepts **`x-api-key`** or **`Authorization: Bearer <key>`** on each POST to `/mcp`.

<CodeGroup>
  ```bash UCP CLI theme={null}
  # Per command — repeat --header on every catalog call
  ucp catalog search \
    --profile channel3 \
    --header "x-api-key: $CHANNEL3_API_KEY" \
    --set /query='wireless headphones' \
    --set '/pagination/limit=3' \
    --format json
  ```

  ```bash UCP CLI (persistent) theme={null}
  # ~/.ucp/profiles/channel3/headers.json
  {
    "default": {},
    "businesses": {
      "https://ucp.trychannel3.com": {
        "x-api-key": "${CHANNEL3_API_KEY}"
      }
    }
  }

  # Then export CHANNEL3_API_KEY in your shell; all catalog commands use Token tier.
  ucp catalog search \
    --set /query='wireless headphones' \
    --set '/pagination/limit=3' \
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
            "query": "wireless headphones",
            "pagination": { "limit": 3 }
          }
        }
      }
    }'
  ```
</CodeGroup>

<Note>
  The UCP CLI has no separate `--api-key` flag. Use **`--header`** per call or
  **`headers.json`** on the profile ([Shopify ucp-cli
  docs](https://github.com/Shopify/ucp-cli#custom-request-headers-auth-tenancy-tracing)).
  Values support `${ENV_VAR}` interpolation so secrets stay out of the file.
</Note>

## 3. Request placement commission data (optional)

With a Token-tier key, add **`catalog.placements: ["affiliate"]`** to receive
`variants[].placement` commission data. See [Extension
reference](/ucp/catalog-global-extension#catalogplacements-opt-in).

```bash theme={null}
ucp catalog search \
  --header "x-api-key: $CHANNEL3_API_KEY" \
  --set /query='running shoes' \
  --set '/placements=["affiliate"]' \
  --format json
```

## 4. Check that it worked

Response headers:

```
x-ucp-auth-tier: token
```

In **`structuredContent`** (curl) or **`result`** (CLI), your buy links should be monetized to your account. Compare with the same search without a key (no monetization).

Bad or missing keys fall back to anonymous limits (no 401):

```
x-ucp-auth-tier: anonymous
```

## What's next

<CardGroup cols={2}>
  <Card title="Rate limits" icon="gauge" href="/ucp/auth-and-rate-limiting">
    Anonymous vs Token
  </Card>

  <Card title="Search" icon="search" href="/ucp/search-catalog">
    Run a search with your key
  </Card>
</CardGroup>
