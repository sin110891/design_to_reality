> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# List Brands

> Paginated list of brands, capped at the top 5,000.



## OpenAPI

````yaml get /v1/brands
openapi: 3.1.0
info:
  title: FastAPI
  version: 0.1.0
servers:
  - url: https://api.trychannel3.com
    description: Production environment
security: []
paths:
  /v1/brands:
    get:
      tags:
        - v1
      summary: List Brands
      description: Paginated list of brands, capped at the top 5,000.
      operationId: list_brands_public_v1_brands_get
      parameters:
        - name: limit
          in: query
          required: false
          schema:
            type: integer
            maximum: 100
            minimum: 1
            description: Max items per page (1-100).
            default: 20
            title: Limit
          description: Max items per page (1-100).
        - name: cursor
          in: query
          required: false
          schema:
            anyOf:
              - type: string
              - type: 'null'
            description: >-
              Pagination cursor returned by a prior call. Omit for the first
              page.
            title: Cursor
          description: Pagination cursor returned by a prior call. Omit for the first page.
        - name: country
          in: query
          required: false
          schema:
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
            description: >-
              ISO 3166-1 alpha-2 country code that `best_commission_rate` is
              scoped to. Defaults to 'US' when unset.
            title: Country
          description: >-
            ISO 3166-1 alpha-2 country code that `best_commission_rate` is
            scoped to. Defaults to 'US' when unset.
      responses:
        '200':
          description: Successful Response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PaginatedListBrandsResponse'
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
          source: |-
            import Channel3 from '@channel3/sdk';

            const client = new Channel3({
              apiKey: process.env['CHANNEL3_API_KEY'], // This is the default and can be omitted
            });

            // Automatically fetches more pages as needed.
            for await (const brand of client.brands.list()) {
              console.log(brand.id);
            }
        - lang: Python
          source: |-
            import os
            from channel3_sdk import Channel3

            client = Channel3(
                api_key=os.environ.get("CHANNEL3_API_KEY"),  # This is the default and can be omitted
            )
            page = client.brands.list()
            page = page.items[0]
            print(page.id)
        - lang: Go
          source: "package main\n\nimport (\n\t\"context\"\n\t\"fmt\"\n\n\t\"github.com/channel3-ai/sdk-go\"\n\t\"github.com/channel3-ai/sdk-go/option\"\n)\n\nfunc main() {\n\tclient := channel3go.NewClient(\n\t\toption.WithAPIKey(\"My API Key\"),\n\t)\n\tpage, err := client.Brands.List(context.TODO(), channel3go.BrandListParams{})\n\tif err != nil {\n\t\tpanic(err.Error())\n\t}\n\tfmt.Printf(\"%+v\\n\", page)\n}\n"
        - lang: CLI
          source: |-
            channel3 brands list \
              --api-key 'My API Key'
components:
  schemas:
    PaginatedListBrandsResponse:
      properties:
        items:
          items:
            $ref: '#/components/schemas/Brand'
          type: array
          title: Items
          description: List of brands
        next_cursor:
          anyOf:
            - type: string
            - type: 'null'
          title: Next Cursor
          description: Cursor to fetch the next page of results. Null if no more results.
      type: object
      required:
        - items
      title: PaginatedListBrandsResponse
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
    Brand:
      properties:
        id:
          type: string
          title: Id
        name:
          type: string
          title: Name
        logo_url:
          anyOf:
            - type: string
            - type: 'null'
          title: Logo Url
        description:
          anyOf:
            - type: string
            - type: 'null'
          title: Description
        best_commission_rate:
          type: number
          title: Best Commission Rate
          description: >-
            The maximum commission rate for the brand in the requested country
            (default 'US'), as a percentage
          default: 0
      type: object
      required:
        - id
        - name
      title: Brand
  securitySchemes:
    APIKeyHeader:
      type: apiKey
      in: header
      name: x-api-key

````