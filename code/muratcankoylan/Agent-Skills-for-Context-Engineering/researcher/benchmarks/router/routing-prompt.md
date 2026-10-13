You are routing an incoming task to the most relevant skill from a curated collection. Your only job is to pick the best skill.

# Available skills ({{SKILL_COUNT}})

Each item is `<name>` followed by the skill's activation description.

{{SKILL_BLOCK}}

# Task

The user has the following task. Read it carefully and identify which skill (if any) most directly applies.

```
{{USER_PROMPT}}
```

# Output

Return ONLY a single JSON object. No prose, no markdown, no code fence.

The JSON object must have exactly these keys:

- `ranking`: an array of skill names, ordered most-to-least relevant. Include only skills you genuinely consider relevant. At least one skill must appear.
- `confidence`: a number between 0.0 and 1.0 describing your confidence in the top choice.
- `rationale`: a single sentence explaining why the top choice is the best match.

Example:

```
{"ranking":["skill-a","skill-b"],"confidence":0.82,"rationale":"The task is about X, which is the core scope of skill-a."}
```
