# evaluate.py: runs every example in samples/ and compares it with expected.json
# run: uv run data-agent-eval
# use it every time you change the model / edit a prompt, to see whether results got better or worse
import json
import logging
import math
import sys
import tempfile
from pathlib import Path

from data_agent.doc_loader import classify

SAMPLES_DIR = Path('samples')
TOLERANCE = 1e-3  # relative difference still counted as equal


def _same(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=TOLERANCE, abs_tol=TOLERANCE)
    return str(a).strip() == str(b).strip()


def compare(expected: list[dict], actual: list[dict]) -> list[str]:
    # return a list of problems; empty = pass
    problems = []
    if len(expected) != len(actual):
        problems.append(f'number of tables: expected {len(expected)}, got {len(actual)}')
    for i, (exp, act) in enumerate(zip(expected, actual), start=1):
        if len(exp['rows']) != len(act['rows']):
            problems.append(f"table {i}: {len(act['rows'])} rows, expected {len(exp['rows'])}")
            continue
        for r, (er, ar) in enumerate(zip(exp['rows'], act['rows']), start=1):
            if len(er) != len(ar) or not all(_same(x, y) for x, y in zip(er, ar)):
                problems.append(f'table {i} row {r}: got {ar}, expected {er}')
                break
    return problems


def main() -> None:
    # imported inside the function: compare() can be used in tests without setting up the pipeline/LLM
    from data_agent.pipeline import run_all

    logging.basicConfig(level=logging.WARNING)
    folders = sorted(p for p in SAMPLES_DIR.iterdir() if (p / 'expected.json').exists())
    passed = 0
    for folder in folders:
        files = [str(f) for f in folder.iterdir() if classify(f.name)]
        guides = [f for f in files if classify(f) == 'guide']
        data = [f for f in files if classify(f) == 'data'][0]
        expected = json.loads((folder / 'expected.json').read_text())['tables']

        with tempfile.TemporaryDirectory() as work_dir:
            try:
                result = run_all(guides, data, work_dir)
                problems = compare(expected, [t.model_dump() for t in result.tables])
            except Exception as e:
                problems = [f'error: {e}']

        if problems:
            print(f'❌ {folder.name}')
            for p in problems:
                print('   -', p)
        else:
            passed += 1
            print(f'✅ {folder.name}')

    print(f'\n{passed}/{len(folders)} samples passed')
    sys.exit(0 if passed == len(folders) else 1)
