> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Similar Products

> Find products similar to a given product.

Consider setting ``filters`` to narrow results to the
same gender, brand, category, price range, etc. when you only want
similar items within a specific slice of the catalog.



## OpenAPI

````yaml post /v1/similar
openapi: 3.1.0
info:
  title: FastAPI
  version: 0.1.0
servers:
  - url: https://api.trychannel3.com
    description: Production environment
security: []
paths:
  /v1/similar:
    post:
      tags:
        - v1
      summary: Similar Products
      description: |-
        Find products similar to a given product.

        Consider setting ``filters`` to narrow results to the
        same gender, brand, category, price range, etc. when you only want
        similar items within a specific slice of the catalog.
      operationId: similar_v1_similar_post
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SimilarProductsRequest'
        required: true
      responses:
        '200':
          description: Successful Response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SearchResponse'
        '401':
          description: Unauthorized - Invalid or missing authentication
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              examples:
                missing_key:
                  summary: Missing API Key
                  value:
                    detail: >-
                      Unauthorized. Missing authentication key. Make sure to
                      attach an x-api-key with your request. Need help? Reach
                      out to support@trychannel3.com.
                invalid_key:
                  summary: Invalid API Key
                  value:
                    detail: >-
                      API key was provided but is invalid. Need help? Reach out
                      to support@trychannel3.com.
        '402':
          description: Payment required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              example:
                detail: >-
                  You have used all of your free credits. Add a payment method
                  to continue.
        '404':
          description: Product not found
          content:
            application/json:
              example:
                detail: Product not found
              schema:
                $ref: '#/components/schemas/ErrorResponse'
        '422':
          description: Validation Error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              example:
                detail:
                  - loc:
                      - body
                      - query
                    msg: field required
                    type: value_error.missing
        '500':
          description: Internal Server Error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              example:
                detail: Internal Server Error
      security:
        - APIKeyHeader: []
      x-codeSamples:
        - lang: JavaScript
          source: >-
            import Channel3 from '@channel3/sdk';


            const client = new Channel3({
              apiKey: process.env['CHANNEL3_API_KEY'], // This is the default and can be omitted
            });


            // Automatically fetches more pages as needed.

            for await (const productDetail of client.products.findSimilar({
            product_id: 'product_id' })) {
              console.log(productDetail.id);
            }
        - lang: Python
          source: |-
            import os
            from channel3_sdk import Channel3

            client = Channel3(
                api_key=os.environ.get("CHANNEL3_API_KEY"),  # This is the default and can be omitted
            )
            page = client.products.find_similar(
                product_id="product_id",
            )
            page = page.products[0]
            print(page.id)
        - lang: Go
          source: "package main\n\nimport (\n\t\"context\"\n\t\"fmt\"\n\n\t\"github.com/channel3-ai/sdk-go\"\n\t\"github.com/channel3-ai/sdk-go/option\"\n)\n\nfunc main() {\n\tclient := channel3go.NewClient(\n\t\toption.WithAPIKey(\"My API Key\"),\n\t)\n\tpage, err := client.Products.FindSimilar(context.TODO(), channel3go.ProductFindSimilarParams{\n\t\tSimilarProductsRequest: channel3go.SimilarProductsRequestParam{\n\t\t\tProductID: \"product_id\",\n\t\t},\n\t})\n\tif err != nil {\n\t\tpanic(err.Error())\n\t}\n\tfmt.Printf(\"%+v\\n\", page)\n}\n"
        - lang: CLI
          source: |-
            channel3 products find-similar \
              --api-key 'My API Key' \
              --product-id product_id
components:
  schemas:
    SimilarProductsRequest:
      properties:
        product_id:
          type: string
          title: Product Id
          description: Canonical product ID to find similar products for.
        limit:
          anyOf:
            - type: integer
              minimum: 1
            - type: 'null'
          title: Limit
          description: Optional limit on the number of results. Default is 20, max is 30.
          default: 20
        filters:
          $ref: '#/components/schemas/SearchFilters'
          description: >-
            Optional filters. Search will only consider products that match all
            of the filters.
          default: {}
        config:
          $ref: '#/components/schemas/LocaleConfig'
          description: Optional locale configuration.
          default: {}
        page_token:
          anyOf:
            - type: string
            - type: 'null'
          title: Page Token
          description: >-
            Opaque token from a previous similar response to fetch the next page
            of results.
      additionalProperties: false
      type: object
      required:
        - product_id
      title: SimilarProductsRequest
      description: Find products similar to a given product.
    SearchResponse:
      properties:
        products:
          items:
            $ref: '#/components/schemas/Product'
          type: array
          title: Products
        next_page_token:
          anyOf:
            - type: string
            - type: 'null'
          title: Next Page Token
          description: Token to fetch the next page. Null when no more results.
      type: object
      required:
        - products
      title: SearchResponse
      description: v1 paginated search response.
    ErrorResponse:
      properties:
        detail:
          anyOf:
            - type: string
            - items:
                additionalProperties: true
                type: object
              type: array
          title: Detail
      type: object
      required:
        - detail
      title: ErrorResponse
    SearchFilters:
      properties:
        brand_ids:
          anyOf:
            - items:
                type: string
              type: array
            - type: 'null'
          title: Brand Ids
          description: If provided, only products from these brands will be returned
        gender:
          anyOf:
            - type: string
              enum:
                - male
                - female
            - type: 'null'
          title: Gender
        condition:
          anyOf:
            - type: string
              enum:
                - new
                - refurbished
                - used
            - type: 'null'
          title: Condition
          description: >-
            Filter by offer condition. Requires at least one offer matching the
            requested condition, locale, and any price filter. Offers without
            condition data are indexed as new.
        age:
          anyOf:
            - items:
                type: string
                enum:
                  - newborn
                  - infant
                  - toddler
                  - kids
                  - adult
              type: array
            - type: 'null'
          title: Age
          description: >-
            Filter by age group. Age-agnostic products are treated as adult
            products.
        price:
          anyOf:
            - $ref: '#/components/schemas/SearchFilterPrice'
            - type: 'null'
          description: If provided, only products within this price range will be returned
        availability:
          anyOf:
            - items:
                $ref: '#/components/schemas/AvailabilityStatus'
              type: array
            - type: 'null'
          title: Availability
          description: >-
            If provided, only products with these availability statuses will be
            returned
        sale:
          anyOf:
            - type: string
              const: on_sale
            - type: 'null'
          title: Sale
          description: >-
            If 'on_sale', only products with at least one on-sale offer (priced
            below its compare-at price) for the requested locale are returned.
            If omitted, no filter.
        website_ids:
          anyOf:
            - items:
                type: string
              type: array
            - type: 'null'
          title: Website Ids
          description: >-
            If provided, only products from these websites will be returned.
            Accepts website IDs or domains (e.g. "nike.com").
        category_ids:
          anyOf:
            - items:
                type: string
              type: array
            - type: 'null'
          title: Category Ids
          description: >-
            If provided, only products from these categories will be returned.
            Accepts category slugs.
        exclude_brand_ids:
          anyOf:
            - items:
                type: string
              type: array
            - type: 'null'
          title: Exclude Brand Ids
          description: >-
            If provided, products from these brands will be excluded from the
            results
        exclude_website_ids:
          anyOf:
            - items:
                type: string
              type: array
            - type: 'null'
          title: Exclude Website Ids
          description: >-
            If provided, products from these websites will be excluded from the
            results. Accepts website IDs or domains (e.g. "nike.com").
        exclude_category_ids:
          anyOf:
            - items:
                type: string
              type: array
            - type: 'null'
          title: Exclude Category Ids
          description: >-
            If provided, products in these categories (or their descendants)
            will be excluded from the results. Accepts category slugs.
        colors:
          anyOf:
            - $ref: '#/components/schemas/SearchColorsFilter'
            - type: 'null'
          description: >-
            [Beta: filter is experimental and may be changed] If provided, find
            products containing all of these colors.
        attributes:
          anyOf:
            - additionalProperties:
                items:
                  type: string
                type: array
              type: object
            - type: 'null'
          title: Attributes
          description: >-
            If provided, only products whose extracted attributes match these
            key/value constraints will be returned. Keys are attribute handles
            (e.g. 'color', 'material') and values are lists of allowed values
            (OR within a key, AND across keys). When a category filter is also
            supplied, all keys must be valid attributes of at least one of the
            requested categories. See `Category.attributes` for the valid
            keys/values per category.
        dimensions:
          anyOf:
            - $ref: '#/components/schemas/SearchFilterDimensions'
            - type: 'null'
          description: >-
            If provided, only products with at least one offer whose physical
            dimensions satisfy every given range will be returned. Offer
            dimensions in responses are converted to the units used here.
      additionalProperties: false
      type: object
      title: SearchFilters
      description: Search filters for the search API.
    LocaleConfig:
      properties:
        language:
          anyOf:
            - type: string
              enum:
                - en
                - de
                - fr
                - it
                - es
                - nl
                - sv
                - fi
                - pt
                - cs
                - el
                - ro
            - type: 'null'
          title: Language
          description: >-
            ISO 639-1 language code. When unset, inferred from ``country``
            (preferred) then ``currency``, defaulting to ``en``.
        country:
          anyOf:
            - type: string
              enum:
                - US
                - GB
                - EU
                - AU
                - CA
                - IE
                - DE
                - AT
                - FR
                - BE
                - IT
                - ES
                - NL
                - SE
                - FI
                - PT
                - CZ
                - GR
                - RO
            - type: 'null'
          title: Country
          description: >-
            ISO 3166-1 alpha-2 country code. May stay unset for pan-region
            storefronts (e.g. ``currency=EUR`` with no specific country).
        currency:
          anyOf:
            - type: string
              enum:
                - USD
                - CAD
                - AUD
                - GBP
                - EUR
                - SEK
                - CZK
                - RON
            - type: 'null'
          title: Currency
          description: >-
            ISO 4217 currency code. When unset, inferred from ``country`` (e.g.
            ``GB`` → ``GBP``), defaulting to ``USD``.
        length_unit:
          anyOf:
            - $ref: '#/components/schemas/LengthUnit'
            - type: 'null'
          description: >-
            Preferred unit for length dimensions (length/width/height) in
            responses. A request dimension filter's unit for the field takes
            precedence; when neither is set, the merchant's stated unit is
            returned.
        weight_unit:
          anyOf:
            - $ref: '#/components/schemas/WeightUnit'
            - type: 'null'
          description: >-
            Preferred unit for weight dimensions in responses. A request
            dimension filter's weight unit takes precedence; when neither is
            set, the merchant's stated unit is returned.
      additionalProperties: false
      type: object
      title: LocaleConfig
      description: >-
        Locale options for API requests.


        Locale fields are optional; the server infers missing values. Details
        are

        on ``language``, ``country``, and ``currency`` below.
    Product:
      properties:
        id:
          type: string
          title: Id
        title:
          type: string
          title: Title
        description:
          anyOf:
            - type: string
            - type: 'null'
          title: Description
        brands:
          items:
            $ref: '#/components/schemas/ProductBrand'
          type: array
          title: Brands
          description: Ordered list of brands.
        images:
          items:
            $ref: '#/components/schemas/ProductImage'
          type: array
          title: Images
          default: []
        categories:
          items:
            type: string
          type: array
          title: Categories
          deprecated: true
        category:
          anyOf:
            - $ref: '#/components/schemas/CategorySummary'
            - type: 'null'
          description: >-
            The single category this product belongs to, as a structured
            `CategorySummary` (slug, title, path, has_children). Replaces the
            deprecated `categories` field.
        gender:
          anyOf:
            - type: string
              enum:
                - male
                - female
                - unisex
            - type: 'null'
          title: Gender
        age:
          anyOf:
            - type: string
              enum:
                - newborn
                - infant
                - toddler
                - kids
                - adult
            - type: 'null'
          title: Age
          description: >-
            Target age group. Age-agnostic products are typically returned as
            'adult'.
        materials:
          anyOf:
            - items:
                type: string
              type: array
            - type: 'null'
          title: Materials
        key_features:
          anyOf:
            - items:
                type: string
              type: array
            - type: 'null'
          title: Key Features
        offers:
          items:
            $ref: '#/components/schemas/ProductOffer'
          type: array
          title: Offers
          description: All merchant offers for this product in the requested locale.
        variants:
          anyOf:
            - $ref: '#/components/schemas/Variants'
            - type: 'null'
          description: >-
            Variant interaction state — options, selected. Absent when the
            product has no variations.
        structured_attributes:
          additionalProperties:
            items:
              type: string
            type: array
          type: object
          title: Structured Attributes
          description: >-
            Structured attributes extracted for this product, keyed by attribute
            handle (e.g. 'color', 'material'). Values are the canonical allowed
            values for that handle.
      type: object
      required:
        - id
        - title
      title: Product
      description: Product with detailed information.
    SearchFilterPrice:
      properties:
        min_price:
          anyOf:
            - type: number
            - type: 'null'
          title: Min Price
          description: Minimum price, in dollars and cents
        max_price:
          anyOf:
            - type: number
            - type: 'null'
          title: Max Price
          description: Maximum price, in dollars and cents
      additionalProperties: false
      type: object
      title: SearchFilterPrice
      description: Price filter for search. Values are inclusive.
    AvailabilityStatus:
      type: string
      enum:
        - InStock
        - LimitedAvailability
        - PreOrder
        - BackOrder
        - SoldOut
        - OutOfStock
        - Discontinued
        - Unknown
      title: AvailabilityStatus
    SearchColorsFilter:
      properties:
        palette:
          items:
            $ref: '#/components/schemas/SearchFilterColor'
          type: array
          title: Palette
          description: Colors required in matching products. Treated as an AND condition.
      additionalProperties: false
      type: object
      required:
        - palette
      title: SearchColorsFilter
      description: >-
        [Beta] Color filter wrapper. Holds the list of required colors today;

        reserved for future filter-level options (e.g. match modes, tolerance
        overrides).
    SearchFilterDimensions:
      properties:
        length:
          anyOf:
            - $ref: '#/components/schemas/SearchFilterLengthDimension'
            - type: 'null'
        width:
          anyOf:
            - $ref: '#/components/schemas/SearchFilterLengthDimension'
            - type: 'null'
        height:
          anyOf:
            - $ref: '#/components/schemas/SearchFilterLengthDimension'
            - type: 'null'
        weight:
          anyOf:
            - $ref: '#/components/schemas/SearchFilterWeightDimension'
            - type: 'null'
      additionalProperties: false
      type: object
      title: SearchFilterDimensions
      description: >-
        Physical-dimension range filters, matched against the same offer.


        Matching products have at least one offer satisfying every provided

        range (alongside any locale/price/availability filters). Values are

        compared with a small relative tolerance. An offer with no dimension
        data

        for a filtered field does not match; note that when a single merchant on
        a

        product reports a dimension it is shared across that product's offers,
        so a

        matching offer may not itself surface that dimension in the response.
    LengthUnit:
      type: string
      enum:
        - mm
        - cm
        - m
        - in
        - ft
      title: LengthUnit
    WeightUnit:
      type: string
      enum:
        - mg
        - g
        - kg
        - oz
        - lb
      title: WeightUnit
    ProductBrand:
      properties:
        id:
          type: string
          title: Id
        name:
          type: string
          title: Name
      type: object
      required:
        - id
        - name
      title: ProductBrand
    ProductImage:
      properties:
        url:
          type: string
          title: Url
        is_main_image:
          type: boolean
          title: Is Main Image
          default: false
        is_cleaned_image:
          type: boolean
          title: Is Cleaned Image
          description: >-
            True if this URL points to a cleaned image. A cleaned image has a
            square aspect ratio and a uniform, monochromatic background. Cleaned
            images are best displayed in a product grid.
          default: false
        shot_type:
          anyOf:
            - $ref: '#/components/schemas/ApiProductImageType'
            - type: 'null'
        alt_text:
          anyOf:
            - type: string
            - type: 'null'
          title: Alt Text
      type: object
      required:
        - url
      title: ProductImage
      description: Product image with metadata.
    CategorySummary:
      properties:
        slug:
          type: string
          title: Slug
          description: URL-friendly slug (e.g. 'sofas')
        title:
          type: string
          title: Title
          description: Human-readable category title
        path:
          items:
            $ref: '#/components/schemas/CategoryRef'
          type: array
          title: Path
          description: >-
            Hierarchical path as a structured list, root first; the last entry
            is this category itself
        has_children:
          type: boolean
          title: Has Children
          description: Whether this category has subcategories
      type: object
      required:
        - slug
        - title
        - has_children
      title: CategorySummary
      description: Lean category representation used in search hits and list rows.
    ProductOffer:
      properties:
        url:
          type: string
          title: Url
        domain:
          type: string
          title: Domain
        price:
          $ref: '#/components/schemas/Price'
        availability:
          type: string
          enum:
            - InStock
            - OutOfStock
          title: Availability
        condition:
          anyOf:
            - type: string
              enum:
                - new
                - refurbished
                - used
            - type: 'null'
          title: Condition
          description: >-
            Condition of this merchant offer (new, used, or refurbished). Null
            when condition is unknown.
        max_commission_rate:
          type: number
          title: Max Commission Rate
          description: >-
            The maximum commission rate for the merchant, as a decimal fraction:
            0 is no commission, 0.5 is 50% commission. 'Max' because the actual
            commission rate may be lower due to vendor-specific affiliate rules.
          default: 0
        dimensions:
          anyOf:
            - $ref: '#/components/schemas/Dimensions'
            - type: 'null'
          description: Physical dimensions of this offer. Null when unknown.
      type: object
      required:
        - url
        - domain
        - price
        - availability
      title: ProductOffer
    Variants:
      properties:
        options:
          items:
            $ref: '#/components/schemas/VariantOption'
          type: array
          title: Options
        selected:
          items:
            $ref: '#/components/schemas/SelectedOption'
          type: array
          title: Selected
      type: object
      required:
        - options
        - selected
      title: Variants
      description: |-
        Wrapper for variant-interaction state on a Product.

        Holds `options` and `selected`. `options` represent all of the
        configuration options for the product. `selected` represents the
        currently selected option values.
    SearchFilterColor:
      properties:
        hex:
          type: string
          title: Hex
          description: sRGB hex string, e.g. '#a1b2c3'
        percentage:
          anyOf:
            - type: number
            - type: 'null'
          title: Percentage
          description: Percentage of color, where 1.0 is 100%
      type: object
      required:
        - hex
      title: SearchFilterColor
      description: A single color requirement for the color filter.
    SearchFilterLengthDimension:
      properties:
        min:
          anyOf:
            - type: number
            - type: 'null'
          title: Min
          description: Minimum value, in `unit`. Inclusive.
        max:
          anyOf:
            - type: number
            - type: 'null'
          title: Max
          description: Maximum value, in `unit`. Inclusive.
        unit:
          $ref: '#/components/schemas/LengthUnit'
          description: Unit that min/max are expressed in
      additionalProperties: false
      type: object
      required:
        - unit
      title: SearchFilterLengthDimension
    SearchFilterWeightDimension:
      properties:
        min:
          anyOf:
            - type: number
            - type: 'null'
          title: Min
          description: Minimum value, in `unit`. Inclusive.
        max:
          anyOf:
            - type: number
            - type: 'null'
          title: Max
          description: Maximum value, in `unit`. Inclusive.
        unit:
          $ref: '#/components/schemas/WeightUnit'
          description: Unit that min/max are expressed in
      additionalProperties: false
      type: object
      required:
        - unit
      title: SearchFilterWeightDimension
    ApiProductImageType:
      type: string
      enum:
        - hero
        - lifestyle
        - on_model
        - detail
        - scale_reference
        - angle_view
        - flat_lay
        - in_use
        - packaging
        - size_chart
        - product_information
        - merchant_information
      title: ApiProductImageType
      description: Product image type classification for API responses.
    CategoryRef:
      properties:
        slug:
          type: string
          title: Slug
          description: URL-friendly slug (e.g. 'sofas')
        title:
          type: string
          title: Title
          description: Human-readable category title
      type: object
      required:
        - slug
        - title
      title: CategoryRef
      description: Lean reference to a category, used in path and children arrays.
    Price:
      properties:
        price:
          type: number
          title: Price
          description: The current price of the product, including any discounts.
        compare_at_price:
          anyOf:
            - type: number
            - type: 'null'
          title: Compare At Price
          description: The original price of the product before any discounts.
        currency:
          type: string
          title: Currency
          description: The currency code of the product, like USD, EUR, GBP, etc.
      type: object
      required:
        - price
        - currency
      title: Price
    Dimensions:
      properties:
        length:
          anyOf:
            - $ref: '#/components/schemas/LengthDimension'
            - type: 'null'
        width:
          anyOf:
            - $ref: '#/components/schemas/LengthDimension'
            - type: 'null'
        height:
          anyOf:
            - $ref: '#/components/schemas/LengthDimension'
            - type: 'null'
        weight:
          anyOf:
            - $ref: '#/components/schemas/WeightDimension'
            - type: 'null'
      type: object
      title: Dimensions
      description: >-
        Physical dimensions of a product offer. Members are null when unknown.


        Values are standardized to the supported unit set; a merchant-stated
        value

        whose unit is not one of those units is omitted rather than shown.
    VariantOption:
      properties:
        name:
          type: string
          title: Name
          description: The name of the option (e.g. 'Color', 'Size')
        values:
          items:
            $ref: '#/components/schemas/OptionValue'
          type: array
          title: Values
          description: The values of the option (e.g. ['Blue', 'Red', 'Green'])
      type: object
      required:
        - name
        - values
      title: VariantOption
      description: One dimension of a product family (e.g. 'Color', 'Size').
    SelectedOption:
      properties:
        name:
          type: string
          title: Name
          description: The name of the selected option (e.g. 'Color', 'Size')
        label:
          type: string
          title: Label
          description: The display value of the selected option (e.g. 'Blue', 'XL')
      type: object
      required:
        - name
        - label
      title: SelectedOption
      description: One effective selection on a product, post server-side relaxation.
    LengthDimension:
      properties:
        number:
          type: number
          title: Number
        unit:
          $ref: '#/components/schemas/LengthUnit'
          description: >-
            The unit from the request's dimension filters when one was given
            (the value is converted to it); otherwise the unit the merchant
            stated.
      type: object
      required:
        - number
        - unit
      title: LengthDimension
      description: A length measurement, in one of the supported length units.
    WeightDimension:
      properties:
        number:
          type: number
          title: Number
        unit:
          $ref: '#/components/schemas/WeightUnit'
          description: >-
            The unit from the request's dimension filters when one was given
            (the value is converted to it); otherwise the unit the merchant
            stated.
      type: object
      required:
        - number
        - unit
      title: WeightDimension
      description: A weight measurement, in one of the supported weight units.
    OptionValue:
      properties:
        label:
          type: string
          title: Label
          description: The display value of the option value (e.g. 'Blue')
        exists:
          type: boolean
          title: Exists
          description: >-
            Whether the option value exists on the product, or is a
            configuration only present on another variant of the same product.
            For example, a shirt that comes in multiple colors, but only one
            color is available in Size XL.
        available:
          anyOf:
            - $ref: '#/components/schemas/AvailabilityStatus'
            - type: 'null'
          description: >-
            The availability status of the option value. None when returned on
            search results, hydrated only on get product detail requests.
        thumbnail_url:
          anyOf:
            - type: string
            - type: 'null'
          title: Thumbnail Url
          description: >-
            For options that reference different products, this is the URL of
            the thumbnail image for the option value. E.g., a shoe that comes in
            multiple colors will have an OptionValue for each color with a
            thumbnail_url set.
        product_id:
          anyOf:
            - type: string
            - type: 'null'
          title: Product Id
          description: >-
            The product id that represents this value. Variants that point to
            different products will have this field set, as well as
            thumbnail_url for displaying selector icons.
      type: object
      required:
        - label
        - exists
      title: OptionValue
      description: One value of one variant option (e.g. 'Blue' under 'Color')
  securitySchemes:
    APIKeyHeader:
      type: apiKey
      in: header
      name: x-api-key

````