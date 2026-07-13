# QuickAdd and ActivateCourse LTI 1.3 Tool

Python Flask app that combines the legacy QuickAdd and ActivateCourse Brightspace
tools behind one LTI 1.3 registration. The app uses Brightspace OAuth2 client
credentials for API calls instead of ID-key Valence credentials.

## Brightspace Setup

Register one LTI 1.3 tool with these endpoints:

- OIDC login URL: `/login/`
- Launch URL: `/launch/`
- JWKS URL: `/jwks/`

Create two deployments for that same tool:

- QuickAdd deployment
- ActivateCourse deployment

Put both deployment ids in `tool_config.json`, then map each deployment id in
`.env`:

```env
QUICKADD_DEPLOYMENT_ID=...
ACTIVATE_COURSE_DEPLOYMENT_ID=...
```

At launch time, the app reads the LTI deployment id claim and routes to the
correct workflow.

## Workflows

QuickAdd renders a small form. Submitting the form:

1. Finds the Brightspace user by username.
2. Enrolls the user in the current course offering with the selected role.
3. Enrolls the user in every section in that offering.

ActivateCourse does not render an HTML page. It immediately toggles/updates the
current course offering and returns JSON:

```json
{
  "success": true,
  "message": "The site has been activated successfully.",
  "org_unit_id": "12345",
  "is_active": true
}
```

Role checks from the legacy tools are intentionally not included.

## Local Setup

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Replace the placeholder values in `.env` and `tool_config.json`.

Development keys were generated locally under `keys/` for smoke testing. For
production, replace them with the actual LTI key pair and register the public
key/JWKS with Brightspace.
