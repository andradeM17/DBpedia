import os
import pickle
import ast

files = [
    "Testing/4.1/output/dictionaries/entity_types.txt",
    "Testing/4.1/output/dictionaries/properties.txt",
    "Testing/4.1/output/dictionaries/superclasses.txt"
]

for file in files:
    with open(file, "r", encoding="utf-8") as f:
        data = ast.literal_eval(f.read())  # converts text -> real dict

    base, _ = os.path.splitext(file)
    out_file = base + ".pickle"

    with open(out_file, "wb") as f:
        pickle.dump(data, f)