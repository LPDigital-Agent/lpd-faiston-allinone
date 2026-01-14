---
paths:
  - "**/*.py"
  - "server/**/*"
  - "**/lambda*/**/*"
  - "**/requirements*.txt"
  - "**/pyproject.toml"
---

# Python & Lambda Runtime Rules

## Lambda Runtime Policy

ALL AWS Lambda functions MUST use:
- **Architecture:** `arm64`
- **Runtime:** `Python 3.13`

## Lambda Context

Lambda is allowed ONLY as an execution substrate required by AWS Bedrock AgentCore.

Do NOT design standalone Lambda microservices—this is an agentic platform.

## SDLC & Clean Code

Follow state-of-the-art practices:
- Code reviews
- Automated tests
- CI/CD pipelines
- Linting/formatting (ruff, black)
- Maintainable, readable code

## Security (Pentest-Ready)

Platform MUST be security-first, aligned with:
- OWASP
- NIST CSF
- MITRE ATT&CK
- CIS
- AWS Security
- AWS Well-Architected Security Pillar
- Microsoft SDL
