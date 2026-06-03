# Troubleshoot GitHub Access

## Purpose

Resolve missing repository, issue, or pull-request access for an MCP-enabled agent.

## When To Use

Use when the agent cannot read repository files, create issues, create pull requests, or update non-sensitive state files.

## Required Information

- Repository URL.
- Agent tool access.
- Requested GitHub operation.

## Preconditions

- Customer can adjust GitHub or MCP permissions.

## Approval Required

Approval is required before changing repository permissions, creating issues, creating pull requests, or writing files.

## Steps

1. Identify the missing GitHub capability.
2. Confirm repository read access.
3. Confirm issue or pull-request tool access if needed.
4. Explain what permission is missing.
5. Ask the customer to enable the exact missing capability.
6. Retry only after the customer confirms access.

## Validation

Confirm the agent can perform the requested GitHub action or explain the remaining missing permission.

## Failure Handling

If access remains blocked, provide a concise escalation note the customer can give to a GitHub administrator.

## State Update

Record only non-sensitive access status after approval.

## Completion Message

Summarize what access works, what is missing, and who must approve the next change.
