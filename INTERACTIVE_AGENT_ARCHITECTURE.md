# GHOSTCLAW: INTERACTIVE AGENT + BACKEND SERVICE ARCHITECTURE

**Date**: March 30, 2026  
**Scope**: CLI + Interactive Agent Chat + Backend Service (Unified)  
**Decision**: OPTION 3 - Unified Architecture

---

## OVERVIEW: THREE OPERATION MODES

```
┌──────────────────────────────────────────────────────────────┐
│                   GHOSTCLAW PLATFORM                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  MODE 1: BATCH CLI (KEEP)                                  │
│  ─────────────────────────────                             │
│  $ ghostclaw /path/to/repo --use-ai --json                │
│  └─ Single-pass analysis, output file/stdout              │
│  └─ Use: Scripting, CI/CD, batch jobs                     │
│                                                              │
│  MODE 2: INTERACTIVE AGENT (NEW!) ⭐                       │
│  ────────────────────────────────────                      │
│  $ ghostclaw agent spawn /path/to/repo                    │
│  └─ Interactive terminal session                           │
│  └─ Multi-turn conversation with GhostAgent               │
│  └─ Questions: "What's wrong here?", "Fix this pattern"   │
│  └─ Real-time analysis, refactoring suggestions           │
│  └─ Use: Development, code review, learning               │
│                                                              │
│  MODE 3: BACKEND SERVICE (NEW)                            │
│  ──────────────────────────────                           │
│  $ docker-compose up                                       │
│  $ curl -X POST http://localhost:8000/api/v1/analyses    │
│  └─ FastAPI service + job queue                           │
│  └─ Multi-user, auth, scaling                             │
│  └─ Use: Production, team collaboration, web UI           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## ARCHITECTURE: THREE-LAYER UNIFIED SYSTEM

```
┌────────────────────────────────────────────────────────────────┐
│ LAYER 1: ENTRY POINTS (CLI / Service)                         │
├────────────────────────────────────────────────────────────────┤
│                                                               │
│  CLI Executable (pip install ghostclaw)                     │
│  ├── ghostclaw /path [--use-ai] [--json]                    │
│  │   └─ Batch analysis (existing)                           │
│  │                                                           │
│  └── ghostclaw agent spawn /path                            │
│      └─ Interactive agent chat (NEW)                        │
│                                                               │
│  FastAPI Service (Docker)                                   │
│  ├── POST /api/v1/analyses                                  │
│  │   └─ Trigger async analysis                             │
│  │                                                           │
│  └── WebSocket /ws/agent/{session_id}                       │
│      └─ Stream interactive agent responses (NEW)            │
│                                                               │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ LAYER 2: AGENT CORE (Shared Business Logic)                   │
├────────────────────────────────────────────────────────────────┤
│                                                               │
│  GhostAgent (CORE)                                           │
│  ├── src/ghostclaw/core/agent.py                            │
│  └── Methods:                                                │
│      ├── analyze()           # Single-pass batch            │
│      ├── chat_turn()         # Interactive (NEW)            │
│      ├── refactor_suggest()  # Recommendation               │
│      └── explain()           # Context explanation          │
│                                                               │
│  Interactive Session Manager (NEW)                          │
│  ├── src/ghostclaw/core/agent_session.py                   │
│  └── Methods:                                                │
│      ├── create_session()    # Start interactive            │
│      ├── save_context()      # Preserve analysis context    │
│      ├── retrieve_context()  # Between-turn memory          │
│      └── close_session()     # Cleanup                      │
│                                                               │
│  CodebaseAnalyzer (UNCHANGED)                               │
│  └── Core analysis logic (no changes needed)                │
│                                                               │
│  LLMClient (ENHANCED)                                       │
│  ├── supports streaming for chat                            │
│  ├── context management                                     │
│  └── multi-turn conversation                                │
│                                                               │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ LAYER 3: CLI / SERVICE WRAPPERS (Different Entry Points)       │
├────────────────────────────────────────────────────────────────┤
│                                                               │
│  CLI Layer (Existing)                                        │
│  ├── src/ghostclaw/cli/ghostclaw.py                         │
│  ├── src/ghostclaw/cli/commands/analyze.py                  │
│  └── src/ghostclaw/cli/commands/agent.py (NEW!)             │
│                                                               │
│  Service Layer (New)                                        │
│  ├── app/main.py                                            │
│  ├── app/api/v1/analyses.py                                 │
│  ├── app/api/v1/agent.py (NEW!)                             │
│  │   └── WebSocket endpoint for interactive chat            │
│  └── app/tasks/analyze_task.py                              │
│                                                               │
└────────────────────────────────────────────────────────────────┘
```

---

## DETAIL: INTERACTIVE AGENT COMMAND

### 1. CLI Command Structure

```bash
ghostclaw agent spawn /path/to/repo [OPTIONS]

OPTIONS:
  --ai-provider TEXT          AI provider (openrouter/openai/anthropic)
  --ai-model TEXT             Specific model to use
  --initial-analysis          Run full analysis first (default: Yes)
  --context-size INT          Max tokens for context (default: 8000)
  --stream / --no-stream      Stream responses (default: Yes)
  --save-session FILE         Save session log to file
  --load-session FILE         Load previous session context
  --verbose                   Show internal analysis steps
```

### 2. Interactive Session Flow

```
$ ghostclaw agent spawn /path/to/repo

┌─────────────────────────────────────────────────────────┐
│ GHOSTCLAW INTERACTIVE AGENT v1.0                       │
│ Repository: /path/to/repo                             │
│ Stack: Python 3.11                                    │
│ Files: 42 | LoC: 12,543                              │
│ Vibe Score: 62/100 (Moderate)                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Initial Scan Complete.                                │
│ Type 'help' for commands, 'exit' to quit             │
│                                                         │
│ Red Flags Detected:                                   │
│  • File coupling.py has 8 levels of nesting          │
│  • FunctionProcessor.analyze() is 340 LoC            │
│  • 3 circular dependencies detected                  │
│                                                         │
│ Ready for interactive analysis.                      │
│                                                         │
└─────────────────────────────────────────────────────────┘

agent> what's the biggest issue with this codebase?

GHOSTCLAW AGENT:
The top concern is in `src/ghostclaw/core/coupling.py` (line 145).
The `CouplingAnalyzer` class has 8 levels of nested control flow,
creating a cognitive debt of 87.

Recommendation: Extract the inner `_process_imports()` to a separate method.
This would reduce nesting to 4 levels and improve testability.

Would you like me to:
1. Suggest specific refactoring
2. Explain why this matters
3. Show similar patterns in the codebase
4. Continue with next issue

agent> 1

GHOSTCLAW AGENT:
Refactoring proposal for `src/ghostclaw/core/coupling.py`:

BEFORE (lines 140-200):
```python
def analyze_imports(self, root):
    for file in files:
        if file.endswith('.py'):
            for line in file.readlines():
                if 'import' in line:
                    parsed = parse_import(line)
                    for dep in parsed.dependencies:
                        if dep not in self.seen:
                            links.append({...})
```

AFTER:
```python
def analyze_imports(self, root):
    for file in files:
        if file.endswith('.py'):
            self._process_py_imports(file, links)

def _process_py_imports(self, file, links):
    for line in file.readlines():
        if 'import' in line:
            parsed = parse_import(line)
            self._add_dependencies(parsed, links)

def _add_dependencies(self, parsed, links):
    for dep in parsed.dependencies:
        if dep not in self.seen:
            links.append({...})
```

Impact:
✓ Nesting depth: 8 → 4
✓ Testability: Each method has single responsibility
✓ Readability: Clear intent at each level

Apply this change? (y/n)

agent> y

[Applying refactoring...]
[File updated: src/ghostclaw/core/coupling.py]
[Running tests...]
[Tests passed: 42/42]

Refactoring applied successfully!
Next issue: ...

agent> explain nesting depth

GHOSTCLAW AGENT:
Nesting depth measures how deeply nested your control structures are.

Score Breakdown for Your Code:
┌─────────────────────────────────────────┐
│ Nesting Depth Analysis                 │
├─────────────────────────────────────────┤
│ Files with depth 1-3:  35 files (83%)  │
│ Files with depth 4-5:   6 files (14%)  │
│ Files with depth 6-7:   1 file  (2%)   │
│ Files with depth 8+:    1 file  (1%)   │
│                                         │
│ Rule of Thumb:                         │
│ • Depth < 4: Good (easy to read)       │
│ • Depth 4-6: Fair (consider refactor)  │
│ • Depth > 6: Bad (high cognitive load) │
└─────────────────────────────────────────┘

Your worst offender: coupling.py (depth 8)
Already suggested for refactoring above.

Continue?

agent> compare coupling.py to similar files

[Finding similar patterns...]

agent> save session as review-2026-03-30

Session saved to: .ghostclaw/sessions/review-2026-03-30.json

agent> exit

Session ended. Analysis saved.
```

---

## IMPLEMENTATION: CORE NEW COMPONENTS

### 1. Interactive Agent Session Manager

```python
# src/ghostclaw/core/agent_session.py

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
import json

@dataclass
class AgentMessage:
    role: str  # "user" or "agent"
    content: str
    timestamp: datetime
    analysis_context: Optional[Dict] = None


class AgentSession:
    """Manages interactive agent session state."""
    
    def __init__(self, repo_path: str, initial_report: Optional[Dict] = None):
        self.repo_path = repo_path
        self.session_id = str(uuid.uuid4())
        self.created_at = datetime.utcnow()
        self.messages: List[AgentMessage] = []
        self.initial_report = initial_report  # From initial analysis
        self.context_cache = {}  # Keeps files, deps analyzed
        
    def add_message(self, role: str, content: str, context: Optional[Dict] = None):
        """Track conversation turn."""
        msg = AgentMessage(
            role=role,
            content=content,
            timestamp=datetime.utcnow(),
            analysis_context=context
        )
        self.messages.append(msg)
    
    def get_conversation_history(self, last_n: int = 10) -> str:
        """Format recent messages for LLM context."""
        recent = self.messages[-last_n:]
        formatted = "\n".join([
            f"{msg.role.upper()}: {msg.content}"
            for msg in recent
        ])
        return formatted
    
    def save_to_file(self, file_path: str):
        """Persist session for later replay."""
        session_data = {
            "session_id": self.session_id,
            "repo_path": self.repo_path,
            "created_at": self.created_at.isoformat(),
            "initial_report": self.initial_report,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "analysis_context": msg.analysis_context
                }
                for msg in self.messages
            ]
        }
        with open(file_path, 'w') as f:
            json.dump(session_data, f, indent=2)
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'AgentSession':
        """Resume previous session."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        session = cls(
            repo_path=data["repo_path"],
            initial_report=data["initial_report"]
        )
        session.session_id = data["session_id"]
        session.created_at = datetime.fromisoformat(data["created_at"])
        
        for msg_data in data["messages"]:
            session.add_message(
                role=msg_data["role"],
                content=msg_data["content"],
                context=msg_data.get("analysis_context")
            )
        
        return session
```

### 2. Extended GhostAgent for Interactive Mode

```python
# src/ghostclaw/core/agent.py (additions)

class GhostAgent:
    # ... existing code ...
    
    async def chat_turn(
        self,
        user_query: str,
        session: AgentSession,
        stream: bool = True
    ) -> str:
        """
        Handle single interactive chat turn.
        
        Example:
            agent = GhostAgent(repo_path)
            session = AgentSession(repo_path, initial_report)
            
            response = await agent.chat_turn(
                "What's the worst code smell?",
                session
            )
            print(response)  # Stream or full response
        """
        # Build context for LLM
        conversation = session.get_conversation_history(last_n=5)
        
        prompt = f"""
        You are GhostClaw, an architectural code review agent.
        
        Repository: {self.repo_path}
        Initial Analysis:
        {json.dumps(session.initial_report, indent=2)}
        
        Conversation History:
        {conversation}
        
        User Question: {user_query}
        
        Provide actionable analysis:
        1. Specific files/functions affected
        2. Why it matters (architectural impact)
        3. Concrete refactoring suggestion (if applicable)
        4. Next steps for investigation
        """
        
        # Call LLM with streaming
        response = ""
        async for chunk in self.llm_client.stream_completion(prompt):
            response += chunk
            if stream:
                yield chunk  # For terminal streaming
            else:
                pass  # Accumulate
        
        # Save exchange in session
        session.add_message("user", user_query)
        session.add_message("agent", response)
        
        return response
    
    async def suggest_refactoring(
        self,
        file_path: str,
        session: AgentSession
    ) -> Dict[str, any]:
        """Suggest refactoring for specific file."""
        prompt = f"""
        Based on the analysis of {file_path}, provide:
        1. Specific refactoring changes (with code)
        2. Rationale for each change
        3. Expected improvements (metrics)
        4. Risk assessment
        
        File context: {json.dumps(session.initial_report)}
        """
        
        response = await self.llm_client.create_completion(prompt)
        
        return {
            "file": file_path,
            "suggestions": response,
            "can_apply": True
        }
```

### 3. CLI Command for Interactive Agent

```python
# src/ghostclaw/cli/commands/agent.py (NEW)

import asyncio
from argparse import ArgumentParser, Namespace
from ghostclaw.cli.commander import Command
from ghostclaw.core.agent import GhostAgent
from ghostclaw.core.agent_session import AgentSession
from ghostclaw.core.analyzer import CodebaseAnalyzer
from pathlib import Path
import sys


class AgentCommand(Command):
    """Interactive agent spawn command."""
    
    @property
    def name(self) -> str:
        return "agent"
    
    @property
    def description(self) -> str:
        return "Run interactive agent chat session"
    
    def configure_parser(self, parser: ArgumentParser) -> None:
        subparsers = parser.add_subparsers(dest="agent_action")
        
        # ghostclaw agent spawn
        spawn_parser = subparsers.add_parser(
            "spawn",
            help="Spawn interactive agent session"
        )
        spawn_parser.add_argument("repo_path", help="Path to repository")
        spawn_parser.add_argument(
            "--ai-provider",
            default="openrouter",
            choices=["openrouter", "openai", "anthropic"]
        )
        spawn_parser.add_argument("--ai-model", default=None)
        spawn_parser.add_argument(
            "--no-initial-analysis",
            action="store_true",
            help="Skip initial full analysis"
        )
        spawn_parser.add_argument(
            "--save-session",
            default=None,
            help="Save session to file"
        )
        spawn_parser.add_argument(
            "--load-session",
            default=None,
            help="Load previous session"
        )
        spawn_parser.add_argument(
            "--stream",
            action="store_true",
            default=True,
            help="Stream responses"
        )
    
    async def execute(self, args: Namespace) -> int:
        if args.agent_action == "spawn":
            return await self._spawn_agent(args)
        return 1
    
    async def _spawn_agent(self, args: Namespace) -> int:
        """Main interactive agent loop."""
        repo_path = args.repo_path
        
        # Print header
        print("\n" + "="*60)
        print("GHOSTCLAW INTERACTIVE AGENT v1.0")
        print("="*60)
        print(f"Repository: {repo_path}\n")
        
        # Run initial analysis (unless skipped)
        if not args.no_initial_analysis:
            print("Running initial analysis...")
            analyzer = CodebaseAnalyzer()
            initial_report = await analyzer.analyze(repo_path)
            print(f"✓ Vibe Score: {initial_report.vibe_score}/100")
            print(f"✓ Files Analyzed: {initial_report.files_analyzed}")
            print(f"✓ Red Flags: {len(initial_report.red_flags)}\n")
        else:
            initial_report = None
        
        # Initialize session
        if args.load_session:
            session = AgentSession.load_from_file(args.load_session)
            print(f"✓ Session loaded: {args.load_session}")
        else:
            session = AgentSession(repo_path, initial_report)
        
        # Initialize agent
        agent = GhostAgent(
            repo_path=repo_path,
            use_ai=True,
            ai_provider=args.ai_provider,
            ai_model=args.ai_model
        )
        
        # Interactive loop
        print("Type 'help' for commands, 'exit' to quit\n")
        
        while True:
            try:
                user_input = input("agent> ").strip()
                
                if not user_input:
                    continue
                
                if user_input == "exit":
                    # Save session if requested
                    if args.save_session:
                        session.save_to_file(args.save_session)
                        print(f"✓ Session saved: {args.save_session}")
                    print("\nGoodbye!")
                    return 0
                
                if user_input == "help":
                    self._print_help()
                    continue
                
                if user_input.startswith("explain "):
                    concept = user_input.replace("explain ", "")
                    await self._explain_concept(agent, session, concept)
                    continue
                
                # General chat
                print("\n")
                response_text = ""
                async for chunk in agent.chat_turn(
                    user_input,
                    session,
                    stream=args.stream
                ):
                    print(chunk, end="", flush=True)
                    response_text += chunk
                
                print("\n")
                
            except KeyboardInterrupt:
                print("\n\nSession interrupted. Save before exit? (y/n): ", end="")
                if input().lower() == "y":
                    file = input("Filename: ")
                    session.save_to_file(file)
                    print(f"✓ Saved to {file}")
                break
            except Exception as e:
                print(f"Error: {e}")
    
    def _print_help(self):
        """Print available commands."""
        print("""
Available Commands:
  
  <question>              Ask agent about code (e.g., "What's the worst pattern?")
  explain <concept>       Explain architectural concept (e.g., "explain nesting depth")
  refactor <file>         Suggest refactoring for file
  compare <file1> <file2> Compare architectural patterns
  save <filename>         Save current session
  load <filename>         Load previous session
  status                  Show current analysis status
  exit                    End session
  help                    Show this help
        """)
    
    async def _explain_concept(self, agent, session, concept):
        """Explain architectural concept."""
        prompt = f"""
        Explain this architectural concept in the context of Python code:
        Concept: {concept}
        
        Repository: {session.repo_path}
        Initial Report: {json.dumps(session.initial_report, indent=2)}
        
        Provide:
        1. Definition
        2. Why it matters
        3. Score in this codebase
        4. Examples from this repo
        5. How to improve
        """
        
        response = await agent.llm_client.create_completion(prompt)
        print(response)
```

---

## PARALLEL: BACKEND SERVICE WITH WEBSOCKET

### Interactive Agent via Service (WebSocket)

```python
# app/api/v1/agent.py (FastAPI backend)

from fastapi import APIRouter, WebSocket, Depends, HTTPException
from app.core.agent import GhostAgent
from app.core.agent_session import AgentSession
from app.auth import get_current_user
from app.db.models import User
import json
import asyncio

router = APIRouter(prefix="/ws", tags=["agent"])


@router.websocket("/agent/{session_id}")
async def websocket_agent(
    websocket: WebSocket,
    session_id: str,
    user: User = Depends(get_current_user)
):
    """
    WebSocket endpoint for interactive agent chat.
    
    Client Usage:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws/agent/123?token=JWT');
    
    ws.onopen = () => {
        ws.send(JSON.stringify({
            action: "chat",
            message: "What's the biggest issue?"
        }));
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("Agent:", data.response);
    };
    ```
    """
    await websocket.accept()
    
    try:
        # Load session
        from app.db.repository import SessionRepository
        db_session = SessionRepository()
        session_data = await db_session.get_session(session_id, user.id)
        
        if not session_data:
            await websocket.send_json({
                "error": "Session not found",
                "type": "error"
            })
            await websocket.close()
            return
        
        # Initialize agent
        agent = GhostAgent(
            repo_path=session_data["repo_path"],
            use_ai=True
        )
        
        # Restore session
        session = AgentSession.load_from_dict(session_data)
        
        # Chat loop
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            message = data.get("message")
            
            if action == "chat":
                # Stream response
                response = ""
                async for chunk in agent.chat_turn(message, session, stream=True):
                    response += chunk
                    await websocket.send_json({
                        "type": "stream",
                        "chunk": chunk
                    })
                
                # Save to DB
                await db_session.save_session(session_id, session, user.id)
                
                await websocket.send_json({
                    "type": "complete",
                    "full_response": response
                })
            
            elif action == "save":
                await db_session.save_session(session_id, session, user.id)
                await websocket.send_json({
                    "type": "saved",
                    "message": "Session saved"
                })
            
            elif action == "explain":
                concept = data.get("concept")
                # ... explain logic ...
    
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    
    finally:
        await websocket.close()
```

---

## ARCHITECTURE SUMMARY: UNIFIED SYSTEM

```
┌──────────────────────────────────────────────────────────────┐
│ GHOSTCLAW v1.0: UNIFIED PLATFORM                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│ DISTRIBUTION CHANNELS:                                      │
│                                                              │
│ 1. PyPI Package (CLI + Interactive Agent)                  │
│    ├── pip install ghostclaw                               │
│    ├── ghostclaw /path/repo --json          [BATCH]        │
│    └── ghostclaw agent spawn /path/repo      [INTERACTIVE] │
│                                                              │
│ 2. Docker Service (Backend API + WebSocket)               │
│    ├── docker-compose up                                   │
│    ├── POST /api/v1/analyses                 [BATCH]      │
│    └── WS /api/v1/agent                      [INTERACTIVE]│
│                                                              │
│ 3. Web UI (Next.js)                                        │
│    ├── http://localhost:3000                              │
│    ├── Batch analysis form                                │
│    └── Interactive agent chat panel (real-time)           │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ SHARED CORE (NO DUPLICATION):                             │
│                                                              │
│ src/ghostclaw/core/                                        │
│ ├── agent.py              (GhostAgent + chat_turn)        │
│ ├── agent_session.py      (Interactive state)             │
│ ├── analyzer.py           (Analysis engine)               │
│ ├── llm_client.py         (LLM integration)               │
│ └── ... (all other core modules)                          │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ ENTRY POINTS (Different interfaces, same logic):          │
│                                                              │
│ CLI Layer (src/ghostclaw/cli/)                            │
│ ├── AnalyzeCommand        (batch)                         │
│ └── AgentCommand          (interactive)                   │
│                                                              │
│ Service Layer (app/ directory)                            │
│ ├── app/api/analyses.py   (batch endpoint)                │
│ ├── app/api/agent.py      (websocket endpoint)            │
│ └── app/tasks/            (celery task runners)           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## IMPLEMENTATION TIMELINE

### Phase 1: Core Interactive Features (Week 1)
- [ ] Create `agent_session.py` (session state + persistence)
- [ ] Add `chat_turn()` method to `GhostAgent`
- [ ] Create `AgentCommand` in CLI (`ghostclaw agent spawn`)
- [ ] Terminal UI with streaming responses
- [ ] Session save/load functionality
- [ ] Tests for interactive flow

**Deliverable**: Working CLI interactive agent
```bash
$ ghostclaw agent spawn /path/to/repo
agent> what's the biggest issue?
[Agent responds with analysis...]
```

### Phase 2: LLM Integration (Week 1-2)
- [ ] Enhance `LLMClient` for multi-turn conversations
- [ ] Context management (conversation history)
- [ ] Streaming responses for CLI
- [ ] Cost optimization (context pruning)
- [ ] Tests for LLM integration

**Deliverable**: Full chat loop with AI responses

### Phase 3: Backend WebSocket (Week 2)
- [ ] Add WebSocket endpoint to FastAPI
- [ ] Integrate agent with FastAPI service
- [ ] Session persistence in PostgreSQL
- [ ] Streaming to frontend over WS

**Deliverable**: Backend service supports interactive chat

### Phase 4: Frontend Integration (Week 2-3)
- [ ] Next.js agent chat component
- [ ] WebSocket client (reconnect, error handling)
- [ ] Real-time streaming display
- [ ] Session management UI

**Deliverable**: Web UI can chat with agent in real-time

### Phase 5: Polish & Optimization (Week 3)
- [ ] Context optimization (don't send whole repo)
- [ ] Caching strategies for faster responses
- [ ] Error recovery
- [ ] User guides & docs

---

## FILE STRUCTURE: UPDATED

```
ghostclaw/
├── src/ghostclaw/
│   ├── core/
│   │   ├── agent.py                 # UPDATED: + chat_turn()
│   │   ├── agent_session.py         # NEW: Interactive state
│   │   ├── analyzer.py              # Unchanged
│   │   ├── llm_client.py            # UPDATED: Streaming
│   │   └── ... (rest unchanged)
│   │
│   └── cli/
│       ├── commands/
│       │   ├── analyze.py           # Existing batch command
│       │   └── agent.py             # NEW: Interactive command
│       ├── ghostclaw.py             # Updated to register both
│       └── ... (rest unchanged)
│
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── analyses.py          # Batch endpoint
│   │       └── agent.py             # NEW: WebSocket agent
│   ├── tasks/
│   │   └── analyze_task.py          # Celery task
│   └── ...
│
├── tests/
│   ├── unit/
│   │   ├── test_agent_session.py    # NEW
│   │   ├── test_chat_turn.py        # NEW
│   │   └── ...
│   └── integration/
│       ├── test_interactive_flow.py # NEW
│       └── ...
│
├── pyproject.toml                   # Updated deps for streaming
├── Dockerfile                       # Service
└── docker-compose.yml               # Dev environment
```

---

## EXAMPLE USAGE FLOWS

### Flow 1: CLI Batch (Existing)
```bash
$ ghostclaw /path/to/repo --use-ai --json
[Single pass, output file, exit]
```

### Flow 2: CLI Interactive (NEW)
```bash
$ ghostclaw agent spawn /path/to/repo
agent> what's wrong?
[Agent responds]
agent> fix this pattern
[Agent suggests refactoring]
agent> explain nesting
[Agent explains concept]
agent> save my-session
[Saves session]
agent> exit
```

### Flow 3: Service Batch (Backend)
```bash
POST /api/v1/analyses
Input: {"repo_url": "...", "use_ai": true}
Output: 202 Accepted (returns job_id)
[Client polls /status until complete]
```

### Flow 4: Service Interactive (WebSocket)
```javascript
// Client connects
ws = new WebSocket("ws://localhost:8000/ws/agent/session-123")

// Send messages
ws.send(JSON.stringify({action: "chat", message: "what's wrong?"}))

// Stream response
ws.onmessage = (event) => {
    data = JSON.parse(event.data)
    if (data.type === "stream") {
        display(data.chunk)  // Real-time
    }
}
```

### Flow 5: Web UI (Next.js)
```
[User opens http://localhost:3000]
[Selects repo to analyze]
[Runs initial analysis]
[Opens "Agent Chat" tab]
[Types question in chat input]
[Real-time response streams in chat panel]
[Can save session, export, etc.]
```

---

## KEY DESIGN DECISIONS

### 1. NO Code Duplication
- Single `GhostAgent` class
- Works for both batch AND interactive
- CLI wraps it (sync), Service wraps it (async)

### 2. Stateful Sessions
- `AgentSession` tracks conversation history
- Persists to file (CLI) or DB (Service)
- Can resume later

### 3. Streaming for UX
- LLMClient supports streaming
- Terminal shows live response (CLI)
- WebSocket sends chunks (Service)
- Frontend displays progressively (Web)

### 4. Optional AI
- Interactive agent requires AI enabled
- Batch mode works without AI
- Graceful degradation

---

## SUMMARY: YOUR ARCHITECTURE

```
✅ KEEP CLI
   ├── Batch: ghostclaw /path (unchanged)
   └── Interactive: ghostclaw agent spawn /path (NEW)

✅ ADD BACKEND SERVICE
   ├── API: FastAPI with job queue
   ├── Interactive: WebSocket for real-time chat
   └── Web UI: React/Next.js frontend

✅ SINGLE CORE
   └── src/ghostclaw/core/ (all business logic)
      ├── Works in CLI
      ├── Works in Celery task
      ├── Works in WebSocket handler
      ├── NO duplication
      └── NO sync/async mess (properly wrapped)

✅ THREE INTERFACES FOR SAME PROBLEM
   ├── CLI (developer, scripting)
   ├── API (production, scaling)
   └── Web (team collaboration)
```

---

**Next Step**: Shall I create:
1. ✅ Starter code for `agent_session.py`?
2. ✅ Sample interactive flow implementation?
3. ✅ WebSocket endpoint code?
4. ✅ Next.js chat component example?

Which part would you like me to scaffold first? 🚀
