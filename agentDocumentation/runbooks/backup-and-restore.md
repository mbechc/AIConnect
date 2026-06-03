# Backup And Restore

## Purpose

Guide backup or restore planning for AI Connect configuration and operational data.

## When To Use

Use when the customer asks to back up, restore, or verify recoverability.

## Required Information

- Environment type.
- Backup target.
- PostgreSQL backup method.
- Repository and certificate backup policy.
- Restore target.

## Preconditions

- Customer has approved any restore or overwrite operation.
- Secret handling is defined.

## Approval Required

Approval is required before restore, overwrite, service stop, database import, or certificate changes.

## Steps

1. Identify what needs backup or restore.
2. Confirm whether this is lab, pilot, or production.
3. Explain that current repository docs do not define a full automated backup system.
4. Inventory relevant assets: PostgreSQL data, `.env`, certificates, Compose files, firmware source, and state files.
5. Ask approval before executing any restore or overwrite.
6. Validate service health after any approved action.

## Validation

Confirm backend health, MCP availability, and expected device records after restore.

## Failure Handling

If backup automation is missing, create a GitHub issue for implementation.

## State Update

Record backup policy references only. Do not store backup secrets.

## Completion Message

Summarize what is protected, what is not yet automated, and the next recovery-readiness action.
