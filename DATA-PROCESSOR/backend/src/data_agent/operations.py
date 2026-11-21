# operations.py: the "dictionary" of pandas operations a plan is allowed to use
# the LLM only picks an op + parameters; our code does the calculating (so results are deterministic)
import ast
import math

import numpy as np
import pandas as pd

from data_agent.custom_types import Step


class PlanError(Exception):
    # error caused by a bad plan (missing column, odd formula, etc.)
    # the message is sent back to the LLM so it can fix the plan
    pass


CONSTANTS = {'pi': math.pi, 'e': math.e}
ALLOWED_FUNCS = {'sqrt', 'abs', 'log', 'log10', 'exp', 'sin', 'cos', 'tan'}

# allowed kinds of formula "pieces". Anything else (attribute access, import, lambda, etc.) is rejected
_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare,
    ast.Name, ast.Load, ast.Constant, ast.Call,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv,
    ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or, ast.BitAnd, ast.BitOr,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
)


def validate_expr(expr: str, columns: list[str]) -> None:
    # check the formula BEFORE running it: only numbers, column names, constants, math functions allowed
    if '^' in expr:
        raise PlanError(f"formula '{expr}' uses '^'. For powers use '**'")
    try:
        tree = ast.parse(expr, mode='eval')
    except SyntaxError as e:
        raise PlanError(f"formula '{expr}' is not valid: {e.msg}") from e

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise PlanError(f"formula '{expr}' uses disallowed syntax: {type(node).__name__}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FUNCS:
                raise PlanError(f"formula '{expr}': the only allowed functions are {sorted(ALLOWED_FUNCS)}")
            if node.keywords:
                raise PlanError(f"formula '{expr}': functions cannot take named arguments")
        if isinstance(node, ast.Name):
            allowed = set(columns) | set(CONSTANTS) | ALLOWED_FUNCS
            if node.id not in allowed:
                raise PlanError(f"formula '{expr}': '{node.id}' is not a column. Available columns: {columns}")


def _need(step: Step, *names: str) -> None:
    # make sure the required parameters for this op are filled in
    for name in names:
        if getattr(step, name) in (None, [], ''):
            raise PlanError(f"op '{step.op}' needs parameter '{name}'")


def _check_columns(df: pd.DataFrame, cols: list[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise PlanError(f'columns {missing} do not exist. Available columns: {list(df.columns)}')


# ---------- one function per op ----------

def op_compute(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    # create a new column from a formula, e.g. T = time_10_swings / 10
    _need(step, 'new_column', 'expr')
    validate_expr(step.expr, list(df.columns))
    df = df.copy()
    df[step.new_column] = df.eval(step.expr, resolvers=[CONSTANTS])
    return df


def op_filter(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    # filter rows, e.g. trial > 1 and string_length <= 1
    _need(step, 'expr')
    validate_expr(step.expr, list(df.columns))
    return df.query(step.expr, resolvers=[CONSTANTS])


def op_select(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    # pick + order columns (used to match a template's format)
    _need(step, 'columns')
    _check_columns(df, step.columns)
    return df[step.columns]


def op_rename(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    _need(step, 'renames')
    mapping = {r.old: r.new for r in step.renames}
    _check_columns(df, list(mapping))
    return df.rename(columns=mapping)


def op_sort(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    _need(step, 'by')
    _check_columns(df, step.by)
    return df.sort_values(step.by, ascending=not step.descending)


def op_round(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    # if columns is empty: round all numeric columns
    _need(step, 'decimals')
    cols = step.columns or list(df.select_dtypes('number').columns)
    _check_columns(df, cols)
    df = df.copy()
    df[cols] = df[cols].round(step.decimals)
    return df


def op_group_agg(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    # mean/sum per group, e.g. mean g per string_length
    _need(step, 'by', 'aggregations')
    _check_columns(df, step.by + [a.column for a in step.aggregations])
    named = {a.output: (a.column, a.func) for a in step.aggregations}
    return df.groupby(step.by, as_index=False).agg(**named)


def op_aggregate(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    # one-row summary of the whole data, e.g. mean g
    _need(step, 'aggregations')
    _check_columns(df, [a.column for a in step.aggregations])
    row = {a.output: df[a.column].agg(a.func) for a in step.aggregations}
    return pd.DataFrame([row])


def op_linear_fit(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    # linear regression y = slope * x + intercept, plus R²
    _need(step, 'x', 'y')
    _check_columns(df, [step.x, step.y])
    x = df[step.x].astype(float).to_numpy()
    y = df[step.y].astype(float).to_numpy()
    if len(x) < 2:
        raise PlanError('linear_fit needs at least 2 rows of data')
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    ss_res = float(((y - y_pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot else 1.0
    return pd.DataFrame([{'slope': slope, 'intercept': intercept, 'r2': r2}])


OPERATIONS = {
    'compute': op_compute,
    'filter': op_filter,
    'select': op_select,
    'rename': op_rename,
    'sort': op_sort,
    'round': op_round,
    'group_agg': op_group_agg,
    'aggregate': op_aggregate,
    'linear_fit': op_linear_fit,
}


def apply_step(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    try:
        return OPERATIONS[step.op](df, step)
    except PlanError:
        raise
    except Exception as e:  # other pandas errors are also turned into PlanError so the LLM can fix them
        raise PlanError(f"op '{step.op}' failed: {type(e).__name__}: {e}") from e


def describe_step(step: Step) -> str:
    # "human" version of each step, shown under the table
    match step.op:
        case 'compute':
            return f'{step.new_column} = {step.expr}'
        case 'filter':
            return f'filter: {step.expr}'
        case 'select':
            return f"columns: {', '.join(step.columns or [])}"
        case 'rename':
            return 'rename: ' + ', '.join(f'{r.old} → {r.new}' for r in step.renames or [])
        case 'sort':
            direction = 'high → low' if step.descending else 'low → high'
            return f"sort {', '.join(step.by or [])} ({direction})"
        case 'round':
            cols = ', '.join(step.columns) if step.columns else 'all numbers'
            return f'round {cols} to {step.decimals} decimals'
        case 'group_agg' | 'aggregate':
            aggs = ', '.join(f'{a.output} = {a.func}({a.column})' for a in step.aggregations or [])
            per = f" per {', '.join(step.by)}" if step.op == 'group_agg' and step.by else ''
            return f'{aggs}{per}'
        case 'linear_fit':
            return f'linear regression: {step.y} = slope × {step.x} + intercept'
    return step.op
