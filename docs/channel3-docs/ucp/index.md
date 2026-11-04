> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# UCP catalog overview

> Search products across the web using the Universal Commerce Protocol

Channel3 runs a product catalog at **`ucp.trychannel3.com`**. It speaks [UCP](https://ucp.dev/) (Universal Commerce Protocol), so shopping agents can search and look up products without learning a custom Channel3 API.

For most agents, MCP is the simpler approach. See [MCP](/mcp-overview). Examples in this section show **UCP CLI** and **curl** side by side.

## What you can do

| Action                             | Tool name                       |
| ---------------------------------- | ------------------------------- |
| Search many stores at once         | `search_catalog`                |
| Look up by product ID or store URL | `lookup_catalog`, `get_product` |

Extra filters and store details live in the **`com.trychannel3.catalog.global`** extension. See [Extension reference](/ucp/catalog-global-extension).

## Two URLs to know

| URL                                               | What it does                                     |
| ------------------------------------------------- | ------------------------------------------------ |
| `GET https://ucp.trychannel3.com/.well-known/ucp` | Tells your agent what's available (profile JSON) |
| `POST https://ucp.trychannel3.com/mcp`            | Where you call the tools                         |

## Auth

Channel3 supports two tiers. See [Authentication](/ucp/authentication) and [Rate limits](/ucp/auth-and-rate-limiting).

| Tier          | How                                    | Good for                                   |
| ------------- | -------------------------------------- | ------------------------------------------ |
| **Anonymous** | No API key                             | Quick tests, [quickstart](/ucp/quickstart) |
| **Token**     | `x-api-key` header on each `/mcp` POST | Production traffic, monetized buy links    |

You do **not** need to host your own UCP profile to use the catalog — Channel3's profile above is enough. See [About profiles](/ucp/about-profiles).

**UCP CLI note:** Without a key, CLI commands run as **Anonymous**. Pass **`--header "x-api-key: …"`** or configure [profile `headers.json`](/ucp/authentication) for Token tier on `ucp.trychannel3.com`.

## Same data as the REST API

UCP uses the same products as `POST /v1/search`, `POST /v1/lookup`, and `GET /v1/products/{ID}`. Put the query in **`catalog`**; responses include **`products`**, **`pagination`**, and sometimes **`messages`**.

## Where to start

<Steps>
  <Step title="Quickstart">
    Install the UCP CLI and run your first search. [Quickstart](/ucp/quickstart)
  </Step>

  <Step title="Add a key (step 6)">
    Token tier for production traffic, monetizable links, and placements.
    [Authentication](/ucp/authentication) · [Rate
    limits](/ucp/auth-and-rate-limiting)
  </Step>

  <Step title="Search and lookup">
    [Search](/ucp/search-catalog) · [Lookup](/ucp/lookup-catalog) · [Get
    product](/ucp/get-product)
  </Step>
</Steps>
