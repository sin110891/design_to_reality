> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Agentic Search

> Let an LLM decompose complex, multi-constraint queries into structured sub-searches for higher-quality results.

Set `config.mode: "agentic"` on [`POST /v1/search`](/api-reference/v1/search) when queries read like a person describing what they want rather than a keyword phrase. An LLM decomposes the query into a structured plan — brands, retailers, category, gender, age, condition, price range, colors, and product attributes — then runs multiple structured sub-searches and merges them into one ranked result list.

<CodeGroup>
  ```typescript TypeScript theme={null}
  import Channel3 from "@channel3/sdk";

  const client = new Channel3(); // reads CHANNEL3_API_KEY from env

  const results = await client.products.search({
    query: "waterproof trail running shoes for wide feet under $120",
    config: { mode: "agentic" },
  });
  ```

  ```python Python theme={null}
  from channel3_sdk import Channel3

  client = Channel3()  # reads CHANNEL3_API_KEY from env

  results = client.products.search(
      query="waterproof trail running shoes for wide feet under $120",
      config={"mode": "agentic"},
  )
  ```

  ```bash cURL theme={null}
  curl -X POST https://api.trychannel3.com/v1/search \
    -H "x-api-key: $CHANNEL3_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"query": "waterproof trail running shoes for wide feet under $120", "config": {"mode": "agentic"}}'
  ```
</CodeGroup>

## Default vs. agentic

Default search already does some entity extraction on your query. Agentic search goes much further:

* **Rich filter extraction** — extracts constraints across all `SearchFilters`: price, brands, websites, gender, age, condition, availability, colors, and category.
* **Multiple queries** — plans and runs several searches, then intelligently picks the quality results from across them.
* **Structured attribute enrichment** — parses implied categories and features out of the query and deterministically filters products down to only those that match the attributes.

## Everything else works the same

The request and response shapes are identical to `default` mode. Explicit `filters` are combined with what the planner extracts, and pagination via `next_page_token` works as usual.

<Cards>
  <Card title="Search" icon="magnifying-glass" href="/guides/search" arrow="true">
    Text search, filters, pagination, and the other search modes.
  </Card>

  <Card title="Attribute Search" icon="sliders" href="/guides/advanced-search" arrow="true">
    Build structured attribute filters yourself for full control.
  </Card>
</Cards>
