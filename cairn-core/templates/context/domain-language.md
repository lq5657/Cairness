---
alwaysApply: true
---
# Domain Language

This file records the shared domain vocabulary that future `cc-*` commands should use in specs, tasks, reviews, tests, and system explanations.

It is not split by programming language. Split it only by domain context or bounded context when a repo has multiple business vocabularies.

## Usage Rules

- Record domain concepts, product concepts, business states, and user-facing nouns that reduce ambiguity.
- Do not record general programming terms, framework names, package names, or language-specific implementation details.
- Prefer one canonical term. Put rejected aliases under `_Avoid_`.
- When a user uses a term that conflicts with this file, call out the conflict before freezing scope.
- If multiple contexts exist, keep this file as the root map and link to context-specific files such as `.cairness/context/domain/ordering.md`.

## Terms

**Term**: One-sentence definition of the domain concept.
_Avoid_: ambiguous-alias, implementation-name

## Relationships

- **Term A** relates to **Term B** in a precise way.

## Flagged Ambiguities

- `ambiguous term`: pending / resolved. Record the competing meanings and the selected canonical term when confirmed.

## Context Splits

Use this section only when one glossary would mix unrelated domain languages.

| Context | Glossary | Scope | Relationship |
|---------|----------|-------|--------------|
| default | this file | Whole project or single domain context | none |
