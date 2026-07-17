# ADR-0001 — Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-07-16

## Context

`cofferdam` is built with a document-driven ("Scribe Coding") methodology in
which design decisions must be discoverable and durable, so that later work —
by a human or an AI agent — does not silently re-open settled questions or
contradict earlier reasoning.

## Decision

We keep Architecture Decision Records under `docs/adr/`, one file per decision,
using Michael Nygard's template (Context / Decision / Consequences). ADRs are
immutable; a decision is changed by adding a superseding ADR, not by editing the
original. The [CHANGELOG](../../CHANGELOG.md) mirrors decisions in a "Decided"
section for a chronological view.

## Consequences

- Every significant decision has a stable citation (e.g. "ADR-0005") usable from
  code comments and other docs.
- Reviewers can see *why* as easily as *what*.
- A small amount of ceremony accompanies each real decision; trivial choices do
  not warrant an ADR.
