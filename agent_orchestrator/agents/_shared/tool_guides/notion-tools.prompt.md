# Notion Tools Usage Guide

## When to Use

- Creating and updating documentation pages
- Managing knowledge bases
- Organizing team wikis
- Linking documentation to Linear issues

## Available Tools (notion MCP server)

### `create_page`

```json
{
  "parent_page_id": "parent-uuid",
  "title": "API Authentication Guide",
  "content": {
    "type": "blocks",
    "blocks": [
      {
        "type": "heading_1",
        "text": "Authentication"
      },
      {
        "type": "paragraph",
        "text": "Our API uses JWT tokens for authentication."
      },
      {
        "type": "code",
        "language": "bash",
        "text": "curl -H 'Authorization: Bearer <token>' https://api.example.com"
      }
    ]
  }
}
```

**Use when**: Creating new documentation pages or guides.

### `update_page`

```json
{
  "page_id": "page-uuid",
  "title": "Updated API Guide",
  "append_content": {
    "type": "blocks",
    "blocks": [
      {
        "type": "heading_2",
        "text": "New Section"
      }
    ]
  }
}
```

**Use when**: Updating existing documentation with new information.

### `search_pages`

```json
{
  "query": "authentication",
  "filter": {
    "property": "Type",
    "value": "Guide"
  }
}
```

**Use when**: Finding existing documentation to update or reference.

### `get_page`

```json
{
  "page_id": "page-uuid",
  "include_content": true
}
```

**Use when**: Reading page content for updates or references.

### `create_database`

```json
{
  "parent_page_id": "parent-uuid",
  "title": "API Endpoints",
  "schema": {
    "Endpoint": { "type": "title" },
    "Method": { "type": "select" },
    "Description": { "type": "text" },
    "Status": { "type": "status" }
  }
}
```

**Use when**: Creating structured documentation like API references.

## Common Patterns

**Pattern 1: New Documentation**

1. `search_pages` → check if page exists
2. `create_page` → create new guide
3. Add structured content (headings, code blocks, tables)
4. Link to related Linear issues

**Pattern 2: Update Existing Docs**

1. `search_pages` → find relevant pages
2. `get_page` → read current content
3. `update_page` → append new sections
4. Add "Last Updated" timestamp

**Pattern 3: API Documentation**

1. `create_database` → structured API reference
2. Add rows for each endpoint
3. Include request/response examples
4. Link to implementation code (GitHub)

## Content Types

- **Headings**: heading_1, heading_2, heading_3
- **Text**: paragraph, bulleted_list, numbered_list
- **Code**: code (with language), quote
- **Media**: image, video, embed
- **Layout**: column_list, divider, table_of_contents

## Safety Rules

- Always check if page exists before creating
- Use append_content to avoid overwriting
- Include clear headings for navigation
- Add code examples with proper language highlighting
- Link related documentation pages together
