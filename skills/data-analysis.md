# Skill: Data Analysis

## Description
Analyze datasets, generate visualizations, compute statistics, and extract insights using the code interpreter.

## Agent Requirements
- Code interpreter with Python data science libraries
- LLM for interpretation and narrative generation

## Input
- `data_source`: URL, blob reference, or inline data
- `analysis_type`: exploratory | statistical | trend | comparison
- `questions`: Specific questions to answer

## Output
- Analysis summary with key insights
- Visualizations (stored in blob storage)
- Statistical metrics
- Recommendations

## Example Task Template
```
Analyze the provided dataset and answer the following questions:
{questions}

Data source: {data_source}
Analysis type: {analysis_type}

Use Python with pandas, matplotlib, and scipy for analysis.
Generate visualizations and save them.
Provide a clear narrative summary of findings.
```

## Tags
- data-analysis
- visualization
- statistics
- code-interpreter
