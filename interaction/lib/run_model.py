"""One read-only structured model call; callers own failure policy."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

from .schema import validate


def classify_with_model(prompt: str, schema: dict, state_dir: Path, *,
                        run_bin: str | None = None, timeout: int = 600) -> dict:
    with tempfile.TemporaryDirectory(prefix='triage-', dir=state_dir) as tmp:
        tmp = Path(tmp)
        (tmp / 'prompt.txt').write_text(prompt)
        (tmp / 'schema.json').write_text(json.dumps(schema))
        command = run_bin if run_bin is not None else os.environ.get(
            'PRTS_RUN_MODEL', str(Path(__file__).resolve().parents[1] / 'bin/run'))
        result = subprocess.run([command, str(tmp / 'prompt.txt'),
                                 '--output-schema', str(tmp / 'schema.json'), '-o', str(tmp / 'answer.json')],
                                stdin=subprocess.DEVNULL, text=True, capture_output=True, timeout=timeout)
        if result.returncode:
            raise RuntimeError(f'模型分诊失败（退出码 {result.returncode}）: ' + result.stderr[-2000:])
        answer = json.loads(result.stdout)
        validate(answer, schema)
        return answer
