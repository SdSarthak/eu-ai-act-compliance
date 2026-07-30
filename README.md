# EU AI Act Compliance Tool

A SaaS platform that helps startups - especially HR Tech AI companies - comply
with Regulation (EU) 2024/1689, the EU AI Act.

Register your AI systems, classify them against the Act, work through the
obligations that classification produces, and export the documentation a
conformity assessment asks for.

## What it does

**Risk classification.** A deterministic, rule-based engine walks the Act's
decision order: Article 5 prohibited practices first, then Article 6(1) safety
components, then the eight Annex III high-risk areas, then the Article 6(3)
derogation for narrow preparatory tasks, then the Article 50 transparency
triggers. Every verdict comes back with the reasoning, the provisions engaged, a
confidence score and the obligations that follow.

**Compliance checklist.** Saving a classification generates a per-system
checklist from the requirement catalogue for that risk level - Articles 9 to 15,
17, 43, 47, 49, 72 and 73 for high-risk systems; Article 50 duties for limited
risk; Chapter V add-ons for general-purpose models. Items can be marked in
progress, complete or not applicable, with evidence notes. The system's
compliance score and status are derived from the checklist, not entered by hand.
Re-classifying rebuilds the checklist while preserving progress on obligations
that still apply.

**Document generation.** Seven document types, each rendered from live system
data - the classification reasoning, the assessment history and the current
checklist state:

| Document | Basis |
| --- | --- |
| Technical documentation | Annex IV, referenced by Article 11 |
| Risk assessment report | Article 9 |
| EU declaration of conformity | Article 47 |
| Data governance policy | Article 10 |
| Transparency notice | Article 50 |
| Human oversight plan | Article 14 |
| Serious incident report | Article 73 |

Documents are versioned per system and per type, and export to PDF.

**Billing.** Four plans with enforced quotas on AI systems and document types,
plus Stripe Checkout, the customer portal and subscription webhooks. Quotas
apply whether or not Stripe credentials are configured.

## Tech stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, Zustand
- **Auth**: JWT bearer tokens, bcrypt password hashing
- **PDF**: ReportLab
- **Payments**: Stripe

## Quick start

### Docker

```bash
cp backend/.env.example backend/.env   # then set SECRET_KEY
docker compose up -d
```

- Frontend: http://localhost:5173
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

The backend container runs `alembic upgrade head` before starting.

### Manual setup

#### Backend

```bash
cd backend

python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt

copy .env.example .env         # cp on Linux/macOS, then edit it
python -c "import secrets; print(secrets.token_urlsafe(48))"   # SECRET_KEY

alembic upgrade head
uvicorn app.main:app --reload
```

Postgres is the target database, but SQLite works for a quick local run - set
`DATABASE_URL=sqlite:///./compliance.db` in `.env`.

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server proxies `/api` to `http://localhost:8000`. Override with
`API_PROXY_TARGET` when the API is elsewhere.

## Tests

```bash
cd backend
python -m pytest              # 103 tests
python -m pytest --cov=app    # with coverage
```

The suite runs against a throwaway SQLite database created per test, so no
external services are needed.

```bash
cd frontend
npm run lint
npm run build                 # also type-checks
```

## Configuration

Every variable is documented in `backend/.env.example`. The ones that matter:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Postgres or SQLite connection string |
| `SECRET_KEY` | JWT signing key - must be changed for any real deployment |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime, default 30 |
| `CORS_ORIGINS` | Comma-separated list of allowed browser origins |
| `FRONTEND_URL` | Base URL for Stripe success and cancel redirects |
| `DOCUMENT_STORAGE_DIR` | Where generated PDFs are written |
| `STRIPE_SECRET_KEY` | Leave blank to run without billing |
| `STRIPE_WEBHOOK_SECRET` | Required to accept Stripe webhooks |
| `STRIPE_PRICE_STARTER` / `_GROWTH` / `_SCALE` | Recurring price IDs per plan |

With Stripe unconfigured the app runs normally: plans and quotas still apply,
and the checkout, portal and webhook endpoints return 503.

## API

All routes are under `/api/v1`. Interactive docs at `/docs`.

### Authentication
- `POST /auth/register` - create an account
- `POST /auth/login` - OAuth2 password grant, returns a bearer token
- `GET /auth/me` - current user
- `PATCH /auth/me` - update the profile (the company name appears on documents)

### AI systems
- `GET /ai-systems/` - list
- `POST /ai-systems/` - create (subject to the plan quota)
- `GET /ai-systems/{id}` - detail with checklist progress
- `PUT /ai-systems/{id}` - update
- `DELETE /ai-systems/{id}` - delete with its assessments, checklist and documents
- `POST /ai-systems/{id}/recalculate` - rebuild the checklist and rescore

### Risk classification
- `POST /classification/classify` - classify without saving
- `POST /classification/classify/{system_id}` - classify, store the assessment and build the checklist
- `GET /classification/assessments/{system_id}` - assessment history

### Compliance
- `GET /compliance/overview` - portfolio dashboard figures
- `GET /compliance/systems/{system_id}/checklist` - obligations and their status
- `POST /compliance/systems/{system_id}/checklist/sync` - rebuild from the catalogue
- `PATCH /compliance/items/{item_id}` - update status or evidence notes

### Documents
- `GET /documents/templates` - document types available on the current plan
- `POST /documents/generate` - generate one document
- `POST /documents/systems/{system_id}/generate-all` - generate the whole pack
- `GET /documents/` - list, optionally filtered by `ai_system_id`
- `PATCH /documents/{id}` - edit title, content or review status
- `GET /documents/{id}/pdf` - export to PDF
- `DELETE /documents/{id}` - delete

### Billing
- `GET /billing/plans` - public plan catalogue
- `GET /billing/subscription` - current plan and quota usage
- `POST /billing/checkout` - start a Stripe Checkout session
- `POST /billing/portal` - open the Stripe customer portal
- `POST /billing/webhook` - Stripe subscription lifecycle events

## EU AI Act risk levels

1. **Unacceptable** - prohibited under Article 5 (social scoring, real-time
   remote biometric identification in public spaces, emotion inference at work,
   untargeted facial scraping, and five more).
2. **High** - Article 6 and Annex III (recruitment and worker management,
   creditworthiness, education, essential services, law enforcement, migration,
   justice, democratic processes, biometrics, critical infrastructure). The full
   Chapter III obligations apply.
3. **Limited** - Article 50 transparency duties (chatbots, synthetic content,
   emotion recognition, biometric categorisation).
4. **Minimal** - no specific obligations beyond Article 4 AI literacy.

The Article 6(3) derogation is modelled too: a listed system that performs only a
narrow preparatory task under meaningful human review can fall outside the
high-risk category, and the tool flags that this must be documented and notified.

## Target market

HR Tech AI startups building CV screening tools, candidate ranking systems,
automated interview analysis and performance evaluation AI - all squarely inside
Annex III point 4.

## Pricing

| Plan | Price | AI systems | Documents |
| --- | --- | --- | --- |
| Free | $0/mo | 1 | Risk assessment |
| Starter | $99/mo | 1 | Technical documentation, risk assessment, declaration of conformity |
| Growth | $299/mo | 5 | All types |
| Scale | $499/mo | Unlimited | All types, priority support |

## Project structure

```
backend/
  alembic/            Database migrations
  app/
    api/v1/           Route handlers (thin)
    core/             Config, database, security
    models/           SQLAlchemy models
    schemas/          Pydantic request and response models
    services/         Domain logic: classification, requirements,
                      compliance scoring, documents, billing
  tests/              Pytest suite
frontend/
  src/
    components/       Shared UI
    pages/            Route pages
    services/         Typed API client
    stores/           Zustand auth store
```

## Disclaimer

This tool supports compliance work; it is not legal advice. The classification
engine encodes the text of the Regulation as published, but a real conformity
assessment needs qualified legal review.

## License

MIT
