> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Product Discovery Skill

> Let an existing agent search products, compare prices, and check availability on demand

The product discovery skill is for an existing agent, workflow, or harness that needs to search products, compare prices, or check availability directly during a conversation. It is not for integrating Channel3 APIs into a service — use the [Channel3 API skill](/skills/channel3-api) or [MCP server](/mcp-overview) for that.

## Install

```bash theme={null}
npx skills add channel3-ai/skills --skill product-discovery
```

## Use it

Once installed, your agent can search the Channel3 catalog on demand. Try a prompt like:

```text theme={null}
Use the product discovery skill to find running shoes under $150 and compare the top options.
```

## Source

<Card title="channel3-ai/skills" icon="github" href="https://github.com/channel3-ai/skills" arrow="true">
  View the skill source, open issues, or contribute on GitHub.
</Card>
