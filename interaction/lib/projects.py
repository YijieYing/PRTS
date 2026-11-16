"""Shared project vocabulary; explicitly shared with pulse."""
import os
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[2]

def mapping():
    path = Path(os.environ.get('PRTS_PROJECTS', ROOT / 'human/projects.toml'))
    return tomllib.loads(path.read_text()).get('project', []) if path.exists() else []

def aliases(c):
    return {a: p['name'] for p in c.get('mapping', []) for a in p.get('aliases', [])}

def canonical(name, items=None):
    if name in (None, '', '未归属', '不属于项目', '其他'):
        return None
    return aliases({'mapping': mapping() if items is None else items}).get(name, name)

def match(cwd, items=None):
    if not cwd: return None
    path = str(Path(cwd).expanduser()).rstrip('/')
    if path == str(Path.home()).rstrip('/'):
        return None
    for p in sorted(mapping() if items is None else items, key=lambda p: len(str(Path(p['path']).expanduser())), reverse=True):
        prefix = str(Path(p['path']).expanduser()).rstrip('/')
        if prefix == str(Path.home()).rstrip('/'):
            continue
        if path == prefix or (not p.get('exact') and path.startswith(prefix + '/')):
            return canonical(p['name'], items)
    return None
