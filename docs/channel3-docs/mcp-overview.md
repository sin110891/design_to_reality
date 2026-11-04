> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# MCP

> Add the Channel3 MCP to your agent

## What is the Channel3 MCP?

The Channel3 MCP gives your AI agents superpowers for product discovery. Your agent can search through tens of millions of real products in real-time, complete with current prices, rich images, detailed descriptions, and real-time availability.

## Quick Start (Free Tier)

No API key required. Connect directly and start searching:

```
https://mcp.trychannel3.com/
```

## Unlimited Access

The Channel3 MCP has a generous free tier. For pay-as-you-go usage, create an account and add your API key.

1. [Create an account](https://trychannel3.com) and generate an API key.
2. Append `?apiKey=<your-api-key>` to the MCP URL:

```
https://mcp.trychannel3.com/?apiKey=<your-api-key>
```

## Setup

export const PreviewButton = ({children, href}) => {
  return <a href={href} className="text-sm font-medium text-white dark:!text-zinc-950 bg-zinc-900 hover:bg-zinc-700 dark:bg-zinc-100 hover:dark:bg-zinc-300 rounded-full px-3.5 py-1.5 not-prose">
      {children}
    </a>;
};

<Tabs>
  <Tab title="Cursor">
    <PreviewButton href="cursor://anysphere.cursor-deeplink/mcp/install?name=Channel3&config=eyJ1cmwiOiJodHRwczovL21jcC50cnljaGFubmVsMy5jb20vIn0=">Install in Cursor</PreviewButton>

    Or manually add to `~/.cursor/mcp.json`:

    ```json theme={null}
    {
      "mcpServers": {
        "Channel3": {
          "url": "https://mcp.trychannel3.com/"
        }
      }
    }
    ```
  </Tab>

  <Tab title="VS Code">
    <PreviewButton href="https://vscode.dev/redirect/mcp/install?name=Channel3&config=%7B%22type%22%3A%22http%22%2C%22url%22%3A%22https%3A//mcp.trychannel3.com/%22%7D">Install in VS Code</PreviewButton>

    Or manually add to `.vscode/mcp.json`:

    ```json theme={null}
    {
      "servers": {
        "Channel3": {
          "type": "http",
          "url": "https://mcp.trychannel3.com/"
        }
      }
    }
    ```
  </Tab>

  <Tab title="Claude Code">
    ```bash theme={null}
    claude mcp add --transport http Channel3 "https://mcp.trychannel3.com/"
    ```
  </Tab>

  <Tab title="Claude Desktop">
    Add to your Claude Desktop config file:

    **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
    **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

    ```json theme={null}
    {
      "mcpServers": {
        "Channel3": {
          "command": "npx",
          "args": ["-y", "mcp-remote", "https://mcp.trychannel3.com/sse"]
        }
      }
    }
    ```
  </Tab>

  <Tab title="Codex">
    ```bash theme={null}
    codex mcp add Channel3 --url https://mcp.trychannel3.com/
    ```
  </Tab>

  <Tab title="OpenCode">
    ```json theme={null}
    {
      "mcp": {
        "Channel3": {
          "type": "remote",
          "url": "https://mcp.trychannel3.com/",
          "enabled": true
        }
      }
    }
    ```
  </Tab>
</Tabs>

That's it! Your agent can now find any product online.
