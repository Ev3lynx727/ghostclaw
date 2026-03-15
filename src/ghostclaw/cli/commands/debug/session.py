"""
Interactive REPL for ghostclaw debug sessions.
"""

import cmd
from typing import Any, Dict

class GhostclawDebugConsole(cmd.Cmd):
    """Interactive REPL for ghostclaw debug sessions."""

    intro = """\
\x1b[36m▼ Ghostclaw Debug Console ▼\x1b[0m

Available commands:
  /help          Show this help
  /exit          Exit debugger (abort analysis)
  /continue     Continue analysis to next breakpoint or end
  /break [phase] Set breakpoint at phase
  /state         Show current state variables
  /config        Show config (sanitized)
  /files [N]     List up to N files (default 20)
  /metrics       Show metrics dict
  /adapters      Show adapter results
  /stack         Show stack-specific analysis results
  /issues        Show issues list
  /ghosts        Show architectural ghosts
  /coupling      Show coupling metrics
  /py EXPR       Evaluate Python expression
  /imports       Show top imports for circular dependency check
  /help [cmd]    Show help for a command

Shortcuts: /c = /continue, /q = /exit, /s = /state
Type Python expressions directly (no slash) to inspect variables.
\x1b[36m────────────────────────────────────────────────────────────\x1b[0m
"""
    prompt = "\x1b[32m(ghostclaw)\x1b[0m "

    def __init__(self, context: Dict[str, Any]):
        super().__init__()
        self.ctx = context
        self._breakpoints = set(context.get('breakpoints', []))
        self._current_phase = None
        self._running = True

    def precmd(self, line: str):
        return line.strip()

    def default(self, line: str):
        if line.startswith('/'):
            print(f"Unknown command: {line.split()[0]}")
            return
        try:
            result = eval(line, globals(), self.ctx)
            if result is not None:
                print(repr(result))
        except Exception as e:
            print(f"\x1b[31mError:\x1b[0m {e}")

    def do_help(self, arg: str):
        if arg:
            super().do_help(arg)
        else:
            print(self.__doc__ or "No additional help available.")

    def do_exit(self, arg: str):
        print("Aborting analysis.")
        self._running = False
        return True

    def do_quit(self, arg: str):
        return self.do_exit(arg)

    def do_continue(self, arg: str):
        print("Continuing analysis...")
        return True

    def do_break(self, arg: str):
        if not arg:
            print("Current breakpoints:", ', '.join(sorted(self._breakpoints)) or "(none)")
            return
        phase = arg.lower().strip()
        valid_phases = {'start', 'config', 'files', 'metrics', 'adapters', 'stack', 'pre-synth', 'post-synth', 'end'}
        if phase in valid_phases:
            self._breakpoints.add(phase)
            print(f"Breakpoint set at phase: {phase}")
        else:
            print(f"Invalid phase. Choose from: {', '.join(sorted(valid_phases))}")

    def do_state(self, arg: str):
        print("\x1b[36mCurrent State:\x1b[0m")
        print(f"  Phase: {self._current_phase}")
        print(f"  Breakpoints: {', '.join(sorted(self._breakpoints)) or '(none)'}")
        print(f"  Variables: {', '.join(sorted(self.ctx.keys()))}")

    def do_config(self, arg: str):
        cfg = self.ctx.get('config')
        if not cfg:
            print("No config available.")
            return
        print("\x1b[36mConfig (sanitized):\x1b[0m")
        sensitive = {'api_key', 'GHOSTCLAW_API_KEY', 'openai_api_key', 'anthropic_api_key'}
        for k, v in cfg.__dict__.items():
            if any(s in k.lower() for s in sensitive):
                print(f"  {k}: <REDACTED>")
            else:
                print(f"  {k}: {v}")

    def do_files(self, arg: str):
        files = self.ctx.get('files', [])
        try:
            limit = int(arg) if arg else 20
        except:
            limit = 20
        print(f"\nShowing up to {limit} files (total: {len(files)}):")
        for i, f in enumerate(files[:limit], 1):
            print(f"  {i:4}. {f}")
        if len(files) > limit:
            print(f"  ... and {len(files)-limit} more")

    def do_metrics(self, arg: str):
        metrics = self.ctx.get('metrics', {})
        print("\x1b[36mMetrics:\x1b[0m")
        for k, v in metrics.items():
            print(f"  {k}: {v}")

    def do_adapters(self, arg: str):
        results = self.ctx.get('adapter_results', [])
        print(f"\x1b[36mAdapters ({len(results)} ran):\x1b[0m")
        for i, res in enumerate(results, 1):
            name = res.get('adapter', 'unknown')
            files = res.get('files_analyzed', 0)
            issues = len(res.get('issues', []))
            print(f"  {i}. {name}: {files} files, {issues} issues")

    def do_stack(self, arg: str):
        stack_result = self.ctx.get('stack_result', {})
        print("\x1b[36mStack Analysis:\x1b[0m")
        for k, v in stack_result.items():
            if isinstance(v, (list, dict)):
                print(f"  {k}: {type(v).__name__} with {len(v)} items")
            else:
                print(f"  {k}: {v}")

    def do_issues(self, arg: str):
        issues = self.ctx.get('issues', [])
        print(f"\n\x1b[31mIssues ({len(issues)}):\x1b[0m")
        for i, issue in enumerate(issues[:50], 1):
            print(f"  {i}. {issue}")
        if len(issues) > 50:
            print(f"  ... and {len(issues)-50} more")

    def do_ghosts(self, arg: str):
        ghosts = self.ctx.get('ghosts', [])
        print(f"\n\x1b[33mArchitectural Ghosts ({len(ghosts)}):\x1b[0m")
        for i, ghost in enumerate(ghosts[:20], 1):
            print(f"  {i}. {ghost}")
        if len(ghosts) > 20:
            print(f"  ... and {len(ghosts)-20} more")

    def do_coupling(self, arg: str):
        coupling = self.ctx.get('coupling_metrics', {})
        print("\n\x1b[36mCoupling Metrics:\x1b[0m")
        for k, v in coupling.items():
            print(f"  {k}: {v}")

    def do_imports(self, arg: str):
        edges = self.ctx.get('import_edges', [])
        if not edges:
            print("No import graph available.")
            return
        from collections import Counter
        indegree = Counter()
        for src, dst in edges:
            indegree[dst] += 1
        print("\n\x1b[36mTop imports (by in-degree):\x1b[0m")
        for mod, count in indegree.most_common(20):
            print(f"  {mod}: imported by {count} modules")

    def do_py(self, arg: str):
        if not arg:
            print("Usage: /py EXPRESSION")
            return
        try:
            result = eval(arg, globals(), self.ctx)
            if result is not None:
                print(f"\x1b[32m{repr(result)}\x1b[0m")
        except Exception as e:
            print(f"\x1b[31mError:\x1b[0m {e}")

    do_c = do_continue
    do_q = do_exit
    do_s = do_state
