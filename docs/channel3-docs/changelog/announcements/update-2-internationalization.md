> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Internationalization

> Filter by country, language, and currency — plus a new Discord and more free credits

*May 1, 2026 · API Update #2*

Hey Developer,

Channel3's API has officially gone global. Now, **you can filter by [country](https://docs.trychannel3.com/api-reference/v1/search), [language](https://docs.trychannel3.com/api-reference/v1/search), and [currency](https://docs.trychannel3.com/api-reference/v1/search) on your search requests** to only view products that fit your target audience. Many of these products are still monetizable with affiliate, and our team is hard at work partnering with more brands to get you higher commissions. (If there are any brands you'd like to see commissions for, let us know!)

Upgrade to SDK version 3.2.0 to try it out now!

Also, we're launching a [**Channel3 Discord**](https://discord.gg/6J6MjctXrH), a one-stop shop for all things Channel3 and agentic commerce: request features, report bugs, show off what you've built, or just chat with like-minded builders.

Lastly, we've updated our pricing. Now, **every developer gets 1,000 free credits *every month***, resetting on the 1st of every month. Nothing else has changed, just more free credits for everyone. [Full pricing info is available on our docs](https://docs.trychannel3.com/pricing).

## Internationalization FAQ

**Are these products monetizable?**

Yes, many of these products will be monetizable and tracked with monetizable links. We've made deals with thousands of brands over the last few months, and we're adding new brands every day.

**Which locales are available?**

We're starting with the markets where we've seen the highest demand from developers: Europe, the UK, Canada, and Australia. You can view a full list of our [supported locales in our docs](https://docs.trychannel3.com/api-reference/v1/search).

If you want us to expand to a market where we haven't yet, ask in the Discord (or reply to this email)!

**Do you have every product from every locale now?**

Not yet, but we hope our coverage is sufficient to replace your current product data solution. If there are gaps that are keeping your app/agent from being a truly great personal shopper, ask in the Discord! These markets are foreign to us (pun intended), and we'd appreciate any help in filling in gaps.

**How do I add this to my app?**

Locales can be provided in `SearchConfig` on every `/search` request, or you can instantiate your `Channel3` client with a specific locale when using your [preferred SDK](https://docs.trychannel3.com/sdk).

The fastest way to get this set up is to install our Channel3 skills and ask your preferred coding agent to add support for your desired locale! Just run:

```bash theme={null}
npx skills add channel3-ai/skills --skill channel3-api
```

And copy this into your coding assistant:

```
Use the channel3-ai Skill to only search for products from the UK
```

## Discord

We love the feedback, updates, and requests we've gotten in our inboxes. Instead of having these great ideas sequestered to our inboxes, we want to open up a forum for you all to share what you've built, talk through what you want to build, and socialize amongst other agentic-commerce builders!

[Join the Discord at this link.](https://discord.gg/6J6MjctXrH) We have a few channels to start:

* **#support** — something broken or misbehaving? Send a message in here!
* **#showcase** — show off what you've built. Demo, ideate, offer feedback; get inspiration and beta testers.
* **#community** — are your friends tired of you bringing up agentic commerce in conversation? Come hang out in #community!
* **#feature-requests** — feeling like your app or agent is *almost* perfect, if *only* Channel3 could do X… send that here! Maybe it's on our radar, maybe it's way too hard, maybe we'll have something up by the end of the day 👀
* **#tips-and-help-forum** — as we see clever ways to build with Channel3 or common pitfalls, we'll broadcast them here.

Want to build something, but we don't support your use-case? Drop a request in the Discord or hit reply and let us know.

And, as always, we love to hear what you're building!

George
