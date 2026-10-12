import ollama 


response = ollama.list() #ollama list 
#print(response) 

#chat API 
res = ollama.chat(
    model = 'llama3.2:1b', 
    messages = [
        {'role': 'user', 'content': 'tell me a funny story'}
    ], 
    stream=True
)

for chunk in res: 
    print(chunk['message']['content'], end='', flush=True)


res = ollama.generate(
    model = 'llama3.2:1b', 
    prompt= 'why is the sky blue'
)

print(ollama.show('llama3.2:1b'))

modelfile = """
FROM llama3.2:1b
SYSTEM 
PARAMETER temperature 0.6
"""

ollama.create(model='smith', modelfile=modelfile)

res = ollama.generate(model = "smith", prompt='how to make good advertisement')
print(res['response'])