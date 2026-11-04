> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# About profiles

> The JSON file that tells agents what the catalog server supports

A **profile** is a small JSON file at a fixed URL. Agents read it to learn which UCP features a server supports.

## Channel3's profile

```
GET https://ucp.trychannel3.com/.well-known/ucp
```

Fetch this once when your agent starts (or cache it for a few hours). It advertises catalog search and lookup, the MCP URL, and the `com.trychannel3.catalog.global` extension.

## Do you need your own profile?

**No.** In full UCP, a merchant might host a profile for cart, checkout, and orders. Channel3's catalog is search and lookup only — you consume Channel3's profile; you don't publish one.

**Auth is separate.** Identifying yourself to Channel3 uses an optional API key in HTTP headers, not a profile file. See [Authentication](/ucp/authentication) and [Rate limits](/ucp/auth-and-rate-limiting).

## What is `meta`?

UCP tool calls look like `{ "meta": ..., "catalog": ... }`. Put your query in **`catalog`** (`query`, `ids`, `urls`, filters, pagination).

**`meta`** is for capability negotiation in the UCP spec. On **`ucp.trychannel3.com`** today, catalog tools ignore it — pass **`"meta": null`** in curl. Auth uses HTTP headers (`x-api-key`), not `meta`.

## What's next

<CardGroup cols={2}>
  <Card title="API key" icon="key" href="/ucp/authentication">
    Token tier setup
  </Card>

  <Card title="Rate limits" icon="shield" href="/ucp/auth-and-rate-limiting">
    Anonymous vs Token
  </Card>
</CardGroup>
