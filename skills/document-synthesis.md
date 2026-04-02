# Skill: Document Synthesis

## Description
Combine information from multiple documents or sources into a cohesive output document with proper structure and citations.

## Agent Requirements
- Document retrieval tools (MCP servers)
- LLM for synthesis and writing

## Input
- `sources`: List of document references or search queries
- `output_format`: report | executive_summary | comparison | briefing
- `focus_areas`: Key topics to emphasize

## Output
- Synthesized document in requested format
- Source attribution
- Key takeaways section

## Example Task Template
```
Synthesize information from the following sources into a {output_format}:

Sources: {sources}
Focus areas: {focus_areas}

Structure the output with clear sections, proper citations,
and a key takeaways summary at the end.
```

## Tags
- document-synthesis
- writing
- multi-source
- reporting
