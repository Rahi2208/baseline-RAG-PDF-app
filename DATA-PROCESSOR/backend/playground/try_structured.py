# try_structured.py: test the model answering in JSON that matches a Pydantic schema
# run: uv run python playground/try_structured.py
import logging

from pydantic import BaseModel

from data_agent import llm

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)


class Formula(BaseModel):
    name: str
    formula: str
    variables: list[str]


result = llm.structured('Explain the formula for the period of a simple pendulum.', Formula, label='try')
print(type(result))    # <class '__main__.Formula'>  -> already a Python object, not text
print(result.formula)
print(result.variables)
