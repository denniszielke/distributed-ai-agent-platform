# Skill: Research and Summarize

## Description
Research a topic using available tools and produce a comprehensive summary with key findings, sources, and recommendations.

## Agent Requirements
- Access to web search or document retrieval MCP tools
- LLM reasoning capabilities for synthesis

## Input
- `topic`: The subject to research
- `depth`: shallow | medium | deep
- `format`: bullet_points | narrative | structured

## Output
- Summary text with key findings
- List of sources consulted
- Confidence score (1-100)

## Example Task Template
```
Research the following topic thoroughly: {topic}

Use available search and document tools to gather information.
Synthesize findings into a {format} summary at {depth} depth.
Include key facts, different perspectives, and cite sources.
```

## Tags
- research
- summarization
- knowledge-gathering
