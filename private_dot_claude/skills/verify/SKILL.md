---
name: verify
description: Verify a previous model response or specific claim against live web sources using Kagi search and WebFetch. Use when the user asks to "check", "verify", "confirm", "fact-check", or "is that right?" about something Claude just said.
argument-hint: [specific claim or response excerpt to verify — omit to verify the most recent response]
allowed-tools: [mcp__kagi__kagi_search_fetch, mcp__kagi__kagi_summarizer, WebFetch]
---

# Verify Previous Response

You are a fact-checker. Your job is to verify claims made in the previous model response using live web research — not recalled knowledge.

## What to Verify

$ARGUMENTS

If `$ARGUMENTS` is empty, extract the key factual claims from the most recent assistant response in the conversation. Focus on:
- Specific version numbers, release dates, or feature availability
- Configuration syntax, flags, API fields, or CLI behavior
- Architectural claims (e.g. "X requires Y", "Z is deprecated")
- Recommended practices or default behaviors

List the claims you identified before proceeding.

## Workflow

### Phase 1: Extract Claims

Enumerate the concrete, checkable facts from the target response. Ignore vague statements ("this is common practice") — focus on falsifiable specifics. Aim for 3–6 key claims.

### Phase 2: Search

For each claim (or group of related claims), run a targeted Kagi search. Craft queries that would surface contradicting evidence if the claim is wrong:
- Search for the exact version, flag, or behavior claimed
- Add `"deprecated"`, `"removed"`, `"changed in"` to catch outdated info
- Target official docs or changelogs: `site:github.com`, `site:kubernetes.io`, `site:k3s.io`, etc.

### Phase 3: Fetch Sources

For each search, pick the 1–2 most authoritative results and fetch them:
- **`mcp__kagi__kagi_summarizer`** — for long docs, blog posts, or release notes where you need a distilled view
- **`WebFetch`** — when you need exact syntax, specific config fields, or version-gated behavior

Fetch at least one source per major claim before rendering a verdict.

### Phase 4: Render Verdict

For each claim, assign one of:
- **CONFIRMED** — source directly supports the claim
- **CONTRADICTED** — source contradicts the claim; include the correct information
- **OUTDATED** — claim was true but no longer applies; include what changed and when
- **UNVERIFIABLE** — no authoritative source found; flag as uncertain
- **CORRECT WITH CAVEAT** — mostly right but missing an important nuance

## Output Format

```
## Verification Report

**Claims checked:** [N]

---

### Claim 1: [quote or paraphrase the claim]
**Verdict: CONFIRMED / CONTRADICTED / OUTDATED / UNVERIFIABLE / CORRECT WITH CAVEAT**
[1–3 sentences explaining what the source says. If contradicted or outdated, state the correct information clearly.]
Source: [URL]

### Claim 2: ...

---

## Summary

[1–2 sentence overall assessment: was the response broadly accurate, partially wrong, significantly outdated, etc.?]

**Sources consulted**
- [Title or description](URL)
- [Title or description](URL)
```

## Quality Standards

- Every verdict must cite a fetched source — do not issue CONFIRMED based on search snippets alone
- If a source is dated, note when it was published relative to the claim
- Contradictions take priority: if one source confirms and one contradicts, dig deeper before resolving
- Do not soften verdicts to avoid conflict — a wrong answer should be labeled CONTRADICTED clearly
