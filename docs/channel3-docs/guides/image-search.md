> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Image Search

> Visual product discovery by image URL or base64 upload.

Channel3 supports visual search by image URL or base64 upload.

## Search by image URL

Pass any publicly accessible image URL to find visually matching products.

<CodeGroup>
  ```typescript TypeScript theme={null}
  import Channel3 from "@channel3/sdk";

  const client = new Channel3();

  const results = await client.products.search({
    image_url: "https://example.com/images/blue-couch.jpg",
  });

  console.log(results.products[0].title);
  ```

  ```python Python theme={null}
  from channel3_sdk import Channel3

  client = Channel3()

  results = client.products.search(
      image_url="https://example.com/images/blue-couch.jpg",
  )
  print(results.products[0].title)
  ```

  ```bash cURL theme={null}
  curl -X POST https://api.trychannel3.com/v1/image-search \
    -H "x-api-key: $CHANNEL3_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"image_url": "https://example.com/images/blue-couch.jpg"}'
  ```
</CodeGroup>

## Search by base64 image

Upload an image directly as a base64 string — no public URL required. Great for in-app camera flows or screenshots.

<CodeGroup>
  ```typescript TypeScript theme={null}
  import fs from "node:fs";
  import Channel3 from "@channel3/sdk";

  const client = new Channel3();

  const b64 = fs.readFileSync("shoe.jpg").toString("base64");
  const results = await client.products.search({ base64_image: b64 });

  console.log(results.products[0].title);
  ```

  ```python Python theme={null}
  import base64
  from channel3_sdk import Channel3

  client = Channel3()

  with open("shoe.jpg", "rb") as f:
      b64 = base64.b64encode(f.read()).decode("utf-8")

  results = client.products.search(base64_image=b64)
  print(results.products[0].title)
  ```
</CodeGroup>

<Cards>
  <Card title="URL Lookup" icon="link" href="/guides/url-lookup" arrow="true">
    Resolve canonical products from supported retailer page URLs.
  </Card>

  <Card title="Similar Products" icon="clone" href="/guides/similar-products" arrow="true">
    Recommend visually similar products from a canonical product ID.
  </Card>

  <Card title="Cleaned Images" icon="sparkles" href="/guides/cleaned-images" arrow="true">
    Prefer square, uniform-background images for consistent product grids.
  </Card>
</Cards>
