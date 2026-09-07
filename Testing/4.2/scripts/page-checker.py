# Import necessary libraries
from SPARQLWrapper import SPARQLWrapper, JSON
from SPARQLWrapper.SPARQLExceptions import EndPointInternalError
import csv
import re
from datetime import datetime
import ast

# Initialize the SPARQL endpoint to DBpedia
sparql = SPARQLWrapper("http://dbpedia.org/sparql")
LIMIT = 50  # Limit the number of property values per entity to avoid huge queries
LENGTH_OF_LIST = 2 # Value found in results/counts.csv TODO: this should be dynamic
UPDATE_RATE = 400 # How often to update the cache files
CATEGORY = "test"  # Example category; can be changed as needed
CATEGORIES = ["arts and recreation", "biography", "food and agriculture", "geography", "history", "language and literature", "religion", "science", "social sciences", "technology"]
CACHING = True

if CACHING:
    with open("Testing/4.1/output/dictionaries/properties.txt", "r", encoding="utf-8") as p:
        prop_domain_and_range = ast.literal_eval(p.read())
    with open("Testing/4.1/output/dictionaries/entity_types.txt", "r", encoding="utf-8") as e:
        entity_types = ast.literal_eval(e.read())
    with open("Testing/4.1/output/dictionaries/superclasses.txt", "r", encoding="utf-8") as s:
        superclasses_for_types = ast.literal_eval(s.read())


# -------------------------
# --- Validation functions
# -------------------------

def always_valid(text):
    """Validation function that always returns True. Used for XSD string types."""
    return True

def is_yyyy_mm_dd(text: str) -> bool:
    """
    Checks if a string is a valid date in YYYY-MM-DD format.
    Handles negative years by stripping the minus sign and padding the year to 4 digits.
    """
    try:
        if text.startswith('-'):
            temp_text = text[1:]
            parts = temp_text.split("-")
            if len(parts[0]) < 4:
                parts[0] = parts[0].zfill(4)  # pad negative year to 4 digits
            padded_text = "-".join(parts)
            datetime.strptime(padded_text, "%Y-%m-%d")
        else:
            datetime.strptime(text, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def is_double(text: str) -> bool:
    """Checks if text can be converted to a float."""
    try:
        float(text)
        return True
    except ValueError:
        return False

def is_year(text: str) -> bool:
    """Checks if text is an integer, possibly negative (for years)."""
    return re.fullmatch(r"-?\d+", text) is not None

def is_non_negative_integer(text: str) -> bool:
    """Checks if text is a non-negative integer."""
    if not text:
        return False
    text = text.strip()
    return text.isdigit()

def is_positive_integer(text: str) -> bool:
    """Checks if text is a positive integer (>0)."""
    return text.isdigit() and int(text) > 0

def is_integer(text: str) -> bool:
    """Checks if text is an integer (non-negative, as written)."""
    return text.isdigit()

# -------------------------
# --- SPARQL query execution
# -------------------------

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

# -------------------------
# --- Functions to fetch counts
# -------------------------

def get_counts(entity):
    """
    Counts the number of distinct ontology properties where the entity appears as subject or object.
    Excludes certain trivial properties (like abstract or image-related ones) to reduce noise.
    Returns SPARQL results.
    """
    query = f"""SELECT
        (COUNT(DISTINCT ?prop_as_subject) AS ?subjectPropertyCount)
        (COUNT(DISTINCT ?prop_as_object) AS ?objectPropertyCount)
        WHERE {{
            {{<http://dbpedia.org/resource/{entity}> ?prop_as_subject ?value .
                FILTER(STRSTARTS(STR(?prop_as_subject), "http://dbpedia.org/ontology/"))
                FILTER(!CONTAINS(STR(?prop_as_subject), "wikiPage"))
                FILTER(?prop_as_subject NOT IN ( dbo:abstract, dbo:bicycleInformation, dbo:boilerPressure, dbo:carNumber, dbo:careerStation, dbo:collection, dbo:damage, dbo:depictionDescription, dbo:description, dbo:event, dbo:imageSize, dbo:impactFactorAsOf, dbo:isHandicappedAccessible, dbo:leaderFunction, dbo:lengthReference, dbo:liberationDate, dbo:logo, dbo:mapCaption, dbo:militaryService, dbo:minister, dbo:name, dbo:note, dbo:notes, dbo:numberOfVisitorsAsOf, dbo:orderInOffice, dbo:other, dbo:parkingInformation, dbo:personFunction, dbo:picture, dbo:politicalLeader, dbo:projectKeyword, dbo:pronunciation, dbo:quote, dbo:reference, dbo:restingPlacePosition, dbo:restriction, dbo:sales, dbo:selection, dbo:signature, dbo:soundRecording, dbo:speaker, dbo:statisticLabel, dbo:strength, dbo:termPeriod, dbo:thumbnail, dbo:title, dbo:tournamentRecord, dbo:visitorStatisticsAsOf, dbo:winsAtAsia, dbo:winsAtAus, dbo:winsAtChallenges, dbo:winsAtChampionships, dbo:winsAtJapan, dbo:winsAtLET, dbo:winsAtNWIDE, dbo:winsAtOtherTournaments, dbo:winsAtPGA, dbo:winsAtSenEuro, dbo:winsInEurope ))
            }}
            UNION
            {{?value ?prop_as_object <http://dbpedia.org/resource/{entity}> .
                FILTER(STRSTARTS(STR(?prop_as_object), "http://dbpedia.org/ontology/"))
                FILTER(!CONTAINS(STR(?prop_as_object), "wikiPage"))
                FILTER(?prop_as_object NOT IN ( dbo:abstract, dbo:bicycleInformation, dbo:boilerPressure, dbo:carNumber, dbo:careerStation, dbo:collection, dbo:damage, dbo:depictionDescription, dbo:description, dbo:event, dbo:imageSize, dbo:impactFactorAsOf, dbo:isHandicappedAccessible, dbo:leaderFunction, dbo:lengthReference, dbo:liberationDate, dbo:logo, dbo:mapCaption, dbo:militaryService, dbo:minister, dbo:name, dbo:note, dbo:notes, dbo:numberOfVisitorsAsOf, dbo:orderInOffice, dbo:other, dbo:parkingInformation, dbo:personFunction, dbo:picture, dbo:politicalLeader, dbo:projectKeyword, dbo:pronunciation, dbo:quote, dbo:reference, dbo:restingPlacePosition, dbo:restriction, dbo:sales, dbo:selection, dbo:signature, dbo:soundRecording, dbo:speaker, dbo:statisticLabel, dbo:strength, dbo:termPeriod, dbo:thumbnail, dbo:title, dbo:tournamentRecord, dbo:visitorStatisticsAsOf, dbo:winsAtAsia, dbo:winsAtAus, dbo:winsAtChallenges, dbo:winsAtChampionships, dbo:winsAtJapan, dbo:winsAtLET, dbo:winsAtNWIDE, dbo:winsAtOtherTournaments, dbo:winsAtPGA, dbo:winsAtSenEuro, dbo:winsInEurope ))
            }}
        }}
    """
    result = run_query(query)
    return result

# -------------------------
# --- Functions to fetch properties/values
# -------------------------

def get_prop_and_obj(entity):
    """Fetches all ontology properties and values where entity is the subject."""
    query = f"""
        SELECT ?property ?value
        WHERE {{
            <http://dbpedia.org/resource/{entity}> ?property ?value .
            FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
            FILTER(!CONTAINS(STR(?property), "wikiPage"))
            FILTER(?property NOT IN ( dbo:abstract, dbo:bicycleInformation, dbo:boilerPressure, dbo:carNumber, dbo:careerStation, dbo:collection, dbo:damage, dbo:depictionDescription, dbo:description, dbo:event, dbo:imageSize, dbo:impactFactorAsOf, dbo:isHandicappedAccessible, dbo:leaderFunction, dbo:lengthReference, dbo:liberationDate, dbo:logo, dbo:mapCaption, dbo:militaryService, dbo:minister, dbo:name, dbo:note, dbo:notes, dbo:numberOfVisitorsAsOf, dbo:orderInOffice, dbo:other, dbo:parkingInformation, dbo:personFunction, dbo:picture, dbo:politicalLeader, dbo:projectKeyword, dbo:pronunciation, dbo:quote, dbo:reference, dbo:restingPlacePosition, dbo:restriction, dbo:sales, dbo:selection, dbo:signature, dbo:soundRecording, dbo:speaker, dbo:statisticLabel, dbo:strength, dbo:termPeriod, dbo:thumbnail, dbo:title, dbo:tournamentRecord, dbo:visitorStatisticsAsOf, dbo:winsAtAsia, dbo:winsAtAus, dbo:winsAtChallenges, dbo:winsAtChampionships, dbo:winsAtJapan, dbo:winsAtLET, dbo:winsAtNWIDE, dbo:winsAtOtherTournaments, dbo:winsAtPGA, dbo:winsAtSenEuro, dbo:winsInEurope ))
        }}
    """
    result = run_query(query)
    return result

def get_prop_and_subj(entity):
    """Fetches all ontology properties and values where entity is the object."""
    query = f"""
        SELECT ?property ?value
        WHERE {{
            ?value ?property <http://dbpedia.org/resource/{entity}> .
            FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
            FILTER(!CONTAINS(STR(?property), "wikiPage"))
            FILTER(?property NOT IN ( dbo:abstract, dbo:bicycleInformation, dbo:boilerPressure, dbo:carNumber, dbo:careerStation, dbo:collection, dbo:damage, dbo:depictionDescription, dbo:description, dbo:event, dbo:imageSize, dbo:impactFactorAsOf, dbo:isHandicappedAccessible, dbo:leaderFunction, dbo:lengthReference, dbo:liberationDate, dbo:logo, dbo:mapCaption, dbo:militaryService, dbo:minister, dbo:name, dbo:note, dbo:notes, dbo:numberOfVisitorsAsOf, dbo:orderInOffice, dbo:other, dbo:parkingInformation, dbo:personFunction, dbo:picture, dbo:politicalLeader, dbo:projectKeyword, dbo:pronunciation, dbo:quote, dbo:reference, dbo:restingPlacePosition, dbo:restriction, dbo:sales, dbo:selection, dbo:signature, dbo:soundRecording, dbo:speaker, dbo:statisticLabel, dbo:strength, dbo:termPeriod, dbo:thumbnail, dbo:title, dbo:tournamentRecord, dbo:visitorStatisticsAsOf, dbo:winsAtAsia, dbo:winsAtAus, dbo:winsAtChallenges, dbo:winsAtChampionships, dbo:winsAtJapan, dbo:winsAtLET, dbo:winsAtNWIDE, dbo:winsAtOtherTournaments, dbo:winsAtPGA, dbo:winsAtSenEuro, dbo:winsInEurope ))
        }}
    """
    result = run_query(query)
    return result

# -------------------------
# --- CSV writing
# -------------------------

def get_values(category, titles):
    """
    For a given category and list of entity titles:
    - Fetch values where each entity appears as subject and object.
    - Write results to a CSV file with columns: Subject, Property, Object.
    - Limits the number of values per property to avoid huge files.
    """
    with open(f"Testing/4.1/output/values/{category}-values.csv", "w", newline="", encoding="utf-8") as f:
        new_titles = []
        writer = csv.DictWriter(f, fieldnames=["Subject", "Property", "Object"])
        for i, title in enumerate(titles):
            print(f"{i+1}. {title} ({round((100*i)/len(titles))}%)")
            po = get_prop_and_obj(title)
            ps = get_prop_and_subj(title)
            if po == ps:
                redirects = run_query(f"""
                                SELECT ?value
                                WHERE {{
                                    <http://dbpedia.org/resource/{title}> <http://dbpedia.org/ontology/wikiPageRedirects> ?value .
                                    }}
                                """)
                if redirects != {'head': {'link': [], 'vars': ['value']}, 'results': {'distinct': False, 'ordered': True, 'bindings': []}}:
                    title = redirects['results']['bindings'][0]['value']['value'].split('/')[-1]
                    print("Redirected to", title)
                    po = get_prop_and_obj(title)
                    ps = get_prop_and_subj(title)
            new_titles.append(title)
            results = [
                ("subject", po),  # Entity as subject
                ("object", ps)   # Entity as object
            ]
            prop_count= {}
            for direction, result in results:
                print("Checking", direction)
                for binding in result["results"]["bindings"]:
                    prop = binding["property"]["value"].split('/')[-1]  # Get local name
                    if LIMIT == -1 or prop_count.get(prop, 0) < LIMIT:
                        value_name = binding["value"]["value"].split('/')[-1]
                        if direction == "subject":
                            writer.writerow({
                                "Subject": title,
                                "Property": prop,
                                "Object": value_name
                            })
                        else:  # entity is object
                            writer.writerow({
                                "Subject": value_name,
                                "Property": prop,
                                "Object": title
                            })
                        prop_count[prop] = prop_count.get(prop, 0) + 1
            f.flush()
    return new_titles

# -------------------------
# --- Validation of values
# -------------------------

def validate(category):
    """
    Validates the values in the CSV file for a given category.
    - Checks types of subjects and objects.
    - Uses XSD validators for literal values.
    - Writes results to a validation CSV with validity status.
    """
    with open(f"Testing/4.2/output/values/{category}-values.csv", newline="", encoding="utf-8") as values, open(f"Testing/4.2/output/validations/{category}-validations.csv", "w", newline="", encoding="utf-8") as validations:
        reader = csv.reader(values)
        writer = csv.DictWriter(validations, fieldnames=["Subject", "Property", "Object", "Validity", "Lists"])

        for i, row in enumerate(reader):
            
            subj, prop, obj = row
            print(subj, prop, obj)

            if CACHING:
                # Fetch domain and range for the property
                if prop not in prop_domain_and_range:
                    print(prop, "not in cache")
                    prop_domain_and_range[prop] = get_domain_and_range(prop)
                expected_domain, expected_range = prop_domain_and_range[prop]

                # Fetch types for subject and object
                if subj not in entity_types:
                    entity_types[subj] = get_types(subj)
                actual_domain = entity_types[subj]

                if obj not in entity_types:
                    entity_types[obj] = get_types(obj)
                actual_range = entity_types[obj]
            else:
                expected_domain, expected_range = get_domain_and_range(prop)
                actual_domain = get_types(subj)
                actual_range = get_types(obj)



            # XSD validators for literal types
            xsd_validators = {
                "http://www.w3.org/2001/XMLSchema#string": always_valid,
                "http://www.w3.org/1999/02/22-rdf-syntax-ns#langString": always_valid,
                "http://www.w3.org/2001/XMLSchema#date": is_yyyy_mm_dd,
                "http://www.w3.org/2001/XMLSchema#double": is_double,
                "http://www.w3.org/2001/XMLSchema#float": is_double,
                "http://www.w3.org/2001/XMLSchema#gYear": is_year,
                "http://www.w3.org/2001/XMLSchema#nonNegativeInteger": is_non_negative_integer,
                "http://www.w3.org/2001/XMLSchema#positiveInteger": is_positive_integer,
                "http://www.w3.org/2001/XMLSchema#integer": is_integer,
            }

            # Validate literals
            if expected_range.__contains__("http://www.w3.org/2001/XMLSchema") or expected_range.__contains__("http://www.w3.org/1999/02/22-rdf-syntax-ns"):
                validator = xsd_validators.get(expected_range)
                if validator and validator(obj):
                    validity = "Valid"
                elif validator:
                    validity = "Invalid"
                else:
                    validity = f"Unknown {expected_range}"
            else:
                # Validate resources using their types
                if (not expected_domain and expected_range in actual_range):
                    validity = "Valid (No expected domain, range matches)"
                elif (not expected_range and expected_domain in actual_domain):
                    validity = "Valid (No expected range, domain matches)"
                elif (not expected_domain and not expected_range):
                    validity = "Valid (no expected domain or range)"
                elif (expected_range in actual_range and expected_domain in actual_domain):
                    validity = "Valid (Fully valid)"
                elif not actual_domain or not actual_range:
                    validity = "Possibly valid"
                else:
                    validity = "Not valid"

            print("\t", validity)
            writer.writerow({
                "Subject": subj,
                "Property": prop,
                "Object": obj,
                "Validity": validity,
                "Lists": [expected_domain, actual_domain, expected_range, actual_range]
            })
            validations.flush()

            if i % UPDATE_RATE == 0 and CACHING:
                with open('Testing/4.1/output/dictionaries/entity_types.txt', 'w', encoding="utf-8") as e, open('Testing/4.1/output/dictionaries/properties.txt', 'w', encoding="utf-8") as p, open('Testing/4.1/output/dictionaries/superclasses.txt', 'w', encoding="utf-8") as s:
                    e.write(str(entity_types))
                    p.write(str(prop_domain_and_range))
                    s.write(str(superclasses_for_types))

        print(set(entity_types))
        print(set(prop_domain_and_range))

        

# -------------------------
# --- Helper functions for SPARQL
# -------------------------

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

def get_types(entity):
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
                if base_type not in superclasses_for_types or not(CACHING):
                    print(base_type, "not in cache")
                    superclasses_for_types[base_type] = get_superclasses(base_type)
                types.extend([base_type] + superclasses_for_types[base_type])
    return set(types)  # Return unique types

def get_pages_from_specific_list():
    # Ask the user for a DBpedia category (resource name)
    category = input("Category? ")

    # Base SPARQL query:
    # Select distinct pages that are wiki-linked from the given category resource
    query = f"""SELECT DISTINCT ?page
        WHERE {{
        <http://dbpedia.org/resource/{category}>
            <http://dbpedia.org/ontology/wikiPageWikiLink> ?page .
    """

    # --- Filtering by properties ---
    # Ask the user for filtering properties (comma-separated)
    filtering_props = input("Filtering property? ").split(",")
    prop_patterns = []

    # If the input is not empty
    if filtering_props != ['']:
        for p in filtering_props:
            p = p.strip()  # Remove extra spaces
            # Create a SPARQL pattern where ?value has a given property pointing to ?page
            prop_patterns.append(
                f"?value <http://dbpedia.org/ontology/{p}> ?page ."
            )
    
        # Combine all property patterns using UNION
        # This means a page is kept if it matches at least one property
        if prop_patterns:
            query += " { " + " } UNION { ".join(prop_patterns) + " } "

    # --- Filtering by types ---
    # Ask the user for filtering types (comma-separated)
    filtering_types = input("Filtering type? ").split(",")
    type_patterns = []

    # If the input is not empty
    if filtering_types != ['']:
        for t in filtering_types:
            t = t.strip()  # Remove extra spaces
            # Create a SPARQL pattern enforcing a specific rdf:type
            type_patterns.append(f"?page rdf:type dbo:{t} .")

        # Combine all type patterns using UNION
        # This means a page is kept if it matches at least one type
        if type_patterns:
            query += " { " + " } UNION { ".join(type_patterns) + " } "

    # Close the WHERE block of the SPARQL query
    query += " }"

    # Execute the SPARQL query
    result = run_query(query)

    # Write the resulting page names to a text file
    # The filename is based on the chosen category
    with open(f"Testing/4.1/output/pages/{category}.txt", "w", encoding="utf-8") as f:
        for binding in result['results']['bindings']:
            # Extract only the page name from the full DBpedia URI
            page = binding['page']['value'].split("/")[-1]
            f.write(page + "\n")

# -------------------------
# --- Main workflow
# -------------------------

def main():
    choice = input("Get counts (C), get values (V), get names from a specific current_category (S) or validate existing values (E)? ")

    if choice == "E":
        # Validate previously fetched CSV values
        for category in CATEGORIES:
            current_category = f"group 3/{category}"
            validate(current_category)
    elif choice == "S":
        get_pages_from_specific_list()
    elif choice == "V":
        '''for category in CATEGORIES:
            current_category = f"top-1000/{category}"'''
        if current_category:
            print(current_category)
            # Read entity titles from file
            with open(f"Testing/4.1/output/pages/{current_category}.txt", "r", encoding="utf-8") as f:
                titles = [line.strip() for line in f if line.strip()]
                # Fetch values for the entities and write to CSV
                new_titles = get_values(current_category, titles)

            with open(f"Testing/4.1/output/pages/{current_category}.txt", "w", encoding="utf-8") as f:
                for title in new_titles:
                    f.write(title + "\n")

    else:
        print(current_category)
        # Read entity titles from file
        with open(f"Testing/4.1/output/pages/{current_category}.txt", "r", encoding="utf-8") as f:
            titles = [line.strip() for line in f if line.strip()]

            # Fetch counts of subject/object properties and write to CSV
            with open("counts.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["title", "Subject Count", "Object Count"])
                writer.writeheader()
                for title in enumerate(titles):
                    result = get_counts(title)
                    bindings = result["results"]["bindings"][0]
                    subject_count = int(bindings["subjectPropertyCount"]["value"])
                    object_count = int(bindings["objectPropertyCount"]["value"])

                    print(title, ":", subject_count, "and", object_count)
                    writer.writerow({
                        "title": title,
                        "Subject Count": subject_count,
                        "Object Count": object_count
                    })
                    f.flush()

if __name__ == "__main__":
    main()