# Day-2 Operations

Use this file for operational support after initial activation.

## Supported Intents

- check platform health
- show current status
- add a new site
- add a new device
- troubleshoot an alert
- create a change request
- prepare a maintenance window
- backup configuration
- restore configuration
- rotate credentials
- explain an error
- generate a customer status report

## Standard Day-2 Process

1. Identify the affected system.
2. Read platform inventory.
3. Check known issues.
4. Run the relevant health check.
5. Ask before changing anything.
6. Validate after the change.
7. Record the result.
8. Create or update a GitHub issue if follow-up is needed.

## Health Report Format

| Area | Status | Evidence | Action |
|---|---|---|---|
| MCP access | OK / Warning / Failed | What was checked | Next action |
| GitHub access | OK / Warning / Failed | What was checked | Next action |
| Platform services | OK / Warning / Failed | What was checked | Next action |
| Integrations | OK / Warning / Failed | What was checked | Next action |
| Security posture | OK / Warning / Failed | What was checked | Next action |

## AI Connect Day-2 Boundaries

- Adding a site maps to `create_site` or the equivalent REST API.
- Adding a device maps to the Bridge-generated onboarding and claim flow.
- Device disable and factory reset are sensitive actions.
- Serial sessions are auditable and require approval before opening or transmitting.
- Backup and restore are not fully automated by current repository docs; explain the available files and create a follow-up issue for missing automation if needed.
