> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# CLI

> Use Channel3 from your terminal.

The Channel3 CLI lets you call any API endpoint from your terminal. Source code lives at [github.com/channel3-ai/cli](https://github.com/channel3-ai/cli).

## Installation

```sh theme={null}
brew install channel3-ai/tap/channel3
```

To upgrade to the latest version:

```sh theme={null}
brew upgrade channel3
```

## Authentication

Set your API key via environment variable, or pass it with `--api-key` on any command.

```sh theme={null}
export CHANNEL3_API_KEY="your_api_key_here"
```

You can also set `CHANNEL3_LANGUAGE`, `CHANNEL3_COUNTRY`, and `CHANNEL3_CURRENCY` to apply default locale settings to every call.

<Note>
  To set these permanently, add the `export` lines to your `~/.zshrc` (or `~/.bashrc`) and run `source ~/.zshrc` to apply them to your current shell.
</Note>

## Usage

Commands follow a resource-based structure:

```sh theme={null}
channel3 [resource] <command> [flags...]
```

For example, to search for products:

```sh theme={null}
channel3 products search --query "organic cotton t-shirt"
```

Pass `--help` to any command for full flag documentation.

### Passing files

Use the `@` prefix to send a file as an argument — useful for image search:

```sh theme={null}
channel3 products search --base64-image @shoe.jpg
```

### Output formats

Change the output format with `--format` (`json`, `jsonl`, `yaml`, `pretty`, `raw`, `explore`), or extract fields with `--transform` using [GJSON syntax](https://github.com/tidwall/gjson/blob/master/SYNTAX.md):

```sh theme={null}
channel3 products search --query "running shoes" --transform "products.#.title"
```
