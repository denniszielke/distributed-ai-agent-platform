# Agent Swarm Platform

A distributed multi-agent system where specialized agents collaborate to achieve complex objectives. Built on Microsoft Foundry with MCP (Model Context Protocol) server integration.

## Key Principles

- **Distributed Intelligence**: Tasks are divided among specialized agents, enabling parallel processing and efficiency
- **Emergent Behavior**: Interactions among agents create sophisticated solutions beyond individual capabilities
- **Adaptive Response**: The swarm dynamically adjusts to changing conditions, ensuring resilience
- **Collaborative Learning**: Agents share insights and improve collectively via historical execution plan search

## Architecture

```
User → Swarm Controller → Planner Agent → Worker Agents → Aggregator Agent → Result
            ↕                    ↕               ↕               ↕
       MCP Server          AI Search        MCP Tools        SQLite DB
            ↕                    ↕               ↕               ↕
      Azure Storage        Vector DB      Foundry SDK    App Insights
```

| Component | Port | Description |
|-----------|------|-------------|
| `swarm_controller` | 8000 | Central orchestrator – task distribution, lifecycle management |
| `planner_agent` | 8001 | Decomposes objectives into executable task plans |
| `swarm_registry` | 8002 | Catalog of agents, MCP servers, tools, and skills |
| `aggregator_agent` | 8003 | Synthesizes task results into final output |
| `swarm_mcp_server_foundry` | 8004 | MCP server exposing swarm operations |
| `swarm_dashboard` | 8080 | Web UI for monitoring swarm status |

## Communication Layer

- **Azure Storage Queues** – asynchronous messaging between agents and controller
- **Azure Blob Storage** – binary file sharing between agents
- **FastAPI HTTP** – synchronous service-to-service communication

## Quick Start

### Prerequisites

- Python 3.12+
- Azure subscription (OpenAI, AI Search, Storage, Container Apps)
- [Azure Developer CLI](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/)

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env

# Run all services (each in a separate terminal)
cd src/swarm_controller && uvicorn app:app --port 8000
cd src/planner_agent && uvicorn app:app --port 8001
cd src/swarm_registry && uvicorn app:app --port 8002
cd src/aggregator_agent && uvicorn app:app --port 8003
cd src/swarm_mcp_server_foundry && python server.py
cd src/swarm_dashboard && uvicorn app:app --port 8080
```

### Deploy to Azure

```bash
azd auth login
azd up

# Deploy individual services
./azd-hooks/deploy.sh swarm-controller <env-name>
./azd-hooks/deploy.sh planner-agent <env-name>
./azd-hooks/deploy.sh swarm-registry <env-name>
./azd-hooks/deploy.sh aggregator-agent <env-name>
./azd-hooks/deploy.sh swarm-mcp-server-foundry <env-name>
./azd-hooks/deploy.sh swarm-dashboard <env-name>
```

## Project Structure

```
├── agents.md                          # Agent capabilities documentation
├── azure.yaml                         # Azure Developer CLI configuration
├── docs/                              # Documentation
│   ├── architecture.md
│   └── getting-started.md
├── infra/                             # Infrastructure as Code (Bicep)
│   ├── main.bicep                     # Main template
│   ├── ai/                            # OpenAI + AI Search
│   ├── core/host/                     # Container Apps + Registry
│   ├── core/monitor/                  # Application Insights
│   ├── core/security/                 # Key Vault + RBAC
│   └── core/storage/                  # Storage Account
├── skills/                            # Skill definitions (markdown)
│   ├── research-and-summarize.md
│   ├── code-generation.md
│   ├── data-analysis.md
│   ├── document-synthesis.md
│   └── multi-step-workflow.md
└── src/
    ├── swarm_controller/              # Central orchestrator
    ├── planner_agent/                 # Plan decomposition
    ├── aggregator_agent/              # Result aggregation
    ├── swarm_registry/                # Agent/tool registry
    ├── swarm_mcp_server_foundry/      # MCP server interface
    └── swarm_dashboard/               # Web dashboard
```

## License

See [LICENSE](LICENSE) for details.
