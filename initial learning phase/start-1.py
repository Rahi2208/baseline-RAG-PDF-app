import requests
import json 

url = "http://localhost:11434/api/generate" 

data = {
    "model" : 'llama3.2:1b', 
    "prompt" : 'tell me a funny short story'
}

res = requests.post(url, json=data, stream=True) #requests.post(url server, json=data yang mau dikirim, stream)
#reuqests.post() -> peirntah untuk post, res = requsts.post() -> jawaban hasil post nya 

#check the response status
if res.status_code == 200: 
    print('Generated text:', end = ' ', flush=True) 

    for line in res.iter_lines(): 
        if line:
            decoded_line = line.decode('utf-8') #decode the line 
            result = json.loads(decoded_line) #loads to json
            generated_text = result.get("response", "") #ambil dari json "respo"
            print(generated_text, end="", flush=True) 

else: 
    print('ERROR', res.status_code, res.text) 


"""
dari res, masih dalam encoded data, terus for line in res.iter_lines()  
di decode line.decode('utf-8') hsilnya jadi string
, kita mau ambil response nya aja, 

di line 
print(line)
# b'{"model":"llama3.2:1b","created_at":"2026-10-12T01:56:00Z","response":"Once","done":false}'

print(type(line))
# <class 'bytes'>

di decoded_line 
decoded_line = line.decode('utf-8')

print(decoded_line)
# {"model":"llama3.2:1b","created_at":"2026-10-12T01:56:00Z","response":"Once","done":false}

print(type(decoded_line))
# <class 'str'>

di json jadi dictionary semua, terus kita .get(keys, substitute), keys="response", substitute = ""

"""