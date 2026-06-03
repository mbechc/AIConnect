# Start Here

This repository contains operational instructions for AI Connect.

The customer should interact with AI Connect through an MCP-enabled AI agent.

The agent should guide the customer step by step.

## Main Customer Intents

If the customer says:

- "Start setup"
- "Activate the platform"
- "Help me get started"
- "Onboard me"
- "Install the solution"

Use:

- `docs/agent/10_CUSTOMER_ONBOARDING.md`
- `docs/agent/20_PRECHECKS.md`
- `runbooks/activate-platform.md`

If the customer says:

- "Check health"
- "Is everything working?"
- "Show current status"
- "Do a platform check"

Use:

- `docs/agent/50_DAY2_OPERATIONS.md`
- `runbooks/check-platform-health.md`

If the customer says:

- "Something is broken"
- "Troubleshoot"
- "It stopped working"
- "I get an error"

Use:

- `docs/agent/60_TROUBLESHOOTING.md`

If the customer says:

- "Add a site"
- "Add a device"
- "Expand the platform"

Use the relevant runbook under `runbooks/`.

## State Files

Maintain customer-specific non-sensitive state in:

- `state/customer-profile.yaml`
- `state/onboarding-status.yaml`
- `state/platform-inventory.yaml`

If the real state files do not exist, create them from the example files after customer approval.

## Important

Never store secrets in state files.

State files may contain names, URLs, service names, inventory, operating mode, onboarding status, non-sensitive configuration references, and secret names or locations.

Secrets must be stored only in the approved secret store or local ignored runtime files.
