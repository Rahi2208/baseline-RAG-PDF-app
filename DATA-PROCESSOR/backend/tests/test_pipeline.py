# test the pipeline WITHOUT a real model: llm.structured is replaced by a fake function (monkeypatch)
from data_agent import pipeline
from data_agent.custom_types import Instructions, Plan, Review, Step, TablePlan


def test_bad_plan_gets_fixed_using_the_error_message(pendulum_dir, pendulum_plan, monkeypatch):
    bad_plan = Plan(tables=[TablePlan(id='results', title='R', source='data', steps=[
        Step(op='compute', new_column='T', expr='time / 10'),  # wrong column
    ])])
    answers = [bad_plan, pendulum_plan]  # first answer is wrong, second is correct
    prompts_seen = []

    def fake_structured(prompt, schema, images=None, label=''):
        prompts_seen.append(prompt)
        return answers.pop(0)

    monkeypatch.setattr(pipeline.llm, 'structured', fake_structured)
    bundle = pipeline.step_load([str(pendulum_dir / 'guide.pdf')], str(pendulum_dir / 'data.xlsx'),
                                str(pendulum_dir.parent.parent / 'uploads' / 'test'))
    plan = pipeline.step_plan(bundle, Instructions(items=['T = t / 10'], expected_tables=['R']))

    assert plan == pendulum_plan
    assert 'FAILED' in prompts_seen[1] and "'time' is not a column" in prompts_seen[1]


def test_run_all_with_fake_llm(pendulum_dir, pendulum_plan, monkeypatch, tmp_path):
    def fake_structured(prompt, schema, images=None, label=''):
        if schema is Instructions:
            return Instructions(items=['calculate T', 'calculate g'], expected_tables=['Results', 'Summary'])
        if schema is Plan:
            return pendulum_plan
        return Review(items=[])

    monkeypatch.setattr(pipeline.llm, 'structured', fake_structured)
    result = pipeline.run_all([str(pendulum_dir / 'guide.pdf')], str(pendulum_dir / 'data.xlsx'), str(tmp_path))
    assert [t.title for t in result.tables] == ['Calculation Results', 'Summary']
    assert result.tables[1].rows == [[9.791, 0.09]]
