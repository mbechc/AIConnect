# Change Management

Use change management for production changes, security changes, credential rotation, device disablement, factory reset, serial sessions, and repository permission changes.

## Change Request Structure

Present:

1. Intended action.
2. Reason for the action.
3. Expected impact.
4. Systems affected.
5. Rollback option.
6. Validation method.
7. Approval question.

## Recording Changes

After an approved change:

- Update non-sensitive state files if they exist and the customer approved state updates.
- Create or update a GitHub issue for follow-up work.
- Do not write secrets, token values, claim-code material, MQTT passwords, or private keys.
