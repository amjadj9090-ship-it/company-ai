# Company AI v7.9.0 — Core Governance & Operations

## Purpose
Strengthen the internal operating layer before launch by adding controlled record lifecycle management, search, executive visibility and task ownership.

## Core additions
- PATCH lifecycle for permitted core entities.
- Owner-only deletion with audit trail.
- Protected-order update guard.
- Global authenticated search respecting role permissions.
- Executive dashboard for summary, lead pipeline, approvals and recent activity.
- Task assignment endpoint.
- Expanded core summary for AI employees, automations, memberships, agent builds and referrals.

## Security / authority
The central permission engine remains authoritative. Binding contracts and protected financial commitments remain owner-only. Deletion is owner-only. Money-out operations remain blocked for AI/staff.

## Validation
- Python compileall: PASS
- Full automated test suite: PASS
- ZIP integrity: PASS

## Explicitly deferred
Deployment, hosting, domain, production database validation, payment gateways and external channel integrations remain launch-stage tasks and are not part of this release.
