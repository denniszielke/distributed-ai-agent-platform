# Getting Started

## Prerequisites

- Python 3.12+
- Azure subscription with:
  - Azure OpenAI (GPT-4o + text-embedding-ada-002)
  - Azure AI Search
  - Azure Storage Account
  - Azure Container Apps
  - Azure Container Registry
  - Azure Application Insights
- [Azure Developer CLI (azd)](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/)

## Local Development

### 1. Clone and setup

```bash
git clone https://github.com/denniszielke/distributed-ai-agent-platform.git
cd distributed-ai-agent-platform
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your Azure resource details
```

### 3. Run services locally

```bash
# Terminal 1: Swarm Controller
cd src/swarm_controller && uvicorn app:app --port 8000

# Terminal 2: Planner Agent
cd src/planner_agent && uvicorn app:app --port 8001

# Terminal 3: Swarm Registry
cd src/swarm_registry && uvicorn app:app --port 8002

# Terminal 4: Aggregator Agent
cd src/aggregator_agent && uvicorn app:app --port 8003

# Terminal 5: MCP Server
cd src/swarm_mcp_server_foundry && python server.py

# Terminal 6: Dashboard
cd src/swarm_dashboard && uvicorn app:app --port 8080
```

### 4. Deploy to Azure

```bash
azd auth login
azd up
```

## Deploying Individual Services

```bash
# Build and deploy a single service
./azd-hooks/deploy.sh <service-name> <env-name>

# Examples:
./azd-hooks/deploy.sh swarm-controller myenv
./azd-hooks/deploy.sh planner-agent myenv
```
