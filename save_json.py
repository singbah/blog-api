import os, json

def save_t_json(file):
    try:
        products = os.path.join(os.getcwd(), "static", "products.json")
        if not os.path.exists(products):
            with open(products, 'w') as fi:
                json.dump([], fi, indent=4)
            # return False
        
        all_products = []
        with open(products, 'r') as pd:
            all_products = json.load(pd)
            
        all_products.append(file)
    
        with open(products, "w") as fd:
            json.dump(all_products, fd, indent=4)
        return True
    except Exception as e:
        print(e)

def read_json_file():
    try:
        products = os.path.join(os.getcwd(), "static", "products.json")    
        files = []
        with open(products, 'r') as fd:
            files = json.load(fd)
        return files
    except Exception as e:
        return []
    
files = read_json_file()

print(files)
