> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Cleaned Images

> Prefer square, uniform-background product images for consistent grids.

Product images on the `ProductImage` type include an `is_cleaned_image` flag. When `true`, the image has a square aspect ratio and a uniform background — ideal for product grids where raw retailer shots would mix on-model photos and mismatched aspect ratios.

## Prefer cleaned images in grids

When displaying search or similar-product results, pick the cleaned image when one is available:

```typescript TypeScript theme={null}
const heroImage = product.images.find(img => img.is_cleaned_image) ?? product.images[0];
```

This works on any product response that includes `images` — search, lookup, and product detail all expose the same `ProductImage` model.

<Cards>
  <Card title="Image Search" icon="image" href="/guides/image-search" arrow="true">
    Visual search is a common place to surface cleaned images in a grid.
  </Card>

  <Card title="Color Filters" icon="palette" href="/guides/color-filters" arrow="true">
    Combine color filters with cleaned images for palette-matched, uniform grids.
  </Card>

  <Card title="UI Components" icon="puzzle-piece" href="/guides/ui-and-hooks" arrow="true">
    Channel3 components can prefer cleaned images in product cards automatically.
  </Card>
</Cards>
