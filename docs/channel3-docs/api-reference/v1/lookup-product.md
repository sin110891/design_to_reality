> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Lookup Product

> Retrieve product information for any supported product URL.

Returns the same Product model as GET /v1/products/{product_id}.
The product_id in the response can be used with the Product Detail endpoint.



## OpenAPI

````yaml post /v1/lookup
openapi: 3.1.0
info:
  title: FastAPI
  version: 0.1.0
servers:
  - url: https://api.trychannel3.com
    description: Production environment
security: []
paths:
  /v1/lookup:
    post:
      tags:
        - v1
      summary: Lookup Product
      description: >-
        Retrieve product information for any supported product URL.


        Returns the same Product model as GET /v1/products/{product_id}.

        The product_id in the response can be used with the Product Detail
        endpoint.
      operationId: lookup_product_v1_lookup_post
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/LookupRequest'
        required: true
      responses:
        '200':
          description: Successful Response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/LookupResponse'
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
          description: >-
            URL is not a product page (e.g. category listing, search results,
            homepage) or is on an unsupported domain
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              example:
                detail: URL is not a product page
        '500':
          description: Unable to extract product data from the given URL
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              example:
                detail: Product extraction failed
        '504':
          description: Timeout
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'
              example:
                detail: Request timed out
      security:
        - APIKeyHeader: []
      x-codeSamples:
        - lang: JavaScript
          source: |-
            import Channel3 from '@channel3/sdk';

            const client = new Channel3({
              apiKey: process.env['CHANNEL3_API_KEY'], // This is the default and can be omitted
            });

            const lookupResponse = await client.products.lookup({ url: 'url' });

            console.log(lookupResponse.product);
        - lang: Python
          source: |-
            import os
            from channel3_sdk import Channel3

            client = Channel3(
                api_key=os.environ.get("CHANNEL3_API_KEY"),  # This is the default and can be omitted
            )
            lookup_response = client.products.lookup(
                url="url",
            )
            print(lookup_response.product)
        - lang: Go
          source: "package main\n\nimport (\n\t\"context\"\n\t\"fmt\"\n\n\t\"github.com/channel3-ai/sdk-go\"\n\t\"github.com/channel3-ai/sdk-go/option\"\n)\n\nfunc main() {\n\tclient := channel3go.NewClient(\n\t\toption.WithAPIKey(\"My API Key\"),\n\t)\n\tlookupResponse, err := client.Products.Lookup(context.TODO(), channel3go.ProductLookupParams{\n\t\tLookupRequest: channel3go.LookupRequestParam{\n\t\t\tURL: \"url\",\n\t\t},\n\t})\n\tif err != nil {\n\t\tpanic(err.Error())\n\t}\n\tfmt.Printf(\"%+v\\n\", lookupResponse.Product)\n}\n"
        - lang: CLI
          source: |-
            channel3 products lookup \
              --api-key 'My API Key' \
              --url url
components:
  schemas:
    LookupRequest:
      properties:
        url:
          type: string
          title: Url
          description: The URL of the product to look up
        max_staleness_hours:
          type: integer
          minimum: 1
          title: Max Staleness Hours
          description: >-
            Maximum age (in hours) of cached product data before forcing a fresh
            lookup. Defaults to 3 hours.
          default: 3
      additionalProperties: false
      type: object
      required:
        - url
      title: LookupRequest
    LookupResponse:
      properties:
        product:
          $ref: '#/components/schemas/Product'
      type: object
      required:
        - product
      title: LookupResponse
      description: Response from the /v1/lookup endpoint.
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
  securitySchemes:
    APIKeyHeader:
      type: apiKey
      in: header
      name: x-api-key

````