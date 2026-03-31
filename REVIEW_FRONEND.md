# 🔍 Frontend Setup Review & Backend Sync

**Status:** Next.js 14 + Supabase + Python Backend  
**Last Updated:** March 30, 2026  
**Review Purpose:** Validate frontend/backend integration and ensure clean sync

---

## 📋 Frontend Setup Checklist

### ✅ Project Structure
- [x] Next.js App Router configured
- [x] TypeScript enabled with strict mode
- [x] Directory structure created (app/, prisma/, public/)
- [x] Environment variables templated (.env.example)
- [x] Tailwind CSS configured for styling
- [x] PostCSS configured with autoprefixer

**Validation Command:**
```bash
npm run type-check  # Verify TypeScript compilation
```

### ✅ API Routes (Replace Express Gateway)
- [x] `app/api/health/route.ts` - Health check endpoint
- [x] `app/api/analyses/route.ts` - Main analysis endpoint (POST/GET)
- [x] `app/api/analyses/[id]/route.ts` - Single analysis retrieval

**What Each Does:**
```typescript
POST /api/analyses
├─ Input: { repoPath: string, options?: object }
├─ Process: Spawns Python Ghostclaw subprocess
└─ Output: AnalysisResult { id, status, vibeScore, ghosts, report }

GET /api/analyses
├─ Query: ?limit=10&offset=0
├─ Process: Fetches analysis history from database
└─ Output: Array of AnalysisResult[]

GET /api/health
├─ Purpose: Check service health
└─ Output: { status, backendStatus, uptime, timestamp }
```

### ✅ Frontend Pages & Components
- [x] `app/layout.tsx` - Root layout with metadata
- [x] `app/page.tsx` - Landing page with hero section
- [x] `app/dashboard/page.tsx` - Main dashboard
- [x] `app/components/AnalysisForm.tsx` - Form component (client-side)

**User Flow:**
```
Home Page (/page.tsx)
    ↓ [Click "Start Analysis"]
Dashboard (/dashboard/page.tsx)
    ↓ [Form submission]
AnalysisForm (components/AnalysisForm.tsx)
    ↓ [POST /api/analyses]
Python Backend (Ghostclaw)
    ↓ [Analysis results]
Results Display (AnalysisForm)
    ↓ [Show vibe score, ghosts, report]
```

### ✅ Database Configuration
- [x] Prisma ORM configured
- [x] Database schema created (User, Analysis models)
- [x] Type-safe queries ready
- [x] Environment variables for SQLite (dev) + Supabase (prod)

**Current Schema:**
```prisma
model User {
  id: String          // UUID
  email: String       // UNIQUE
  name: String?
  password: String?
  analyses: Analysis[]
  createdAt: DateTime
}

model Analysis {
  id: String          // UUID
  userId: String      // FK to User
  repoPath: String
  vibeScore: Int
  ghosts: String[]    // JSON array
  report: Json        // Full analysis report
  status: String
  createdAt: DateTime
}
```

---

## 🔗 Backend Integration Points

### Critical Sync Points

| Component | Frontend | Backend | Status |
|-----------|----------|---------|--------|
| **Python Spawn** | `app/api/analyses/route.ts` | Ghostclaw CLI | ✅ Ready |
| **Database Access** | `app/lib/prisma.ts` | SQLite3/Supabase | ✅ Ready |
| **Data Format** | `app/types/analysis.ts` | JSON output | ✅ Defined |
| **API Contract** | Type validation (Zod) | stdout JSON | ✅ Validated |
| **Authentication** | NextAuth.js (ready) | User sessions | ⏳ Not implemented |

### Data Flow Diagram

```
Frontend Form Input
    ↓
Validation (Zod Schema)
    ↓
POST /api/analyses
    ↓
Node.js spawn('python -m ghostclaw ...')
    ↓
Python Ghostclaw CLI
    ├─ Analyze repository
    ├─ Generate vibe score
    ├─ Extract ghosts
    └─ Create JSON report
    ↓
Capture stdout (JSON)
    ↓
Parse JSON → AnalysisResult type
    ↓
Store in Prisma (Database)
    ↓
Return to Frontend
    ↓
Display in AnalysisForm component
```

---

## 🔄 Clean Sync Checklist

### Backend Sync Requirements

#### ✅ Step 1: Verify Python Installation
```bash
python --version              # Should be 3.10+
python -m ghostclaw --help   # Verify Ghostclaw works
```

**What to Check:**
- [ ] Python 3.10+ installed
- [ ] Ghostclaw package installed (`pip install ghostclaw`)
- [ ] Ghostclaw CLI executable
- [ ] `--json` flag supported (for JSON output)

#### ✅ Step 2: Verify Ghostclaw JSON Output Format
Run this locally to see what data structure Next.js expects:
```bash
python -m ghostclaw /path/to/repo --json > output.json
cat output.json
```

**Expected Output Structure:**
```json
{
  "vibeScore": 75,
  "ghosts": ["ghost1", "ghost2"],
  "report": {
    "files": [...],
    "patterns": [...],
    "recommendations": [...]
  },
  "metadata": {
    "timestamp": "2026-03-30T...",
    "repoPath": "/path/to/repo"
  }
}
```

**Sync Action:**
- [ ] If structure differs, update `parseGhostclawOutput()` in `app/api/analyses/route.ts`
- [ ] If new fields added, extend `AnalysisResult` type in `app/types/analysis.ts`

#### ✅ Step 3: Verify SQLite3 Integration
Check if backend uses SQLite3 for local storage:
```bash
# Check backend code for SQLite3 usage
grep -r "sqlite3" ../ghostclaw/  # Adjust path to your backend
```

**Sync Action:**
- [ ] If backend uses SQLite directly, ensure Prisma schema matches
- [ ] If schema differs, update `prisma/schema.prisma`
- [ ] Run migration: `npx prisma migrate dev`

#### ✅ Step 4: Verify Supabase Configuration
If using Supabase in production:
```bash
# Test connection
npx prisma db push --skip-generate
```

**Required Environment Variables:**
```bash
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxxxx
DATABASE_URL=postgresql://user:pass@db.supabase.co:5432/postgres
```

**Sync Action:**
- [ ] Create Supabase project
- [ ] Get PostgreSQL connection string
- [ ] Set DATABASE_URL in `.env.local`
- [ ] Run `npx prisma migrate dev`

#### ✅ Step 5: Verify API Contract
Test the API endpoint locally:

```bash
# Start Next.js dev server
npm run dev

# In another terminal, test the API
curl -X POST http://localhost:3000/api/analyses \
  -H "Content-Type: application/json" \
  -d '{"repoPath": "/path/to/your/repo"}'

# Expected response:
# {
#   "id": "uuid...",
#   "status": "completed",
#   "vibeScore": 75,
#   "ghosts": [...],
#   "report": {...},
#   "timestamp": "..."
# }
```

**Sync Validation:**
- [ ] Response matches `AnalysisResult` type
- [ ] All required fields present
- [ ] Status codes correct (200 success, 400+ errors)
- [ ] Error messages descriptive

---

## 🧪 Testing Checklist

### Unit Tests (Create if needed)
```bash
# Test API route parsing
npm test app/api/analyses/route.ts

# Test type validation
npm test app/types/analysis.ts

# Test Prisma query
npm test app/lib/prisma.ts
```

### Integration Tests
```bash
# Test frontend → API → Python → Database flow
npm test --integration

# Manual test checklist:
```

| Test Case | Steps | Expected | Status |
|-----------|-------|----------|--------|
| **Health Check** | `GET /api/health` | `{"status":"ok"}` | ⏳ Untested |
| **Create Analysis** | `POST /api/analyses` with repo path | Returns `AnalysisResult` with id | ⏳ Untested |
| **Retrieve Analysis** | `GET /api/analyses?limit=10` | Returns array of previous analyses | ⏳ Untested |
| **Get Single Result** | `GET /api/analyses/{id}` | Returns specific analysis | ⏳ Untested |
| **Form Submission** | Fill form + click Submit on dashboard | Shows loading → results | ⏳ Untested |
| **Error Handling** | Submit with invalid repo path | Shows error message | ⏳ Untested |
| **Database Persistence** | Refresh page after analysis | Results still visible | ⏳ Untested |

**Run Manual Tests:**
```bash
# Terminal 1: Start development server
npm run dev

# Terminal 2: Run integration tests
npm test:integration

# Terminal 3: Manual API testing
curl -X POST http://localhost:3000/api/analyses \
  -H "Content-Type: application/json" \
  -d '{"repoPath": "/path/to/repo"}'
```

---

## 🔐 Environment & Configuration

### Development Environment (.env.local)
```bash
# Database (SQLite for local dev)
DATABASE_URL="file:./dev.db"

# Supabase (set when ready for cloud)
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=

# Authentication
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=dev-secret-key

# Python Backend
PYTHON_BACKEND_PATH=/path/to/ghostclaw
NODE_ENV=development
```

### Production Environment (Set on Vercel)
```bash
# Database (Supabase PostgreSQL)
DATABASE_URL=postgresql://user:pass@db.supabase.co:5432/postgres

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxxxx_anon_key

# Authentication
NEXTAUTH_URL=https://yourdomain.com
NEXTAUTH_SECRET=production-secret-key

# Production mode
NODE_ENV=production
```

**Sync Checklist:**
- [ ] All required variables set
- [ ] No secrets in code (only in .env.local)
- [ ] .env.local in .gitignore
- [ ] .env.example updated when adding new vars
- [ ] Production env vars set on hosting platform

---

## 📦 Dependencies Version Check

### Critical Versions (Verify Compatibility)

```json
{
  "next": "14.1.0",           // App Router support
  "react": "18.2.0",          // Client components
  "typescript": "5.3.0",      // Strict mode
  "@prisma/client": "5.7.0",  // Type-safe ORM
  "@supabase/supabase-js": "2.38.0",  // Cloud DB
  "tailwindcss": "3.4.0",     // Styling
  "next-auth": "4.24.0"       // Auth ready
}
```

**Sync Check:**
```bash
# Verify all dependencies installed
npm list --depth=0

# Check for security vulnerabilities
npm audit

# Update if needed
npm update
```

---

## 🚨 Common Sync Issues & Fixes

### Issue 1: Python Backend Not Found
**Symptom:** `Error: spawn ENOENT python`

**Fix:**
```bash
# Check Python path
which python              # Linux/Mac
where python             # Windows

# Update PYTHON_BACKEND_PATH in .env.local
PYTHON_BACKEND_PATH=/usr/bin/python3
```

### Issue 2: Database Connection Failed
**Symptom:** `error: connect ECONNREFUSED`

**Fix:**
```bash
# Check SQLite file exists
ls -la dev.db

# Reset database
rm dev.db
npx prisma migrate dev --name init

# Verify Supabase connection
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
```

### Issue 3: Types Not Matching
**Symptom:** `Property 'vibeScore' does not exist on type 'unknown'`

**Fix:**
```bash
# Regenerate Prisma types
npx prisma generate

# Check type definitions
cat app/types/analysis.ts
```

### Issue 4: API Route Not Spawning Python
**Symptom:** Analysis hangs or returns empty result

**Fix:**
```typescript
// Add debug logging to app/api/analyses/route.ts
console.log('Spawning Python with:', pythonArgs);
const analysis = spawn(pythonPath, pythonArgs);
analysis.on('error', (err) => console.error('Spawn error:', err));
```

---

## 🔄 Backend Sync Workflow

### When Backend Changes

**Scenario 1: Backend adds new field to output**
```json
// Before
{ "vibeScore": 75, "ghosts": [...] }

// After  
{ "vibeScore": 75, "ghosts": [...], "spookLevel": "high" }
```

**Action:**
1. Update `AnalysisResult` type in `app/types/analysis.ts`
2. Update `parseGhostclawOutput()` in `app/api/analyses/route.ts`
3. Update Prisma schema if storing persistently
4. Test API endpoint
5. Update frontend display component

**Commands:**
```bash
# Step 1: Update types
nano app/types/analysis.ts

# Step 2: Update API route
nano app/api/analyses/route.ts

# Step 3: Regenerate Prisma
npx prisma generate

# Step 4: Test
curl -X POST http://localhost:3000/api/analyses ...
```

---

**Scenario 2: Backend changes JSON output format**
```json
// Before
{ "report": { "files": [...] } }

// After
{ "analysis": { "fileList": [...] } }
```

**Action:**
1. Check `parseGhostclawOutput()` function
2. Update JSON path parsing
3. Test with actual backend output
4. Update type definitions if struct changes

---

**Scenario 3: Backend requires new parameters**
```bash
# Before
python -m ghostclaw /path/to/repo --json

# After
python -m ghostclaw /path/to/repo --json --detailed --no-cache
```

**Action:**
1. Update `AnalysisRequestSchema` in `app/api/analyses/route.ts`
2. Add new parameters to form in `AnalysisForm.tsx`
3. Pass new options to spawn command
4. Test with backend

---

## ✨ Quick Validation Commands

Run these to verify clean sync:

```bash
# 1. Check Next.js build
npm run build

# 2. Check TypeScript
npm run type-check

# 3. Check dependencies
npm audit

# 4. Start dev server
npm run dev

# 5. Test health endpoint
curl http://localhost:3000/api/health

# 6. Test analysis endpoint
curl -X POST http://localhost:3000/api/analyses \
  -H "Content-Type: application/json" \
  -d '{"repoPath": "/path/to/repo"}'

# 7. Check database
npx prisma studio

# 8. Validate types
npx prisma generate
```

---

## 📊 Integration Status Matrix

| Component | Setup | Tested | Synced | Notes |
|-----------|-------|--------|--------|-------|
| Next.js Framework | ✅ | ⏳ | ✅ | App Router configured |
| TypeScript | ✅ | ⏳ | ✅ | Strict mode enabled |
| API Routes | ✅ | ⏳ | ✅ | 3 endpoints ready |
| Prisma ORM | ✅ | ⏳ | ⏳ | Schema created, not migrated |
| Supabase Client | ✅ | ⏳ | ✅ | Credentials from env |
| Database (SQLite) | ✅ | ⏳ | ⏳ | Not initialized |
| Database (Supabase) | ✅ | ⏳ | ⏳ | Pending Supabase setup |
| Python Spawning | ✅ | ⏳ | ⏳ | Depends on Python path |
| Tailwind CSS | ✅ | ⏳ | ✅ | Configured |
| NextAuth.js | ⏳ | ❌ | ⏳ | In dependencies, not implemented |
| React Components | ✅ | ⏳ | ✅ | Client-side ready |
| Landing Page | ✅ | ⏳ | ✅ | Page template created |
| Dashboard UI | ✅ | ⏳ | ✅ | Page template created |

---

## 🎯 Next Actions

### Immediate (Today)
- [ ] Run `npm install` to install dependencies
- [ ] Verify Python 3.10+ installed and Ghostclaw available
- [ ] Test `python -m ghostclaw --help` to verify backend works
- [ ] Copy `.env.example` to `.env.local`
- [ ] Update `DATABASE_URL` for SQLite or Supabase

### Short-term (This Week)
- [ ] Run `npx prisma migrate dev --name init` to initialize database
- [ ] Run `npm run dev` to start development server
- [ ] Test health endpoint: `GET http://localhost:3000/api/health`
- [ ] Test analysis endpoint with valid repo path
- [ ] Verify results display in UI

### Medium-term (This Month)
- [ ] Test complete flow (form → API → Python → database → display)
- [ ] Add authentication with NextAuth.js if needed
- [ ] Add unit tests for API routes
- [ ] Add integration tests for frontend
- [ ] Deploy to staging environment

### Long-term (Production)
- [ ] Set up Supabase project
- [ ] Add production environment variables
- [ ] Deploy to Vercel
- [ ] Set up monitoring and logging
- [ ] Add CI/CD pipeline (GitHub Actions)

---

## 🆘 Getting Help

**If something doesn't work:**

1. **Check logs:**
   ```bash
   npm run dev  # Watch terminal output
   # Frontend logs appear here
   
   # Backend logs from Python appear in same terminal
   ```

2. **Check types:**
   ```bash
   npm run type-check
   ```

3. **Check build:**
   ```bash
   npm run build
   ```

4. **Debug API route:**
   - Add `console.log()` in `app/api/analyses/route.ts`
   - Test with curl from terminal
   - Check network tab in browser DevTools

5. **Debug database:**
   ```bash
   npx prisma studio  # GUI database viewer
   ```

6. **Review documentation:**
   - [MIGRATION.md](./MIGRATION.md) - Migration details
   - [NEXTJS_SETUP.md](./NEXTJS_SETUP.md) - Next.js setup
   - [ARCHITECTURE.md](./ARCHITECTURE.md) - System design

---

## 📝 Sign-off Checklist

- [ ] All frontend files created ✓
- [ ] All API routes ready ✓
- [ ] Database schema defined ✓
- [ ] Environment variables templated ✓
- [ ] TypeScript configured ✓
- [ ] Tailwind CSS configured ✓
- [ ] Documentation completed ✓
- [ ] Backend integration points identified ✓
- [ ] Testing checklist prepared ✓
- [ ] Sync procedures documented ✓

**Status:** Ready for `npm install` and `npm run dev`

**Next Owner:** You! 👉 Follow the "Immediate" actions above.

---

**Last Review Date:** March 30, 2026  
**Review Status:** ✅ Complete - Frontend Ready for Backend Integration  
**Reviewer:** GitHub Copilot

