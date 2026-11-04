> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Search Categories

> Search categories by free-text query.



## OpenAPI

````yaml get /v1/categories/search
openapi: 3.1.0
info:
  title: FastAPI
  version: 0.1.0
servers:
  - url: https://api.trychannel3.com
    description: Production environment
security: []
paths:
  /v1/categories/search:
    get:
      tags:
        - v1
      summary: Search Categories
      description: Search categories by free-text query.
      operationId: search_categories_public_v1_categories_search_get
      parameters:
        - name: query
          in: query
          required: true
          schema:
            type: string
            minLength: 1
            maxLength: 200
            description: Free-text query (e.g. 'sofas', 'yoga mats').
            title: Query
          description: Free-text query (e.g. 'sofas', 'yoga mats').
        - name: limit
          in: query
          required: false
          schema:
            type: integer
            maximum: 20
            minimum: 1
            description: Maximum number of categories to return.
            default: 5
            title: Limit
          description: Maximum number of categories to return.
      responses:
        '200':
          description: Successful Response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/SearchCategoriesResponse'
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


            const searchCategoriesResponse = await client.categories.search({
            query: 'x' });


            console.log(searchCategoriesResponse.categories);
        - lang: Python
          source: |-
            import os
            from channel3_sdk import Channel3

            client = Channel3(
                api_key=os.environ.get("CHANNEL3_API_KEY"),  # This is the default and can be omitted
            )
            search_categories_response = client.categories.search(
                query="x",
            )
            print(search_categories_response.categories)
        - lang: Go
          source: "package main\n\nimport (\n\t\"context\"\n\t\"fmt\"\n\n\t\"github.com/channel3-ai/sdk-go\"\n\t\"github.com/channel3-ai/sdk-go/option\"\n)\n\nfunc main() {\n\tclient := channel3go.NewClient(\n\t\toption.WithAPIKey(\"My API Key\"),\n\t)\n\tsearchCategoriesResponse, err := client.Categories.Search(context.TODO(), channel3go.CategorySearchParams{\n\t\tQuery: \"x\",\n\t})\n\tif err != nil {\n\t\tpanic(err.Error())\n\t}\n\tfmt.Printf(\"%+v\\n\", searchCategoriesResponse.Categories)\n}\n"
        - lang: CLI
          source: |-
            channel3 categories search \
              --api-key 'My API Key' \
              --query x
components:
  schemas:
    SearchCategoriesResponse:
      properties:
        categories:
          items:
            $ref: '#/components/schemas/CategorySummary'
          type: array
          title: Categories
          description: Categories matching the query, ordered by relevance.
      type: object
      required:
        - categories
      title: SearchCategoriesResponse
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
  securitySchemes:
    APIKeyHeader:
      type: apiKey
      in: header
      name: x-api-key

````