# GHOSTCLAW: CLI vs Backend Service - Architecture Decision

**Date**: March 30, 2026  
**Context**: Converting CLI package (PyPI) → Backend Service (Docker)  
**Question**: Keep legacy CLI or replace with backend service?

---

## EXECUTIVE SUMMARY

| Scenario | Keep CLI? | Keep Service? | Recommended? | Effort | User Impact |
|----------|-----------|---------------|--------------|--------|-------------|
| **Both (Dual)** | ✅ Yes | ✅ Yes | ❓ Maybe | 🔴 HIGH | ✅ Full backward compat |
| **Service Only** | ❌ No | ✅ Yes | ⭐ **BEST** | 🟢 LOW | ⚠️ Break CLI users |
| **Unified** | ✅ Yes (thin) | ✅ Yes | ✅ Good | 🟡 MED | ✅ Best of both |
| **CLI Only** | ✅ Yes | ❌ No | ❌ Bad | 🟢 LOW | ❌ Can't scale |

---

## 3 POSSIBLE ARCHITECTURES

### **OPTION 1: DUAL SYSTEM (Keep Both Separate)**

```
PyPI Package: ghostclaw (CLI)
    ├── src/ghostclaw/cli/
    ├── src/ghostclaw/core/ (business logic)
    └── Distribution: pip install ghostclaw

Docker Service: ghostclaw-backend
    ├── app/ (FastAPI)
    ├── src/ghostclaw/ (shared core logic)
    └── Distribution: Docker image
```

**Pros**:
- ✅ CLI users NOT broken (backward compatible)
- ✅ Both can use same core logic (`src/ghostclaw/core/`)
- ✅ Non-invasive transition (cli can warn users)

**Cons**:
- ❌ **Heavy maintenance**: Two entry points, two execution models
- ❌ **Code duplication**: Both files do config loading, error handling, output
- ❌ **Sync vs Async confusion**: CLI is sync, service is async
- ❌ **Testing burden**: Test both CLI + API paths
- ❌ **Dependency hell**: CLI needs all deps, service needs different deps

**When to Choose**:
- If you have **MANY active CLI users** in production
- If you cannot control breaking changes
- If you need 6+ months migration window

---

### **OPTION 2: SERVICE ONLY (Deprecate CLI)**

```
PyPI Package: DEPRECATED
    ├── Last version: 0.2.5 (final CLI)
    └── Deprecation notice: "Use ghostclaw-backend Docker service"

Docker Service: ghostclaw-backend (PRIMARY)
    ├── app/ (FastAPI)
    ├── src/ghostclaw/core/ (business logic)
    └── CLI tool REMOVED
```

**Pros**:
- ✅ **Clean architecture**: Single source of truth (backend)
- ✅ **Easier maintenance**: Single code path
- ✅ **Better UX**: Consistent auth, quotas, history
- ✅ **Scalable**: Job queue, multi-worker support
- ✅ **Faster development**: Focus on one thing

**Cons**:
- ❌ **Breaking change**: Existing CLI users need to migrate
- ❌ **Requires Docker**: Higher barrier to entry
- ❌ **No offline mode**: Always needs service

**When to Choose**:
- If you own/control most CLI usage
- If you're fine with **v1.0 major version bump**
- If team wants clean slate (RECOMMENDED FOR YOU!)

---

### **OPTION 3: UNIFIED (CLI as Thin Client)**

```
PyPI Package: ghostclaw-client (NEW NAME)
    ├── src/ghostclaw_client/cli/
    │   └── Command-line interface (thin wrapper)
    ├── src/ghostclaw_client/sdk/
    │   └── Python SDK to call backend API
    └── pip install ghostclaw-client

Docker Service: ghostclaw-backend (PRIMARY)
    ├── app/ (FastAPI)
    ├── src/ghostclaw/ (core logic)
    ├── src/ghostclaw_mcp/ (MCP server)
    └── Docker image

┌─────────────┐         ┌──────────────┐
│   CLI User  │─http──→ │ Backend API  │
│ (local cmd) │         │ (Docker)     │
└─────────────┘         └──────────────┘
```

**Pros**:
- ✅ **Best of both worlds**: CLI still works, but calls backend
- ✅ **Backward compatible**: `ghostclaw /path` still works
- ✅ **Single backend**: Only maintain service
- ✅ **Consistent**: All users hit same backend
- ✅ **Auth built-in**: CLI users get quotas, history

**Cons**:
- ⚠️ **Requires backend running**: Can't use offline
- ⚠️ **Additional dependency**: SDK + CLI wrapper
- ⚠️ **Network latency**: Every call goes over HTTP

**When to Choose**:
- If you want **backward compatibility** but **single backend**
- If users should **always use backend** anyway
- If you have a **hosted backend** (Kuberenetes, Cloud Run)

---

## MY RECOMMENDATION ⭐

Based on your setup:

### **Choose OPTION 2: SERVICE ONLY** (Best for Your Case)

**Reasoning**:

1. **You're building from scratch**
   - This is new Ghostclaw service, not existing production CLI
   - No legacy users to break on day 1
   - You control the ecosystem

2. **Frontend design already assumes backend**
   - REVIEW_FRONTEND.md shows Next.js calling backend API
   - Not calling CLI subprocess
   - Auth, quotas built into service design

3. **Single source of truth earns you**
   - ✅ Simpler codebase
   - ✅ Faster feature development
   - ✅ No sync/async confusion
   - ✅ Same metrics for all users
   - ✅ Central rate limiting

4. **CLI has limited value in new design**
   - LocalRepo cloning → backend handles it
   - Auth required → CLI user needs token
   - Job queue → CLI can't wait synchronously anyway
   - Better to be explicit: "backend service" not "also works CLI"

5. **Version boundary is clean**
   - **v0.2.5** (PyPI): Final CLI release
   - **v1.0.0** (Docker): Backend service launch
   - Users understand: "CLI is legacy, use service"

---

## IMPLEMENTATION PATH (YOUR CASE)

### **Step 1: Architect Backend Service (v1.0.0)**

```
New repository: ghostclaw-backend (or ghostclaw on main branch)
├── app/ (FastAPI + Celery + auth)
├── src/ghostclaw/ (reuse core logic - copy from old)
├── docker-compose.yml (local dev)
├── pyproject.toml (backend deps only)
└── Dockerfile

NO src/ghostclaw/cli/ in this version
NO argparse, NO stdout formatting
```

### **Step 2: Deprecate Old CLI (Optional)**

```python
# In old src/ghostclaw/cli/ghostclaw.py (final version 0.2.5)

if __name__ == "__main__":
    print("""
    ⚠️  Ghostclaw CLI (v0.2.5) is DEPRECATED.
    
    The CLI has transitioned to a backend service.
    
    To continue using Ghostclaw:
    1. Start the service: docker-compose up
    2. Use the API: curl http://localhost:8000/api/v1/analyses
    3. Or access the UI: http://localhost:3000
    
    Learn more: https://github.com/Ev3lynx727/ghostclaw/blob/main/MIGRATION_GUIDE.md
    """)
    sys.exit(1)
```

### **Step 3: Create Migration Guide**

```markdown
# MIGRATION_GUIDE.md

## From CLI v0.2.5 to Backend Service v1.0.0

### Before (CLI)
```bash
ghostclaw /path/to/repo --use-ai --json > report.json
```

### After (Backend Service)
```bash
# 1. Start service
docker-compose up

# 2. Create analysis
curl -X POST http://localhost:8000/api/v1/analyses \
  -H "Authorization: Bearer <token>" \
  -d '{"repo_url": "/path/to/repo", "use_ai": true}'

# Or use Python SDK
from ghostclaw_backend import Client
client = Client("http://localhost:8000")
result = client.analyze("/path/to/repo", use_ai=True)
```
```

### **Step 4: Maintain Core Logic Bridge**

```
src/ghostclaw/core/ → SAME in both versions
  ├── agent.py (GhostAgent class)
  ├── analyzer.py (CodebaseAnalyzer)
  ├── models.py (ArchitectureReport)
  └── ... (all analysis logic)

v0.2.5 (CLI): imports ghostclaw.core
v1.0.0 (Service): imports ghostclaw.core

→ Single source of truth for business logic
```

---

## WHERE SHOULD GHOSTAGENT LIVE?

### **Option A: In Backend Service Only** (Recommended)

```
ghostclaw-backend/
├── src/ghostclaw/
│   ├── core/
│   │   ├── agent.py (GhostAgent - MAIN HOME)
│   │   └── ...
│   └── ...
├── app/
│   └── tasks/analyze_task.py (imports GhostAgent from src/)
└── Dockerfile
```

**Pros**:
- ✅ Single location
- ✅ No duplication
- ✅ Clear who owns it

**Cons**:
- ❌ Breaking change for CLI users (they lose it)

---

### **Option B: In Shared Library** (If keeping CLI)

```
ghostclaw-core/ (separate package)
├── src/ghostclaw_core/
│   ├── agent.py (GhostAgent)
│   ├── analyzer.py
│   └── ...
└── pyproject.toml

ghostclaw-cli/ (old CLI, now minimal)
├── src/ghostclaw_cli/
└── depends_on: ghostclaw-core

ghostclaw-backend/ (service)
├── app/
└── depends_on: ghostclaw-core
```

**Pros**:
- ✅ Code sharing
- ✅ Both can use GhostAgent

**Cons**:
- ❌ Extra package to manage
- ❌ Version coordination complexity

---

## DECISION MATRIX

```
┌─────────────────────────────────────────────────────────┐
│ YOUR SITUATION ANALYSIS                                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Current Status:                                        │
│  • Have working CLI (PyPI)                            │
│  • Building Next.js frontend (calls backend API)      │
│  • Have users? → UNKNOWN (ask this!)                 │
│  • New greenfield project? → YES                     │
│                                                         │
│ Timeline:                                              │
│  • v0.2.5 (current): CLI package                     │
│  • v1.0.0 (goal): Backend service                    │
│  • User migration window: How long?                  │
│                                                         │
│ Answer these to decide:                               │
│ ❓ Do you have ACTIVE CLI users in production?        │
│ ❓ How many? (1? 10? 100+?)                          │
│ ❓ Do they need 6+ months migration time?            │
│ ❓ Must you maintain backward compatibility?         │
│ ❓ Or is this a NEW service launch?                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## FINAL RECOMMENDATION TABLE

| Question | Answer | → Decision |
|----------|--------|-----------|
| **New service from scratch?** | ✅ Yes | Use **OPTION 2/3** |
| **Large existing CLI user base?** | ❌ No | Use **OPTION 2** (cleanest) |
| **Must support offline mode?** | ❌ Not needed | Use **OPTION 2** |
| **Want CLI for dev convenience?** | ✅ Maybe | Use **OPTION 3** (thin client) |
| **Have hosted backend running?** | 🤔 Future | Use **OPTION 3** (CLI talks to it) |

**For YOUR use case** (greenfield Next.js + Ghostclaw service):

```
🎯 RECOMMENDED: OPTION 2 (Service Only)
   
   ✅ Keep v0.2.5 CLI as final release (archive)
   ✅ v1.0.0 is BACKEND SERVICE (Docker primary)
   ✅ GhostAgent lives in: src/ghostclaw/core/ (backend)
   ✅ App architecture: FastAPI (no CLI in service layer)
   ✅ Migration path: Web UI replaces CLI
```

---

## WHAT THIS MEANS FOR YOUR DEVELOPMENT

### **Immediate Actions** (Today):

1. **Keep v0.2.5 as-is** (PyPI package, CLI works)
   ```bash
   # On develop branch, last CLI commit
   git tag v0.2.5-cli-final
   ```

2. **Create v1.0.0 branch** (Backend service)
   ```bash
   git checkout -b feature/ghostclaw-backend
   # OR: Start in new directory: ghostclaw-backend/
   ```

3. **Copy core logic**
   ```bash
   # Copy only:
   src/ghostclaw/core/
   src/ghostclaw/stacks/
   src/ghostclaw/lib/
   
   # DO NOT copy:
   src/ghostclaw/cli/        ❌ LEAVE OUT
   src/ghostclaw_mcp/        ⚠️  CONSIDER LATER
   ```

4. **Build TIER 1-5** from BACKEND_ARCHITECTURE_BLUEPRINT.md
   ```
   NEW structure:
   ├── app/api/          (FastAPI endpoints)
   ├── app/services/     (business services)
   ├── app/tasks/        (Celery: GhostAgent calls)
   ├── app/auth/         (JWT + RBAC)
   ├── src/ghostclaw/    (copied core logic)
   ├── Dockerfile
   └── docker-compose.yml
   ```

### **Communication to Users** (Transition):

```markdown
# Ghostclaw Roadmap

## v0.2.5 (Current - CLI)
- Last version of CLI package
- Still available on PyPI
- Support: 6 months (until v1.0 stable)
- Use: `pip install ghostclaw==0.2.5`

## v1.0.0 (Next - Backend Service)
- New architecture: Docker-native service
- Web API + Web UI
- Async job queue, multi-user support
- CLI removed (use Web UI instead)
- Migration guide provided

## Migration (Timeline)
- v1.0.0 stable: Q4 2026
- CLI support ends: Q2 2027
- Recommend upgrade: Q1 2027
```

---

## ARCHITECTURE SUMMARY

```
┌──────────────────────────────────────────────────────────┐
│ FINAL ARCHITECTURE (Service Only - RECOMMENDED)         │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Users:                                                 │
│    ├─ Web (Next.js) → API calls                        │
│    ├─ API (FastAPI) ← Backend service                  │
│    └─ Legacy CLI users → Soft deprecation (docs)       │
│                                                          │
│  Code Structure:                                        │
│    ├─ app/          (NEW FastAPI layer)                │
│    ├─ app/tasks/    (GhostAgent calls here)            │
│    ├─ src/ghostclaw/core/  (REUSED logic)             │
│    └─ NO src/ghostclaw/cli/ in v1.0.0                │
│                                                          │
│  GhostAgent Home:                                       │
│    ├─ File: src/ghostclaw/core/agent.py               │
│    ├─ Called by: Celery task in app/tasks/            │
│    ├─ Async wrapper: Yes (run_in_threadpool)          │
│    └─ Result: Saved to PostgreSQL                      │
│                                                          │
│  Execution Model:                                       │
│    User Request                                         │
│      ↓ (REST API)                                      │
│    FastAPI endpoint                                     │
│      ↓ (queue)                                         │
│    Celery worker                                        │
│      ↓ (import & run)                                  │
│    GhostAgent.analyze()                                 │
│      ↓ (save result)                                   │
│    PostgreSQL                                           │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## ANSWER YOUR QUESTION

**Q: Is legacy CLI still needed?**

**A: NO.** For your use case:

```
❌ Remove CLI from v1.0.0 backend service
   → Keep v0.2.5 as final CLI release (PyPI archive)
   → Deprecate with migration guide

✅ Frontend (Next.js) replaces CLI as primary interface
   → Users access via Web UI, not command line
   → Same backend, better UX

✅ GhostAgent stays, but moves to backend
   → Still in src/ghostclaw/core/agent.py
   → Called by Celery task, not CLI
   → Same analysis logic, different wrapper

✅ One backend, shared core logic
   → Single source of truth
   → Easier maintenance
   → Consistent for all users
```

**Bottom Line**:
```
v0.2.5: CLI + Core
    ↓ (Deprecate CLI)
v1.0.0: Backend Service (uses same Core)
    ↓ (Primary interface)
Next.js Web UI (Calls Backend API)
```

---

## NEXT STEPS

1. **Confirm with team**: Do you have active CLI users? (If no → Option 2 is perfect)
2. **Fork/branch**: Create `feature/ghostclaw-backend` branch
3. **Copy core**: `src/ghostclaw/core/` → new backend repo
4. **Build Phase 1**: Basic FastAPI + GhostAgent call
5. **Test**: Make sure GhostAgent runs from Celery task
6. **Document**: Deprecation notice for CLI users

---

**Need help starting Phase 1 of backend service?** 🚀

I can create:
- ✅ Starter FastAPI scaffold
- ✅ Celery task template for GhostAgent
- ✅ Database schema
- ✅ Docker setup

Just confirm: **No active CLI users to support?** 🎯
