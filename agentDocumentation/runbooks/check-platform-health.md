# Check Platform Health

## Purpose

Report current AI Connect platform status.

## When To Use

Use when the customer asks "check health", "is everything working", "show current status", or similar.

## Required Information

- Backend endpoint or MCP endpoint.
- Available tools.
- Platform inventory if present.

## Preconditions

- Read-only checks are allowed.
- Sensitive credentials are available through approved tool context, not through chat.

## Approval Required

Read-only health checks do not require approval. Changes to fix findings require approval.

## Steps

1. Read platform inventory if present.
2. Inspect available tools.
3. Run MCP `platform_summary` if available.
4. Check `/health` and `/ready` if REST access is available.
5. Check device list and presence if MCP or REST supports it.
6. Check known warnings and failures in state.
7. Return the standard Day-2 health report table.

## Validation

Evidence must come from tool output, repository state, or explicit customer-provided status.

## Failure Handling

If a health check cannot run, mark it `Warning` or `Failed` with the missing evidence.

## State Update

Update `agentDocumentation/state/platform-inventory.yaml` health summary after approval.

## Completion Message

Return the health table plus the next recommended action.
