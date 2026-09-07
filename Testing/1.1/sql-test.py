import csv
import re
from SPARQLWrapper import SPARQLWrapper, JSON

sparql = SPARQLWrapper("https://dbpedia.org/sparql")
sparql.setReturnFormat(JSON)


# === HELPERS ===

def clean_up_name(resource_name):
    """Convert human-readable name to DBpedia resource format"""
    if not(resource_name.__contains__(".")):
        resource_name = re.sub(r'^(.*?), (.*?)$', r'\2_\1', resource_name)  # Last, First → First_Last
    resource_name = resource_name.replace(" ", "_")
    resource_name = resource_name.replace("'", r"\'")
    resource_name = resource_name.replace("(", r"\(")
    resource_name = resource_name.replace(")", r"\)")

    return resource_name


def query_dbpedia(query):
    """Run a SPARQL query and return JSON results"""
    try:
        sparql.setQuery(query)
        return sparql.query().convert()
    except Exception as e:
        print(f"SPARQL error: {e}")
        return {"results": {"bindings": []}}


def get_properties_and_types(page_name):
    """
    Fetch dbo: properties, their values, ranges, and value types in ONE query.
    Returns list of tuples: (property, value_name, value_uri, range, type)
    """
    query = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX dbo: <http://dbpedia.org/ontology/>
    PREFIX dbr: <http://dbpedia.org/resource/>
    
    SELECT ?property ?value ?range ?type WHERE {{
        dbr:{page_name} ?property ?value .
        FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
        FILTER(ISURI(?value))
        FILTER(!CONTAINS(STR(?property), "wikiPage"))
        FILTER(?property != dbo:thumbnail)

        OPTIONAL {{ ?property rdfs:range ?range }}
        OPTIONAL {{ ?value rdf:type ?type 
                   FILTER(STRSTARTS(STR(?type), "http://dbpedia.org/ontology/")) }}
    }}
    """
    results = query_dbpedia(query)
    props = []
    for r in results["results"]["bindings"]:
        prop = r["property"]["value"].split("/")[-1]
        value_uri = r["value"]["value"]
        value_name = value_uri.split("/")[-1]
        range_uri = r.get("range", {}).get("value", None)
        type_uri = r.get("type", {}).get("value", None)
        props.append((prop, value_name, value_uri, range_uri, type_uri))
    return props


def get_references(page_name):
    """Fetch references where other resources point to this page"""
    query = f"""
    PREFIX dbo: <http://dbpedia.org/ontology/>
    PREFIX dbr: <http://dbpedia.org/resource/>
    
    SELECT ?subject ?property ?range ?type WHERE {{
        ?subject ?property dbr:{page_name} .
        FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
        FILTER(!CONTAINS(STR(?property), "wikiPage"))
        
        OPTIONAL {{ ?property rdfs:range ?range }}
        OPTIONAL {{ dbr:{page_name} rdf:type ?type
                   FILTER(STRSTARTS(STR(?type), "http://dbpedia.org/ontology/")) }}
    }}
    """
    results = query_dbpedia(query)
    refs = []
    for r in results["results"]["bindings"]:
        subject = r["subject"]["value"]
        prop = r["property"]["value"].split("/")[-1]
        range_uri = r.get("range", {}).get("value", None)
        type_uri = r.get("type", {}).get("value", None)
        refs.append((subject, prop, range_uri, type_uri))
    return refs


# === MAIN ===

with open('Wiki/wikimedia_vital_articles.txt', 'r', encoding="utf-8") as pages, open('Testing/1000_optimised(2).csv', 'w', encoding="utf-8", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Page Name", "Score", "Datapoints"])

    current_list = [line.strip() for line in pages.readlines() if line.strip() and not line.startswith("#")]

    for page in current_list:
        clean_page = clean_up_name(page)
        print(f"\n=== Analysing {page} ===")

        score, denom = 0, 0

        # --- Properties ---
        properties = get_properties_and_types(clean_page)
        for prop, value_name, value_uri, range_uri, type_uri in properties:
            print(f"{prop} → {value_name}")

            if not range_uri:
                print("\t❓ No defined range")
                score += 0.5
                denom += 1
            elif type_uri and range_uri == type_uri:
                print("\t✅ Valid")
                score += 1
                denom += 1
            else:
                print("\t❌ Invalid")
                denom += 1
                print(f"\tExpected: {range_uri.split('/')[-1] if range_uri else 'N/A'}")
                print(f"\tActual: {type_uri.split('/')[-1] if type_uri else 'N/A'}")

        # --- References ---
        print(f"\nAnalysing references to {page}...")
        refs = get_references(clean_page)
        for subject, prop, range_uri, type_uri in refs:
            subj_name = subject.split("/")[-1].replace("_", " ")
            print(f"{subj_name} ({prop}) → {page}")

            if not range_uri:
                print("\t❓ No defined range")
                score += 0.5
                denom += 1
            elif type_uri and range_uri == type_uri:
                print("\t✅ Valid")
                score += 1
                denom += 1
            else:
                print("\t❌ Invalid")
                denom += 1

        # --- Score ---
        if denom > 0:
            pct = round(score / denom * 100, 2)
        else:
            pct = 0
        print(f"Score: {pct}% ({score}/{denom})\n")
        writer.writerow([page, pct, denom])
