"""Read-only compatibility adapter for AgentConsole's internal scan API.

Reuse its Claude metadata/transcript and Codex SQLite readers; do not duplicate
parsers. No process inspection, HTTP, or conversation-detail reads are needed.
AgentConsole is an optional sibling checkout; failures warn on stderr and leave
subscriptions/dispatch history available.
"""
import importlib.util
from pathlib import Path
import sys


def reader():
    path = Path(__file__).resolve().parents[2] / 'AgentConsole/agent_console/scan.py'
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location('_prts_agentconsole_scan', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Scan a wider window; groups applies the inclusive 14-day cutoff once.
    module.RECENT_DAYS = 15
    return module


def scan(module=None):
    module = module or reader()
    if module is None:
        return []
    agents = []
    for collect in (module.claude_agents, module.codex_agents):
        try:
            agents.extend(collect({}, {}))
        except (OSError, ValueError, KeyError, TypeError, module.sqlite3.Error) as exc:
            print(f'status: {collect.__name__}: {exc}', file=sys.stderr)
    return agents
