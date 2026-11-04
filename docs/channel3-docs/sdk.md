> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# SDK

> Get started with the Channel3 SDKs for TypeScript and Python.

## Installation

<CodeGroup>
  ```typescript TypeScript theme={null}
  // npm
  npm install @channel3/sdk

  // yarn
  yarn add @channel3/sdk

  // pnpm
  pnpm add @channel3/sdk
  ```

  ```python Python theme={null}
  # pip
  pip install channel3-sdk

  # uv
  uv add channel3-sdk
  ```
</CodeGroup>

## Authentication

You can provide your API key using the `CHANNEL3_API_KEY` environment variable, or by passing it directly to the client.

<CodeGroup>
  ```typescript TypeScript theme={null}
  import Channel3 from "@channel3/sdk";

  // Initialize with environment variable
  const client = new Channel3();

  // Or, initialize with API key directly
  const clientWithKey = new Channel3({
    apiKey: "your_api_key_here",
  });
  ```

  ```python Python theme={null}
  from channel3_sdk import Channel3, AsyncChannel3

  # Initialize with environment variable
  client = Channel3()

  # Or, initialize with API key directly
  client_with_key = Channel3(api_key="your_api_key_here")

  # Async client
  async_client = AsyncChannel3()
  ```
</CodeGroup>

## Default locale

Set a default locale once on the client and it'll apply to every search and product detail call. Per-call values (e.g. `config.country` on search, `?country=` on product detail) override the client default.

<CodeGroup>
  ```typescript TypeScript theme={null}
  import Channel3 from "@channel3/sdk";

  const client = new Channel3({
    country: "GB",
    currency: "GBP",
  });

  // Uses GB / GBP
  await client.products.search({ query: "raincoat" });

  // Override per-call (returns DE / EUR offers regardless of the client default)
  await client.products.search({
    query: "raincoat",
    config: { country: "DE", currency: "EUR" },
  });
  ```

  ```python Python theme={null}
  from channel3_sdk import Channel3

  client = Channel3(country="GB", currency="GBP")

  client.products.search(query="raincoat")

  client.products.search(
      query="raincoat",
      config={"country": "DE", "currency": "EUR"},
  )
  ```
</CodeGroup>

You can also set defaults via environment variables: `CHANNEL3_LANGUAGE`, `CHANNEL3_COUNTRY`, `CHANNEL3_CURRENCY`. The same pattern applies to dimension units — set `lengthUnit` / `weightUnit` on the client (or `CHANNEL3_LENGTH_UNIT` / `CHANNEL3_WEIGHT_UNIT`) to choose the units dimensions come back in. See [Dimension units](/guides/localization#dimension-units).

<Note>
  When only `country` is set, the server infers `currency` (e.g. `GB` → `GBP`) and `language` (e.g. `GB` → `en`). When all three are unset, defaults to `en` / `US` / `USD`.
</Note>

## Usage

All top-level endpoints are available as properties on the client. For example, to use the `search` endpoint:

<CodeGroup>
  ```typescript TypeScript theme={null}
  import Channel3 from "@channel3/sdk";

  const client = new Channel3();

  async function main() {
    const response = await client.products.search({
      query: "organic cotton t-shirt",
    });

    console.log(response);
  }

  main();
  ```

  ```python Python theme={null}
  from channel3_sdk import Channel3

  client = Channel3()

  def main():
      response = client.products.search(
          query="organic cotton t-shirt"
      )
      print(response)

  if __name__ == "__main__":
      main()
  ```
</CodeGroup>

## Async usage

<CodeGroup>
  ```typescript TypeScript theme={null}
  import Channel3 from "@channel3/sdk";

  const client = new Channel3();

  async function main() {
    const response = await client.products.search({
      query: "organic cotton t-shirt",
    });
    console.log(response);
  }

  main();
  ```

  ```python Python theme={null}
  import asyncio
  from channel3_sdk import AsyncChannel3

  client = AsyncChannel3()

  async def main():
      response = await client.products.search(
          query="organic cotton t-shirt"
      )
      print(response)

  if __name__ == "__main__":
      asyncio.run(main())
  ```
</CodeGroup>

<Card title="Advanced SDK usage" icon="code" href="/sdk-advanced" arrow="true">
  Filters, pagination, image search, product detail, brands, categories, and error handling.
</Card>
