# AI Connect

AI Connect lets an AI assistant help troubleshoot physical devices that are hard to reach, poorly documented, or sitting beside people who are not trained to diagnose them. Common targets are Cisco routers, switches, firewalls, and other serial-console equipment in remote closets, vehicles, factories, customer sites, or temporary locations.

The field person should not need to know console commands, baud rates, log interpretation, or escalation routines. They should be able to plug in a small bridge, get it online, and let a skilled operator or AI assistant guide the troubleshooting session through a controlled backend.

AI Connect turns an M5Atom Lite RS232 device into a secure remote console bridge for that job. The intent is to give an AI-capable operations layer controlled serial access through a backend the owner manages, without making the field device responsible for deciding who owns it or which organisation it belongs to.

Security is the centre of the design. A backend may serve multiple organisations, so device ownership, MQTT permissions, claim codes, MCP tools, and serial sessions are scoped by backend-controlled identity and state. A hardware identifier can identify a Bridge, but it is not treated as a secret and must not grant ownership by itself.

The REST API is the stable control plane, but the preferred operational frontend is MCP. The AI agent connects to the MCP server and guides the operator through setup, configuration, validation, troubleshooting, device onboarding, health checks, and serial sessions.

Devices start unclaimed. The Bridge registers itself with the backend, the backend operator assigns it to the correct organisation and site, and the backend returns per-device credentials. After claiming, the device publishes status, heartbeat, and serial-session messages for normal operation.

## How To Start

First install and start the backend. Use `backend/README.md` for the backend services, environment variables, certificates, health checks, and MCP endpoint.

After the backend is running, connect an MCP-enabled agent such as OpenClaw, Codex, or another compatible agent to this repository and to the AI Connect MCP server. The agent should use the operational documentation in this repository to configure the installation and guide the operator step by step.

Start the agent with this prompt file:

```text
https://github.com/mbechc/AIConnect/blob/main/agentDocumentation/prompts/customer-start.md
```

The agent-facing entrypoints are:

- `agentDocumentation/AGENTS.md`
- `agentDocumentation/docs/agent/00_START_HERE.md`
- `agentDocumentation/runbooks/activate-platform.md`
- `agentDocumentation/policies/`
- `agentDocumentation/state/*.example.yaml`

Detailed backend and Bridge information remains in:

- `backend/README.md`
- `bridge/README.md`
- `bridge/claim-process/README.md`
