# Agent Swarm Platform – Agent Capabilities

## Overview

This document describes the agent types available in the Agent Swarm Platform and their capabilities for distributed task execution.

## Core Agents

### Planner Agent
- **Role**: Decomposes high-level objectives into executable task plans
- **Capabilities**: Intent detection, task decomposition, agent matching, historical plan lookup
- **Access**: Swarm registry (agents, MCP servers, skills), AI Search vector DB
- **Output**: `AgentPlan` with ordered tasks and agent assignments

### Aggregator Agent
- **Role**: Collects and synthesizes results from worker agent executions
- **Capabilities**: Result correlation, objective validation, summary generation, success scoring
- **Access**: Objective database, plan database, task results
- **Output**: Final result summary with confidence score

### Worker Agents (Dynamic)
Worker agents are created at runtime via Microsoft Foundry based on the execution plan. Each worker specializes in a specific task type:

#### Execute Agent
- General-purpose task execution using LLM reasoning
- Follows task templates with specific instructions
- Reports structured results back to the controller

#### Code Interpreter Agent
- Executes dynamically generated Python code
- Uses Foundry session pools for sandboxed execution
- Suitable for data analysis, calculations, file processing

#### MCP Tool Call Agent
- Invokes tools exposed by registered MCP servers
- Bridges between the swarm and external tool ecosystems
- Supports any tool registered in the swarm registry

## Agent Communication

All agents communicate through Azure Storage:
- **Queues**: Task scheduling, status updates, result delivery
- **Blob Storage**: Binary file sharing between agents
- **Controller Inbox**: `swarm-controller-inbox` queue
- **Aggregator Inbox**: `swarm-aggregator-inbox` queue

## Agent Lifecycle

1. **Created**: Foundry agent provisioned with task-specific instructions and tools
2. **Executing**: Agent processes input, optionally calls MCP tools
3. **Completed**: Result posted to controller, agent cleaned up
4. **Recorded**: Execution plan stored in AI Search for future reference

## Extending the Swarm

To add a new agent type:
1. Register the agent in the swarm registry (`/agents` endpoint)
2. Define the agent's capabilities and associated MCP servers
3. Create skill markdown files in `/skills` for the planner to reference
4. The planner will automatically consider the new agent for matching tasks
