import json

import pytest

from data_agent.custom_types import Plan, Step, TablePlan
from data_agent.doc_loader import read_data
from data_agent.evaluate import compare
from data_agent.executor import run_plan
from data_agent.operations import PlanError


def test_pendulum_plan_matches_answer(pendulum_dir, pendulum_plan):
    sheets = read_data(str(pendulum_dir / 'data.xlsx'))
    tables = run_plan(pendulum_plan, sheets)
    expected = json.loads((pendulum_dir / 'expected.json').read_text())['tables']

    assert compare(expected, [t.model_dump() for t in tables]) == []
    assert tables[0].columns == ['Trial', 'L (m)', 'T (s)', 'g (m/s2)']  # template format
    assert 'g = 4 * pi ** 2 * string_length_m / t_period ** 2' in tables[0].formulas


def test_wrong_source(pendulum_dir):
    sheets = read_data(str(pendulum_dir / 'data.xlsx'))
    plan = Plan(tables=[TablePlan(id='x', title='X', source='does_not_exist', steps=[])])
    with pytest.raises(PlanError, match="source 'does_not_exist'"):
        run_plan(plan, sheets)


def test_error_mentions_table_and_step(pendulum_dir):
    sheets = read_data(str(pendulum_dir / 'data.xlsx'))
    plan = Plan(tables=[TablePlan(id='results', title='R', source='data', steps=[
        Step(op='compute', new_column='T', expr='time / 10'),  # column "time" does not exist
    ])])
    with pytest.raises(PlanError, match="table 'results', step 1"):
        run_plan(plan, sheets)
