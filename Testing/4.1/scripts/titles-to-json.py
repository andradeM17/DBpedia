import json
import random
import urllib.parse

num_lines = 200
files = ["people.txt", "geography.txt", "history.txt"]
data = {}

for file_name in files:
    key = file_name[:-4]  # 'a.txt' -> 'a'
    try:
        with open("Testing/4.1/output/pages/"+file_name, "r", encoding="utf-8") as f:
            all_lines = [
                urllib.parse.unquote(line.strip())  # decode URL-encoded text
                for line in f if line.strip()
            ]
            if file_name == "people.txt":
                selected_lines = random.sample(all_lines, min(500, len(all_lines)))
            else:
                selected_lines = random.sample(all_lines, min(num_lines, len(all_lines)))        
            data[key] = selected_lines
    except FileNotFoundError:
        print(f"{file_name} not found.")
        data[key] = []

# Write to JSON file
with open("Testing/4.1/output/random-entities/random_output.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("Randomly selected lines saved to random_output.json")
