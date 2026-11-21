import pandas as pd
import pytest

from data_agent.custom_types import Aggregation, Step
from data_agent.operations import PlanError, apply_step, validate_expr

COLS = ['a', 'b']


def df() -> pd.DataFrame:
    return pd.DataFrame({'a': [1.0, 4.0, 9.0], 'b': [2, 2, 3], 'group': ['x', 'y', 'x']})


# ---------- formula validation ----------
def test_valid_formula_passes():
    validate_expr('sqrt(a) * pi + b ** 2', COLS)


@pytest.mark.parametrize('expr', [
    "__import__('os').system('ls')",  # trying to run a system command
    'a.__class__',                     # attribute access
    'c + 1',                           # column does not exist
    'a ^ 2',                           # ^ is not power in Python
    'max(a)',                          # function not allowed
])
def test_dangerous_or_wrong_formula_rejected(expr):
    with pytest.raises(PlanError):
        validate_expr(expr, COLS)


# ---------- each op ----------
def test_compute():
    out = apply_step(df(), Step(op='compute', new_column='c', expr='a / b'))
    assert out['c'].tolist() == [0.5, 2.0, 3.0]


def test_filter():
    out = apply_step(df(), Step(op='filter', expr="a > 2 and group == 'x'"))
    assert out['a'].tolist() == [9.0]


def test_round_all_numeric_columns():
    data = pd.DataFrame({'x': [1.23456], 'y': [2.98765], 'name': ['a']})
    out = apply_step(data, Step(op='round', decimals=2))
    assert out.iloc[0].tolist() == [1.23, 2.99, 'a']


def test_group_agg():
    step = Step(op='group_agg', by=['group'],
                aggregations=[Aggregation(column='a', func='sum', output='total')])
    out = apply_step(df(), step)
    assert dict(zip(out['group'], out['total'])) == {'x': 10.0, 'y': 4.0}


def test_aggregate_becomes_one_row():
    step = Step(op='aggregate', aggregations=[Aggregation(column='a', func='mean', output='avg')])
    out = apply_step(df(), step)
    assert out.shape == (1, 1) and out['avg'][0] == pytest.approx(14 / 3)


def test_linear_fit():
    data = pd.DataFrame({'x': [1, 2, 3], 'y': [3, 5, 7]})  # y = 2x + 1
    out = apply_step(data, Step(op='linear_fit', x='x', y='y'))
    assert out['slope'][0] == pytest.approx(2)
    assert out['intercept'][0] == pytest.approx(1)
    assert out['r2'][0] == pytest.approx(1)


def test_missing_required_parameter():
    with pytest.raises(PlanError, match="needs parameter 'expr'"):
        apply_step(df(), Step(op='compute', new_column='c'))


def test_column_does_not_exist():
    with pytest.raises(PlanError, match='do not exist'):
        apply_step(df(), Step(op='select', columns=['zzz']))
