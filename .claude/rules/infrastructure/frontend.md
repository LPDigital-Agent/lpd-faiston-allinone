---
paths:
  - "client/**/*"
  - "**/*.tsx"
  - "**/*.ts"
  - "**/*.jsx"
  - "**/*.js"
  - "**/*.css"
  - "**/*.scss"
  - "**/package.json"
---

# Frontend Development Rules

## Authentication Flow

```
Frontend (JWT) → faiston_asset_management (HTTP) → faiston_sga_* (A2A/SigV4)
```

- Frontend authenticates via **Amazon Cognito**
- Frontend calls HTTP orchestrator endpoints
- **NEVER** call A2A agents directly from frontend
- A2A agents use SigV4, not JWT

## General Guidelines

- Keep frontend logic focused on UI/UX
- Business logic belongs in agents, not frontend
- Use proper error handling for agent responses
- Handle HIL (Human-in-the-Loop) interactions gracefully

## SDLC Standards

- Code reviews required
- Automated tests (unit + integration)
- Linting/formatting enforced
- TypeScript preferred over JavaScript
