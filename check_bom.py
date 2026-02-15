import os

def check_bom(filepath):
    if not os.path.exists(filepath):
        print(f"{filepath} not found")
        return
    with open(filepath, 'rb') as f:
        raw = f.read(3)
        if raw == b'\xef\xbb\xbf':
            print(f"{filepath} has UTF-8 BOM")
        else:
            print(f"{filepath} no BOM")

check_bom(r'c:\Users\ralskwo\Desktop\Study\Privates\FoodFinder\backend\.env')
check_bom(r'c:\Users\ralskwo\Desktop\Study\Privates\FoodFinder\frontend\.env')
