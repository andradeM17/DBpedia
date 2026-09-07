import csv, ast

SCORE_IF_VALID = 1
SCORE_IF_POSSIBLY_VALID = 0
categories = ["arts and recreation", "biography", "food and agriculture", "geography", "history", "language and literature", "religion", "science", "social sciences", "technology"]


def overall_validity():
    with open(f"Testing/4.2/results/group 3/validity of all categories.csv", "w", newline='', encoding="utf-8") as out:
        writer = csv.writer(out)
        writer.writerow(["Category", "Valid", "Valid because there was no expected domain or range", "Valid range but no expected domain", "Valid domain but no expected range", "Completely valid", "Possibly Valid", "Invalid"])
        for category in categories:
            valid_count = 0
            valid_no_d_or_r_count = 0
            valid_d_and_no_r_count = 0
            valid_r_and_no_d_count = 0
            fully_valid_count = 0
            possibly_valid_count = 0
            invalid_count = 0

            with open(f"Testing/4.2/output/validations/group 3/{category}-validations.csv", newline='', encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    validity = row[3]
                    if validity.startswith("Valid"):
                        valid_count += 1
                        if validity == "Valid (no expected domain or range)":
                            valid_no_d_or_r_count += 1
                        elif validity == "Valid (No expected domain, range matches)":
                            valid_r_and_no_d_count += 1
                        elif validity == "Valid (No expected range, domain matches)":
                            valid_d_and_no_r_count += 1
                        else:
                            fully_valid_count += 1
                    elif validity == "Possibly valid":
                        possibly_valid_count += 1
                    else:
                        invalid_count += 1

            writer.writerow([category, valid_count, valid_no_d_or_r_count, valid_r_and_no_d_count, valid_d_and_no_r_count, fully_valid_count, possibly_valid_count, invalid_count])

def fine_grained_validity():
    for category in categories:
        with open(f"Testing/4.2/output/pages/group 3/{category}.txt", encoding="utf-8") as entities_file:
            entities = [line.strip() for line in entities_file.readlines()]

        with open(f"Testing/4.2/output/validations/group 3/{category}-validations.csv", newline='', encoding="utf-8") as f, open(f"Testing/4.2/results/group 3/validity of {category} entities.csv", "w", newline='', encoding="utf-8") as g:
            reader = csv.reader(f)
            rows = list(reader)
            writer = csv.writer(g)
            writer.writerow(["Entity", "Overall validity %", "Number of triples", "Subject validity %", "Number of instances as a subject", "Object validity %", "Number of instances as a subject"])
            for entity in entities:
                sub_valid_count = 0
                obj_valid_count = 0
                sub_count = 0
                obj_count = 0
                count = 0
                for row in rows:
                    sub = row[0]
                    obj = row[2]
                    validity = row[3]
                    if sub == entity:
                        sub_count += 1
                        count += 1
                        if validity.startswith("Valid"):
                            sub_valid_count += SCORE_IF_VALID
                        elif validity == "Possibly valid":
                            sub_valid_count += SCORE_IF_POSSIBLY_VALID
                    elif obj == entity:
                        obj_count += 1
                        count += 1
                        if validity.startswith("Valid"):
                            obj_valid_count += SCORE_IF_VALID
                        elif validity == "Possibly valid":
                            obj_valid_count += SCORE_IF_POSSIBLY_VALID
                print(f"Entity: {entity}")
                writer.writerow([entity,
                                 round((100*(sub_valid_count + obj_valid_count)) / count) if count > 0 else 0,
                                 count,
                                 round((100*sub_valid_count) / sub_count) if sub_count > 0 else 0,
                                 sub_count,
                                 round((100*obj_valid_count) / obj_count) if obj_count > 0 else 0,
                                 obj_count])

def all_invalidities():
    with open(f"Testing/4.2/results/group 3/invalidities.csv", "w", newline='', encoding="utf-8") as g:
        writer = csv.writer(g)
        writer.writerow(["Expected", "Actual"])
        for category in categories:
            with open(f"Testing/4.2/output/validations/group 3/{category}-validations.csv", newline='', encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row[3] == "Not valid":
                        invalidities = ast.literal_eval(row[4])
                        if invalidities[0] not in invalidities[1]:
                            writer.writerow([invalidities[0], invalidities[1]])
                        if invalidities[2] not in invalidities[3]:
                            writer.writerow([invalidities[2], invalidities[3]])

def invalid_properties():
    with open(f"Testing/4.2/results/group 3/invalid-properties.csv", "w", newline='', encoding="utf-8") as g:
        writer = csv.writer(g)
        writer.writerow(["Property", "Category"])
        for category in categories:
            with open(f"Testing/4.2/output/validations/group 3/{category}-validations.csv", newline='', encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row[3] == "Not valid":
                        writer.writerow([row[1], category])

def all_properties():
    data = {}  # property -> {category: count}
    # Count occurrences
    for category in categories:
        with open(f"Testing/4.2/output/validations/group 3/{category}-validations.csv",
                  newline='', encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                prop = row[1]
                if prop not in data:
                    data[prop] = {c: 0 for c in categories}
                data[prop][category] += 1

    # Write pivot table
    with open(f"Testing/4.2/results/group 3/all-properties.csv",
              "w", newline='', encoding="utf-8") as g:
        writer = csv.writer(g)
        # Header row
        writer.writerow(["Property"] + categories)
        # Rows: property + counts per category
        for prop in sorted(data.keys()):
            writer.writerow([prop] + [data[prop][category] for category in categories])

def main():
    all_invalidities()
    invalid_properties()
    overall_validity()
    fine_grained_validity()
    all_properties()

if __name__ == "__main__":
    main()