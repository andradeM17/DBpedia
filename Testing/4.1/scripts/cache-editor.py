import ast
import csv
from collections import Counter
from SPARQLWrapper import SPARQLWrapper, JSON
from SPARQLWrapper.SPARQLExceptions import EndPointInternalError
import time

sparql = SPARQLWrapper("http://dbpedia.org/sparql")

edges = {}
with open("Testing/4.1/output/dictionaries/superclasses.csv", newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    for subclass, superclass in reader:
        edges.setdefault(subclass, []).append(superclass)

def property_builder(csv_path, output_txt_path):
    """
    Reads a CSV with columns: property, domain, range
    and writes a .txt file containing a Python dict of the form:
    {
        property: (domain, range),
        ...
    }
    """

    result = {}

    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)

        # Skip header if present
        rows = list(reader)
        if not rows:
            return

        # Detect and skip header row if it matches expected labels
        start_idx = 0
        if rows[0] and rows[0][0].strip().lower() == "property":
            start_idx = 1

        for row in rows[start_idx:]:
            if len(row) < 3:
                continue

            prop = row[0].strip()
            domain = row[1].strip()
            range_ = row[2].strip()

            # Normalize empty values
            domain = domain if domain else ''
            range_ = range_ if range_ else ''

            result[prop] = (domain, range_)

    # Write dictionary as a Python literal string
    with open(output_txt_path, "w", encoding="utf-8") as f:
        f.write(repr(result))

def rescue(category):
    with open("Testing/4.1/output/dictionaries/entity_types.txt", encoding="utf-8") as e_ts, \
    open("Testing/4.1/output/dictionaries/properties.txt", encoding="utf-8") as properties, \
    open(f"Testing/4.1/output/validations/top-1000/{category}-validations.csv", encoding="utf-8") as validated, \
    open(f"Testing/4.1/output/values/top-1000/{category}-values.csv", encoding="utf-8") as values:
        prop_domain_and_range = ast.literal_eval(properties.read())
        entity_types = ast.literal_eval(e_ts.read())

        validated = csv.reader(validated)
        values = csv.reader(values)
        subjects = set()
        objects = set()
        for row in values:
            if len(row) >= 3:
                subjects.add(row[0])
                objects.add(row[2])
        for i, row in enumerate(validated):
            subj, prop, obj, validity, types = row        
            
            if prop not in prop_domain_and_range:
                print(prop, "not in cache")
                prop_domain_and_range[prop] = types[0], types[2]

            # Fetch types for subject and object
            if subj not in entity_types and ("http://dbpedia.org/resource/" + subj) in subjects:
                entity_types[subj] = types[1]
            actual_domain = entity_types[subj]

            if obj not in entity_types and ("http://dbpedia.org/resource/" + obj) in objects:
                entity_types[obj] = types[3]
            actual_range = entity_types[obj]

        with open('Testing/4.1/output/dictionaries/entity_types.txt', 'w', encoding="utf-8") as e, open('Testing/4.1/output/dictionaries/properties.txt', 'w', encoding="utf-8") as p:
                        e.write(str(entity_types))
                        p.write(str(prop_domain_and_range))

def popularity_sort():
    with open("Testing/4.1/output/dictionaries/entity_types.txt", 'r', encoding="utf-8") as e_ts:
        entity_types = ast.literal_eval(e_ts.read())
        print("File opened!")
    counts = Counter()

    for size in ["1000", "10000"]:
        if size == "1000":
            categories = ["arts and recreation", "biography", "food and agriculture", "geography", "history", "language and literature", "measurements", "philosophy", "religion", "science", "social sciences", "technology"]
        else:
            categories = ["anthropology, psychology and everyday life", "arts", "biology", "geography", "history", "language and literature", "mathematics", "people", "philosophy", "physics", "religion", "society and social sciences", "technology"]
       
        for category in categories:
            print (size, category)
            with open(f"Testing/4.1/output/values/top-{size}/{category}-values.csv", 'r', encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 3:
                        subject = row[0]
                        obj = row[2]

                        counts[subject] += 1
                        counts[obj] += 1
            print("CSVs counted!")

    filtered_entities = {
        k: v for k, v in entity_types.items() if counts[k] > 100
    }

    return filtered_entities

def update_types():
    still_failing = []

    with open("Testing/4.1/output/dictionaries/entity_types.txt", "r", encoding="utf-8") as f:
        entity_types = ast.literal_eval(f.read())

    with open("Testing/4.1/output/dictionaries/superclasses.txt", "r", encoding="utf-8") as f:
        superclasses_for_types = ast.literal_eval(f.read())

    total = len(entity_types)
    print(total, "samples")
    entity_types = dict(sorted(entity_types.items(), key=lambda item: item[0]))  # Sort by entity name
    #entity_types = popularity_sort()  # Sort by popularity

    for i, (entity, types) in enumerate(entity_types.items()):
        if types == {"RETRY"}:
            print("Sample", i + 1, ":", entity, "(", round((100 * i) / len(entity_types)), "%)")
            current_types = get_types(entity, superclasses_for_types)

            if current_types == {"RETRY"}:
                print("Retry failed for", entity)
                still_failing.append(entity)
                continue

            if types != current_types:
                print(types)
                print(current_types)
                print("Update to", entity)
                entity_types[entity] = current_types

        if i % 25000 == 0:
            with open("Testing/4.1/output/dictionaries/entity_types.txt", "w", encoding="utf-8") as f:
                f.write(str(entity_types))

    # Write once at the end
    with open("Testing/4.1/output/dictionaries/entity_types.txt", "w", encoding="utf-8") as f:
        f.write(str(entity_types))

    print("Still failing:", still_failing)

def get_superclasses(type_uri):
    result = []
    visited = set()
    stack = [type_uri]

    while stack:
        current = stack.pop()
        for sup in edges.get(current, []):
            if sup not in visited:
                visited.add(sup)
                result.append(sup)
                stack.append(sup)

    return result

def get_types(entity, superclasses_for_types):
    """
    Returns the ontology types of an entity, including all superclasses.
    Only returns types in the dbo: namespace.
    """
    types = []
    query = f"""
        SELECT DISTINCT ?type
        WHERE {{
            <{entity}> rdf:type ?type .
            FILTER(STRSTARTS(STR(?type), "http://dbpedia.org/ontology/"))
        }}
    """
    result = run_query(query)
    if result == "RETRY":
        time.sleep(2)
        return {"RETRY"}
    if result["results"]["bindings"]:
        for binding in result["results"]["bindings"]:
            if "type" in binding:
                base_type = binding["type"]["value"]
                if base_type not in superclasses_for_types:
                    print(base_type, "not in cache")
                    superclasses_for_types[base_type] = get_superclasses(base_type)
                types.extend([base_type] + superclasses_for_types[base_type])
    return set(types)  # Return unique types

def get_superclasses(type_uri):
    edges = {}

    # load all subclass -> list(superclass)
    with open("Testing/4.1/output/dictionaries/superclasses.csv", newline="") as f:
        reader = csv.reader(f)
        for subclass, superclass in reader:
            edges.setdefault(subclass, []).append(superclass)

    result = []
    visited = set()

    stack = [type_uri]
    while stack:
        current = stack.pop()
        for sup in edges.get(current, []):
            if sup not in visited:
                visited.add(sup)
                result.append(sup)
                stack.append(sup)

    return result

def run_query(query):
    """
    Executes a SPARQL query against DBpedia.
    Returns results in JSON format.
    Handles endpoint errors by returning an empty bindings list.
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    try:
        return sparql.query().convert()
    except EndPointInternalError as e:
        # DBpedia endpoint errors handled gracefully
        return "RETRY"
    except Exception as e:
        # Catch-all for unexpected errors
        return "RETRY"
    
def sort_alphabetically():
    with open("Testing/4.1/output/dictionaries/entity_types.txt", "r", encoding="utf-8") as e, open("Testing/4.1/output/dictionaries/properties.txt", "r", encoding="utf-8") as p, open("Testing/4.1/output/dictionaries/superclasses.txt", "r", encoding="utf-8") as s:
        entity_types = ast.literal_eval(e.read())
        properties = ast.literal_eval(p.read())
        superclasses = ast.literal_eval(s.read())
        entity_types = dict(sorted(entity_types.items(), key=lambda item: item[0]))  # Sort by entity name
        properties = dict(sorted(properties.items(), key=lambda item: item[0]))  # Sort by property name
        superclasses = dict(sorted(superclasses.items(), key=lambda item: item[0]))
    with open("Testing/4.1/output/dictionaries/entity_types.txt", "w", encoding="utf-8") as e, open("Testing/4.1/output/dictionaries/properties.txt", "w", encoding="utf-8") as p, open("Testing/4.1/output/dictionaries/superclasses.txt", "w", encoding="utf-8") as s:
        e.write(str(entity_types))
        p.write(str(properties))
        s.write(str(superclasses))

def main():
    #rescue("arts and recreation")
    #update_types()
    #print("\nTypes updated!\n\n")
    #property_builder("Testing/4.1/output/dictionaries/properties.csv", "Testing/4.1/output/dictionaries/properties.txt")
    sort_alphabetically()

if __name__ == "__main__":
    main()