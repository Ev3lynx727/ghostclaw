# GHOSTCLAW BACKEND SERVICE ARCHITECTURE BLUEPRINT

**Status:** Design Document for CLI → Backend Conversion  
**Date:** March 30, 2026  
**Version:** 0.2.5a1  
**Frontend Design Reference:** REVIEW_FRONTEND.md

---

## 1. OVERVIEW: CLI TO BACKEND TRANSFORMATION

### Current State (PyPI Package)
```
ghostclaw (CLI Package)
├── CLI Entry: src/ghostclaw/cli/ghostclaw.py
├── Business Logic: src/ghostclaw/core/
├── Distribution: PyPI (pip install ghostclaw)
└── Execution: Single-threaded, blocking, user-facing
```

### Target State (Backend Service)
```
ghostclaw-backend (Service)
├── API Layer: FastAPI REST endpoints
├── Business Logic: Unchanged (core/ reused as library)
├── Distribution: Docker container + systemd
├── Execution: Async, multi-worker, request-driven
├── Storage: PostgreSQL (Supabase) + Redis
├── Jobs: Celery/RQ for long-running analyses
└── Auth: JWT + RBAC per user/team
```

### Key Transformation Points
| Aspect | CLI | Backend Service |
|--------|-----|-----------------|
| **Entry Point** | `ghostclaw` CLI command | FastAPI `POST /api/analyses` |
| **Execution** | Synchronous, user waits | Asynchronous, job queue |
| **Database** | SQLite (optional) | PostgreSQL (required) |
| **Output** | Stdout/file | JSON response + DB |
| **Auth** | None | JWT tokens, user context |
| **Scaling** | Single machine | Multi-worker, load-balanced |
| **Observability** | Logfire (local) | Logfire + distributed tracing |
| **Config** | File-based + env | Server-side + request params |

---

## 2. PROPOSED BACKEND ARCHITECTURE

### 2.1 High-Level Service Layout

```
┌──────────────────────────────────────────────────────────────────┐
│                    NGINX / Load Balancer                         │
│                  (reverse proxy, SSL termination)                │
└─────────────────────────────────────────┬──────────────────────┘
                                          │
                ┌─────────────────────────┼─────────────────────────┐
                ↓                         ↓                         ↓
        ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
        │  FastAPI     │         │  FastAPI     │         │  FastAPI     │
        │  Worker 1    │         │  Worker 2    │         │  Worker N    │
        │  (port 8001) │         │  (port 8002) │         │  (port 800N) │
        └──────┬───────┘         └──────┬───────┘         └──────┬───────┘
               │                        │                        │
               └────────────────────────┼────────────────────────┘
                                        │
        ┌───────────────────────────────┼───────────────────────────┐
        ↓                               ↓                           ↓
   ┌─────────────┐             ┌──────────────┐          ┌──────────────┐
   │  Celery     │             │  PostgreSQL  │          │    Redis     │
   │  Beat       │             │  (Supabase)  │          │    Cache     │
   │  (scheduler)│             │  - Users     │          │  - Sessions  │
   └─────────────┘             │  - Analyses  │          │  - Job queue │
                               │  - Reports   │          │  - Hotdata   │
        │                      │  - Audit log │          └──────────────┘
        ↓                      └──────────────┘
   ┌─────────────┐
   │  Celery     │
   │  Worker 1   │
   │  Worker 2   │
   │  Worker N   │
   │  (analysis) │
   └─────────────┘
        │
        ↓
   ┌─────────────────────┐
   │  GhostAgent +       │  (Unchanged from CLI)
   │  CodebaseAnalyzer   │
   │  + Plugins          │
   │  (Business Logic)   │
   └─────────────────────┘
```

### 2.2 Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ TIER 1: API & AUTH LAYER                                        │
├─────────────────────────────────────────────────────────────────┤
│  app/main.py                                                    │
│  ├── FastAPI app initialization                                │
│  ├── Middleware (CORS, logging, auth)                          │
│  ├── Exception handlers                                         │
│  └── Health check endpoints                                     │
│                                                                 │
│  app/api/v1/                                                   │
│  ├── analyses.py       (POST /analyses, GET /analyses/{id})    │
│  ├── auth.py           (POST /auth/login, POST /auth/register) │
│  ├── reports.py        (GET /reports, GET /reports/{id})       │
│  ├── health.py         (GET /health)                           │
│  └── admin.py          (GET /queue/stats, GET /workers)        │
│                                                                 │
│  app/auth/                                                     │
│  ├── jwt_handler.py    (Token generation, validation)          │
│  ├── permissions.py    (RBAC enforcement)                      │
│  └── models.py         (User, Team, Role schemas)              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TIER 2: BUSINESS LOGIC LAYER                                    │
├─────────────────────────────────────────────────────────────────┤
│  app/services/                                                  │
│  ├── analysis_service.py                                       │
│  │   ├── schedule_analysis(repo_path, user_id) → job_id      │
│  │   ├── get_analysis_status(job_id) → AnalysisStatus         │
│  │   └── get_analysis_result(job_id) → ArchitectureReport     │
│  │                                                             │
│  ├── user_service.py                                           │
│  │   ├── create_user(email, password) → User                  │
│  │   ├── get_user(user_id) → User                             │
│  │   └── update_quota(user_id) → RemainingQuota               │
│  │                                                             │
│  └── repo_service.py                                           │
│      ├── clone_repo(url, target_dir) → local_path             │
│      ├── validate_repo(path) → bool                           │
│      └── cleanup_repo(path) → bool                            │
│                                                                 │
│  app/tasks/ (Celery task definitions)                          │
│  ├── analyze_task.py                                           │
│  │   └── run_ghostclaw_analysis(repo_path) → report           │
│  │                                                             │
│  └── cleanup_task.py                                           │
│      └── cleanup_old_repos(days) → count                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TIER 3: CORE ANALYSIS LAYER                                     │
├─────────────────────────────────────────────────────────────────┤
│  (Imported from src/ghostclaw/core - NO CHANGES)               │
│                                                                 │
│  ghostclaw/                                                    │
│  ├── core/agent.py        (GhostAgent - reused as-is)         │
│  ├── core/analyzer.py     (CodebaseAnalyzer - reused)         │
│  ├── core/adapters/       (PluginRegistry - reused)           │
│  ├── core/llm_client.py   (LLMClient - reused)                │
│  ├── core/models.py       (ArchitectureReport - reused)       │
│  └── core/cache.py        (Cache - enhanced with Redis)       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TIER 4: DATA ACCESS LAYER                                       │
├─────────────────────────────────────────────────────────────────┤
│  app/db/                                                        │
│  ├── models.py            (SQLAlchemy models)                  │
│  ├── schemas.py           (Pydantic schemas for API)           │
│  ├── session.py           (Database session management)        │
│  └── migrations/          (Alembic migrations)                 │
│                                                                 │
│  app/cache/                                                    │
│  ├── redis_client.py      (Redis connection pool)              │
│  ├── job_cache.py         (Job status cache)                   │
│  └── session_cache.py     (User session cache)                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ TIER 5: INFRASTRUCTURE LAYER                                    │
├─────────────────────────────────────────────────────────────────┤
│  config/                                                        │
│  ├── settings.py          (Pydantic settings)                  │
│  ├── database.py          (DB connection)                      │
│  └── cache.py             (DependencyInjection)                │
│                                                                 │
│  docker/                                                        │
│  ├── Dockerfile            (API container)                     │
│  ├── Dockerfile.worker     (Celery worker)                     │
│  ├── Dockerfile.beat       (Celery beat)                       │
│  └── docker-compose.yml    (Local development)                 │
│                                                                 │
│  k8s/                                                           │
│  ├── deployment.yaml       (Kubernetes deployment)             │
│  ├── service.yaml          (K8s service)                       │
│  └── configmap.yaml        (Config management)                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. DETAILED RESTRUCTURING PLAN

### 3.1 Directory Structure (New Backend Layout)

```
ghostclaw-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app entry
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── analyses.py          # POST /v1/analyses
│   │   │   ├── auth.py              # POST /v1/auth/login
│   │   │   ├── reports.py           # GET /v1/reports/{id}
│   │   │   ├── health.py            # GET /v1/health
│   │   │   ├── plugins.py           # GET /v1/plugins
│   │   │   └── admin.py             # GET /v1/admin/queue
│   │   └── deps.py                  # Dependencies (DB session, auth)
│   │
│   ├── auth/
│   │   ├── __init__.py
│   │   ├── jwt_handler.py           # Token generation/validation
│   │   ├── permissions.py           # RBAC logic
│   │   └── models.py                # User, Team, Role
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── analysis_service.py      # Analysis orchestration
│   │   ├── user_service.py          # User management
│   │   ├── repo_service.py          # Repository cloning
│   │   ├── quota_service.py         # Rate limiting
│   │   └── storage_service.py       # Report persistence
│   │
│   ├── tasks/                       # Celery task definitions
│   │   ├── __init__.py
│   │   ├── analyze_task.py          # @app.task run_analysis()
│   │   └── cleanup_task.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py                # SQLAlchemy ORM
│   │   ├── schemas.py               # Pydantic schemas
│   │   ├── session.py               # AsyncSession manager
│   │   └── migrations/              # Alembic (auto-generated)
│   │
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── redis_client.py
│   │   ├── job_cache.py
│   │   └── session_cache.py
│   │
│   └── config/
│       ├── __init__.py
│       ├── settings.py              # Pydantic BaseSettings
│       ├── database.py
│       └── cache.py
│
├── src/ghostclaw/                   # Reused from CLI (unchanged)
│   ├── core/
│   ├── lib/
│   ├── stacks/
│   └── ...
│
├── docker/
│   ├── Dockerfile                   # API + workers
│   ├── Dockerfile.worker
│   ├── Dockerfile.beat
│   └── docker-compose.yml
│
├── k8s/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   └── secrets.yaml
│
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_analysis_service.py
│   │   ├── test_auth.py
│   │   └── test_api_endpoints.py
│   │
│   └── integration/
│       ├── test_analysis_workflow.py
│       └── test_user_workflow.py
│
├── migrations/                      # Alembic migrations
│   ├── versions/
│   └── env.py
│
├── scripts/
│   ├── init_db.py
│   ├── seed_users.py
│   └── health_check.sh
│
├── config/
│   ├── .env.example
│   └── logging.yaml                 # Logging config
│
├── pyproject.toml                   # Dependencies for service
├── requirements.txt
├── Dockerfile
│
├── README.md                        # Backend service docs
└── BACKEND_INTEGRATION.md           # Integration guide (this file)
```

### 3.2 Database Schema (SQLAlchemy Models)

```python
# app/db/models.py

from sqlalchemy import Column, String, Integer, JSON, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=True)
    team_id = Column(String, ForeignKey("teams.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    analyses = relationship("Analysis", back_populates="user")
    team = relationship("Team", back_populates="members")
    
    # Quota tracking
    monthly_quota = Column(Integer, default=100)  # analyses/month
    used_quota = Column(Integer, default=0)
    quota_reset_date = Column(DateTime, default=datetime.utcnow)


class Team(Base):
    __tablename__ = "teams"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    members = relationship("User", back_populates="team")
    analyses = relationship("Analysis", back_populates="team")


class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    team_id = Column(String, ForeignKey("teams.id"), nullable=True)
    
    # Input
    repo_url = Column(String, nullable=False)  # GitHub URL or local path
    repo_path = Column(String, nullable=True)  # Cloned local path
    branch = Column(String, default="main")
    
    # Job tracking
    job_id = Column(String, unique=True, nullable=False)  # Celery task_id
    status = Column(String, default="pending")  # pending, running, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    
    # Results
    vibe_score = Column(Integer, nullable=True)
    report = Column(JSON, nullable=True)  # Full ArchitectureReport
    errors = Column(JSON, default=[])  # List of error messages
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="analyses")
    team = relationship("Team", back_populates="analyses")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)  # create_analysis, view_report, etc.
    resource_type = Column(String, nullable=False)  # Analysis, Report, User
    resource_id = Column(String, nullable=False)
    details = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
```

### 3.3 API Endpoints (FastAPI Routes)

```python
# app/api/v1/analyses.py

from fastapi import APIRouter, Depends, HTTPException, Query
from app.services import AnalysisService
from app.auth import get_current_user
from app.db.schemas import AnalysisCreate, AnalysisResponse
from typing import List

router = APIRouter(prefix="/v1/analyses", tags=["analyses"])

@router.post("", response_model=AnalysisResponse)
async def create_analysis(
    analysis_req: AnalysisCreate,
    user: User = Depends(get_current_user),
    service: AnalysisService = Depends()
):
    """
    Create a new analysis job.
    
    Request:
        {
            "repo_url": "https://github.com/user/repo",
            "branch": "main",
            "use_ai": false
        }
    
    Response:
        {
            "id": "uuid...",
            "user_id": "uuid...",
            "status": "pending",
            "job_id": "celery-task-id",
            "created_at": "2026-03-30T12:00:00Z"
        }
    """
    # Check quota
    if user.monthly_quota <= user.used_quota:
        raise HTTPException(status_code=429, detail="Monthly quota exceeded")
    
    # Schedule analysis
    analysis = await service.schedule_analysis(
        repo_url=analysis_req.repo_url,
        user_id=user.id,
        branch=analysis_req.branch,
        use_ai=analysis_req.use_ai
    )
    return analysis


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: str,
    user: User = Depends(get_current_user),
    service: AnalysisService = Depends()
):
    """Get analysis status and results."""
    analysis = await service.get_analysis(analysis_id, user_id=user.id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.get("", response_model=List[AnalysisResponse])
async def list_analyses(
    user: User = Depends(get_current_user),
    limit: int = Query(10, le=100),
    offset: int = Query(0, ge=0),
    service: AnalysisService = Depends()
):
    """List user's analyses with pagination."""
    analyses = await service.list_analyses(user_id=user.id, limit=limit, offset=offset)
    return analyses


@router.get("/{analysis_id}/status")
async def get_status(
    analysis_id: str,
    user: User = Depends(get_current_user),
    service: AnalysisService = Depends()
):
    """Poll analysis status (job_status + progress)."""
    status = await service.get_status(analysis_id, user_id=user.id)
    # Returns: {"status": "running", "progress": 45, "eta": "2m"}
    return status


@router.delete("/{analysis_id}")
async def cancel_analysis(
    analysis_id: str,
    user: User = Depends(get_current_user),
    service: AnalysisService = Depends()
):
    """Cancel a pending/running analysis."""
    result = await service.cancel_analysis(analysis_id, user_id=user.id)
    return {"message": "Analysis cancelled", "success": result}
```

### 3.4 Celery Tasks

```python
# app/tasks/analyze_task.py

from celery import shared_task, Task
from app.services import AnalysisService, StorageService
from ghostclaw.core.agent import GhostAgent
import logging

logger = logging.getLogger(__name__)

class AnalysisTask(Task):
    """Base task with error handling & logging."""
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@shared_task(bind=True, base=AnalysisTask)
def run_ghostclaw_analysis(
    self,
    analysis_id: str,
    repo_path: str,
    use_ai: bool = False,
    ai_provider: str = "openrouter"
):
    """
    Main analysis task (runs on Celery worker).
    
    Flow:
    1. Initialize GhostAgent (reused from CLI)
    2. Run analysis
    3. Persist report to DB
    4. Update job status
    """
    try:
        logger.info(f"Starting analysis {analysis_id}")
        
        # Update status
        AnalysisService.update_status(analysis_id, "running")
        
        # Run analysis using reused GhostAgent
        agent = GhostAgent(
            repo_path=repo_path,
            use_ai=use_ai,
            ai_provider=ai_provider
        )
        report = agent.analyze()
        
        # Save report
        StorageService.save_report(analysis_id, report)
        
        # Mark complete
        AnalysisService.update_status(
            analysis_id,
            "completed",
            vibe_score=report.vibe_score,
            report_data=report.dict()
        )
        
        logger.info(f"Analysis {analysis_id} completed")
        return {"status": "success", "analysis_id": analysis_id}
        
    except Exception as exc:
        logger.error(f"Analysis {analysis_id} failed: {exc}")
        AnalysisService.update_status(analysis_id, "failed", error=str(exc))
        # Raise for retry
        raise self.retry(exc=exc)


@shared_task
def cleanup_old_repos(days: int = 7):
    """Scheduled task to cleanup old cloned repositories."""
    from app.services import RepoService
    count = RepoService.cleanup_old_repos(days)
    logger.info(f"Cleaned up {count} repositories")
    return count
```

### 3.5 Service Layer

```python
# app/services/analysis_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Analysis
from app.tasks.analyze_task import run_ghostclaw_analysis
from datetime import datetime
import uuid

class AnalysisService:
    """Service for orchestrating analysis workflow."""
    
    @staticmethod
    async def schedule_analysis(
        repo_url: str,
        user_id: str,
        branch: str = "main",
        use_ai: bool = False,
        db: AsyncSession = None
    ) -> Analysis:
        """Schedule a new analysis (create DB record + queue Celery task)."""
        
        # 1. Clone repository
        repo_path = await RepoService.clone_repo(repo_url, branch)
        
        # 2. Create Analysis record
        analysis_id = str(uuid.uuid4())
        analysis = Analysis(
            id=analysis_id,
            user_id=user_id,
            repo_url=repo_url,
            repo_path=repo_path,
            branch=branch,
            status="pending",
            job_id="..."  # Will be set below
        )
        db.add(analysis)
        await db.commit()
        
        # 3. Queue Celery task
        task = run_ghostclaw_analysis.delay(
            analysis_id=analysis_id,
            repo_path=repo_path,
            use_ai=use_ai
        )
        analysis.job_id = task.id
        await db.commit()
        
        return analysis
    
    @staticmethod
    async def get_analysis(analysis_id: str, user_id: str, db: AsyncSession) -> Analysis:
        """Fetch analysis with authorization check."""
        analysis = await db.query(Analysis).filter(
            Analysis.id == analysis_id,
            Analysis.user_id == user_id
        ).first()
        return analysis
    
    @staticmethod
    async def get_status(analysis_id: str, user_id: str, db: AsyncSession) -> dict:
        """Get real-time job status from Celery + DB."""
        analysis = await AnalysisService.get_analysis(analysis_id, user_id, db)
        
        # Get Celery task status
        from celery.result import AsyncResult
        task_result = AsyncResult(analysis.job_id)
        
        return {
            "status": task_result.status,
            "progress": analysis.progress,
            "message": task_result.info if task_result.status == "PROGRESS" else None
        }
    
    @staticmethod
    async def list_analyses(
        user_id: str,
        limit: int = 10,
        offset: int = 0,
        db: AsyncSession = None
    ) -> list[Analysis]:
        """List user's analyses with pagination."""
        analyses = await db.query(Analysis).filter(
            Analysis.user_id == user_id
        ).order_by(
            Analysis.created_at.desc()
        ).limit(limit).offset(offset).all()
        return analyses
```

---

## 4. TECHNOLOGY STACK FOR BACKEND SERVICE

### 4.1 Core Dependencies

```toml
# pyproject.toml

[project]
dependencies = [
    # FastAPI & Web
    "fastapi>=0.100.0",
    "uvicorn[standard]>=0.23.0",
    "pydantic>=2.0.0",
    
    # Database
    "sqlalchemy>=2.0.0",
    "alembic>=1.13.0",
    "asyncpg>=0.28.0",  # PostgreSQL driver
    "psycopg2-binary>=2.9.0",
    
    # Async Task Queue
    "celery>=5.3.0",
    "redis>=5.0.0",
    
    # Authentication
    "python-jose[cryptography]>=3.3.0" ,
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.6",
    
    # Validation & Serialization
    "pydantic-settings>=2.0.0",
    "python-dotenv>=1.0.0",
    
    # Original Ghostclaw deps (still needed)
    "pyyaml>=6.0.3",
    "requests>=2.32.5",
    "httpx>=0.28.1",
    "tenacity>=9.0.0",
    "rich>=14.3.0",
    "openai>=1.50.0",
    "anthropic>=0.40.0",
    "pluggy>=1.0.0",
    "aiosqlite>=0.20.0",
    "lizard>=1.21.2",
    "logfire>=4.30.0",
    "pydantic-ai-slim[openai]>=1.73.0",
    
    # Observability
    "opentelemetry-api>=1.20.0",
    "opentelemetry-sdk>=1.20.0",
    "opentelemetry-exporter-otlp>=1.20.0",
    
    # Utilities
    "GitPython>=3.1.0",
    "python-dateutil>=2.8.0",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "httpx",
    "pytest-cov",
    "black",
    "ruff",
]

docker = [
    "gunicorn>=21.0.0",
]
```

### 4.2 External Services Required

| Service | Purpose | Config |
|---------|---------|--------|
| **PostgreSQL** | Primary database (users, analyses, reports) | `DATABASE_URL=postgresql://...` |
| **Redis** | Job queue, caching, sessions | `REDIS_URL=redis://...` |
| **Supabase** | Managed PostgreSQL + auth (optional) | `SUPABASE_URL`, `SUPABASE_KEY` |
| **OpenAI/Anthropic** | LLM synthesis | `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` |
| **GitHub (optional)** | OAuth for user registration | `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET` |

---

## 5. API SPECIFICATION

### 5.1 Request/Response Schema

```python
# app/db/schemas.py (Pydantic models for API)

from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

class AnalysisCreate(BaseModel):
    repo_url: HttpUrl
    branch: str = "main"
    use_ai: bool = False
    ai_provider: Optional[str] = "openrouter"

class AnalysisResponse(BaseModel):
    id: str
    user_id: str
    repo_url: str
    status: str  # pending, running, completed, failed
    vibe_score: Optional[int] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: int = 0
    
    class Config:
        from_attributes = True

class AnalysisDetailResponse(AnalysisResponse):
    report: Optional[dict] = None
    errors: Optional[list] = None

class UserCreate(BaseModel):
    email: str
    password: str
    name: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    monthly_quota: int
    used_quota: int
    is_active: bool
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class HealthResponse(BaseModel):
    status: str  # "ok", "degraded", "error"
    api_version: str
    db_status: str
    redis_status: str
    workers_active: int
    queue_depth: int
```

### 5.2 Complete Endpoint List

```
AUTH ENDPOINTS
POST   /api/v1/auth/register          Register new user
POST   /api/v1/auth/login             Login (JWT token)
POST   /api/v1/auth/refresh           Refresh token
POST   /api/v1/auth/logout            Logout

ANALYSIS ENDPOINTS
POST   /api/v1/analyses               Create analysis (async)
GET    /api/v1/analyses               List user's analyses
GET    /api/v1/analyses/{id}          Get analysis detail
GET    /api/v1/analyses/{id}/status   Poll job status
DELETE /api/v1/analyses/{id}          Cancel analysis

REPORT ENDPOINTS
GET    /api/v1/reports                List reports
GET    /api/v1/reports/{id}           Get report JSON
GET    /api/v1/reports/{id}/pdf       Export PDF

USER ENDPOINTS
GET    /api/v1/users/me               Get current user
PUT    /api/v1/users/me               Update profile
GET    /api/v1/users/quota            Check quota usage
POST   /api/v1/users/quota/reset      (Admin) reset quota

ADMIN ENDPOINTS (requires admin role)
GET    /api/v1/admin/health           Service health
GET    /api/v1/admin/queue/stats      Celery queue stats
GET    /api/v1/admin/workers          Active workers
POST   /api/v1/admin/config           Update config
GET    /api/v1/admin/audit-logs       Audit trail

PLUGIN ENDPOINTS
GET    /api/v1/plugins                List available plugins
GET    /api/v1/plugins/{name}         Get plugin details
POST   /api/v1/plugins/{name}/enable  (Admin) enable plugin
POST   /api/v1/plugins/{name}/disable (Admin) disable plugin
```

---

## 6. CONVERSION PHASES

### Phase 1: Foundation (Week 1)
**Goal**: Wrap existing GhostAgent in FastAPI, single-threaded

**Tasks**:
- [ ] Create FastAPI project structure (`app/main.py`, `app/api/`)
- [ ] Create PostgreSQL schema (SQLAlchemy models)
- [ ] Implement `/api/v1/analyses` POST endpoint (simple sync call)
- [ ] Implement `/api/v1/analyses/{id}` GET endpoint
- [ ] Add basic error handling & validation
- [ ] Docker setup (single container with FastAPI)
- [ ] Tests for main endpoints

**Deliverables**:
- Synchronous API wrapper around GhostAgent
- Basic PostgreSQL persistence
- Docker container running locally
- Next.js frontend can call `/api/analyses` and get results (slow)

**Frontend Scope**:
- Update `app/api/analyses/route.ts` to call Python backend
- Add loading state, polling for results
- Display vibe score + report

### Phase 2: Async Job Queue (Week 2)
**Goal**: Decouple long-running analysis from HTTP request

**Tasks**:
- [ ] Setup Redis server (docker-compose)
- [ ] Setup Celery with Redis broker
- [ ] Create `analyze_task.py` (Celery task)
- [ ] Refactor `/api/v1/analyses` POST to queue task (return immediately)
- [ ] Implement `/api/v1/analyses/{id}/status` for polling
- [ ] Setup Celery beat for scheduled cleanup tasks
- [ ] Docker: separate API, worker, beat services
- [ ] Tests for task queue, polling

**Deliverables**:
- Async job queue system
- Non-blocking API responses
- Job status polling
- Multiple worker support
- docker-compose with API + worker + Redis

**Frontend Scope**:
- Polling loop for analysis status
- Better UX with "Analysis in progress..." message
- WebSocket support (optional, advanced)

### Phase 3: Authentication & RBAC (Week 3)
**Goal**: User isolation, quotas, team support

**Tasks**:
- [ ] Implement JWT auth system (`auth/jwt_handler.py`)
- [ ] Add user model + registration endpoint
- [ ] Protect all endpoints with `@Depends(get_current_user)`
- [ ] Implement quota tracking & enforcement
- [ ] Add team model + team management endpoints
- [ ] Audit logging middleware
- [ ] RBAC decorator for admin endpoints
- [ ] Tests for auth flows

**Deliverables**:
- User registration & login
- JWT token management
- Quota system (e.g., 100 analyses/month)
- Team/multi-user support
- Audit trail

**Frontend Scope**:
- Login/register pages (NextAuth.js)
- Pass JWT token in requests
- Display quota usage
- Team selection dropdown

### Phase 4: Observability & Scaling (Week 4)
**Goal**: Production-ready monitoring, Docker Compose, optional K8s

**Tasks**:
- [ ] Setup distributed tracing (Logfire + OTLP)
- [ ] Metrics collection (Prometheus-style)
- [ ] Structured logging (JSON logs)
- [ ] Rate limiting middleware
- [ ] Request size limits (prevent abuse)
- [ ] Health check endpoints
- [ ] Docker Compose with monitoring stack (Prometheus, Grafana)
- [ ] Kubernetes manifests (optional)
- [ ] Load testing

**Deliverables**:
- Full observability (logs, traces, metrics)
- Rate limiting & resource quotas
- Production-ready Docker Compose
- K8s deployment manifests (optional)
- Performance benchmarks

**Frontend Scope**:
- Admin dashboard (queue stats, worker health)
- Error tracking integration (Sentry)

### Phase 5: Advanced Features (Week 5+)
**Goal**: Scale, optimize, add advanced features

**Tasks**:
- [ ] Distributed caching (Redis for hot data)
- [ ] Report webhooks (notify on completion)
- [ ] Git webhook integration (auto-trigger on push)
- [ ] Streaming responses for large reports
- [ ] Report comparison (delta vs. previous)
- [ ] Export formats (PDF, CSV)
- [ ] API versioning strategy
- [ ] WebSocket support (real-time progress)

**Deliverables**:
- Advanced integrations
- Performance optimizations
- Extended API surface

---

## 7. MIGRATION FROM CLI TO SERVICE

### 7.1 Keeping Core Logic Unchanged

The **beauty** of this architecture is that `src/ghostclaw/core/` **remains completely unchanged**:

```python
# In Celery task: reuse GhostAgent as-is
from ghostclaw.core.agent import GhostAgent

@shared_task
def run_ghostclaw_analysis(analysis_id, repo_path, use_ai=False):
    agent = GhostAgent(repo_path=repo_path, use_ai=use_ai)
    report = agent.analyze()  # Same as CLI!
    # ...persist to database...
    return report
```

### 7.2 Deprecation Path

**Option A: Keep CLI + Service separate**
```
PyPI Package: ghostclaw (CLI only)
Docker Image: ghostclaw-backend (Service only)
```

**Option B: Unified package**
```
PyPI Package: ghostclaw (includes CLI + service entry point)
  pip install ghostclaw              # CLI mode
  python -m ghostclaw.backend        # Service mode
```

### 7.3 Breaking Changes During Transition

| Change | Impact | Mitigation |
|--------|--------|-----------|
| Database becomes required | Configuration | Use SQLite as default for dev, PostgreSQL for prod |
| Async required in service | Code | Wrap sync code in `run_in_threadpool()` if needed |
| Job queue adds latency | UX | Polling endpoint for status, WebSocket for real-time |
| Config changes (env vars) | Documentation | Provide migration guide + `.env.example` |

---

## 8. TESTING STRATEGY

### 8.1 Unit Tests

```python
# tests/unit/test_analysis_service.py

import pytest
from app.services.analysis_service import AnalysisService
from app.db.models import Analysis

@pytest.mark.asyncio
async def test_schedule_analysis(db_session):
    """Test creating an analysis job."""
    analysis = await AnalysisService.schedule_analysis(
        repo_url="https://github.com/test/repo",
        user_id="user-123",
        db=db_session
    )
    assert analysis.id
    assert analysis.status == "pending"
    assert analysis.job_id


@pytest.mark.asyncio
async def test_get_status(db_session):
    """Test polling analysis status."""
    # Create analysis
    analysis = await AnalysisService.schedule_analysis(...)
    
    # Immediately check status (should be "pending")
    status = await AnalysisService.get_status(analysis.id, "user-123", db_session)
    assert status["status"] in ["pending", "queued"]
```

### 8.2 Integration Tests

```python
# tests/integration/test_analysis_workflow.py

@pytest.mark.asyncio
async def test_full_analysis_workflow(client, db_session):
    """Test complete flow: auth → create → poll → get result."""
    
    # 1. Register user
    resp = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert resp.status_code == 201
    user_id = resp.json()["id"]
    
    # 2. Login & get token
    resp = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Create analysis
    resp = client.post("/api/v1/analyses", headers=headers, json={
        "repo_url": "https://github.com/test/repo",
        "use_ai": False
    })
    assert resp.status_code == 202  # Accepted (async)
    analysis_id = resp.json()["id"]
    
    # 4. Poll status
    for _ in range(60):  # Wait up to 60 seconds
        resp = client.get(f"/api/v1/analyses/{analysis_id}/status", headers=headers)
        status = resp.json()["status"]
        if status == "completed":
            break
        await asyncio.sleep(1)
    
    # 5. Get result
    resp = client.get(f"/api/v1/analyses/{analysis_id}", headers=headers)
    assert resp.status_code == 200
    result = resp.json()
    assert result["vibe_score"] is not None
    assert result["report"] is not None
```

### 8.3 Load Testing

```bash
# Using locust for load testing
pip install locust

# locustfile.py - simulate users creating analyses
from locust import HttpUser, task, between

class AnalysisUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def create_analysis(self):
        self.client.post(
            "/api/v1/analyses",
            headers={"Authorization": f"Bearer {self.token}"},
            json={"repo_url": "https://github.com/test/repo"}
        )

# Run: locust -f locustfile.py --host=http://localhost:8000
```

---

## 9. DEPLOYMENT & OPERATIONS

### 9.1 Docker Compose (Local Development)

```yaml
# docker-compose.yml

version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:pass@db:5432/ghostclaw
      REDIS_URL: redis://redis:6379
      PYTHONUNBUFFERED: 1
    depends_on:
      - db
      - redis
    volumes:
      - ./app:/app/app

  worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.worker
    environment:
      DATABASE_URL: postgresql://user:pass@db:5432/ghostclaw
      REDIS_URL: redis://redis:6379
      PYTHONUNBUFFERED: 1
    depends_on:
      - db
      - redis
    deploy:
      replicas: 2

  beat:
    build:
      context: .
      dockerfile: docker/Dockerfile.beat
    environment:
      DATABASE_URL: postgresql://user:pass@db:5432/ghostclaw
      REDIS_URL: redis://redis:6379
      PYTHONUNBUFFERED: 1
    depends_on:
      - db
      - redis

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: ghostclaw
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

### 9.2 Environment Configuration (.env.example)

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_ENV=development
DEBUG=true
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ghostclaw
DATABASE_ECHO=false

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# AI (LLM)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
OPENROUTER_API_KEY=sk-...
DEFAULT_AI_PROVIDER=openrouter
DEFAULT_AI_MODEL=anthropic/claude-3-sonnet

# GitHub (optional)
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...

# Supabase (optional)
SUPABASE_URL=https://.supabase.co
SUPABASE_SERVICE_KEY=...

# Logging & Observability
LOG_LEVEL=INFO
LOGFIRE_TOKEN=...
SENTRY_DSN=...

# Quotas
DEFAULT_MONTHLY_QUOTA=100
DEFAULT_WORKERS=2
MAX_CONCURRENT_ANALYSES=10
```

### 9.3 Database Migrations (Alembic)

```bash
# Initialize Alembic
alembic init migrations

# Create migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head

# Rollback (if needed)
alembic downgrade -1
```

---

## 10. MONITORING & OBSERVABILITY

### 10.1 Key Metrics

| Metric | Purpose | Alert Threshold |
|--------|---------|-----------------|
| `api_request_duration_seconds` | API latency | > 5s |
| `celery_task_duration_seconds` | Analysis time | > 300s |
| `celery_queue_depth` | Pending jobs | > 100 |
| `db_query_duration_seconds` | DB performance | > 1s |
| `redis_connection_errors` | Redis health | > 5 errors/min |
| `analysis_success_rate` | Success % | < 95% |
| `user_quota_exhaustion` | Quota usage | User > 90% |

### 10.2 Health Check Endpoint

```python
# app/api/v1/health.py

@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Check service health (dependencies)."""
    try:
        # Check DB
        await db.execute("SELECT 1")
        db_status = "ok"
    except:
        db_status = "error"
    
    try:
        # Check Redis
        await redis_client.ping()
        redis_status = "ok"
    except:
        redis_status = "error"
    
    try:
        # Check Celery
        from app.tasks import get_celery_stats
        workers = await get_celery_stats()
        workers_active = len(workers)
    except:
        workers_active = 0
    
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "api_version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": {
            "database": db_status,
            "redis": redis_status,
            "workers": workers_active
        }
    }
```

---

## 11. SUMMARY: WHAT CHANGES, WHAT STAYS

### What STAYS (Unchanged)
✅ `src/ghostclaw/core/` — All business logic  
✅ `src/ghostclaw/stacks/` — Stack detection  
✅ Plugin system (MetricAdapter, StorageAdapter, etc.)  
✅ Vibe score computation  
✅ Configuration loading  
✅ Cache implementation  

### What CHANGES (New)
🆕 **API Layer** — FastAPI with REST endpoints  
🆕 **Job Queue** — Celery + Redis for async processing  
🆕 **Database** — PostgreSQL with SQLAlchemy ORM  
🆕 **Authentication** — JWT-based user & team isolation  
🆕 **Observability** — Structured logging, distributed tracing  
🆕 **Deployment** — Docker, Docker Compose, Kubernetes  

### What TRANSITIONS
↔️ CLI becomes optional (not the primary interface)  
↔️ Configuration becomes server-side instead of file-based  
↔️ Output becomes JSON API instead of stdout  
↔️ Users become managed instead of single-user  

---

## 12. INTEGRATION CHECKLIST

### Before Frontend Starts
- [ ] Phase 1 complete: Basic `/api/v1/analyses` endpoint working
- [ ] PostgreSQL database schema finalized
- [ ] API type definitions shared (Pydantic schemas)
- [ ] Error response format documented

### Before Phase 2 (Async)
- [ ] Celery + Redis running
- [ ] `/api/v1/analyses/{id}/status` endpoint ready
- [ ] Database field for `job_id` added
- [ ] Worker process running & accepting tasks

### Before Phase 3 (Auth)
- [ ] User model & registration endpoint ready
- [ ] JWT token generation & validation working
- [ ] All endpoints accept `Authorization: Bearer <token>`
- [ ] Frontend receiving & caching tokens

### Before Production Deploy
- [ ] All 4 phases complete
- [ ] Load testing passed (100+ concurrent users)
- [ ] Monitoring dashboard (Grafana) setup
- [ ] Alert rules configured
- [ ] Database backed up & tested
- [ ] Kubernetes manifests ready (if applicable)

---

**END OF BLUEPRINT**

Created: March 30, 2026  
For: Ghostclaw Backend Service Migration  
Reference: REVIEW_FRONTEND.md, REVIEW.md
