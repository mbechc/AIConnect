# Troubleshoot Platform Service

## Purpose

Troubleshoot AI Connect backend, MCP, MQTT, database, Caddy, and device-message service issues.

## When To Use

Use when backend health fails, devices disappear, onboarding stalls, MQTT authentication fails, or API/MCP routes return errors.

## Required Information

- Affected service.
- Error message or observed symptom.
- Environment type.
- Available deployment tools.

## Preconditions

- Start with read-only inspection.
- Production changes require approval.

## Approval Required

Approval is required before restarting services, changing configuration, rotating credentials, changing certificates, exposing ports, or modifying data.

## Steps

1. Identify the affected service: `api`, `mcp`, `postgres`, `emqx`, `caddy`, onboarding worker, claim worker, or device-message worker.
2. Check `backend/README.md` for expected behavior.
3. Run read-only health checks if available.
4. Inspect logs if the customer has provided approved access.
5. Map the symptom to likely cause.
6. Propose one next action.
7. Ask approval before changes.
8. Validate after any approved action.

## Validation

Use backend health, MCP tool availability, MQTT connectivity, pending registration status, device presence, or audit logs as appropriate.

## Failure Handling

If service recovery cannot be completed, create an issue with symptom, evidence, affected service, and next proposed action.

## State Update

Record incident notes and validation status without secrets.

## Completion Message

Summarize root cause if known, action taken, validation evidence, and remaining risk.
