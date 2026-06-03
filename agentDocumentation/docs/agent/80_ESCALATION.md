# Escalation

Escalate when the agent cannot safely complete a request with available repository instructions and tools.

## Escalate For

- Missing production approval.
- Missing secret-store access.
- Missing MCP, GitHub, deployment, or infrastructure tools.
- Unclear customer environment.
- Evidence that secrets were committed.
- Incomplete validation after a sensitive action.
- Hardware states that require physical access.
- Serial-console actions that could alter customer equipment.

## Escalation Output

Use this structure:

- What is blocked
- Evidence collected
- Risk if continued
- What decision or access is required
- Suggested GitHub issue title
