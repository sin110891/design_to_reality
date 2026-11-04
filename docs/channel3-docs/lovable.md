> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Lovable

> Build and ship a real shopping app on Lovable in six steps — describe it in prompts, connect Channel3, publish, and start earning. Worked example: KitDen.

[Lovable](https://lovable.dev) builds your app from plain prompts — you describe it, it ships it. Adding Channel3 takes a handful of prompts: real product search, drop-in shopping UI, and automatic monetization, with no SDK wrestling.

This guide builds one end to end, using **KitDen** — an AI room-kit builder ([see it live](https://kitden.lovable.app)) — as the example.

<Frame caption="KitDen's home — describe a vibe, set a budget, and Kit builds a shoppable kit.">
  <img src="https://mintcdn.com/channel3/S0p1cTKgE-dwslW8/public/integrations/lovable/lovable-hero.png?fit=max&auto=format&n=S0p1cTKgE-dwslW8&q=85&s=f722b453e68a9df4442d57abd802a19c" alt="KitDen home page titled Vibeshop your dorm, with a vibe text box, vibe starter chips, and budget options" width="2940" height="1594" data-path="public/integrations/lovable/lovable-hero.png" />
</Frame>

## What you can build

Any of these is a weekend on Lovable. KitDen is the worked example below; the same six steps build the rest.

<CardGroup cols={2}>
  <Card title="Aesthetic room-kit builder" icon="house">
    Vibe + budget → a complete, buyable room. (This is KitDen.)
  </Card>

  <Card title="Gift finder" icon="gift">
    Occasion + recipient + budget → curated, buyable gift picks.
  </Card>

  <Card title="Capsule wardrobe stylist" icon="shirt">
    A few inputs → a cohesive, shoppable outfit set.
  </Card>

  <Card title="Shop-this-photo" icon="image" href="/api-reference/v1/image-search">
    Paste an inspiration image → similar buyable products via Image Search.
  </Card>

  <Card title="Chat concierge" icon="comments">
    A hosted shopping assistant in a chat bubble — zero code (see the optional
    step).
  </Card>
</CardGroup>

## Build a shopping app in 6 steps

From zero to a live, earning app. Every step is a prompt.

<Steps>
  <Step title="Get set up">
    Create a free [Channel3 account](https://trychannel3.com/sign-up) and copy your key from the [API keys page](https://trychannel3.com/dashboard/api) — you'll paste it once, in step 3. Then start a new project at [lovable.dev](https://lovable.dev).

    <Frame caption="Your Channel3 API key — it authenticates requests and attributes your sales.">
      <img src="https://mintcdn.com/channel3/S0p1cTKgE-dwslW8/public/integrations/lovable/lovable-dashboard-apikey.png?fit=max&auto=format&n=S0p1cTKgE-dwslW8&q=85&s=cc063a7c43d0c2371c91bc23c89e4c89" alt="Channel3 dashboard API Key page showing a masked key" width="2464" height="1160" data-path="public/integrations/lovable/lovable-dashboard-apikey.png" />
    </Frame>
  </Step>

  <Step title="Scaffold the app">
    Describe the whole flow once, with placeholder data, so you can see the shape before wiring anything real.

    ```text theme={null}
    Build a web app called KitDen. Home screen: a text box to describe an aesthetic, budget presets ($150 / $300 / $500 + custom), and a "Build my kit" button that leads to a results page of product cards grouped by category (Bedding, Lighting, Wall Decor, Storage, Rug, Desk) — each with image, title, merchant, price, Buy, and Swap, plus a running total vs. budget. Mobile-first. Use placeholder data for now.
    ```

    <Frame caption="One prompt scaffolds the home and results flow.">
      <img src="https://mintcdn.com/channel3/S0p1cTKgE-dwslW8/public/integrations/lovable/lovable-scaffold.png?fit=max&auto=format&n=S0p1cTKgE-dwslW8&q=85&s=a5c807f3d9d2463cec34927889220046" alt="Lovable showing the KitDen scaffold prompt and the generated results page with a budget bar" width="2368" height="1356" data-path="public/integrations/lovable/lovable-scaffold.png" />
    </Frame>
  </Step>

  <Step title="Connect Channel3 and show real products">
    Lovable Cloud (the built-in backend) is on by default — no separate Supabase signup. Prompt Lovable to add a search function that calls Channel3; when it asks for your key, paste it into the secret dialog. The key lives server-side and never reaches the browser.

    ```text theme={null}
    Add a backend function called channel3-search that takes { query, filters, limit }, POSTs to https://api.trychannel3.com/v1/search with the header x-api-key set to a secret named CHANNEL3_API_KEY, and returns the JSON with CORS enabled. Then wire the results page to render real products — the price is offers[0].price.price and the Buy link is offers[0].url. Only search when the user submits, never on keystroke.
    ```

    <Frame caption="Lovable asks for the key once, in a secure dialog — paste it and submit.">
      <img src="https://mintcdn.com/channel3/S0p1cTKgE-dwslW8/public/integrations/lovable/lovable-supabase-secret.png?fit=max&auto=format&n=S0p1cTKgE-dwslW8&q=85&s=bc7f8d2449855c4ca5e204781e2c2874" alt="Lovable secret dialog asking for CHANNEL3_API_KEY while it sets up the channel3-search function" width="2396" height="1362" data-path="public/integrations/lovable/lovable-supabase-secret.png" />
    </Frame>

    <Frame caption="Real Channel3 products, live on the results page.">
      <img src="https://mintcdn.com/channel3/sS125MKuTneSQ35T/public/integrations/lovable/lovable-search-live.png?fit=max&auto=format&n=sS125MKuTneSQ35T&q=85&s=0d90511268d53ce496e3082a193a327e" alt="Lovable confirming the channel3-search function proxies to Channel3 and the results page now fetches real products" width="2940" height="1664" data-path="public/integrations/lovable/lovable-search-live.png" />
    </Frame>
  </Step>

  <Step title="Curate with AI">
    A search returns a flat list; a kit is one cohesive pick per category, under budget. Lovable's built-in AI handles that — no API key, runs server-side.

    ```text theme={null}
    Add curation with Lovable's built-in AI (no API key, server-side). From the aesthetic, have the AI plan a Channel3 search per category, call channel3-search per query, then pick the best item per category within budget with a one-line reason for each. Show the reasons under each card and a short overall summary.
    ```

    <Frame caption="A named, budget-capped kit — chosen and explained by AI.">
      <img src="https://mintcdn.com/channel3/S0p1cTKgE-dwslW8/public/integrations/lovable/lovable-tier1-results.png?fit=max&auto=format&n=S0p1cTKgE-dwslW8&q=85&s=52ab500a86d5272165d741df38f21550" alt="KitDen results page showing a named coastal kit with product cards, a budget summary, and per-item rationale" width="2940" height="1670" data-path="public/integrations/lovable/lovable-tier1-results.png" />
    </Frame>

    <Note>
      Catalog images and titles aren't always perfect (an occasional retail-box shot or generic title). Spot-check picks before you ship, and use Swap to drop in a cleaner match.
    </Note>
  </Step>

  <Step title="Add full product pages">
    Don't hand-build the hard surfaces — Channel3's components install **by prompt** (Lovable reads the registry URL from your message). The `product-details` block already includes the image gallery, every offer, variants, **price history, and recommendations** — you just feed it the data.

    ```text theme={null}
    Add the Channel3 UI components from their shadcn registry at https://ui.trychannel3.com/r/all.json, then build a product detail modal with the product-details block. When I tap a kit item, fetch its detail server-side — add product-detail, price-history, and similar-products actions to channel3-search — and pass the data in as props so the gallery, every offer, price history, and recommendations all render. The components are presentational and never see the key. Buy links to offers[0].url.
    ```

    <Frame caption="The Channel3 components install from one prompt — no terminal.">
      <img src="https://mintcdn.com/channel3/S0p1cTKgE-dwslW8/public/integrations/lovable/lovable-tier2-install.png?fit=max&auto=format&n=S0p1cTKgE-dwslW8&q=85&s=f249d887b796c280905a44023d97f25c" alt="Lovable chat showing the Channel3 shadcn registry install prompt and the resulting product detail dialog" width="2934" height="1658" data-path="public/integrations/lovable/lovable-tier2-install.png" />
    </Frame>

    <Frame caption="A full product page: every offer, price intelligence, similar products, and a one-tap buy.">
      <img src="https://mintcdn.com/channel3/S0p1cTKgE-dwslW8/public/integrations/lovable/lovable-tier2-pdp.png?fit=max&auto=format&n=S0p1cTKgE-dwslW8&q=85&s=0b8e1a366888145d16a05b4814038626" alt="Channel3 product detail modal with merchant offers, best price, and a similar products row" width="2938" height="1664" data-path="public/integrations/lovable/lovable-tier2-pdp.png" />
    </Frame>
  </Step>

  <Step title="Publish and start earning">
    Hit **Publish** (top right), pick a URL, and your app is live. Monetization was automatic the whole time: because search ran with your API key, every `offers[0].url` is an attributed link — you earn when shoppers click through to buy. Nothing to add.

    ```text theme={null}
    No prompt needed — click Publish, choose your URL, and go live.
    ```

    <Frame caption="Publish gives your app a live URL in a couple of clicks.">
      <img src="https://mintcdn.com/channel3/S0p1cTKgE-dwslW8/public/integrations/lovable/lovable-publish-url.png?fit=max&auto=format&n=S0p1cTKgE-dwslW8&q=85&s=44615905f6270373c6c7b701edf148ef" alt="Lovable Publish dialog showing the live website URL" width="1756" height="1352" data-path="public/integrations/lovable/lovable-publish-url.png" />
    </Frame>

    <Frame caption="Track clicks and earnings in the Channel3 dashboard — no analytics code.">
      <img src="https://mintcdn.com/channel3/S0p1cTKgE-dwslW8/public/integrations/lovable/lovable-clicks.png?fit=max&auto=format&n=S0p1cTKgE-dwslW8&q=85&s=3c6f61fe70f1627bfb92c89e55a5933d" alt="Channel3 dashboard Clicks page showing a clicks-over-time graph" width="2474" height="1198" data-path="public/integrations/lovable/lovable-clicks.png" />
    </Frame>

    <Note>
      Any result with an offer where `max_commission_rate > 0` is monetizable — Channel3 has relationships with thousands of brands. Earnings clear after the retailer's return window and pay out via Stripe; complete identity verification in the dashboard so commissions aren't withheld. See [Pricing](/pricing) for the split.
    </Note>
  </Step>
</Steps>

## Build faster with the Channel3 API skill

Lovable is great for UI and scaffolding, but wiring Channel3 search, lookup, and filters is faster with a coding agent that knows the API. Install the [Channel3 API skill](/skills/channel3-api) in Cursor, Claude Code, or another terminal agent:

```bash theme={null}
npx skills add channel3-ai/skills --skill channel3-api
```

Then prompt it alongside Lovable — for example: *"Using the Channel3 API skill, add a channel3-search edge function and wire the results page to real product data."* Your terminal agent handles API integration; Lovable keeps iterating on the app.

## Optional: add a chat concierge (zero code)

Want a shopping assistant instead of (or alongside) the builder? The hosted widget handles conversation, product matching, and checkout links — you configure a persona in the dashboard and paste one iframe.

<Steps>
  <Step title="Configure the widget">
    In the dashboard's **Chat Widgets**, name it, set **Allowed origins** to your app's domain (e.g. `https://kitden.lovable.app`), and write the **Agent instructions** (its persona and rules, e.g. "only suggest dorm-safe items under budget").

    <Frame caption="Configure the hosted widget in the Channel3 dashboard.">
      <img src="https://mintcdn.com/channel3/S0p1cTKgE-dwslW8/public/integrations/lovable/lovable-widget-config.png?fit=max&auto=format&n=S0p1cTKgE-dwslW8&q=85&s=3cf848c912dafcb43a1e7e4e37223c46" alt="Channel3 Chat Widgets dashboard showing allowed origins, agent instructions, and the iframe snippet" width="2940" height="1662" data-path="public/integrations/lovable/lovable-widget-config.png" />
    </Frame>
  </Step>

  <Step title="Paste it into Lovable">
    Copy the generated iframe and drop it into the chat — no edge function, no key on the client.

    ```text theme={null}
    Add this chat widget to the site:
    <iframe src="https://trychannel3.com/widget/{id}" style="width:100%;height:700px;border:0;"></iframe>
    ```

    <Frame caption="The hosted widget returns real, buyable products from a fuzzy request.">
      <img src="https://mintcdn.com/channel3/S0p1cTKgE-dwslW8/public/integrations/lovable/lovable-widget-live.png?fit=max&auto=format&n=S0p1cTKgE-dwslW8&q=85&s=4d38e12a1ce5652ebfcfc0115fb2701a" alt="KitDen chat widget returning two on-budget product picks with an AI rationale" width="400" data-path="public/integrations/lovable/lovable-widget-live.png" />
    </Frame>
  </Step>
</Steps>

<CardGroup cols={2}>
  <Card title="Channel3 API skill" icon="sparkles" href="/skills/channel3-api" arrow="true">
    Teach your coding agent the Channel3 API for faster integration.
  </Card>

  <Card title="UI Components" icon="https://mintcdn.com/channel3/oRJ2GuCXjnj_w_5r/logo/shadcn.png?fit=max&auto=format&n=oRJ2GuCXjnj_w_5r&q=85&s=3f5820a6f3e6f5923a42543ca755650c" href="/ui" arrow="true" width="100" height="100" data-path="logo/shadcn.png">
    The React component catalog and shadcn registry.
  </Card>

  <Card title="Pricing" icon="credit-card" href="/pricing" arrow="true">
    Credits, free tier, and commission split.
  </Card>

  <Card title="Support" icon="envelope" href="mailto:support@trychannel3.com" arrow="true">
    Questions or a brand request? We're happy to help.
  </Card>
</CardGroup>

<Tip>
  Building with Cursor or Claude Code alongside Lovable? Install the Channel3
  API skill in your terminal: `npx skills add channel3-ai/skills --skill
      channel3-api`. See [Channel3 API skill](/skills/channel3-api). (Terminal
  agents only — not the Lovable chat box.)
</Tip>
