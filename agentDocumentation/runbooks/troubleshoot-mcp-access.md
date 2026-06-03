# Troubleshoot MCP Access

## Purpose

Resolve inability to reach or use the AI Connect MCP server.

## When To Use

Use when an agent cannot connect to MCP or expected AI Connect tools are missing.

## Required Information

- MCP endpoint.
- Deployment host or Compose access.
- Expected bind host and port.

## Preconditions

- Read-only checks are available.

## Approval Required

Approval is required before changing bind hosts, restarting services, exposing MCP publicly, or modifying access permissions.

## Steps

1. Read `backend/README.md` MCP section.
2. Confirm endpoint, usually `http://<backend-host>:8001/mcp`.
3. Check whether `MCP_BIND_HOST` keeps MCP on `127.0.0.1`.
4. Check service health if tools allow.
5. Inspect available MCP tools if connected.
6. Ask approval before configuration changes.

## Validation

Confirm the MCP endpoint is reachable and AI Connect tools are visible.

## Failure Handling

If access cannot be fixed with available tools, create an issue describing endpoint, bind-host expectation, and observed error.

## State Update

Record MCP endpoint and status after approval.

## Completion Message

Summarize MCP status, evidence, and the next action.
