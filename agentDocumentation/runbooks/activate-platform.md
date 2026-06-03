# Activate Platform

## Purpose

Guide first-time AI Connect activation for a lab, pilot, or production environment.

## When To Use

Use when the customer says "activate the platform", "start setup", "install the solution", "onboard me", or similar.

## Required Information

- Environment type: lab, pilot, or production.
- Backend host or deployment target.
- MCP endpoint, if deployed.
- API base URL, if deployed.
- MQTT TLS endpoint.
- Approved secret store or local ignored secret-file process.
- Organization name.
- First site name.
- Whether a Bridge is available for claim validation.

## Preconditions

- Repository access is available.
- Required tools are inspected.
- Secrets are not stored in GitHub.
- The customer has approved any production-impacting action.

## Approval Required

Approval is required before changing backend services, rotating provisioning credentials, creating production organizations or sites, claiming devices, requesting factory reset, or opening serial sessions.

## Steps

1. Ask: `Is this a lab, pilot, or production activation?`
2. Read state files if present. If missing, ask approval to create them from `agentDocumentation/state/*.example.yaml`.
3. Check backend prerequisites from `backend/README.md`.
4. Check MCP access and available AI Connect tools.
5. Check GitHub access if issue or pull-request actions are expected.
6. Collect customer profile fields one at a time.
7. Identify required secrets by name or location only. Do not ask for secret values.
8. Explain approval gates from `agentDocumentation/policies/approval-gates.md`.
9. Configure or validate installation settings only if approved and the tool exists.
10. Create or validate organization and site only if approved.
11. Guide Bridge preparation using `bridge/README.md`.
12. Wait for the Bridge to show `Ready for operator claim`.
13. List pending onboarding registrations if the tool exists.
14. Claim the pending registration into the selected site only after approval.
15. Validate backend health, MCP visibility, device claim state, and heartbeat freshness.
16. Summarize handover and create GitHub issues for unresolved items.

Each step must state what was checked, what is missing, what may be done next, and what must not be done.

## Validation

Activation is successful when:

- Backend health or readiness is confirmed.
- MCP access or REST fallback is confirmed.
- Organization and site exist.
- Bridge onboarding registration is claimed or the customer accepted a no-device activation.
- Device presence and heartbeat are confirmed for a claimed Bridge.
- No secrets were written to Git.

## Failure Handling

If a step fails, stop at the failing step, collect evidence, explain the likely area, and ask for the next missing input or approval. Create a GitHub issue if follow-up is needed and tools are available.

## State Update

Update non-sensitive state files only after approval. Record blockers, decisions, completed phases, endpoint references, organization/site names, and device IDs. Never record secret values or claim codes.

## Completion Message

Use:

- What was activated
- What was validated
- What remains open
- What needs approval later
- Recommended next action
