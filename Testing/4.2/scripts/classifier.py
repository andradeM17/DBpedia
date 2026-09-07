import csv

CATEGORIES = ["arts and recreation", "biography", "food and agriculture", "geography", "history", "language and literature", "measurements", "philosophy", "religion", "science", "social sciences", "technology"]

with open("Testing/4.2/output/all-classified.csv", "r", encoding="utf-8") as f:
    reader = csv.reader(f)
    lines = list(reader)
    for line in lines[1:]:  # skip header
        print(line)
        with open(f"Testing/4.2/output/pages/group {line[2]}/{line[1]}.txt", "a", encoding="utf-8") as out_file:
            out_file.write(line[0] + "\n")