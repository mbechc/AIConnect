# Onboard New Customer

## Purpose

Create the non-sensitive operating context an agent needs to support a customer using AI Connect.

## When To Use

Use when the customer is new, state files are missing, or the agent lacks customer context.

## Required Information

- Customer name.
- Contact person.
- Environment type.
- Repository URL.
- Primary agent.
- Secret store location.

## Preconditions

- Customer has approved creating or updating non-sensitive state files.
- No secret values are collected.

## Approval Required

Approval is required before writing state files or creating GitHub issues.

## Steps

1. Check for existing state files.
2. If missing, propose creating files from examples.
3. Ask for customer profile fields one at a time.
4. Record only non-sensitive values.
5. Identify missing operational facts.
6. Create a GitHub issue for unresolved onboarding items if available.

## Validation

Confirm the state files exist and contain no secret values.

## Failure Handling

If the customer cannot provide a value, leave it blank and record a blocker or decision.

## State Update

Update `agentDocumentation/state/customer-profile.yaml` and `agentDocumentation/state/onboarding-status.yaml` after approval.

## Completion Message

Summarize captured profile fields, missing fields, and the next activation step.
