# Extracting Linear Custom Field IDs - Manual Guide

## Background

Linear's GraphQL API does not expose custom field schemas or values via the public API. Custom fields must be extracted manually from the browser's network traffic.

## Test Issue Created

A test issue has been created: **DEV-138**

- URL: https://linear.app/dev-ops/issue/DEV-138/test-custom-field-extraction
- Template: HITL Approval Template (8881211a-7b9c-42ab-a178-608ddf1f6665)

## Extraction Steps

### Step 1: Open Browser DevTools

1. Open the test issue in your browser: https://linear.app/dev-ops/issue/DEV-138/test-custom-field-extraction
2. Open DevTools (F12 or Right-click → Inspect)
3. Go to the **Network** tab
4. Filter by "Fetch/XHR" or "GraphQL"

### Step 2: Trigger GraphQL Request

1. Refresh the page (F5) to capture all network requests
2. OR modify one of the custom fields to trigger an update request

### Step 3: Find the GraphQL Response

Look for requests to `https://api.linear.app/graphql` with:

- Request Type: POST
- Name: "graphql" or similar

Common query names to look for:

- `Issue` (when viewing/loading the issue)
- `IssueUpdate` (when modifying fields)
- `IssueCreate` (initial creation response)

### Step 4: Inspect the Response

Click on the GraphQL request and go to the **Response** tab.

Look for custom field data in the JSON response. It might appear as:

```json
{
  "data": {
    "issue": {
      "id": "...",
      "customField_abc123": "Approved",
      "customField_def456": ["review_proposed_changes"]
    }
  }
}
```

OR as a nested structure:

```json
{
  "data": {
    "issue": {
      "id": "...",
      "fields": {
        "requestStatus": {
          "id": "abc123",
          "value": "Approved"
        },
        "requiredAction": {
          "id": "def456",
          "value": ["review_proposed_changes"]
        }
      }
    }
  }
}
```

### Step 5: Extract Field IDs

Copy the field IDs you find. They will look like UUIDs (e.g., `8f8990917b7e520efcd51f8ebe84055a251f53f8`).

You're looking for two fields:

1. **Request Status** (dropdown field)
2. **Required Action** (checkboxes field)

### Step 6: Update Environment Configuration

Add the field IDs to `config/env/.env`:

```bash
# Linear Custom Field IDs
LINEAR_FIELD_REQUEST_STATUS_ID=<uuid_from_devtools>
LINEAR_FIELD_REQUIRED_ACTION_ID=<uuid_from_devtools>
```

## Alternative: Check Linear's Web App State

If custom fields aren't in GraphQL responses, they might be in Linear's application state:

1. Open Console tab in DevTools
2. Type: `window.__APOLLO_STATE__` or `window.__INITIAL_STATE__`
3. Look for custom field definitions in the state object

## After Extraction

1. Update `config/env/.env` with the field IDs
2. Delete the test issue DEV-138 from Linear
3. Deploy configuration:
   ```powershell
   .\support\scripts\deploy\deploy-to-droplet.ps1 -DeployType config
   ```

## Troubleshooting

### Can't Find Custom Fields in Network Traffic

Try these alternatives:

1. **Edit a custom field value** in the Linear UI

   - Watch Network tab while changing "Request Status"
   - The update request will contain the field ID

2. **Check the template itself**

   - Go to template settings: https://linear.app/dev-ops/settings/templates
   - Edit template 8881211a-7b9c-42ab-a178-608ddf1f6665
   - Inspect network traffic when template loads

3. **Use Linear's API Explorer**
   - Go to: https://linear.app/dev-ops/settings/api
   - Try custom queries to find field schemas

### Field IDs Keep Changing

Custom field IDs are stable and shouldn't change unless:

- Field is deleted and recreated
- Organization is migrated
- Field type is changed

If IDs change, you'll need to update `.env` and redeploy.

## Need Help?

If you're unable to extract the field IDs manually, we can:

1. Proceed without custom fields (approval works manually in Linear UI)
2. Contact Linear support for API documentation
3. Use Linear's official SDK if they have one

The HITL approval workflow will still function - custom fields just make the UX better by pre-filling values.
