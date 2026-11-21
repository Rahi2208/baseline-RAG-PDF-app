# executor.py: runs the plan (Plan) step by step with pandas
import json

import pandas as pd

from data_agent.custom_types import Plan, ResultTable
from data_agent.operations import PlanError, apply_step, describe_step


def to_result_table(table_id: str, title: str, df: pd.DataFrame, formulas: list[str]) -> ResultTable:
    # to_json -> json.loads: turn NaN into null and numpy types into plain numbers
    data = json.loads(df.to_json(orient='split', index=False))
    return ResultTable(id=table_id, title=title, columns=data['columns'],
                       rows=data['data'], formulas=formulas)


def run_plan(plan: Plan, sheets: dict[str, pd.DataFrame]) -> list[ResultTable]:
    frames = dict(sheets)  # data sources: Excel sheets + tables already built
    results: list[ResultTable] = []

    for table in plan.tables:
        if table.source not in frames:
            raise PlanError(
                f"table '{table.id}': source '{table.source}' does not exist. "
                f'Available: {list(frames)}'
            )
        df = frames[table.source]
        for i, step in enumerate(table.steps, start=1):
            try:
                df = apply_step(df, step)
            except PlanError as e:
                raise PlanError(f"table '{table.id}', step {i}: {e}") from e

        frames[table.id] = df  # this table can be the source of the next table
        formulas = [describe_step(s) for s in table.steps]
        results.append(to_result_table(table.id, table.title, df, formulas))

    return results
