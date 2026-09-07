import json
import urllib.parse

files = ["arts and recreation", "biography", "food and agriculture", "geography", "history", "language and literature", "measurements", "philosophy", "religion", "science", "social sciences", "technology"]


data = {}

for file_name in files:
    key = file_name  # 'a.txt' -> 'a'
    try:
        with open("Testing/4.5/output/pages/top-1000/"+file_name+".txt", "r", encoding="utf-8") as f:
            all_lines = [
                urllib.parse.unquote(line.strip())  # decode URL-encoded text
                for line in f if line.strip()
            ]
                    
            data[key] = all_lines
    except FileNotFoundError:
        print(f"{file_name} not found.")
        data[key] = []

# Write to JSON file
with open("Testing/4.5/output/all-entities/all_entities_output-1000.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print("All entities saved to all_entities_output.json")
