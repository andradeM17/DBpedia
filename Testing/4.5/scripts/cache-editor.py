import ast
import csv
from collections import Counter
from SPARQLWrapper import SPARQLWrapper, JSON
from SPARQLWrapper.SPARQLExceptions import EndPointInternalError

sparql = SPARQLWrapper("http://dbpedia.org/sparql")

def rescue():
    with open("Testing/4.5/output/dictionaries/entity_types.txt") as e_ts, open("Testing/4.5/output/dictionaries/properties.txt") as properties, open(f"Testing/4.5/output/validations/top-10000/geography-validations.csv") as validated:
        prop_domain_and_range = ast.literal_eval(properties.read())
        entity_types = ast.literal_eval(e_ts.read())

        reader = csv.reader(validated)
        for i, row in enumerate(reader):
            subj, prop, obj, validity, types = row        

            if prop not in prop_domain_and_range:
                print(prop, "not in cache")
                prop_domain_and_range[prop] = types[0], types[2]

            # Fetch types for subject and object
            if subj not in entity_types:
                entity_types[subj] = types[1]
            actual_domain = entity_types[subj]

            if obj not in entity_types:
                entity_types[obj] = types[3]
            actual_range = entity_types[obj]

        with open('Testing/4.5/output/dictionaries/entity_types.txt', 'w', encoding="utf-8") as e, open('Testing/4.5/output/dictionaries/properties.txt', 'w', encoding="utf-8") as p:
                        e.write(str(entity_types))
                        p.write(str(prop_domain_and_range))

def popularity_sort():
    with open("Testing/4.5/output/dictionaries/entity_types.txt", 'r', encoding="utf-8") as e_ts:
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
            with open(f"Testing/4.5/output/values/top-{size}/{category}-values.csv", 'r', encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 3:
                        subject = row[0]
                        obj = row[2]

                        counts[subject] += 1
                        counts[obj] += 1
            print("CSVs counted!")

    filtered_entities = {
        k: v for k, v in entity_types.items() if counts[k] > 50
    }

    return filtered_entities

def update_types():
    with open("Testing/4.5/output/dictionaries/entity_types.txt", "r", encoding="utf-8") as f:
        entity_types = ast.literal_eval(f.read())

    with open("Testing/4.5/output/dictionaries/superclasses.txt", "r", encoding="utf-8") as f:
        superclasses_for_types = ast.literal_eval(f.read())

    total = len(entity_types)
    print(total, "samples")
    entity_types = dict(sorted(entity_types.items(), key=lambda item: item[0]))  # Sort by entity name
    #entity_types = popularity_sort()  # Sort by popularity

    for i, (entity, types) in enumerate(entity_types.items()):
        if types == ",":
            print("Sample", i + 1, ":", entity, "(", round((100 * i) / total), "%)")
            current_types = get_types(entity, superclasses_for_types)

            if types != current_types:
                print(types)
                print(current_types)
                print("Update to", entity)
                entity_types[entity] = current_types

        if i % 25000 == 0:
            with open("Testing/4.5/output/dictionaries/entity_types.txt", "w", encoding="utf-8") as f:
                f.write(str(entity_types))

    # Write once at the end
    with open("Testing/4.5/output/dictionaries/entity_types.txt", "w", encoding="utf-8") as f:
        f.write(str(entity_types))

def update_properties():
    with open("Testing/4.5/output/dictionaries/properties.txt", "r", encoding="utf-8") as f:
        properties = ast.literal_eval(f.read())

    total = len(properties)
    print(total, "samples")
    properties = dict(sorted(properties.items(), key=lambda item: item[0]))  # Sort by property name

    for i, (prop, (domain, range)) in enumerate(properties.items()):
        if domain == "[" or range == "[":
            print("Sample", i + 1, ":", prop, "(", round((100 * i) / total), "%)")
            current_domain, current_range = get_domain_and_range(prop)

            if (domain, range) != (current_domain, current_range):
                print(domain, range)
                print(current_domain, current_range)
                print("Update to", prop)
                properties[prop] = (current_domain, current_range)

        
    with open("Testing/4.5/output/dictionaries/properties.txt", "w", encoding="utf-8") as f:
        f.write(str(properties))


def get_superclasses(type_uri):
    """Returns all superclasses of a given type, excluding owl:Thing."""
    superclasses = []
    query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT ?superclass
        WHERE {{
            <{type_uri}> rdfs:subClassOf ?superclass .
        }}
    """
    result = run_query(query)
    for binding in result["results"]["bindings"]:
        if "superclass" in binding:
            if binding["superclass"]["value"] != "http://www.w3.org/2002/07/owl#Thing":
                superclasses.append(binding["superclass"]["value"])
    return superclasses

def get_types(entity, superclasses_for_types):
    """
    Returns the ontology types of an entity, including all superclasses.
    Only returns types in the dbo: namespace.
    """
    types = []
    query = f"""
        SELECT DISTINCT ?type
        WHERE {{
            <http://dbpedia.org/resource/{entity}> rdf:type ?type .
            FILTER(STRSTARTS(STR(?type), "http://dbpedia.org/ontology/"))
        }}
    """
    result = run_query(query)
    if result["results"]["bindings"]:
        for binding in result["results"]["bindings"]:
            if "type" in binding:
                base_type = binding["type"]["value"]
                if base_type not in superclasses_for_types:
                    print(base_type, "not in cache")
                    superclasses_for_types[base_type] = get_superclasses(base_type)
                types.extend([base_type] + superclasses_for_types[base_type])
    return set(types)  # Return unique types

def get_domain_and_range(property):
    """Fetches the rdfs:domain and rdfs:range of a DBpedia property."""
    domain = ""
    range = ""
    query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

        SELECT DISTINCT ?domain ?range
        WHERE {{
            dbo:{property} rdfs:domain ?domain .
            dbo:{property} rdfs:range ?range .
        }}
    """
    result = run_query(query)
    if result["results"]["bindings"]:
        binding = result["results"]["bindings"][0]
        if "domain" in binding:
            domain = binding["domain"]["value"]
        if "range" in binding:
            range = binding["range"]["value"]
    return domain, range

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
        return {"results": {"bindings": []}}
    except Exception as e:
        # Catch-all for unexpected errors
        return {"results": {"bindings": []}}

def main():
    #rescue()
    update_types()
    #popularity_sort()
    update_properties()

if __name__ == "__main__":
    main()