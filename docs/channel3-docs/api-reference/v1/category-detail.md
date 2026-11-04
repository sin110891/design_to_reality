> ## Documentation Index
> Fetch the complete documentation index at: https://docs.trychannel3.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Category Detail

> Look up a category by slug.



## OpenAPI

````yaml get /v1/categories/{slug}
openapi: 3.1.0
info:
  title: FastAPI
  version: 0.1.0
servers:
  - url: https://api.trychannel3.com
    description: Production environment
security: []
paths:
  /v1/categories/{slug}:
    get:
      tags:
        - v1
      summary: Category Detail
      description: Look up a category by slug.
      operationId: get_category_public_v1_categories__slug__get
      parameters:
        - name: slug
          in: path
          required: true
          schema:
            type: string
            title: Slug
      responses:
        '200':
          description: Successful Response
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Category'
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
          description: Category not found
          content:
            application/json:
              example:
                detail: No category found matching 'foo'
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
          source: |-
            import Channel3 from '@channel3/sdk';

            const client = new Channel3({
              apiKey: process.env['CHANNEL3_API_KEY'], // This is the default and can be omitted
            });

            const category = await client.categories.retrieve('slug');

            console.log(category.has_children);
        - lang: Python
          source: |-
            import os
            from channel3_sdk import Channel3

            client = Channel3(
                api_key=os.environ.get("CHANNEL3_API_KEY"),  # This is the default and can be omitted
            )
            category = client.categories.retrieve(
                "slug",
            )
            print(category.has_children)
        - lang: Go
          source: "package main\n\nimport (\n\t\"context\"\n\t\"fmt\"\n\n\t\"github.com/channel3-ai/sdk-go\"\n\t\"github.com/channel3-ai/sdk-go/option\"\n)\n\nfunc main() {\n\tclient := channel3go.NewClient(\n\t\toption.WithAPIKey(\"My API Key\"),\n\t)\n\tcategory, err := client.Categories.Get(context.TODO(), \"slug\")\n\tif err != nil {\n\t\tpanic(err.Error())\n\t}\n\tfmt.Printf(\"%+v\\n\", category.HasChildren)\n}\n"
        - lang: CLI
          source: |-
            channel3 categories retrieve \
              --api-key 'My API Key' \
              --slug slug
components:
  schemas:
    Category:
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
        description:
          anyOf:
            - type: string
            - type: 'null'
          title: Description
          description: Natural-language description of products in this category
        children:
          items:
            $ref: '#/components/schemas/CategoryRef'
          type: array
          title: Children
          description: Direct subcategories only (one level)
        attributes:
          items:
            $ref: '#/components/schemas/CategoryAttribute'
          type: array
          title: Attributes
          description: >-
            Structured attributes applicable to this category, with their
            allowed values. Usable as keys in `SearchFilters.attributes`.
      type: object
      required:
        - slug
        - title
        - has_children
      title: Category
      description: Full category representation used in detail responses.
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
    CategoryAttribute:
      properties:
        slug:
          type: string
          title: Slug
          description: URL-friendly identifier (e.g. 'color', 'frame-color')
        name:
          type: string
          title: Name
          description: Human-readable attribute name (e.g. 'Color')
        values:
          items:
            type: string
          type: array
          title: Values
          description: >-
            Allowed values for this attribute. May be empty when no enumerated
            value set is defined.
      type: object
      required:
        - slug
        - name
      title: CategoryAttribute
      description: A structured attribute (e.g. Color, Size) applicable to a category.
  securitySchemes:
    APIKeyHeader:
      type: apiKey
      in: header
      name: x-api-key

````