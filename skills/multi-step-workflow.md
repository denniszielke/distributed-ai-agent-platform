# Skill: Multi-Step Workflow

## Description
Execute a complex multi-step workflow that involves coordination between multiple tools, data transformations, and decision points.

## Agent Requirements
- Access to multiple MCP tool servers
- Code interpreter for data transformations
- LLM for decision-making at branch points

## Input
- `workflow_description`: Natural language description of the workflow
- `steps`: Optional pre-defined step list
- `constraints`: Time limits, quality thresholds, etc.

## Output
- Step-by-step execution log
- Final result for each step
- Overall workflow outcome
- Error report (if any steps failed)

## Example Task Template
```
Execute the following multi-step workflow:

{workflow_description}

Steps to follow:
{steps}

Constraints: {constraints}

Execute each step in order. If a step fails, document the error
and determine if the workflow can continue. Report results for
each step and provide an overall outcome summary.
```

## Tags
- workflow
- multi-step
- orchestration
- automation
