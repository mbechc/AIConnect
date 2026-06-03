# Rotate Secrets

## Purpose

Guide safe rotation of AI Connect credentials.

## When To Use

Use when the customer asks to rotate API tokens, MQTT provisioning credentials, device credentials, database passwords, dashboard passwords, or certificates.

## Required Information

- Secret name, not value.
- Secret store location.
- Affected services or devices.
- Rollback plan.

## Preconditions

- Customer approval is explicit.
- Secret store process is available.
- The agent does not receive or commit secret values.

## Approval Required

Approval is always required before rotating secrets.

## Steps

1. Identify the secret by name and scope.
2. Identify affected services and devices.
3. Present expected impact and rollback option.
4. Ask for approval.
5. Use available approved tool or instruct customer where to place the new secret.
6. Restart or redeploy only if approved.
7. Validate health and authentication.

## Validation

Confirm old credentials no longer work where appropriate and new credentials work through health or connection checks. Do not print secret values.

## Failure Handling

If rotation fails, follow the rollback plan and create an issue with non-sensitive evidence.

## State Update

Record rotation date, secret name, and validation status only.

## Completion Message

Summarize secret scope, affected services, validation evidence, and follow-up work.
