> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Quickstart

> Build AI shopping apps and agents with the Channel3 API.

Developers use the Channel3 API to build AI shopping apps and agents — recommendation engines, visual search, autonomous purchasing agents, and more. Channel3 gives you a access to hundreds of millions of products with prices, availability, structured attributes, and commissions.

<Note>
  Channel3 supports locale-aware search for physical products, starting with the
  U.S. and expanding across select international markets. Coverage outside the
  U.S. may be limited at first. Please{" "}
  <a href="mailto:support@trychannel3.com">contact us</a> if you're looking for
  a specific geography.
</Note>

## Get started in minutes

Already using Claude Code, Cursor, Codex, or another AI coding agent? Install the Channel3 API skill and let your agent handle the integration for you.

**Step 1 — Install the Channel3 API skill:**

```bash theme={null}
npx skills add channel3-ai/skills --skill channel3-api
```

**Step 2 — Add UI components** *(React + shadcn only; skip if you're not building a UI):*

```bash theme={null}
npx shadcn@latest add https://ui.trychannel3.com/r/all.json
```

**Step 3 — Prompt your agent:**

```text theme={null}
Build a shopping experience using the Channel3 skill, Channel3 SDK, and Channel3 provided UI components/hooks. Top: text and image search with filters. Show results in a grid; clicking a product opens a PDP with variant selection, similar products, and a way back to the grid.
```

Your agent now has accurate knowledge of the Channel3 API and will produce working code right away. For a simpler integration without UI components, try: `Help me integrate Channel3 into my project using the Channel3 API skill.`

***

## Detailed Setup

Prefer to set things up step by step? Follow the guide below.

<Steps>
  <Step title="Create your free Channel3 account">
    First things first, you'll need a Channel3 account. This is where you'll
    manage your API keys, track usage, and more.

    <Card title="Create your free Channel3 account" icon="user-plus" href="https://trychannel3.com/sign-up">
      Use your Google account, GitHub, or email to sign up.
    </Card>

    <Note> If you'd like to add multiple users to your organization, just shoot us an email at <a href="mailto:support@trychannel3.com">[support@trychannel3.com](mailto:support@trychannel3.com)</a></Note>
  </Step>

  <Step title="Grab your API key">
    We generated an API key for you when you made your account. Your API key identifies you to Channel3, so we can track your API usage and pay you for the sales you drive.

    <Card title="Go to API keys" icon="key" href="https://trychannel3.com/dashboard/api" />
  </Step>

  <Step title="Start Building with the API">
    Get started with Channel3 using our SDK or by calling the API directly.

    <Card title="SDK" icon="code" href="/sdk" arrow="true">
      View installation instructions, code examples, and usage patterns for TypeScript and Python.
    </Card>

    <Card title="UI + Hooks" icon="block" href="/guides/ui-and-hooks" arrow="true">
      React shopping components (search, PDP, and more) installed via the shadcn registry.
    </Card>

    <Note>
      We also offer an MCP server with a **free tier** — no API key needed. [Learn more about our MCP](/mcp-overview).
    </Note>
  </Step>
</Steps>

We're excited to see what you build. For help, reach out to us at [support@trychannel3.com](mailto:support@trychannel3.com).
