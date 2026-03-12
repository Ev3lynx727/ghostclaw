"""Consolidated services module for v0.1.9 simplification."""

# === Shared imports ===
import asyncio
import subprocess
import datetime
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

# === Core imports for AnalyzerService ===
from ghostclaw.core.analyzer import CodebaseAnalyzer
from ghostclaw.core.cache import LocalCache
from ghostclaw.core.config import GhostclawConfig
from ghostclaw.core.agent import GhostAgent, AgentEvent

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.status import Status
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# === AnalyzerService (from services/analyzer_service.py) ===

class AnalyzerService:
    """
    Service for orchestrating the codebase analysis.
    """

    def __init__(self, repo_path: str, config_overrides: Dict[str, Any], use_cache: bool = True,
                 cache_dir: Optional[Path] = None, cache_ttl: int = 7, json_output: bool = False,
                 benchmark: bool = False):
        self.repo_path = repo_path
        self.config_overrides = config_overrides
        self.use_cache = use_cache
        self.cache_dir = cache_dir
        self.cache_ttl = cache_ttl
        self.json_output = json_output
        self.benchmark = benchmark
        self.cache: Optional[LocalCache] = None
        self.timings: Dict[str, float] = {}
        self.synthesis_streamed = False

    async def run(self) -> Dict[str, Any]:
        """Run the analysis pipeline."""
        try:
            config = GhostclawConfig.load(self.repo_path, **self.config_overrides)
        except Exception as e:
            print(f"Configuration Error: {e}", file=sys.stderr)
            raise Exception(f"Analysis Error: Configuration Error: {e}")

        # Perform storage migration if needed (old .ghostclaw/{reports,cache} -> storage/)
        repo_path = Path(self.repo_path)
        if migrate_legacy_storage(repo_path):
            print("🔧 Migrated storage to new layout under .ghostclaw/storage/", file=sys.stderr)

        # Initialize cache if needed
        if self.use_cache:
            self.cache = LocalCache(
                cache_dir=self.cache_dir,
                ttl_days=self.cache_ttl,
                compression=config.cache_compression
            )

        analyzer = CodebaseAnalyzer(cache=self.cache if self.use_cache else None)
        agent = GhostAgent(config, self.repo_path, analyzer=analyzer)

        console = Console() if HAS_RICH and not self.json_output else None
        status = None
        live = None
        synthesis_content = []
        self.synthesis_streamed = False

        async def on_pre_analyze(data):
            nonlocal status
            if console:
                status = console.status("[bold green]Ghostclaw is analyzing architecture...[/bold green]", spinner="dots")
                status.start()

        async def on_post_metrics(data):
            nonlocal status
            if status:
                status.update("[bold blue]Metrics collected. Preparing Ghost Engine...[/bold blue]")

        async def on_pre_synthesis(data):
            nonlocal status
            if status:
                status.update("[bold cyan]🧠 Ghost Engine Synthesis starting...[/bold cyan]")
                print("\n" + "="*50 + "\n")
                print("🧠 Ghost Engine Synthesis:\n")

        async def on_synthesis_chunk(data):
            nonlocal status, live
            self.synthesis_streamed = True
            chunk = data["chunk"]
            synthesis_content.append(chunk)

            if console:
                if status:
                    status.stop()
                    status = None

                if not live:
                    from rich.live import Live
                    live = Live(Text(""), console=console, refresh_per_second=10, transient=True)
                    live.start()

                live.update(Text("".join(synthesis_content)))
            else:
                output_stream = sys.stderr if self.json_output else sys.stdout
                output_stream.write(chunk)
                output_stream.flush()

        async def on_post_synthesis(data):
            nonlocal live, status
            if live:
                live.stop()
                live = None
            if status:
                status.stop()
                status = None

            output_stream = sys.stderr if self.json_output else sys.stdout
            output_stream.write("\n\n" + "="*50)
            output_stream.flush()
            if console and synthesis_content:
                full_text = "".join(synthesis_content)
                if full_text.strip(): console.print(Markdown(full_text))

        async def on_reasoning_chunk(data):
            nonlocal status, live
            chunk = data["chunk"]
            if console:
                if status:
                    status.stop()
                    status = None
                if not live:
                    from rich.live import Live
                    live = Live(Text(""), console=console, refresh_per_second=10, transient=True)
                    live.start()
                current_text = live.get_renderable()
                if isinstance(current_text, Text):
                    current_text.append(chunk, style="dim italic")
                    live.update(current_text)
            else:
                output_stream = sys.stderr if self.json_output else sys.stdout
                output_stream.write(f"\033[2m{chunk}\033[0m")
                output_stream.flush()

        agent.on(AgentEvent.PRE_ANALYZE, on_pre_analyze)
        agent.on(AgentEvent.POST_METRICS, on_post_metrics)
        agent.on(AgentEvent.PRE_SYNTHESIS, on_pre_synthesis)
        agent.on(AgentEvent.REASONING_CHUNK, on_reasoning_chunk)
        agent.on(AgentEvent.SYNTHESIS_CHUNK, on_synthesis_chunk)
        agent.on(AgentEvent.POST_SYNTHESIS, on_post_synthesis)

        try:
            report = await agent.run()

            if self.benchmark:
                self.timings = getattr(agent, 'timings', {})

            report["_synthesis_streamed"] = self.synthesis_streamed

            # Add token usage to metadata if available (only if AI was used)
            if config.use_ai and hasattr(agent, 'llm_client'):
                lc = agent.llm_client
                # Safely retrieve token counts, handling mocks in tests
                try:
                    total = lc.total_tokens
                    # Only add if total is a number > 0 (skip mocks)
                    if isinstance(total, (int, float)) and total > 0:
                        report.setdefault('metadata', {})['tokens'] = {
                            'prompt': int(getattr(lc, 'prompt_tokens', 0)),
                            'completion': int(getattr(lc, 'completion_tokens', 0)),
                            'total': int(total)
                        }
                except Exception:
                    # If llm_client is a mock or attributes missing, skip
                    pass

            if self.use_cache and self.cache and not config.dry_run and "metadata" in report and "fingerprint" in report["metadata"]:
                self.cache.set(report["metadata"]["fingerprint"], report)

            return report

        except Exception as e:
            if status: status.stop()
            if live: live.stop()
            raise Exception(f"Analysis Error: {e}")

# === PRService (from services/pr_service.py) ===

class PRService:
    """
    Service for automating GitHub Pull Request creation.
    """

    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)

    async def create_pr(self, report_file: Path, title: str, body: str) -> None:
        """
        Automate PR creation: branch, commit, push, gh pr create.

        Args:
            report_file (Path): The path to the report file.
            title (str): The PR title.
            body (str): The PR body.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
        branch_name = f"ghostclaw/arch-report-{timestamp}"

        try:
            # Create branch
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=self.repo_path, check=True, capture_output=True, text=True)

            # Add report with force (to bypass gitignore if needed)
            rel_report_path = report_file.relative_to(Path(self.repo_path))
            subprocess.run(["git", "add", "-f", str(rel_report_path)], cwd=self.repo_path, check=True, capture_output=True, text=True)

            # Commit
            subprocess.run(["git", "commit", "-m", f"Add architecture report: {report_file.name}"], cwd=self.repo_path, check=True, capture_output=True, text=True)

            # Push
            subprocess.run(["git", "push", "-u", "origin", branch_name], cwd=self.repo_path, check=True, capture_output=True, text=True)

            # Create PR
            pr_cmd = ["gh", "pr", "create", "--title", title, "--body", body]
            result = subprocess.run(pr_cmd, cwd=self.repo_path, capture_output=True, text=True, check=True)
            print(f"🔗 PR created: {result.stdout.strip()}")

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create PR: {e.stderr or e}", file=sys.stderr)
            raise e
        except Exception as e:
            print(f"❌ Error during PR creation: {str(e)}", file=sys.stderr)
            raise e

# === ConfigService (from services/config_service.py) ===

class ConfigService:
    """
    Service for initializing Ghostclaw project configuration.
    """

    @staticmethod
    def init_project(path: str = ".") -> None:
        """
        Scaffold local project configuration.

        Args:
            path (str): The directory where the .ghostclaw config should be created.
        """
        cwd = Path(path)
        gc_dir = cwd / ".ghostclaw"
        gc_dir.mkdir(parents=True, exist_ok=True)
        config_file = gc_dir / "ghostclaw.json"

        if config_file.exists():
            raise FileExistsError(f"⚠️ {config_file} already exists. Skipping initialization.")

        template = {
            "use_ai": True,
            "ai_provider": "openrouter",
            "ai_model": None,
            "use_pyscn": False,
            "use_ai_codeindex": False,
            # Delta-Context (v0.1.10)
            "delta_mode": False,
            "delta_base_ref": "HEAD~1",
            # QMD Backend (v0.2.0)
            "use_qmd": False
        }

        # Write JSON5 if available for nicer formatting with comments/trailing commas
        try:
            import json5
            with open(config_file, "w", encoding="utf-8") as f:
                json5.dump(template, f, indent=2)
        except ImportError:
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(template, f, indent=2)

        print(f"✅ Created template config at {config_file}")
        print("💡 Remember: Do NOT save your GHOSTCLAW_API_KEY in this file. Use an environment variable or ~/.ghostclaw/ghostclaw.json.")

# === PluginService (from services/plugin_service.py) ===

from ghostclaw.core.adapters.registry import registry

class PluginService:
    """
    Service for managing external architectural adapters/plugins.
    """

    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path)
        self.plugins_dir = self.workspace_path / ".ghostclaw" / "plugins"
        self.config_path = self.workspace_path / ".ghostclaw" / "ghostclaw.json"

    def initialize_registry(self):
        """Register built-in plugins and any available external ones."""
        registry.register_internal_plugins()
        if self.plugins_dir.exists():
            registry.load_external_plugins(self.plugins_dir)

    def list_plugins(self) -> List[Dict[str, Any]]:
        self.initialize_registry()
        return registry.get_plugin_metadata()

    def get_plugin_info(self, name: str) -> Optional[Dict[str, Any]]:
        self.initialize_registry()
        metadata = registry.get_plugin_metadata()
        for meta in metadata:
            if meta.get("name") == name:
                return meta
        return None

    def add_plugin(self, source_path: str) -> Path:
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source path '{source}' does not exist.")

        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        target = self.plugins_dir / source.name

        if target.exists():
            print(f"⚠️ Plugin '{source.name}' already installed at {target}. Overwriting...")
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()

        try:
            if source.is_dir():
                shutil.copytree(source, target)
            else:
                shutil.copy2(source, target)
            return target
        except Exception as e:
            raise Exception(f"Failed to install plugin: {e}")

    def remove_plugin(self, name: str) -> Path:
        self.initialize_registry()
        name = name.lower()

        if name in registry.internal_plugins:
            raise ValueError(f"Cannot remove built-in plugin '{name}'.")

        target = self.plugins_dir / name

        if not target.exists():
            matches = list(self.plugins_dir.glob(f"{name}*"))
            if matches:
                target = matches[0]

        if target.exists():
            try:
                if target.is_dir():
                    shutil.rmtree(target)
                else:
                    target.unlink()
                return target
            except Exception as e:
                raise Exception(f"Failed to remove plugin: {e}")
        else:
            raise FileNotFoundError(f"External plugin '{name}' not found in {self.plugins_dir}.")

    def enable_plugin(self, name: str) -> None:
        self.initialize_registry()
        all_names = [m.get("name") for m in registry.get_plugin_metadata()]
        if name not in all_names:
            raise ValueError(f"Plugin '{name}' not found. Available: {', '.join(all_names)}")

        config_data = {}
        if self.config_path.exists():
            try:
                config_data = json.loads(self.config_path.read_text())
            except Exception as e:
                raise Exception(f"Failed to read config: {e}")

        enabled = config_data.get("plugins_enabled")
        if enabled is None:
            print(f"ℹ️ Plugin '{name}' is already enabled (all plugins enabled by default).")
            return

        if name in enabled:
            print(f"ℹ️ Plugin '{name}' is already enabled.")
            return

        enabled.append(name)
        config_data["plugins_enabled"] = enabled

        try:
            self.config_path.write_text(json.dumps(config_data, indent=2))
        except Exception as e:
            raise Exception(f"Failed to write config: {e}")

    def disable_plugin(self, name: str) -> None:
        self.initialize_registry()
        all_names = [m.get("name") for m in registry.get_plugin_metadata()]
        if name not in all_names:
            raise ValueError(f"Plugin '{name}' not found. Available: {', '.join(all_names)}")

        config_data = {}
        if self.config_path.exists():
            try:
                config_data = json.loads(self.config_path.read_text())
            except Exception as e:
                raise Exception(f"Failed to read config: {e}")

        enabled = config_data.get("plugins_enabled")
        if enabled is None:
            enabled = [n for n in all_names if n != name]
            config_data["plugins_enabled"] = enabled
            try:
                self.config_path.write_text(json.dumps(config_data, indent=2))
                print(f"✅ Disabled plugin '{name}'. {len(enabled)} plugins remain enabled.")
                return
            except Exception as e:
                raise Exception(f"Failed to write config: {e}")
        else:
            if name not in enabled:
                print(f"ℹ️ Plugin '{name}' is already disabled (not in whitelist).")
                return

            enabled.remove(name)
            config_data["plugins_enabled"] = enabled
            try:
                self.config_path.write_text(json.dumps(config_data, indent=2))
            except Exception as e:
                raise Exception(f"Failed to write config: {e}")

    def test_plugin(self, name: str) -> bool:
        self.initialize_registry()
        metadata = registry.get_plugin_metadata()
        return any(m.get("name") == name for m in metadata)

    def scaffold_plugin(self, name: str) -> Path:
        name = name.lower().replace("-", "_")
        plugin_dir = self.plugins_dir / name
        plugin_dir.mkdir(parents=True, exist_ok=True)

        init_file = plugin_dir / "__init__.py"
        if init_file.exists():
            raise FileExistsError(f"Plugin '{name}' already exists at {plugin_dir}")

        template = f'''
"""
Ghostclaw Adapter: {name}
"""
from typing import Dict, List, Any, Optional
from ghostclaw.core.adapters.base import MetricAdapter, AdapterMetadata
from ghostclaw.core.adapters.hooks import hookimpl

class CustomAdapter(MetricAdapter):
    def get_metadata(self) -> AdapterMetadata:
        return AdapterMetadata(
            name="{name}",
            version="0.1.0",
            description="Custom architectural analysis.",
            dependencies=[]
        )

    async def is_available(self) -> bool:
        return True

    @hookimpl
    async def ghost_analyze(self, root: str, files: List[str]) -> Dict[str, Any]:
        return {{
            "issues": ["Example issue from {name}"],
            "architectural_ghosts": [],
            "red_flags": []
        }}

    @hookimpl
    def ghost_get_metadata(self) -> Dict[str, Any]:
        meta = self.get_metadata()
        return {{
            "name": meta.name,
            "version": meta.version,
            "description": meta.description
        }}
'''''
        init_file.write_text(template)
        return plugin_dir

__all__ = ['AnalyzerService', 'PRService', 'ConfigService', 'PluginService', 'migrate_legacy_storage']


def migrate_legacy_storage(repo_path: Path) -> bool:
    """
    Migrate old .ghostclaw/{reports,cache,ghostclaw.db} to .ghostclaw/storage/{reports,cache,ghostclaw.db}.
    Returns True if any files were moved.
    """
    moved = False
    gc_dir = repo_path / ".ghostclaw"

    # Migrate reports/
    old_reports = gc_dir / "reports"
    new_reports = gc_dir / "storage" / "reports"
    if old_reports.exists() and old_reports.is_dir():
        new_reports.mkdir(parents=True, exist_ok=True)
        for item in old_reports.iterdir():
            if item.is_file():
                target = new_reports / item.name
                if not target.exists():
                    try:
                        item.rename(target)
                        moved = True
                    except Exception:
                        pass
        try:
            old_reports.rmdir()  # remove empty dir
        except OSError:
            pass

    # Migrate cache/
    old_cache = gc_dir / "cache"
    new_cache = gc_dir / "storage" / "cache"
    if old_cache.exists() and old_cache.is_dir():
        new_cache.mkdir(parents=True, exist_ok=True)
        for item in old_cache.iterdir():
            if item.is_file():
                target = new_cache / item.name
                if not target.exists():
                    try:
                        item.rename(target)
                        moved = True
                    except Exception:
                        pass
        try:
            old_cache.rmdir()
        except OSError:
            pass

    # Migrate legacy SQLite DB if present at top-level
    old_db = gc_dir / "ghostclaw.db"
    new_db = gc_dir / "storage" / "ghostclaw.db"
    if old_db.exists() and old_db.is_file() and not new_db.exists():
        new_db.parent.mkdir(parents=True, exist_ok=True)
        try:
            old_db.rename(new_db)
            moved = True
        except Exception:
            pass

    return moved
