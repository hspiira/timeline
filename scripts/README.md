# Seed Scripts

Utilities for creating test data in the Timeline application.

## Create Dummy Subjects

### Method 1: UI Button (Easiest)

1. Login to the application
2. Navigate to `/subjects`
3. If you have no subjects, click the **"Add Demo Data"** button
4. This will create 10 test subjects across different types

### Method 2: Browser Console

1. Login to the application
2. Navigate to `/subjects`
3. Open browser developer console (F12)
4. Run:

```javascript
createDummySubjects()
```

This will create 10 test subjects and automatically refresh the list.

### Method 3: Command Line Script

For larger datasets or CI/CD pipelines:

1. Start the backend server (`dev/timeline`)
2. Login to the UI and get your auth token:
   - Open browser console
   - Run: `localStorage.getItem("auth_token")`
   - Copy the token
3. Run the seed script:

```bash
npx tsx scripts/seed-subjects.ts <YOUR_AUTH_TOKEN>
```

Example:

```bash
npx tsx scripts/seed-subjects.ts eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Test Data

The seed script creates subjects of the following types:

- **users** (3) - Example: `user_john_doe_001`
- **orders** (3) - Example: `ORD-2024-001`
- **projects** (2) - Example: `PROJ-ALPHA`
- **invoices** (1) - Example: `INV-2024-001`
- **shipments** (1) - Example: `SHIP-FDX-001`
- **customers** (2) - Example: `CUST-ACME-001` (CLI only)

Total: 10 subjects (UI) or 15 subjects (CLI script)

## Environment Variables

The seed script uses the following environment variables:

- `VITE_API_URL` - API base URL (default: `http://localhost:8000`)

## Import Workflow from JSON

To create the **New Client Rollout** workflow (or any workflow defined as requirements JSON) in the system:

1. Start the backend server.
2. Log in to the UI and get your auth token:
   - Open browser dev tools → Application → Local Storage (or Console).
   - Run: `localStorage.getItem("auth_token")` and copy the value.
3. From the project root, run:

```bash
pnpm run import:workflow -- <YOUR_AUTH_TOKEN>
```

Or call the script directly with an optional JSON path:

```bash
npx tsx scripts/import-workflow.ts <YOUR_AUTH_TOKEN> docs/workflow-new-client-rollout-v2.json
```

By default the script reads `docs/workflow-new-client-rollout-v2.json`. Optional env: `API_URL`, `TENANT_ID`.

## Notes

- All methods require authentication
- Subjects are created in the current tenant context
- Each subject type is validated according to backend rules (alphanumeric + underscores)
- The CLI script includes a 100ms delay between requests to avoid overwhelming the server
