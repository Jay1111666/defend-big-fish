"""从项目根目录执行；保存真实输出及代码哈希，不生成模拟结果。"""
import difflib
import hashlib
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
stage = sys.argv[1]
assert stage in ('01-red', '02-green', '03-refactor', '04-regression')
if (OUT / f'{stage}.txt').exists():
    raise SystemExit('阶段记录已存在，不覆盖历史证据。日常验证请直接运行 unittest。')
command = [sys.executable, '-m', 'unittest', 'discover', '-v'] if stage == '04-regression' else [
    sys.executable, '-m', 'unittest', 'tests.test_bottle_aura_tdd', '-v']
files = ['model.py', 'config.py', 'art.py', 'main.py', 'tests/test_bottle_aura_tdd.py']
hashes = '\n'.join(f'{name}: {hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}' for name in files)
env = dict(os.environ, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy', PYTHONIOENCODING='utf-8')
result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, encoding='utf-8')
log = f'Stage: {stage}\nUTC: {datetime.now(timezone.utc).isoformat()}\nCommand: {command!r}\n{hashes}\nExit: {result.returncode}\n\n{result.stdout}{result.stderr}'
(OUT / f'{stage}.txt').write_text(log, encoding='utf-8')
snap = OUT / 'snapshots' / stage
snap.mkdir(parents=True, exist_ok=True)
for name in files:
    (snap / Path(name).name).write_bytes((ROOT / name).read_bytes())
previous = {'02-green': '01-red', '03-refactor': '02-green', '04-regression': '03-refactor'}.get(stage)
if previous:
    patch = ''
    for name in files:
        old = OUT / 'snapshots' / previous / Path(name).name
        patch += ''.join(difflib.unified_diff(old.read_text(encoding='utf-8').splitlines(True),
                                            (ROOT / name).read_text(encoding='utf-8').splitlines(True),
                                            fromfile='a/' + name, tofile='b/' + name))
    (OUT / f'{stage}.patch').write_text(patch, encoding='utf-8', newline='\n')
print(log[-5000:])
sys.exit(0 if (result.returncode != 0 if stage == '01-red' else result.returncode == 0) else 1)
