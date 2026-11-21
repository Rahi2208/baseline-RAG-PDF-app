# conftest.py: set up by pytest before any test runs
import os
import subprocess
import sys
from pathlib import Path

import pytest

# tests don't need a real .env; config.py only needs LLM_MODEL to be non-empty
os.environ.setdefault('LLM_MODEL', 'test-model')

from data_agent.custom_types import Aggregation, Plan, RenamePair, Step, TablePlan  # noqa: E402

BACKEND = Path(__file__).parent.parent
SAMPLE = BACKEND / 'samples' / 'pendulum'


@pytest.fixture(scope='session')
def pendulum_dir() -> Path:
    # create the sample files if they don't exist yet
    if not (SAMPLE / 'expected.json').exists():
        subprocess.run([sys.executable, str(SAMPLE.parent / 'make_pendulum.py')], check=True)
    return SAMPLE


@pytest.fixture
def pendulum_plan() -> Plan:
    # the CORRECT plan for the pendulum sample (an ideal LLM answer)
    return Plan(tables=[
        TablePlan(id='results', title='Calculation Results', source='data', steps=[
            Step(op='compute', new_column='t_period', expr='time_10_swings_s / 10'),
            Step(op='compute', new_column='g', expr='4 * pi ** 2 * string_length_m / t_period ** 2'),
            Step(op='round', columns=['t_period', 'g'], decimals=3),
            Step(op='rename', renames=[
                RenamePair(old='trial', new='Trial'),
                RenamePair(old='string_length_m', new='L (m)'),
                RenamePair(old='t_period', new='T (s)'),
                RenamePair(old='g', new='g (m/s2)'),
            ]),
            Step(op='select', columns=['Trial', 'L (m)', 'T (s)', 'g (m/s2)']),
        ]),
        TablePlan(id='summary', title='Summary', source='results', steps=[
            Step(op='aggregate', aggregations=[
                Aggregation(column='g (m/s2)', func='mean', output='g_mean'),
            ]),
            Step(op='round', columns=['g_mean'], decimals=3),
            Step(op='compute', new_column='error', expr='abs(g_mean - 9.8) / 9.8 * 100'),
            Step(op='round', columns=['error'], decimals=2),
            Step(op='rename', renames=[
                RenamePair(old='g_mean', new='mean g'),
                RenamePair(old='error', new='error (%)'),
            ]),
        ]),
    ])
