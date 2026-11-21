# prompts.py: all prompt texts are collected here
# prompts are written in English because the model is more consistent that way,
# but the model is asked to keep the document's language for table titles & contents
import json

from data_agent.custom_types import InputBundle, Instructions, Plan, ResultTable

OPS_REFERENCE = """
Available operations (field "op") and their parameters:
- compute:    new_column, expr   -> add a column from a formula, e.g. expr "time / 10"
- filter:     expr               -> keep rows where the condition is true, e.g. "value > 0 and group == 'A'"
- select:     columns            -> keep and ORDER these columns (use it last to match a template)
- rename:     renames [{old, new}] -> rename columns (use it to match column names in a template)
- sort:       by, descending
- round:      decimals, columns (optional, empty = all numeric columns)
- group_agg:  by, aggregations [{column, func, output}] -> one row per group
- aggregate:  aggregations [{column, func, output}]     -> ONE summary row for the whole table
- linear_fit: x, y               -> one row with slope, intercept, r2
func is one of: mean, sum, min, max, count, std, median

Formula rules (expr):
- use ONLY column names that exist at that point (listed below, plus columns you created earlier)
- power is ** (never ^). Constants: pi, e. Functions: sqrt, abs, log, log10, exp, sin, cos, tan
- strings in conditions use single quotes: group == 'A'

Table rules:
- each table has: id (snake_case, unique), title (in the document's language), source, steps
- source is a sheet name from the data OR the id of an EARLIER table
  (e.g. a summary table can use source = id of the detailed table)
- make exactly one table for each table the guide asks for, in the same order
""".strip()


def _data_block(bundle: InputBundle) -> str:
    parts = []
    for s in bundle.sheets:
        parts.append(
            f'Sheet "{s.name}" ({s.n_rows} rows)\n'
            f'Columns and types: {json.dumps(s.dtypes)}\n'
            f'First rows: {json.dumps(s.sample_rows, ensure_ascii=False)}'
        )
    return '\n\n'.join(parts)


def _guide_block(bundle: InputBundle) -> str:
    text = bundle.guide_text or '(no extractable text, read the attached images)'
    note = f'\n({len(bundle.guide_images)} guide image(s) attached)' if bundle.guide_images else ''
    return text + note


def extract_instructions(bundle: InputBundle) -> str:
    return f"""You read a GUIDE that explains how to process raw (experimental) data into tables.

List every instruction in the guide as short, self-contained items:
formulas (write them exactly), rounding, filters, units, sorting,
and the required table layout (column names and their order) if the guide shows a template.
Also list the tables the guide asks for, in order.
Do not invent instructions that are not in the guide. Keep the guide's language.

GUIDE:
{_guide_block(bundle)}

DATA (only the structure and first rows, for context):
{_data_block(bundle)}"""


def make_plan(bundle: InputBundle, instructions: Instructions,
              previous: Plan | None = None, error: str | None = None) -> str:
    retry = ''
    if previous is not None and error:
        retry = f"""

Your previous plan FAILED with this error:
{error}
Previous plan:
{previous.model_dump_json()}
Fix the problem and return the full corrected plan."""

    return f"""Turn these instructions into a processing plan that will be executed with pandas.
Do NOT calculate numbers yourself; only describe the steps.

{OPS_REFERENCE}

INSTRUCTIONS:
{json.dumps(instructions.items, ensure_ascii=False, indent=1)}

TABLES REQUESTED:
{json.dumps(instructions.expected_tables, ensure_ascii=False)}

DATA:
{_data_block(bundle)}{retry}"""


def review(instructions: Instructions, tables: list[ResultTable]) -> str:
    preview = [
        {'title': t.title, 'columns': t.columns, 'first_rows': t.rows[:5], 'steps': t.formulas}
        for t in tables
    ]
    return f"""Check whether each instruction was followed in the result tables.
For every instruction give: instruction (copy it), done (true/false), note (short reason,
in the instruction's language). Be strict: a wrong formula or a missing column means done = false.

INSTRUCTIONS:
{json.dumps(instructions.items, ensure_ascii=False, indent=1)}

RESULT TABLES:
{json.dumps(preview, ensure_ascii=False, indent=1)}"""
