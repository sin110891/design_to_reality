> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Announcing the /v1 Search API & SDK 3.0.0

> Our new v1 Product Search API, with pagination, offers, collaborations, and smart images

*March 12, 2026 · API Update #1*

Hello Developer!

Today, we're excited to announce Channel3's V1 Product Search API. We've learned a lot about how users and agents want to interact with product data in the last year of building a universal product catalog. We believe this new endpoint is a cleaner design that will help you curate a richer shopping experience and better empower agents to find the perfect product.

Our **new Search API endpoint lives at `/v1/search`**. Check out [the docs here](https://docs.trychannel3.com/api-reference/v1/search) and **upgrade to SDK version 3.0.0** to try it out today! Scroll to the bottom for migration instructions to handle the breaking changes that come with this major version bump.

We'll keep `/v0/search` and `/v0/products` around for a few more weeks, but on Monday, April 13th they'll be officially removed.

## What we added

**Search pagination**

We updated search to return a richer `SearchResponse`, and we now return a `paging_token`. You can page search results up to 500 products, allowing you to build infinite scroll.

**Product offers**

Many products are sold by multiple retailers. We now show "offers" for every product, so you can decide where to send your users — the lowest-price, the highest commission, or the best-known retailer.

**Collaborations**

With our improved `brands` field, our products can now represent collaborations and multiple brands, like "MLB" and "Yankees."

**Smart images**

We look at every image with AI to give you more control over the product you display. Building a scrollable grid? Display `hero` images. Want a cozier, mood board feel? Try showing `lifestyle` images. Hate those annoying sizing charts that ruin the aesthetic of your image carousel? Filter out `size_chart`. Experimenting with virtual try-on? We built `on_model` exactly for this.

## What we removed (breaking changes) + migration instructions

Spring is here in NYC, and we've done some spring cleaning on our API.

On the `SearchRequest`, we've pared down our `SearchConfig` and `SearchFilters`. These fields had been deprecated and had no impact on search results. If you have any dangling references to deprecated fields, you'll have to remove them when you upgrade to 3.0.0.

We've upgraded our search response from a `list[Product]` to a more expressive `SearchResponse`, which includes the `list[Product]` and a `paging_token`. We also cleaned up deprecated fields off of `Product`, so you have more control over the price, availability, brand, image, and product listings you display.

**2-step migration instructions** (alternatively, paste this entire update into Claude Code / Cursor and let it cook):

1. Upgrade your Channel3 [Python or TypeScript SDK](https://docs.trychannel3.com/sdk) to version 3.0.0.
   * If you are using our API directly, point your new search to `/v1/search` and load product details from `/v1/products/`.
2. Audit any usages of the [`/search`](https://docs.trychannel3.com/api-reference/v1/search) endpoint and `Product` models in your app.
   * Update usages of `/search` to expect a `SearchResponse`.
   * Ensure you do not use any deprecated `/search` `SearchRequest` or `Product` response fields:
     * **Request:** `SearchFilters.exclude_product_ids`, `SearchConfig.redirect_mode`
     * **Response:** `Product.url`, `Product.price`, `Product.availability` (we now return *all* offers for this product, deduplicated across merchants — you or your users can choose the best price, whether that's the cheapest offer or the one that earns you the highest commission); `Product.image_url`, `Product.image_urls` (we use multimodal AI to understand every product image, so you can better curate your shopping experience); `Product.brand_id`, `Product.brand_name` (replaced with `Product.brands`, to support collaborations).
3. That's it! Ship it!

Want to build something, but we don't support your use-case? Hit reply and let us know.

And, as always, we love to hear what you're building!

George
