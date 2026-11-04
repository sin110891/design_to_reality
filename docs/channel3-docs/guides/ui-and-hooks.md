> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# UI + Hooks

> Drop-in React components and headless hooks for building shopping experiences on top of Channel3.

Channel3 ships an open-source React component library as a [shadcn registry](https://ui.shadcn.com/registry) — every component arrives in your repo as editable, customizable code. Two high-level blocks cover most apps. If you need something custom, composable primitives and headless hooks are right below them.

<Card title="channel3-ai/channel3-ui" icon="github" href="https://github.com/channel3-ai/channel3-ui" arrow="true">
  Full catalog, install commands, and contributor guide on GitHub.
</Card>

## Install

```bash theme={null}
npx shadcn@latest add https://ui.trychannel3.com/r/all.json
```

All components land in your `components/` directory as editable source files. They're typed directly against the Channel3 SDK — a `ProductDetail` from search or a product fetch drops straight in, with no adapter or mapping layer.

## Blocks

Two compound blocks cover most shopping surfaces:

### `product-search`

A complete search experience in one component: search bar, faceted filters (brand, category, color, price), and an infinitely-scrollable results grid.

```tsx theme={null}
import { ProductSearch } from "@/components/channel3/product-search";

export default function ShopPage() {
  return (
    <ProductSearch
      onSearch={async (params) => {
        "use server";
        return channel3Client.products.search(params);
      }}
    />
  );
}
```

Pass your server-side fetcher — the component never touches your API key directly.

### `product-details`

A full product detail page (PDP): image gallery, variant selection with all availability states, multiple merchant offers, price history chart, and a similar-products carousel.

```tsx theme={null}
import { ProductDetails } from "@/components/channel3/product-details";

export default async function ProductPage({ params }: { params: { id: string } }) {
  const product = await channel3Client.products.retrieve(params.id);

  return (
    <ProductDetails
      product={product}
      onFetchSimilar={async (id) => {
        "use server";
        return channel3Client.products.find_similar({ product_id: id });
      }}
    />
  );
}
```

## Composable primitives

Every piece of the blocks is also available individually:

| Component          | What it renders                                           |
| ------------------ | --------------------------------------------------------- |
| `product-card`     | A single product tile with image, title, price, and brand |
| `product-grid`     | Responsive masonry or uniform grid of `product-card`      |
| `product-carousel` | Horizontally-scrollable product strip                     |
| `variant-selector` | Size/color/option pickers with availability styling       |
| `price-chart`      | Price history line chart from the price tracking API      |
| `offer-list`       | Ranked list of merchant offers for a product              |
| `image-gallery`    | Zoomable image carousel for a PDP                         |
| `search-bar`       | Controlled text + image search input                      |
| `filter-panel`     | Faceted filter sidebar with async options                 |

## Headless hooks

Hooks encapsulate the business logic — use them with your own markup when the default components don't fit your design.

### `use-product-search`

Manages query state, filter plumbing, pagination, and request orchestration. Returns the current results, a loading state, and a setter for each filter.

```tsx theme={null}
import { useProductSearch } from "@/hooks/channel3/use-product-search";

function SearchPage() {
  const { results, isLoading, setQuery, setFilters, loadMore } = useProductSearch({
    onSearch: async (params) => fetch("/api/search", { method: "POST", body: JSON.stringify(params) }).then(r => r.json()),
  });

  return (
    <>
      <input onChange={e => setQuery(e.target.value)} placeholder="Search products…" />
      {isLoading && <Spinner />}
      {results.map(p => <MyProductCard key={p.id} product={p} />)}
      <button onClick={loadMore}>Load more</button>
    </>
  );
}
```

### `use-variant-selection`

Handles variant relaxation, availability vs. existence logic, and cross-product navigation. Returns the resolved `selected` state after each server round-trip — no need to diff your request against the response yourself.

```tsx theme={null}
import { useVariantSelection } from "@/hooks/channel3/use-variant-selection";

function VariantPicker({ product }) {
  const { selected, options, select } = useVariantSelection({
    product,
    onFetch: async (id, opts) => fetch(`/api/products/${id}?${opts}`).then(r => r.json()),
  });

  return (
    <div>
      {options.map(opt => (
        <div key={opt.name}>
          <label>{opt.name}</label>
          {opt.values.map(val => (
            <button
              key={val.label}
              data-selected={selected[opt.name] === val.label}
              onClick={() => select(opt, val)}
            >
              {val.label}
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}
```

### `use-async-options`

Loads category and brand filter options on demand so filter panels are snappy even with large catalogs.

```tsx theme={null}
import { useAsyncOptions } from "@/hooks/channel3/use-async-options";

const { options: brandOptions, isLoading } = useAsyncOptions({
  fetch: () => channel3Client.brands.list({ limit: 50 }),
  map: brand => ({ label: brand.name, value: brand.id }),
});
```

## Architecture note

Components are **presentational**: they accept Channel3 data as props and emit user intent through callbacks. They never call the API directly or read your key — fetch on your server where `CHANNEL3_API_KEY` lives, then pass results down. This keeps your API key server-side and makes every component independently testable.

<Card title="Quickstart" icon="rocket" href="/" arrow="true">
  Install the Channel3 skill and let your agent wire the components in for you.
</Card>
