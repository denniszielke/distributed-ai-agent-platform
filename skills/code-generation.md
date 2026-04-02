# Skill: Code Generation and Analysis

## Description
Generate, analyze, or refactor code based on specifications. Uses code interpreter for validation and testing.

## Agent Requirements
- Code interpreter session pool access
- LLM with strong coding capabilities

## Input
- `specification`: What code to generate or analyze
- `language`: Target programming language
- `action`: generate | analyze | refactor | test

## Output
- Generated/analyzed code
- Explanation of approach
- Test results (if applicable)

## Example Task Template
```
You are a coding specialist. {action} the following:

Specification: {specification}
Language: {language}

Use the code interpreter to validate your work.
Provide clean, well-documented code with explanations.
```

## Tags
- coding
- code-generation
- analysis
- code-interpreter
