> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Search Brands

> Search brands by free-text query.



## OpenAPI

````yaml get /v1/brands/search
openapi: 3.1.0
info:
  title: FastAPI
  version: 0.1.0
servers:
  - url: https://api.trychannel3.com
    description: Production environment
security: []
paths:
  /v1/brands/search:
    get:
      tags:
        - v1
      summary: Search Brands
      description: Search brands by free-text query.
      operationId: search_brands_public_v1_brands_search_get
      parameters:
        - name: query
          in: query
          required: true
          schema:
            type: string
            minLength: 1
            maxLength: 200
            description: Free-text query (e.g. 'Nike', 'lululemon').
            title: Query
          description: Free-text query (e.g. 'Nike', 'lululemon').
        - name: limit
          in: query
          required: false
          schema:
            type: integer
            maximum: 20
            minimum: 1
            description: Maximum number of brands to return.
            default: 5
            title: Limit
          description: Maximum number of brands to return.
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
                $ref: '#/components/schemas/SearchBrandsResponse'
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
          source: >-
            import Channel3 from '@channel3/sdk';


            const client = new Channel3({
              apiKey: process.env['CHANNEL3_API_KEY'], // This is the default and can be omitted
            });


            const searchBrandsResponse = await client.brands.search({ query: 'x'
            });


            console.log(searchBrandsResponse.brands);
        - lang: Python
          source: |-
            import os
            from channel3_sdk import Channel3

            client = Channel3(
                api_key=os.environ.get("CHANNEL3_API_KEY"),  # This is the default and can be omitted
            )
            search_brands_response = client.brands.search(
                query="x",
            )
            print(search_brands_response.brands)
        - lang: Go
          source: "package main\n\nimport (\n\t\"context\"\n\t\"fmt\"\n\n\t\"github.com/channel3-ai/sdk-go\"\n\t\"github.com/channel3-ai/sdk-go/option\"\n)\n\nfunc main() {\n\tclient := channel3go.NewClient(\n\t\toption.WithAPIKey(\"My API Key\"),\n\t)\n\tsearchBrandsResponse, err := client.Brands.Search(context.TODO(), channel3go.BrandSearchParams{\n\t\tQuery: \"x\",\n\t})\n\tif err != nil {\n\t\tpanic(err.Error())\n\t}\n\tfmt.Printf(\"%+v\\n\", searchBrandsResponse.Brands)\n}\n"
        - lang: CLI
          source: |-
            channel3 brands search \
              --api-key 'My API Key' \
              --query x
components:
  schemas:
    SearchBrandsResponse:
      properties:
        brands:
          items:
            $ref: '#/components/schemas/Brand'
          type: array
          title: Brands
          description: Brands matching the query, ordered by relevance.
      type: object
      required:
        - brands
      title: SearchBrandsResponse
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