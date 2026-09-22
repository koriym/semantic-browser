# 1. Record Architecture Decisions

- Status: accepted
- Date: 2026-09-21

## Context

This project is a PoC validating a new concept, and many technical choices are expected over its lifetime. Without a record of why key design decisions were made, tracing "why is it like this?" later becomes difficult, risking inconsistent changes.

## Decision

We record significant architectural decisions as lightweight ADRs (Architecture Decision Records) in the `/docs/adr` directory.

The format follows Michael Nygard's simple structure (Title, Status, Context, Decision, Consequences).

## Consequences

- **Positive:**
  - Design intent becomes explicit, making the code easier to understand for future developers (or a future self).
  - New members gain a valuable resource for learning the project's history.
  - Ad hoc changes are discouraged, making a consistent architecture easier to maintain.
- **Negative:**
  - A small overhead of writing a document for each decision.
