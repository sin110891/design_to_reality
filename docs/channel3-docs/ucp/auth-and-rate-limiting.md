> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Auth and rate limiting

> How identification affects rate limits on the UCP catalog

How you identify yourself sets your **rate limit** and whether **`variants[].url`** buy links credit your vendor account. Both tiers can use `search_catalog`, `lookup_catalog`, and `get_product`.

## The two tiers

| Tier          | How you qualify                                                    | Typical limit (per minute) | Monetization                        |
| ------------- | ------------------------------------------------------------------ | -------------------------- | ----------------------------------- |
| **Token**     | Valid Channel3 API key in `x-api-key` (or `Authorization: Bearer`) | 1000                       | Yes — buy links credit your account |
| **Anonymous** | No key, invalid key, or CLI without `--header`                     | 30                         | No monetization                     |

Limits can change. Check the response header **`x-ucp-auth-tier`** (`token` or `anonymous`).

## Which should I use?

**Token (API key)** — use this for production traffic and monetized buy links. Create a key in the [dashboard](/ucp/authentication) and send it on every MCP POST via **`--header`**, profile **`headers.json`**, **curl**, or your MCP client.

**Anonymous** — fine for quick tests and the [quickstart](/ucp/quickstart) without a key. Too low for real traffic; no monetization.

A bad API key does not return 401. You get anonymous limits instead.

## Good to know

* **Edge limits too.** Cloudflare also rate-limits by IP on claimed headers. The origin enforces the verified tier so a fake `x-api-key` cannot borrow token limits.
* **Auth is on HTTP headers**, not in `meta`. See [About profiles](/ucp/about-profiles#what-is-meta).

## Token (API key)

Send `x-api-key: ...` on every MCP POST.

[Step-by-step setup](/ucp/authentication)

## Anonymous (no auth)

Omit the API key header.

[Quickstart](/ucp/quickstart)

## What's next

<CardGroup cols={2}>
  <Card title="Quickstart" icon="rocket" href="/ucp/quickstart">
    Try it with no key
  </Card>

  <Card title="Add an API key" icon="key" href="/ucp/authentication">
    Move to Token tier
  </Card>
</CardGroup>
