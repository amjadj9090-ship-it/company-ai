# Company AI v8.4.0 — Layan ↔ Central AI Bridge

This release connects the Layan front-end interaction layer to the Central AI Orchestrator as the primary conversation entry point.

## Flow
Visitor → Layan → Central AI session → message → analysis/routing → specialized department/agent → result → Layan.

## Added
- `window.companyAIBridge` client bridge.
- Session start and message endpoints with graceful local-demo fallback.
- Automatic language passthrough (`auto`) and manual language compatibility.
- Source/channel tagging as `layan` / `web`.
- Context field for future customer/project/task context propagation.
- Visible bridge status indicator in the demo UI.

## Governance
The bridge does not grant financial, legal, contract-signing, money-out, or other protected permissions. Existing central permission controls remain authoritative.

## Important
The front-end bridge is an integration layer. Production deployment should place the API behind the existing authenticated API gateway and connect the Layan voice/avatar runtime to the same session ID.
