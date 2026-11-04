> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Attribute Search

> Use structured attributes and category detail to find products by specific features — e.g. sofas with USB charging ports.

Every product in Channel3 has a category, and every category has a set of **structured attributes** — machine-extracted features like material, connectivity, power source, and thousands of others. Combining category detail lookup with the `attributes` search filter lets you express queries that plain text search can't — for example, finding sofas that have USB charging ports.

## The two-step pattern

1. **Discover the category and its attributes** — look up the category detail to see which attribute keys are defined and what values they accept.
2. **Search with an attribute filter** — pass those key/value pairs to `/v1/search` to get precisely matched products.

***

## Step 1 — Get a category slug

You need a category **slug** (for example `sofas`) before you can inspect its attributes. Either find one by text, or grab it from a product you already have.

### Option A — Search for the category

Use the category search endpoint to look up by free text:

<CodeGroup>
  ```typescript TypeScript theme={null}
  import Channel3 from "@channel3/sdk";

  const client = new Channel3();

  const categoryResults = await client.categories.search({ query: "sofas" });

  // Pick the best-matching category
  const category = categoryResults.categories[0];
  console.log(category.slug); // e.g. "sofas"
  console.log(category.title); // "Sofas"
  ```

  ```python Python theme={null}
  from channel3_sdk import Channel3

  client = Channel3()

  category_results = client.categories.search(query="sofas")
  category = category_results.categories[0]
  print(category.slug)   # e.g. "sofas"
  print(category.title)  # "Sofas"
  ```

  ```bash cURL theme={null}
  curl "https://api.trychannel3.com/v1/categories/search?query=sofas" \
    -H "x-api-key: $CHANNEL3_API_KEY"
  ```
</CodeGroup>

### Option B — Grab the category from an existing product

If you already have a representative product — from a search result, lookup, or your own catalog — read its `category.slug` instead of searching:

<CodeGroup>
  ```typescript TypeScript theme={null}
  const product = await client.products.retrieve("2yh8WH5");
  const slug = product.category.slug; // e.g. "sofas"
  ```

  ```python Python theme={null}
  product = client.products.retrieve("2yh8WH5")
  slug = product.category.slug  # e.g. "sofas"
  ```

  ```bash cURL theme={null}
  curl "https://api.trychannel3.com/v1/products/2yh8WH5" \
    -H "x-api-key: $CHANNEL3_API_KEY"
  ```
</CodeGroup>

***

## Step 2 — Retrieve category detail to see its attributes

Call the category detail endpoint with the slug to get the full list of attributes for that category. Each attribute has a `handle` (the key you'll pass to the filter) and a list of known values.

<CodeGroup>
  ```typescript TypeScript theme={null}
  const categoryDetail = await client.categories.retrieve("sofas");

  // Print all attributes and their example values
  for (const attr of categoryDetail.attributes) {
    console.log(`${attr.handle}: ${attr.values.slice(0, 5).join(", ")}`);
  }
  // connectivity: USB, Bluetooth, None
  // material:     Leather, Velvet, Linen, Microfiber, ...
  // seating_capacity: 2, 3, 4, Sectional
  // style:        Mid-Century Modern, Contemporary, ...
  // color:        Beige, Gray, Navy, ...
  ```

  ```python Python theme={null}
  category_detail = client.categories.retrieve("sofas")

  for attr in category_detail.attributes:
      print(f"{attr.handle}: {', '.join(attr.values[:5])}")
  # connectivity: USB, Bluetooth, None
  # material:     Leather, Velvet, Linen, Microfiber, ...
  # seating_capacity: 2, 3, 4, Sectional
  # style:        Mid-Century Modern, Contemporary, ...
  ```

  ```bash cURL theme={null}
  curl "https://api.trychannel3.com/v1/categories/sofas" \
    -H "x-api-key: $CHANNEL3_API_KEY"
  ```
</CodeGroup>

<Note>
  The attributes available vary by category. Always retrieve category detail
  first — don't guess attribute handles.
</Note>

***

## Step 3 — Search with the attribute filter

Now you have the attribute key and its accepted values. Pass them to `POST /v1/search` via the `attributes` filter. The `attributes` filter takes a map of `handle → [values]`.

<CodeGroup>
  ```typescript TypeScript theme={null}
  const results = await client.products.search({
    query: "sofa",
    filters: {
      category: "sofas",
      attributes: {
        connectivity: ["USB"],
      },
    },
    limit: 20,
  });

  console.log(`Found ${results.products.length} sofas with USB charging`);
  results.products.forEach((p) => {
    console.log(p.title, p.offers[0]?.price);
  });
  ```

  ```python Python theme={null}
  results = client.products.search(
      query="sofa",
      filters={
          "category": "sofas",
          "attributes": {
              "connectivity": ["USB"],
          },
      },
      limit=20,
  )

  print(f"Found {len(results.products)} sofas with USB charging")
  for p in results.products:
      print(p.title, p.offers[0].price if p.offers else "")
  ```

  ```bash cURL theme={null}
  curl -X POST https://api.trychannel3.com/v1/search \
    -H "x-api-key: $CHANNEL3_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "query": "sofa",
      "filters": {
        "category": "sofas",
        "attributes": { "connectivity": ["USB"] }
      },
      "limit": 20
    }'
  ```
</CodeGroup>

***

## Full end-to-end example

Here's the complete three-step flow in a single function — discover the category, inspect its attributes, then search:

<CodeGroup>
  ```typescript TypeScript theme={null}
  import Channel3 from "@channel3/sdk";

  const client = new Channel3();

  async function findSofasWithUSB() {
    // 1. Find the category
    const { categories } = await client.categories.search({ query: "sofas" });
    const slug = categories[0].slug; // "sofas"

    // 2. Inspect its attributes
    const detail = await client.categories.retrieve(slug);
    const connectivityAttr = detail.attributes.find(
      (a) => a.handle === "connectivity",
    );

    if (!connectivityAttr?.values.includes("USB")) {
      console.warn("USB not listed as a connectivity value for this category");
    }

    // 3. Search with the attribute filter
    const results = await client.products.search({
      query: "sofa",
      filters: {
        category: slug,
        attributes: { connectivity: ["USB"] },
      },
      limit: 20,
    });

    return results.products;
  }

  findSofasWithUSB().then((products) => {
    console.log(`Found ${products.length} sofas with USB ports:`);
    products.forEach((p) => console.log(" -", p.title));
  });
  ```

  ```python Python theme={null}
  from channel3_sdk import Channel3

  client = Channel3()

  def find_sofas_with_usb():
      # 1. Find the category
      category_results = client.categories.search(query="sofas")
      slug = category_results.categories[0].slug  # "sofas"

      # 2. Inspect its attributes
      detail = client.categories.retrieve(slug)
      connectivity = next(
          (a for a in detail.attributes if a.handle == "connectivity"), None
      )
      if connectivity and "USB" not in connectivity.values:
          print("Warning: USB not listed as a connectivity value for this category")

      # 3. Search with the attribute filter
      results = client.products.search(
          query="sofa",
          filters={
              "category": slug,
              "attributes": {"connectivity": ["USB"]},
          },
          limit=20,
      )
      return results.products

  products = find_sofas_with_usb()
  print(f"Found {len(products)} sofas with USB ports:")
  for p in products:
      print(f"  - {p.title}")
  ```
</CodeGroup>

***

## Combining multiple attributes

Pass multiple keys to narrow further. Values within a key are OR'd; keys are AND'd — so the example below finds sofas that are `(USB OR Bluetooth)` connectivity **and** Velvet material:

<CodeGroup>
  ```typescript TypeScript theme={null}
  const results = await client.products.search({
    query: "sofa",
    filters: {
      category: "sofas",
      attributes: {
        connectivity: ["USB", "Bluetooth"],
        material: ["Velvet"],
      },
    },
  });
  ```

  ```python Python theme={null}
  results = client.products.search(
      query="sofa",
      filters={
          "category": "sofas",
          "attributes": {
              "connectivity": ["USB", "Bluetooth"],
              "material":     ["Velvet"],
          },
      },
  )
  ```
</CodeGroup>

***

## Reading `structured_attributes` on a product

Products returned from `/v1/products/{id}` and `/v1/lookup` include a `structured_attributes` field — a map of attribute handles to their extracted values for that specific product. Use it to display feature chips on a PDP, or to understand what attributes a specific product carries.

```typescript TypeScript theme={null}
const product = await client.products.retrieve("2yh8WH5");

const attrs = product.structured_attributes;
// {
//   connectivity: "USB",
//   material:     "Velvet",
//   color:        "Navy Blue",
//   seating_capacity: "3",
// }

console.log(`Connectivity: ${attrs.connectivity}`);
console.log(`Material: ${attrs.material}`);
```

<Note>
  `structured_attributes` is populated on product detail (`GET /v1/products/{id}
      ` and `POST /v1/lookup`). It is **not** returned on search results.
</Note>

***
