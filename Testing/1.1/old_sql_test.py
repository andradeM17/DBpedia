import csv
import re
from SPARQLWrapper import SPARQLWrapper, JSON

def check_superclass(resource_url, ranges):
    """Check if a resource's superclasses match any of the expected ranges"""
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    
    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dbo: <http://dbpedia.org/ontology/>
    
    SELECT ?superclass WHERE {{
        <{resource_url}> rdfs:subClassOf* ?superclass .
        FILTER(?superclass != <{resource_url}>)
        FILTER(STRSTARTS(STR(?superclass), "http://dbpedia.org/ontology/"))
        FILTER(?superclass != <http://www.w3.org/2002/07/owl#Thing>)
    }}
    """
    
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    
    try:
        results = sparql.query().convert()
        for result in results["results"]["bindings"]:
            superclass_uri = result["superclass"]["value"]
            if superclass_uri in ranges:
                return superclass_uri
        return resource_url
    except:
        return resource_url

def clean_up_name(resource_name):
    """Clean up the resource name by removing unwanted characters"""
    resource_name = re.sub(r'^(.*?), (.*?)$', r'\2 \1', resource_name)  # Last, First to First_Last

    resource_name = resource_name.replace(" ", "_")
    resource_name = resource_name.replace("'", r"\'")
    resource_name = resource_name.replace("(", r"\(")
    resource_name = resource_name.replace(")", r"\)")

    print(resource_name)
    return resource_name

def get_property_range(prop):
    """Fetch rdfs:range for a dbo property using SPARQL"""
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    
    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dbo: <http://dbpedia.org/ontology/>
    
    SELECT ?range WHERE {{
        dbo:{prop} rdfs:range ?range .
    }}
    """
    
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    
    try:
        results = sparql.query().convert()
        ranges = []
        for result in results["results"]["bindings"]:
            ranges.append(result["range"]["value"])
        return ranges
    except:
        return []

def get_property_domain(prop):
    """Fetch rdfs:domain for a dbo property using SPARQL"""
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    
    query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX dbo: <http://dbpedia.org/ontology/>
    
    SELECT ?domain WHERE {{
        dbo:{prop} rdfs:domain ?domain .
    }}
    """
    
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    
    try:
        results = sparql.query().convert()
        domains = []
        for result in results["results"]["bindings"]:
            domains.append(result["domain"]["value"])
        return domains
    except:
        return []

def get_resource_types(resource_name):
    """Fetch rdf:type(s) for a resource, only dbo: types using SPARQL"""
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    
    query = f"""
    SELECT ?type WHERE {{
        <http://dbpedia.org/resource/{resource_name}> rdf:type ?type .
        FILTER(STRSTARTS(STR(?type), "http://dbpedia.org/ontology/"))
    }}
    """
    
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    
    try:
        results = sparql.query().convert()
        types = []
        for result in results["results"]["bindings"]:
            types.append(result["type"]["value"])
        return types
    except:
        print(resource_name, "not found in DBpedia")
        return []

def get_resource_properties(page_name):
    """Get all dbo properties and their values for a resource using SPARQL"""
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    
    query = f"""
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX dbr: <http://dbpedia.org/resource/>
    PREFIX dbo: <http://dbpedia.org/ontology/>
    
    SELECT ?property ?value WHERE {{
        dbr:{page_name} ?property ?value .
        FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
        FILTER(!CONTAINS(STR(?property), "wikiPage"))
        FILTER(?property != dbo:thumbnail)
        FILTER(ISURI(?value))
    }}
    """
    
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    
    try:
        results = sparql.query().convert()
        properties = []
        for result in results["results"]["bindings"]:
            prop_uri = result["property"]["value"]
            value_uri = result["value"]["value"]
            prop_name = prop_uri.split("/")[-1]
            resource_name = value_uri.split("/")[-1]
            properties.append((prop_name, resource_name, value_uri))
        return properties
    except Exception as e:
        print(f"Error querying properties: {e}")
        return []

def get_resource_references(page_name):
    sparql = SPARQLWrapper("https://dbpedia.org/sparql")
    sparql.setReturnFormat(JSON)
    
    query = f"""
    PREFIX dbo: <http://dbpedia.org/ontology/>
    PREFIX dbr: <http://dbpedia.org/resource/>
    
    SELECT ?subject ?property
    WHERE {{
        ?subject ?property dbr:{page_name} .
        FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
        FILTER(!CONTAINS(STR(?property), "wikiPage"))
    }}
    """
    
    sparql.setQuery(query)
    
    try:
        results = sparql.query().convert()
        
        # Extract and return the results
        references = []
        for result in results["results"]["bindings"]:
            subject = result["subject"]["value"]
            property_uri = result["property"]["value"]
            references.append({
                "subject": subject,
                "property": property_uri
            })
        
        return references
        
    except Exception as e:
        print(f"Error querying references: {e}")
        return []

# === MAIN ===

with open('Wiki/wikimedia_vital_articles.txt', 'r', encoding="utf-8") as pages, open('Testing/1.1/1000_(2).csv', 'w', encoding="utf-8", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Page Name", "Score", "Datapoints"])

    current_list = [line.strip() for line in pages.readlines() if line.strip() and not line.startswith("#")]

    for page in current_list:
        score = 0
        denom = 0

        #page = input("Enter the DBpedia page name: ").strip()
        page = current_list.pop(0)

        clean_page = clean_up_name(page)

        print(f"\nAnalysing properties for: {page}")
        print("=" * 30)

        

        # Get all properties for the resource
        properties = get_resource_properties(clean_page)

        if not properties:
            print("No properties found.")
        else:
            for prop, resource_name, resource_uri in properties:
                print(f"{prop} → {resource_name}")

                # get property ranges
                ranges = get_property_range(prop)

                # get resource types
                #resource_name = clean_up_name(resource_name)
                types = get_resource_types(resource_name)

                # check if any match
                if set(ranges) & set(types):
                    print("\t✅ Valid")
                    score += 1
                    denom += 1
                elif ranges == []:
                    print("\t❓ No defined ranges")  
                    score += 0.5   
                    denom += 1              
                else:
                    valid = False
                    for t in types:
                        superclass = check_superclass(t, ranges)
                        if superclass in ranges:
                            valid = True
                            print(f"\t ✅ Valid")
                            score +=1 
                            denom += 1
                            break 
                    if not valid:
                        print("\t❌ Invalid")
                        denom += 1
                        print(f"\tExpected ranges:")
                        for r in ranges:
                            print(f"\t\t{r.split('/')[-1]}")
                        print("\tActual types:")
                        for t in types:
                            print(f"\t\t{t.split('/')[-1]}")
                        if types == []:
                            print("\t\tN/A (No DBO types found)")

        print("\n") 
        print(f"\nAnalysing references to: {page}")

        # Get all references for the resource
        references = get_resource_references(clean_page)

        if not references:
            print("No references found.")
        else:
            print("=" * 30)
            
            old_rpage = ""
            for i, ref in enumerate(references):
                rprop = ref['property']
                subject = ref['subject']
    
                rpage = rprop.split("/")[-1]
                if rpage == old_rpage:
                    continue
                old_rpage = rpage
                ranges = get_property_range(rpage)
                print(f"{subject.split('/')[-1].replace('_', ' ')} ({rpage})  → {page}")
                page_types = get_resource_types(page.replace(" ", "_"))
                if set(ranges) & set(page_types):
                    print("\t✅ Valid")
                    denom += 1
                    score += 1
                elif ranges == []:
                    print("\t❓ No defined ranges")  
                    score += 0.5
                    denom += 1
                else:
                    property_range = get_property_range(rpage)
                    if set(property_range) & set(page_types):
                        print("\t✅ Valid")
                        score += 1
                        denom += 1
                    else:
                        print("\t❌ Invalid")
                        denom += 1

        print("=" * 50)
        print()

        if denom != 0:
            print("Score: ", round(score/denom * 100), "%")
            writer.writerow([page, round(score/denom * 100), denom])
        else:
            writer.writerow([page, 0, 0])

        print("=" * 100)
        print("\n")