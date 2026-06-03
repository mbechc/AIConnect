# Onboard New Site

## Purpose

Add a new AI Connect site under an existing organization.

## When To Use

Use when the customer says "add a site" or "onboard a new site".

## Required Information

- Organization ID or organization name.
- Site name.
- Site description or location if the available tool supports it.

## Preconditions

- MCP or REST access can list organizations.
- The target organization exists.

## Approval Required

Approval is required before creating or renaming a site.

## Steps

1. Read platform inventory.
2. List organizations through MCP or REST.
3. Ask which organization the site belongs to if ambiguous.
4. Ask for approval to create the site.
5. Create the site using `create_site` or REST equivalent.
6. Validate the site appears in the site list.

## Validation

Confirm the site appears under the intended organization.

## Failure Handling

If organization lookup fails, stop and ask for the correct organization or tool access.

## State Update

Update platform inventory with the non-sensitive site reference after approval.

## Completion Message

Summarize the created site, organization, validation evidence, and next useful action.
