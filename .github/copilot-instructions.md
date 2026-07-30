# EU AI Act Compliance Tool - Project Guidelines

## Overview
SaaS platform helping startups (especially HR Tech AI companies) comply with EU AI Act regulations.

## Tech Stack
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS
- **Auth**: JWT tokens
- **Payments**: Stripe
- **Infrastructure**: Docker Compose

## Project Structure
```
/backend          - FastAPI application
  /app
    /api/v1       - API routes
    /core         - Config, security, database
    /models       - SQLAlchemy models
    /schemas      - Pydantic schemas
    /services     - Business logic
/frontend         - React application
  /src
    /components   - Reusable UI components
    /pages        - Route pages
    /hooks        - Custom React hooks
    /services     - API clients
    /stores       - State management
```

## EU AI Act Risk Categories
1. **Unacceptable Risk** - Banned (social scoring, real-time biometric ID)
2. **High Risk** - Strict requirements (HR/recruitment AI, credit scoring)
3. **Limited Risk** - Transparency obligations (chatbots, emotion recognition)
4. **Minimal Risk** - No specific requirements (spam filters, games)

## Key Features
- Risk classification questionnaire
- Documentation generator (technical docs, risk assessments)
- Compliance dashboard with progress tracking
- Alert system for regulatory updates

## Development Commands
```bash
# Backend
cd backend && uvicorn app.main:app --reload

# Frontend
cd frontend && npm run dev

# Docker
docker-compose up -d
```

## Target Market
HR Tech AI startups (CV screening, candidate ranking, automated hiring)
Pricing: $99-499/month for startups
