# try_ask.py: first test of chatting with the model (not part of the app, just for trying things out)
# run: uv run python playground/try_ask.py
import logging

from data_agent import config, llm

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)

print('host :', config.OLLAMA_HOST)
print('model:', config.LLM_MODEL)
print(llm.ask('State the formula for the period of a simple pendulum in one line'))
