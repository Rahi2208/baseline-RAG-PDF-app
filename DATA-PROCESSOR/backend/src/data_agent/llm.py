# llm.py: the only file that talks to the model
# want to switch model/provider? just change this file
import logging
from typing import TypeVar

from ollama import Client
from pydantic import BaseModel, ValidationError

from data_agent import config

logger = logging.getLogger(__name__)
client = Client(host=config.OLLAMA_HOST)  # connection to the ollama server

T = TypeVar('T', bound=BaseModel)
MAX_FORMAT_RETRIES = 2  # if the model's JSON doesn't match the schema, retry this many times


def _chat(messages: list[dict], schema: dict | None, label: str) -> str:
    res = client.chat(
        model=config.LLM_MODEL,
        messages=messages,
        format=schema,                    # force the answer to match the JSON schema
        think=config.LLM_THINK,           # None = model default
        options={
            'temperature': 0,             # 0 = most consistent answers
            'num_ctx': config.LLM_NUM_CTX,
        },
    )
    # ollama reports time in NANOseconds -> divide by 1e9 to get seconds
    seconds = (res.total_duration or 0) / 1e9
    tps = (res.eval_count or 0) / ((res.eval_duration or 1) / 1e9)
    logger.info(
        '[%s] model=%s input=%s output=%s time=%.1fs speed=%.1f tok/s',
        label, config.LLM_MODEL, res.prompt_eval_count, res.eval_count, seconds, tps,
    )
    return res.message.content


def ask(prompt: str) -> str:
    # plain text answer
    return _chat([{'role': 'user', 'content': prompt}], schema=None, label='ask')


def structured(prompt: str, schema: type[T], images: list[str] | None = None,
               label: str = 'llm') -> T:
    # answer as a Pydantic model (schema)
    message: dict = {'role': 'user', 'content': prompt}
    if images:
        message['images'] = images  # image paths, ollama reads the files itself
    messages = [message]

    for attempt in range(1, MAX_FORMAT_RETRIES + 2):
        content = _chat(messages, schema.model_json_schema(), f'{label}#{attempt}')
        try:
            return schema.model_validate_json(content)
        except ValidationError as e:
            logger.warning('[%s] output does not match schema (attempt %s): %s', label, attempt, e)
            # tell the model what was wrong, then ask again
            messages = [
                message,
                {'role': 'assistant', 'content': content},
                {'role': 'user', 'content': f'Your JSON was invalid:\n{e}\nReturn corrected JSON only.'},
            ]
    raise ValueError(f'[{label}] model failed to give valid JSON')
