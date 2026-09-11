# Company AI — Security Test Deployment v8.5.1

## Purpose
This is a disposable public test environment, not production. It is designed to expose integration, UX, browser, API-abuse and security configuration problems before launch.

## Protection added
- HTTPS redirect in production.
- HSTS in production.
- Strict Content Security Policy.
- X-Content-Type-Options / X-Frame-Options / Referrer-Policy / Permissions-Policy.
- Request-size limit.
- Rate limiting on public AI/lead/voice entry points.
- Production JWT secret and password pepper are mandatory and generated/stored as platform secrets.
- Production API documentation is disabled.
- Trusted-host allowlist supported.
- CORS must be explicitly configured.
- Admin page is not served by the public test service.
- Public endpoints never execute protected financial, legal, contract, withdrawal or transfer operations.
- Health endpoint for deployment monitoring.

## Data policy
Do not put real customer secrets, payment data, passwords, contracts, API keys, private files, or confidential company documents into this test environment. The default SQLite database is disposable on free hosting and is not a production data store.

## Hosting recommendation
Render Free is suitable for this test because it supports Python web services and managed TLS at no charge, but its free service can sleep after 15 minutes and its local filesystem is ephemeral. This is acceptable for testing, not production.

## Migration
The application is containerized/configured so the same source can later be moved to paid Render, another VPS/cloud, or the final production infrastructure. Production secrets are environment variables, not committed files.
