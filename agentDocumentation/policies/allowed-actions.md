# Allowed Actions

The agent may perform read-only actions when needed to help the customer.

The agent may:

- read repository files
- inspect configuration
- summarize current state
- propose changes
- create draft files
- create pull requests
- create GitHub issues
- update non-sensitive state files after approval
- run health checks if the required tool access exists

The agent must ask for approval before making changes that affect production systems, secrets, customer data, device state, serial sessions, or access permissions.
