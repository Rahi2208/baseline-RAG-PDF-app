import ollama
import os 

input_file_path = './data/grocery_list.txt' 
output_file_path = './data/categorized-grocery-list.txt' 

model_name = 'llama3.2:1b' 

#check file's existence
if not os.path.exists(input_file_path): #if os.path.exists(path), untuk mengecek apakah path nya exist atau engga
    print(f'input file {input_file_path} does not found') 
    exit(1)

#read input file 
with open(input_file_path, 'r') as f: 
    items = f.read().strip()

prompt = f"""
you are an assistant that categorizes and sorts grocery items. 

Here is a list of grocery items: 
{items} 

Please: 
1. Categorizes these items into appropriate categories such as produce, dairy, meat, grains, and spices.
2. Sort the items alphabetically within each category.
3. Present the categorized list in a clear and organized manner, using bullet points or numbering.
"""

#send prompt to the model(because we interacting with API, we use try except, in js, we ise try error finally)
try: 
    res = ollama.generate(model=model_name, prompt=prompt) 
    geenerated_text = res.get('response','')

    with open(output_file_path, 'w') as f: 
        f.write(geenerated_text.strip())
    print(f'message written in {output_file_path}')

except Exception as e: 
    print('an error has occured') 
    exit(1)