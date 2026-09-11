# Company AI — Central AI / CEO Brain Orchestrator v8.3

## Purpose
The Central AI is now the orchestration layer between customer/website intake and Company AI specialist agents and departments.

## Core flow
`visitor/customer request → Central AI intake → classification → specialist routing → task → integrated review → result`

Protected intents use:
`request → classification → specialist plan → owner approval gate`

## Implemented
- Public `/api/central-ai/intake` for website/voice/avatar entry.
- Authenticated `/api/central-ai/plan` for internal planning.
- `/api/central-ai/plans` for executive visibility.
- `/api/central-ai/plans/{plan_id}/advance` for controlled orchestration progress.
- Backward-compatible `/api/orchestrator/plan` now delegates to the Central AI engine.
- Intent classification for sales, web, apps, marketing, trade, support, finance, legal, entrepreneurship, cybersecurity and central/general work.
- Confidence and classification scores stored with every decision.
- Every plan creates a task and a central decision record.
- Finance/legal/cybersecurity intents are protected and stop at the human-owner approval boundary.
- Universal language field is preserved (`auto` by default) so voice/avatar and website layers can pass the visitor language into orchestration.
- Audit records are created for orchestration activity.

## Governance
The orchestrator does not gain authority to withdraw/transfer company funds, sign binding contracts, or bypass owner-only protected operations.

## Validation
- 36 automated tests passed.
- Python compileall passed.
- ZIP integrity verified after packaging.
