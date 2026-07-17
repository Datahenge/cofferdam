# 01 — Overview

## The name

A **cofferdam** is a temporary watertight enclosure built around a submerged or
waterlogged work site and pumped dry, so that construction can proceed on the
foundation without the surrounding water flooding in. This library is the
software analogue: after a Production database is restored into a non-Production
environment, `cofferdam` holds back the Production *outbound behavior* — the
flood of live emails, API calls, payments, webhooks, and report deliveries — so
the restored data can be worked on safely.

## The problem

ERPNext/Frappe environments are routinely refreshed by restoring Production
MariaDB backups into Dev, Test, or Staging. The restored database carries
Production **integration settings, email accounts, API endpoints, encrypted
credentials, payment configuration, webhooks, report recipients, and scheduled
jobs**. If the non-Production environment is permitted to act on those values,
it behaves as if it were Production:

- calling Production vendor API endpoints,
- emailing real customers and suppliers,
- downloading or synchronizing Production data,
- emailing Production-looking reports built from Staging data,
- authorizing or capturing payments and sending statements,
- running scheduled jobs copied from Production configuration.

## The design rule

> **Restored SQL owns business intent. Local environment config owns execution
> authority.**

The database describes *what the business wants to happen*. Whether a given
outbound side effect *may actually happen here* is decided by a **local TOML
policy file** on the environment's filesystem — never stored in, nor restored
from, the database. The engine answers exactly one question per action:

> *Is this specific side effect allowed **here**?*

## Goals (`BR-OVERVIEW-*`)

- **BR-OVERVIEW-001** — Restored Production SQL alone must never be sufficient to
  execute Production side effects in a non-Production environment.
- **BR-OVERVIEW-002** — Allow *selective* sandbox side effects in Dev/Test/Staging.
- **BR-OVERVIEW-003** — Deny non-Production outbound side effects by default
  unless explicitly permitted (see [ADR-0005](adr/0005-fail-closed-by-default.md)).
- **BR-OVERVIEW-004** — Provide a small, boring, inspectable policy model.
- **BR-OVERVIEW-005** — Support human-maintained local policy with comments.
- **BR-OVERVIEW-006** — Make unsafe calls fail closed with clear errors.
- **BR-OVERVIEW-007** — Keep secrets out of logs and exception messages.
- **BR-OVERVIEW-008** — Be usable inside Frappe/ERPNext without a custom Frappe app.
- **BR-OVERVIEW-009** — Remain testable as a normal Python package (no Bench).

## Non-goals

`cofferdam` is an *enforcement and resolution layer*, not a configuration
platform. The first releases deliberately do **not** provide: DocTypes, Desk UI,
MariaDB tables, migrations, background jobs, a remote/dynamic policy service, hot
reload across workers, an OPA/Rego-style general policy language, a full HTTP
client replacement, a full email subsystem replacement, or secret custody
comparable to Vault / AWS Secrets Manager. A thin optional Frappe app *may* be
added later if Desk UI, fixtures, or Bench commands are needed.

## What ships in v1

TOML policy loading; strict validation; environment identification; per-effect
allow/deny decisions; env-var credential resolution with redaction; a
policy-checked HTTP helper (optional extra); email *policy checks*; Frappe
site-policy discovery helpers; and a `validate` / `inspect` / `decide` CLI. See
[14 — Acceptance Criteria](14-acceptance-criteria.md) for the full checklist and
status.
