# TOOLS.md

The agent may have access to tools such as:

- GitHub repository access
- GitHub issues
- GitHub pull requests
- filesystem access
- AI Connect MCP tools
- REST API clients
- deployment tooling
- Docker or Compose tooling
- monitoring systems
- secret stores
- infrastructure APIs

The agent must inspect available tools before assuming that an action can be performed.

If a required tool is missing, the agent should explain what is missing and guide the customer to enable it.

The agent must not claim that an action was performed unless it has tool evidence.

For AI Connect, prefer MCP tools when available. Use REST API only when MCP is unavailable or the relevant capability is not exposed through MCP.
