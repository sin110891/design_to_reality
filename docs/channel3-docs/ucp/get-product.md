> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Get product

> Load one product by id with get_product

**`get_product`** loads a single product when you already have its id from search or lookup. Use it for full detail and interactive variant selection.

See [quickstart](/ucp/quickstart) to install the UCP CLI.

## Request

<CodeGroup>
  ```bash UCP CLI theme={null}
  ucp catalog get_product HvGOfxD \
    --format json
  ```

  ```bash curl theme={null}
  curl -sS -X POST https://ucp.trychannel3.com/mcp \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d '{
      "jsonrpc": "2.0",
      "id": 1,
      "method": "tools/call",
      "params": {
        "name": "get_product",
        "arguments": {
          "meta": null,
          "catalog": { "id": "HvGOfxD" }
        }
      }
    }'
  ```
</CodeGroup>

## Variant selection

For products with configurable options (color, size, etc.), pass **`catalog.selected`** to narrow the variant. The response includes **`options`** (each value carries an `exists` flag) and **`selected`** (the effective selections after any server-side relaxation). Use a product that has variants — solo products return no `options`.

```json theme={null}
{
  "catalog": {
    "id": "iQ3ukd7",
    "selected": [
      { "name": "Color", "label": "Black Frame" },
      { "name": "Size", "label": "22\"x26\"" }
    ],
    "preferences": ["Color", "Size"],
    "context": {
      "address_country": "US",
      "currency": "USD"
    }
  }
}
```

**`preferences`** controls relaxation order when no exact variant matches all selections. Options are dropped from the end of the list first — e.g. `["Color", "Size"]` keeps Color and relaxes Size.

This mirrors [`GET /v1/products/{id}`](/api-reference/get-v1productsproduct-id) query params `option_<name>=<label>` (e.g. `option_color=Blue&option_size=10`).

## Response shape

The **`product`** object follows the [UCP get\_product spec](https://ucp.dev/latest/specification/catalog/mcp/#get-product-request):

| Field      | Notes                                                                                       |
| ---------- | ------------------------------------------------------------------------------------------- |
| `options`  | Selectable dimensions with a per-value `exists` flag (present on `get_product`, not search) |
| `selected` | Effective selections after relaxation — diff against your request to detect relaxation      |
| `variants` | Per-merchant listings (Channel3 [global extension](/ucp/catalog-global-extension))          |

When a selection resolves to a different canonical product (e.g. switching color), **`product.id`** reflects the resolved product.

## Which tool should I use?

| You have...           | Use              |
| --------------------- | ---------------- |
| A search phrase       | `search_catalog` |
| A list of ids or URLs | `lookup_catalog` |
| One product id        | `get_product`    |

## What's next

<Card title="Extension reference" icon="puzzle" href="/ucp/catalog-global-extension">
  Extra fields and filters
</Card>
