# cli.py: CLI for running the pipeline straight from the terminal (no server)
# example: uv run data-agent samples/pendulum/guide.pdf samples/pendulum/data.xlsx
import argparse
import json
import logging
import tempfile


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    logging.getLogger('httpx').setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description='Process raw data following a guide')
    parser.add_argument('files', nargs='+', help='guide file(s) (PDF/image) + 1 data file (.xlsx/.csv)')
    parser.add_argument('--json', action='store_true', help='print the full result as JSON')
    args = parser.parse_args()

    # imported here so `--help` still works even without a .env file
    from data_agent.doc_loader import classify
    from data_agent.pipeline import run_all

    guides = [f for f in args.files if classify(f) == 'guide']
    datas = [f for f in args.files if classify(f) == 'data']
    if not guides or len(datas) != 1:
        parser.error('need at least 1 guide and exactly 1 data file')

    with tempfile.TemporaryDirectory() as work_dir:
        result = run_all(guides, datas[0], work_dir)

    if args.json:
        print(json.dumps(result.model_dump(mode='json'), ensure_ascii=False, indent=2))
        return

    for table in result.tables:
        print(f'\n=== {table.title} ===')
        print(' | '.join(table.columns))
        for row in table.rows:
            print(' | '.join(str(v) for v in row))
        print('formulas:', '; '.join(table.formulas))
    print('\n=== instruction check ===')
    for item in result.review.items:
        print('✅' if item.done else '❌', item.instruction, '-', item.note)
