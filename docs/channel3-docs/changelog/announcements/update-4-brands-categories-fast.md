> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Brands, Categories, and Search Goes Fast

> Overhauled Brand and Category endpoints, plus sub-second P50 search

*May 16, 2026 · API Update #4*

Hey Developer,

**We've overhauled our Brand and Category endpoints** to make it as easy as possible to search, refine, and repeat across this metadata.

Our goal here at Channel3 is to help you power a shopping experience that surfaces the perfect product for your user. One key component in filtering keyword/semantic matches that don't match the user's intent is robust brand and category filtering. If you can constrain your search space to a set of products a user would be happy picking between, your odds of converting increase significantly.

Category endpoints feature slug support, so you don't need to do a pesky category ID lookup. Internally, we ran migrations over all >100M products to both rebrand and recategorize them. More info below, and check out our [docs](https://docs.trychannel3.com/sdk) for a recommended workflow for an agent to best utilize these endpoints.

You might think, with all of these additions to our API, that we might tank our search performance. Well, our second announcement today is that our endpoint timings are in, and after long days of infra grinding, we're excited to announce **sub-second P50 timing on /v1/search**. In our experimentation, this is definitely fast enough for agents to multiplex or chain requests while still blowing traditional product search workflows out of the water.

## Categories

Our **Categories module** has 3 endpoints: `/v1/categories/search`, `/v1/categories`, and `/v1/categories/{slug}`. On our SDK, these are `client.categories.search`, `client.categories.list`, and `client.categories.retrieve`. Additionally, every `Product` returned [on our API has a list of `categories`](https://docs.trychannel3.com/api-reference/v1/search) (in practice, this is 1 category), which can be used for category narrowing.

Categories are structured in a category tree, which you can [view in its entirety on our docs](https://docs.trychannel3.com/categories). The [`CategoryDetail` returned on our API](https://docs.trychannel3.com/api-reference/v1/category-detail) includes `CategoryRefs` that are sufficient for programmatically traversing the category tree to aid in your development or to provide end users with robust filters. The `CategoryDetail` also returns an [`attributes` field](https://docs.trychannel3.com/api-reference/v1/category-detail), which is a map of structured attributes, such as color, size, and material. It'd be pretty cool to filter deterministically on those attributes… more to come on that 👀.

For agents, our [Channel3 product-discovery skill](https://github.com/channel3-ai/skills) already has explicit instructions to refine queries with relevant category searches. If you're building your own agentic harness, we recommend doing the same.

**Why?** Categories are most important for filtering out semantic or keyword search noise. For example, if you search "canoe" on our API, you'll get some good canoeing options, but you might just as well get a landscape photo of a canoe. Internally, we do attempt to filter down to correct categories based on query intent. But if you're building a clothing shopping app, there's no reason not to constrain your outputs to categories you actually care about.

## Brands

Our **Brands module** mirrors the shape of the Categories module: `/v1/brands/search`, `/v1/brands` for listing, and `/v1/brands/{brand_id}` for getting a brand detail. On the SDK, these are `client.brands.search`, `client.brands.list`, and `client.brands.retrieve`.

`/v1/brands/search` is a simple keyword lookup by brand name, so you can map "nike" to its brand ID `MpZs` for use in `SearchFilters`.

`/v1/brands` lists our relevant brands, which you can page through, so you can programmatically inspect our brand catalog. These are sorted by our internal brand scores, so if you use this in production, you'll only display relevant brands to users. In the future, we'll support filtering down this list, so you can programmatically curate a brand list for your users.

All of these endpoints return the same `Brand` object, which includes a name, logo, and best commission rate.

**Why?** If categories are useful for refining individual queries, curating a brand list for your platform ensures a high floor of product discovery. We strive to provide as many tools as possible for you to impose your taste and curate your shopping experience. Brands are an essential step in this process.

## Performance

We benchmarked our `/v1/search` endpoint and are excited to announce a **sub-second P50 search time**. I won't bore you with all of the internals of our search, but in the span of (less than) a second, we: use language models, sanitize and understand your query, search (both keyword and semantic) our corpus of >100M products, and rerank these keyword and semantic results into one, pageable batch.

Lightning-fast search has obvious benefits. The engagement falloff when a page takes a few or several seconds to load is real. However, we're most excited about making search as fast as possible so we can power the optimal **agentic search experience**.

We built a simple agentic product search harness internally to compare how multiplexed queries (>1 `/v1/search` calls in a single agent call turn) compared to Gemini and ChatGPT. Building out this harness was less than a day of work. The results speak for themselves. Gemini is quick, admittedly, but it inundates you with 10 or more results. In the time it takes ChatGPT to spit back a single, verbose response, you can do multiple round trips with Channel3.

<Frame caption="Response time: a multiplexed Channel3 agent harness vs. Gemini and ChatGPT shopping.">
  <img src="https://mintcdn.com/channel3/oRJ2GuCXjnj_w_5r/public/changelog/update4-response-time-chart.png?fit=max&auto=format&n=oRJ2GuCXjnj_w_5r&q=85&s=6208634d4fed32239d797ba949889c44" alt="A bar chart comparing product recommendation response times across Channel3, Gemini, and ChatGPT" width="2110" height="1035" data-path="public/changelog/update4-response-time-chart.png" />
</Frame>

The difference between waiting 4.5 seconds and 12 seconds for a product recommendation is the difference between converting a sale and churning a user to a traditional shopping experience. Every week, we're adding more tools for you to refine your shopping experience and help surface the perfect products.

Want to build something, but we don't support your use-case? Drop a request in the [Discord](https://discord.gg/6J6MjctXrH) or hit reply and let us know.

And, as always, we love to hear what you're building!

The Channel3 Team
