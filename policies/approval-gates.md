# Approval Gates

The agent must receive explicit approval before performing sensitive actions.

Approval is required before:

- production deployment
- production configuration changes
- DNS changes
- certificate changes
- secret rotation
- user or permission changes
- deletion of resources
- disabling devices
- factory-resetting devices
- opening or transmitting in serial sessions
- disabling monitoring
- closing incidents
- merging pull requests
- changing customer data

The agent should present:

1. intended action
2. expected impact
3. rollback option
4. validation method

Then ask for approval.
