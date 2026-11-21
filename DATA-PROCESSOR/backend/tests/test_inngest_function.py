# test the full Inngest function (5 steps) using Inngest's "mocked" client + a fake LLM
import inngest
from inngest.experimental import mocked

from data_agent import main, pipeline
from data_agent.custom_types import Instructions, Plan, Review


def test_process_job_runs_to_completion(pendulum_dir, pendulum_plan, monkeypatch, tmp_path):
    def fake_structured(prompt, schema, images=None, label=''):
        if schema is Instructions:
            return Instructions(items=['calculate g'], expected_tables=['Results', 'Summary'])
        if schema is Plan:
            return pendulum_plan
        return Review(items=[])

    monkeypatch.setattr(pipeline.llm, 'structured', fake_structured)
    client = mocked.Inngest(app_id='test', serializer=inngest.PydanticSerializer())
    event = inngest.Event(name='data/process', data={
        'job_id': 'test',
        'work_dir': str(tmp_path),
        'guide_paths': [str(pendulum_dir / 'guide.pdf')],
        'data_path': str(pendulum_dir / 'data.xlsx'),
    })

    res = mocked.trigger(main.process_job, event, client)

    assert res.status == mocked.Status.COMPLETED
    assert [t['id'] for t in res.output['tables']] == ['results', 'summary']
