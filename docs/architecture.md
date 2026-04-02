# Architecture Overview

## Agent Swarm Platform

The Agent Swarm Platform implements a distributed multi-agent system where specialized agents collaborate to achieve complex objectives.

### System Flow

```
                    ┌──────────────────┐
                    │   User / API     │
                    └────────┬─────────┘
                             │ 1. Submit Objective
                             ▼
                    ┌──────────────────┐
                    │  Swarm Controller│◄──── MCP Server Interface
                    │    (Brain)       │       (swarm_mcp_server_foundry)
                    └────────┬─────────┘
                             │ 2. Delegate to Planner
                             ▼
                    ┌──────────────────┐
                    │  Planner Agent   │──── AI Search (historical plans)
                    │                  │──── Swarm Registry (agents, tools)
                    └────────┬─────────┘
                             │ 3. Return Plan
                             ▼
                    ┌──────────────────┐
                    │  Swarm Controller│
                    │  (Schedule Tasks)│
                    └────────┬─────────┘
                             │ 4. Launch Workers via Foundry
                    ┌────────┼────────────────┐
                    ▼        ▼                ▼
              ┌──────────┐┌──────────┐┌──────────────┐
              │ Worker 1 ││ Worker 2 ││ Worker N     │
              │ (Execute)││ (Code    ││ (MCP Tool    │
              │          ││  Interp) ││  Call)       │
              └────┬─────┘└────┬─────┘└──────┬───────┘
                   │           │              │
                   └───────────┼──────────────┘
                               │ 5. Results via Queue
                               ▼
                    ┌──────────────────┐
                    │ Aggregator Agent │
                    │ (Synthesize)     │
                    └────────┬─────────┘
                             │ 6. Final Result
                             ▼
                    ┌──────────────────┐
                    │  Swarm Controller│
                    │  (Complete)      │
                    └──────────────────┘
```

### Key Components

| Component | Port | Description |
|-----------|------|-------------|
| Swarm Controller | 8000 | Central orchestrator, task distribution |
| Planner Agent | 8001 | Task decomposition, plan creation |
| Swarm Registry | 8002 | Agent, MCP server, skill catalog |
| Aggregator Agent | 8003 | Result synthesis, objective validation |
| MCP Server | 8004 | Swarm operations via MCP protocol |
| Dashboard | 8080 | Web UI for monitoring |

### Communication Layer

- **Azure Storage Queues**: Asynchronous messaging between agents and controller
- **Azure Blob Storage**: Binary file sharing
- **HTTP APIs**: Direct service-to-service calls for synchronous operations

### Data Storage

- **SQLite**: In-memory database for objectives, plans, and tasks
- **Azure AI Search**: Vector database for historical execution plans
- **Azure Storage**: Communication and file sharing

### Observability

All components send telemetry via OpenTelemetry to Azure Application Insights:
- Distributed tracing across agent interactions
- Metrics for task completion rates and latencies
- Logs for debugging and auditing
