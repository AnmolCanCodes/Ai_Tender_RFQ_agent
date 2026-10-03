# OpsPilot

### AI-Powered Application Reliability & Incident Investigation Platform

OpsPilot is a full-stack developer operations platform that helps engineering teams monitor application events, detect incidents, investigate failures, and understand their possible causes using AI.

Instead of simply providing an AI chatbot, OpsPilot combines:

* Application event ingestion
* Incident detection
* Incident management
* Historical incident analysis
* Technical-document RAG
* AI-powered investigation
* Deployment context
* Redis-based background processing
* PostgreSQL persistence
* Dockerized infrastructure
* Automated CI/CD

The goal is to simulate a realistic production-oriented developer platform while demonstrating full-stack engineering and practical AI engineering.

---

## Problem

When an application starts failing, developers usually have to inspect several sources manually:

* application logs
* error events
* deployment history
* documentation
* previous incidents
* service information
* operational runbooks

This makes debugging slower, especially when the cause is not immediately obvious.

OpsPilot centralizes this information and uses an AI investigation workflow to help developers understand an incident and identify evidence-backed possible causes.

---

# Core Workflow

```text
                    Developer
                        │
                        ▼
                ┌───────────────┐
                │ React Web App │
                └───────┬───────┘
                        │
                        ▼
                 ┌─────────────┐
                 │   FastAPI   │
                 │     API     │
                 └──────┬──────┘
                        │
          ┌─────────────┼──────────────┐
          │             │              │
          ▼             ▼              ▼
    PostgreSQL        Redis        AI Engine
          │             │              │
          │             │         ┌────┴─────┐
          │             │         │ LangGraph│
          │             │         └────┬─────┘
          │             │              │
          │             │       ┌──────┴──────┐
          │             │       │             │
          │             │      RAG          Tools
          │             │       │             │
          │             │       └──────┬──────┘
          │             │              │
          │             │        Hugging Face
          │             │          Inference
          │             │              │
          └─────────────┴──────────────┘
```

---

# How OpsPilot Works

## 1. Create a project

A developer creates an OpsPilot project.

Example:

```text
Project:
ShopFlow

Environment:
Production

Services:
- checkout
- payments
- users
- notifications
```

OpsPilot generates an API key for event ingestion.

---

## 2. Application sends events

Applications can send events to OpsPilot using a REST API.

Example:

```http
POST /api/v1/events
```

Example payload:

```json
{
  "service": "checkout",
  "environment": "production",
  "level": "ERROR",
  "message": "Database connection timeout",
  "timestamp": "2026-10-03T10:32:14Z",
  "metadata": {
    "endpoint": "/checkout",
    "status_code": 500
  }
}
```

OpsPilot validates and stores the event.

---

# 3. Event processing

Incoming events are processed asynchronously.

```text
Application
     │
     ▼
FastAPI
     │
     ▼
Redis Queue
     │
     ▼
Background Worker
     │
     ├── store event
     ├── update statistics
     ├── check thresholds
     └── detect potential incident
```

Redis is used for background processing and later can also support caching and rate limiting.

---

# 4. Incident Detection

OpsPilot monitors incoming events for abnormal behavior.

Examples:

```text
500 errors suddenly increase

Error rate exceeds threshold

Repeated exception occurs

Service becomes unavailable

Large latency increase
```

When configured conditions are met, OpsPilot creates an incident.

Example:

```text
INC-1042

Service:
checkout

Severity:
HIGH

Status:
OPEN

Started:
14:32 UTC

Reason:
500 error rate exceeded threshold
```

---

# 5. Incident Timeline

OpsPilot builds a chronological timeline from available information.

Example:

```text
14:27  Deployment v1.8.2
14:29  API latency increased
14:31  Database connections increased
14:32  500 errors increased
14:33  Incident created
14:34  AI investigation started
```

This helps developers correlate events.

---

# 6. Documentation RAG

Developers can upload technical documentation such as:

```text
README.md
architecture.md
API documentation
database documentation
runbooks
deployment documentation
troubleshooting guides
previous incident reports
```

The ingestion pipeline performs:

```text
Document
   │
   ▼
Text extraction
   │
   ▼
Chunking
   │
   ▼
Hugging Face Embedding Model
   │
   ▼
Vector Embeddings
   │
   ▼
PostgreSQL + pgvector
```

During an investigation, relevant chunks are retrieved and provided to the AI.

---

# 7. AI Investigation

The AI investigation system is implemented using LangGraph.

The investigation is not simply:

```python
llm.invoke("Why did my server fail?")
```

Instead, OpsPilot runs a structured workflow.

```text
START
  │
  ▼
Understand Incident
  │
  ▼
Retrieve Relevant Events
  │
  ▼
Retrieve Documentation
  │
  ▼
Retrieve Historical Incidents
  │
  ▼
Inspect Deployment Context
  │
  ▼
Generate Hypotheses
  │
  ▼
Validate Against Evidence
  │
  ▼
Generate Investigation Report
  │
  ▼
END
```

The AI can produce:

```text
Incident #1042

Summary:
Checkout service experienced elevated 500 errors.

Possible cause:
Database connection exhaustion.

Evidence:
- Database pool reached configured limit.
- 81% of failures occurred on /checkout.
- Error spike began shortly after deployment v1.8.2.
- Similar historical incident occurred previously.

Recommended investigation:
1. Inspect database connection configuration.
2. Review database-related changes in v1.8.2.
3. Check connection lifecycle in checkout handlers.

Sources:
- Event #183921
- Deployment #182
- Runbook: database-incidents.md
- Historical incident #921
```

The system should clearly distinguish evidence from AI-generated hypotheses.

---

# Hugging Face Integration

OpsPilot uses the Hugging Face API for AI inference.

Two model capabilities are required:

### LLM

Used for:

* incident summarization
* hypothesis generation
* evidence analysis
* investigation reports
* natural-language responses

### Embedding Model

Used for:

* document embeddings
* semantic search
* historical incident retrieval
* technical knowledge retrieval

The exact models should be configurable through environment variables rather than hard-coded throughout the application.

Example:

```env
HF_API_TOKEN=your_token

HF_LLM_MODEL=your_llm_model
HF_EMBEDDING_MODEL=your_embedding_model
```

This allows the models to be changed without modifying the application architecture.

---

# Main Features

## Authentication

* User registration
* Login
* JWT authentication
* Password hashing
* Protected routes
* Logout

## Authorization

* Project ownership
* Project members
* Role-based permissions

Example roles:

```text
OWNER
ADMIN
MEMBER
VIEWER
```

---

## Project Management

* Create project
* Update project
* Delete project
* Project API keys
* Environment management
* Service management

---

## Event Ingestion

* REST API
* API-key authentication
* Event validation
* Event storage
* Event filtering
* Event search
* Pagination

---

## Incident Management

* Automatic incident creation
* Manual incident creation
* Severity
* Status
* Assignment
* Timeline
* Comments
* Resolution notes

Incident statuses:

```text
OPEN
INVESTIGATING
RESOLVED
IGNORED
```

---

## AI Investigation

* Incident summarization
* Evidence retrieval
* RAG
* Historical incident retrieval
* Deployment correlation
* Hypothesis generation
* Evidence validation
* Investigation report

---

## Knowledge Base

* Upload documents
* Process documents
* Chunk documents
* Generate embeddings
* Semantic retrieval
* Source citations

---

## Deployment Tracking

Developers can record deployments:

```text
version
service
environment
commit
deployed_at
deployed_by
```

This allows the AI to correlate incidents with recent deployments.

---

## Redis

Redis will be used for:

* Background job queues
* Event processing
* Caching
* Rate limiting

---

## Docker

The application will be containerized.

Development environment:

```text
React
FastAPI
PostgreSQL
Redis
Worker
```

can be started using:

```bash
docker compose up
```

---

## CI/CD

GitHub Actions will automate:

```text
Push / Pull Request
        │
        ▼
Lint
        │
        ▼
Tests
        │
        ▼
Build
        │
        ▼
Docker Build
        │
        ▼
Deployment
```

---

# Technology Stack

## Frontend

* React
* TypeScript
* Vite
* Tailwind CSS

## Backend

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic

## Database

* PostgreSQL
* pgvector

## AI

* Hugging Face Inference API
* LangChain
* LangGraph
* Embeddings
* RAG

## Infrastructure

* Redis
* Docker
* Docker Compose

## CI/CD

* GitHub Actions

## Deployment

Initial deployment can use:

* Vercel for frontend
* Railway / Render for backend and infrastructure

Cloud infrastructure can be expanded later.

---

# Project Architecture

```text
ops-pilot/
│
├── frontend/
│
├── backend/
│
├── worker/
│
├── docs/
│
├── docker/
│
├── .github/
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
└── LICENSE
```

---

# Security Considerations

OpsPilot should never expose sensitive information unnecessarily.

Important security practices include:

* hashed passwords
* JWT authentication
* API key hashing
* environment variables for secrets
* project-level authorization
* rate limiting
* input validation
* file upload restrictions
* safe logging
* protection against prompt injection in retrieved documents

AI-generated recommendations should be treated as assistance rather than automatically executed actions.

---

# Development Philosophy

OpsPilot is intentionally built incrementally.

The project does not attempt to implement every infrastructure technology at once.

The development progression is:

```text
Phase 1
Core full-stack application

        ↓

Phase 2
AI + RAG

        ↓

Phase 3
Redis + background processing

        ↓

Phase 4
Docker

        ↓

Phase 5
Testing + CI/CD

        ↓

Phase 6
Production hardening

        ↓

Phase 7
Optional cloud/Kubernetes improvements
```

The goal is to understand every technology through actual product requirements rather than adding technologies simply for a resume.

---

# Future Improvements

Potential future features include:

* GitHub integration
* automatic deployment ingestion
* Slack/Discord notifications
* email alerts
* OpenTelemetry integration
* metrics ingestion
* distributed tracing
* advanced anomaly detection
* Kubernetes deployment
* cloud infrastructure
* team analytics
* incident postmortem generation
* AI-generated runbooks

These are intentionally outside the initial MVP.

---

# Learning Objectives

By completing OpsPilot, the developer should gain practical experience with:

* Full-stack application architecture
* REST API design
* Authentication and authorization
* PostgreSQL database design
* Vector search
* RAG
* LangChain
* LangGraph
* LLM API integration
* Embedding pipelines
* Redis
* Asynchronous processing
* Docker
* CI/CD
* Automated testing
* Production deployment
* Error handling
* API security
* System design

---

# Project Goal

OpsPilot is designed to demonstrate that the developer can build more than an AI demo.

The project should demonstrate the ability to:

> **Design, build, deploy and maintain a production-oriented full-stack application that uses AI as one component of a larger software system.**

---

## License

MIT
