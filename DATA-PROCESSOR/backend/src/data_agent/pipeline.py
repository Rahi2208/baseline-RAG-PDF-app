# pipeline.py: the processing stages, each a plain function
# main.py wraps each of these functions as one Inngest step,
# but since they're plain functions, they're easy to test and run without Inngest
import logging

from data_agent import llm, prompts
from data_agent.custom_types import InputBundle, Instructions, JobResult, Plan, Review, TableSet
from data_agent.doc_loader import load_inputs, read_data
from data_agent.executor import run_plan
from data_agent.operations import PlanError

logger = logging.getLogger(__name__)
MAX_PLAN_ATTEMPTS = 3  # plan failed to run -> the error is sent to the LLM to fix


def step_load(guide_paths: list[str], data_path: str, work_dir: str) -> InputBundle:
    return load_inputs(guide_paths, data_path, work_dir)


def step_extract(bundle: InputBundle) -> Instructions:
    return llm.structured(prompts.extract_instructions(bundle), Instructions,
                          images=bundle.guide_images, label='extract')


def step_plan(bundle: InputBundle, instructions: Instructions) -> Plan:
    sheets = read_data(bundle.data_path)
    plan: Plan | None = None
    error: str | None = None

    for attempt in range(1, MAX_PLAN_ATTEMPTS + 1):
        prompt = prompts.make_plan(bundle, instructions, previous=plan, error=error)
        plan = llm.structured(prompt, Plan, label='plan')
        try:
            run_plan(plan, sheets)  # "dry run" on the real data: errors show up here
            return plan
        except PlanError as e:
            error = str(e)
            logger.warning('plan failed (attempt %s): %s', attempt, error)

    raise PlanError(f'plan still failed after {MAX_PLAN_ATTEMPTS} attempts: {error}')


def step_run(bundle: InputBundle, plan: Plan) -> TableSet:
    return TableSet(tables=run_plan(plan, read_data(bundle.data_path)))


def step_review(instructions: Instructions, tables: TableSet) -> Review:
    return llm.structured(prompts.review(instructions, tables.tables), Review, label='review')


def run_all(guide_paths: list[str], data_path: str, work_dir: str) -> JobResult:
    # all stages in order, without Inngest (for the CLI & evaluation)
    bundle = step_load(guide_paths, data_path, work_dir)
    instructions = step_extract(bundle)
    plan = step_plan(bundle, instructions)
    tables = step_run(bundle, plan)
    review = step_review(instructions, tables)
    return JobResult(instructions=instructions, plan=plan, tables=tables.tables, review=review)
