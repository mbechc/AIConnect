# Customer Onboarding

Use this file when the customer is starting AI Connect for the first time or adding a new customer environment.

## Agent Sequence

1. Read `agentDocumentation/AGENTS.md`.
2. Read `agentDocumentation/docs/agent/00_START_HERE.md`.
3. Read `README.md`, `backend/README.md`, `bridge/README.md`, and `bridge/claim-process/README.md`.
4. Read `agentDocumentation/runbooks/activate-platform.md`.
5. Check whether the three state files exist.
6. Ask one operational question at a time.

## First Question

Ask:

```text
Is this a lab, pilot, or production activation?
```

## Required Customer Inputs

- Environment type: lab, pilot, or production.
- Backend host or deployment target.
- Public API URL, if configured.
- MCP endpoint, if already deployed.
- MQTT TLS endpoint, if already deployed.
- Secret store name or location.
- Organization name.
- First site name.
- Whether an M5Atom Lite RS232 Bridge is available for claim testing.

Do not ask for secret values. Ask for the approved secret store or local ignored file where the secret will be placed.

## Onboarding Boundaries

The agent may guide backend setup, organization/site creation, provisioning credential setup, Bridge firmware configuration, Bridge claim, and validation if the required tools exist.

The agent must not invent deployment automation, hosted services, or third-party integrations that are not present in repository files or available tools.
