# Import necessary libraries
import random
from unittest import result

from SPARQLWrapper import SPARQLWrapper, JSON
from SPARQLWrapper.SPARQLExceptions import EndPointInternalError
import csv
import re
from datetime import datetime
import ast
import time

# Initialize the SPARQL endpoint to DBpedia
sparql = SPARQLWrapper("http://dbpedia.org/sparql")
LIMIT = 10  # Limit the number of property values per entity to avoid huge queries
CATEGORY = "random_wikipedia_articles"  # Example category; can be changed as needed
CACHING = False

metadata_properties = {'abstract', 'caption', 'comment', 'depictionDescription', 'description', 'image', 'imageSize', 'logo', 'mapCaption', 'motto', 'picture', 'pronunciation', 'quote', 'reference', 'seal', 'signature', 'slogan', 'soundRecording', 'text', 'thumbnail', 'title', 'coatOfArms', 'flag'}
properties_to_ignore = {'abstract', 'bicycleInformation', 'boilerPressure', 'carNumber', 'careerStation', 'collection', 'damage', 'depictionDescription', 'description', 'event', 'imageSize', 'impactFactorAsOf', 'isHandicappedAccessible', 'leaderFunction', 'lengthReference', 'liberationDate', 'logo', 'mapCaption', 'militaryService', 'minister', 'name', 'note', 'notes', 'numberOfVisitorsAsOf', 'orderInOffice', 'other', 'parkingInformation', 'personFunction', 'picture', 'politicalLeader', 'projectKeyword', 'pronunciation', 'quote', 'reference', 'restingPlacePosition', 'restriction', 'sales', 'selection', 'signature', 'soundRecording', 'speaker', 'statisticLabel', 'strength', 'termPeriod', 'thumbnail', 'title', 'tournamentRecord', 'visitorStatisticsAsOf', 'winsAtAsia', 'winsAtAus', 'winsAtChallenges', 'winsAtChampionships', 'winsAtJapan', 'winsAtLET', 'winsAtNWIDE', 'winsAtOtherTournaments', 'winsAtPGA', 'winsAtSenEuro', 'winsInEurope'}

if CACHING:
    with open("Testing/4.1/output/dictionaries/properties.txt", "r", encoding="utf-8") as p:
        prop_domain_and_range = ast.literal_eval(p.read())
    with open("Testing/4.1/output/dictionaries/entity_types.txt", "r", encoding="utf-8") as e:
        entity_types = ast.literal_eval(e.read())
    with open("Testing/4.1/output/dictionaries/superclasses.txt", "r", encoding="utf-8") as s:
        superclasses_for_types = ast.literal_eval(s.read())
else:
    prop_domain_and_range = {}
    entity_types = {}
    superclasses_for_types = {}

edges = {}
with open("Testing/4.1/output/dictionaries/superclasses.csv", newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    for subclass, superclass in reader:
        edges.setdefault(subclass, []).append(superclass)

OUTCOMES = {
            # Valid
            ('skip', 'skip'):    'Valid (No expected domain, no expected range)',
            ('skip', 'pass'):    'Valid (No expected domain, range matches)',
            ('pass', 'skip'):    'Valid (Domain matches, no expected range)',
            ('pass', 'pass'):    'Valid (Domain matches, range matches)',
            # Possibly Valid
            ('skip', 'unknown'):    'Possibly Valid (No expected domain, no actual range to check against)',
            ('unknown', 'skip'):    'Possibly Valid (No actual domain to check against, no expected range)',
            ('unknown', 'pass'):    'Possibly Valid (No actual domain to check against, range matches)',
            ('pass', 'unknown'):    'Possibly Valid (Domain matches, no actual range to check against)',
            ('unknown', 'unknown'): 'Possibly Valid (No actual domain to check against, no actual range to check against)',
            # Invalid
            ('skip', 'fail'):    'Invalid (No expected domain, range does not match)',
            ('fail', 'skip'):    'Invalid (Domain does not match, no expected range)',
            ('fail', 'pass'):    'Invalid (Domain does not match, range matches)',
            ('pass', 'fail'):    'Invalid (Domain matches, range does not match)',
            ('fail', 'fail'):    'Invalid (Domain does not match, range does not match)',
            ('unknown', 'fail'): 'Invalid (No actual domain to check against, range does not match)',
            ('fail', 'unknown'): 'Invalid (Domain does not match, no actual range to check against)',
        }

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

# XSD validators for literal types
XSD_VALIDATORS = {
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
        return "RETRY"
    except Exception as e:
        # Catch-all for unexpected errors
        return "RETRY"

# -------------------------
# --- Functions to fetch properties/values
# -------------------------

def get_prop_and_obj(entity, zero_filter):
    """Fetches all ontology properties and values where entity is the subject."""
    if zero_filter:
        query = f"""
            SELECT ?property ?value
            WHERE {{
                <http://dbpedia.org/resource/{entity}> ?property ?value .
                FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
            }}
        """
        
    else:
        query = f"""
            SELECT ?property ?value
            WHERE {{
                <http://dbpedia.org/resource/{entity}> ?property ?value .
                FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
                FILTER(!CONTAINS(STR(?property), "wikiPage"))
                FILTER(?property NOT IN (dbo:abstract, dbo:caption, dbo:comment, dbo:depictionDescription, dbo:description, dbo:image, dbo:imageSize, dbo:logo, dbo:mapCaption, dbo:motto, dbo:picture, dbo:pronunciation, dbo:quote, dbo:reference, dbo:seal, dbo:signature, dbo:slogan, dbo:soundRecording, dbo:text, dbo:thumbnail, dbo:title, dbo:coatOfArms, dbo:flag))
            }}
        """
    result = run_query(query)
    return result

def get_prop_and_subj(entity, zero_filter):
    """Fetches all ontology properties and values where entity is the object."""
    if zero_filter:
        query = f"""
            SELECT ?property ?value
            WHERE {{
                ?value ?property <http://dbpedia.org/resource/{entity}> .
                FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
            }}
        """

    else:
        query = f"""
            SELECT ?property ?value
            WHERE {{
                ?value ?property <http://dbpedia.org/resource/{entity}> .
                FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
                FILTER(!CONTAINS(STR(?property), "wikiPage"))
                FILTER(?property NOT IN (dbo:abstract, dbo:caption, dbo:comment, dbo:depictionDescription, dbo:description, dbo:image, dbo:imageSize, dbo:logo, dbo:mapCaption, dbo:motto, dbo:picture, dbo:pronunciation, dbo:quote, dbo:reference, dbo:seal, dbo:signature, dbo:slogan, dbo:soundRecording, dbo:text, dbo:thumbnail, dbo:title, dbo:coatOfArms, dbo:flag))
            }}
        """
    result = run_query(query)
    return result

# -------------------------
# --- CSV writing
# -------------------------

def get_values(category, titles, zero_filter=False):
    values_to_redo = []
    """
    For a given category and list of entity titles:
    - Fetch values where each entity appears as subject and object.
    - Write results to a CSV file with columns: Subject, Property, Object.
    - Limits the number of values per property to avoid huge files.
    """
    
    write_file = f"Testing/5.1/{category}-values.csv"

    with open(write_file, "w", newline="", encoding="utf-8") as f:
        new_titles = []
        writer = csv.DictWriter(f, fieldnames=["Subject", "Property", "Object"])
        for i, title in enumerate(titles):
            print(f"{i+1}. {title} ({round((100*i)/len(titles))}%)")
            time.sleep(2)  # Sleep to avoid overwhelming the endpoint
            po = get_prop_and_obj(title, zero_filter)
            time.sleep(2)
            ps = get_prop_and_subj(title,zero_filter)
            if po == ps:
                redirects = run_query(f"""
                                SELECT ?value
                                WHERE {{
                                    <http://dbpedia.org/resource/{title}> <http://dbpedia.org/ontology/wikiPageRedirects> ?value .
                                    }}
                                """)
                if redirects == "RETRY":
                    print("Query failed, skipping", title, "for", direction)
                    values_to_redo.append((title, direction))
                    continue
                if redirects != {'head': {'link': [], 'vars': ['value']}, 'results': {'distinct': False, 'ordered': True, 'bindings': []}}:
                    title = redirects['results']['bindings'][0]['value']['value']
                    print("Redirected to", title)
                    po = get_prop_and_obj(title)
                    ps = get_prop_and_subj(title)
            new_titles.append(title.removeprefix("http://dbpedia.org/resource/"))
            results = [
                ("subject", po),  # Entity as subject
                ("object", ps)   # Entity as object
            ]
            prop_count= {}
            for direction, result in results:
                print("Checking", direction)
                if result == "RETRY":
                    print("Query failed, skipping", title, "for", direction)
                    values_to_redo.append((title, direction))
                    continue 

                ## NEW CODE:
                # All triples are shuffled and sorted by property,
                # to ensure consistent output across runs
                random.seed(42)  # reproducible
                random.shuffle(result["results"]["bindings"])
                result["results"]["bindings"].sort(key=lambda x: x["property"]["value"])  # Sort by property for consistent output

                for binding in result["results"]["bindings"]:
                    prop = binding["property"]["value"]  # Get local name
                    if LIMIT == -1 or prop_count.get(prop, 0) < LIMIT:
                        value_name = binding["value"]["value"]
                        if direction == "subject":
                            writer.writerow({
                                "Subject": "http://dbpedia.org/resource/" + title,
                                "Property": prop,
                                "Object": value_name
                            })
                        else:  # entity is object
                            writer.writerow({
                                "Subject": value_name,
                                "Property": prop,
                                "Object": "http://dbpedia.org/resource/" + title
                            })
                        prop_count[prop] = prop_count.get(prop, 0) + 1
            f.flush()


    print(values_to_redo)
    return new_titles, values_to_redo

# -------------------------
# --- Validation of values
# -------------------------

def validate(category, invalid_manual_fixes=False, undefined_manual_fixes=False):
    """
    Validates the values in the CSV file for a given category.
    - Checks types of subjects and objects.
    - Uses XSD validators for literal values.
    - Writes results to a validation CSV with validity status.
    - Processes entities in batches of 100.
    """
    BATCH_SIZE = 100
    if invalid_manual_fixes:
        output_file = f"Testing/5.1/{category}-validations-invalid_manual.csv"
    elif undefined_manual_fixes:
        output_file = f"Testing/5.1/{category}-validations-undefined_manual.csv"
    else:
        output_file = f"Testing/5.1/{category}-validations.csv"

    with open(f"Testing/5.1/{category}-nmf.csv", newline="", encoding="utf-8") as values, \
    open(output_file, "w", newline="", encoding="utf-8") as validations:
        reader = csv.reader(values)
        writer = csv.DictWriter(validations, fieldnames=["Subject", "Property", "Object", "Validity", "Lists"])

        rows = list(reader)
        total = len(rows)

        for batch_start in range(0, total, BATCH_SIZE):
            batch = rows[batch_start:batch_start + BATCH_SIZE]

            # Pre-fetch all unique props, subjects, and objects in this batch
            if CACHING:
                unique_props = {row[1] for row in batch}
                unique_entities = {
                    row[i] for row in batch for i in (0, 2)
                    if row[i].startswith("http://dbpedia.org/resource/")
                }

                for prop in unique_props:
                    if prop not in prop_domain_and_range:
                        print(prop, "not in cache")
                        prop_domain_and_range[prop] = get_domain_and_range(prop)

                uncached_entities = [e for e in unique_entities if e not in entity_types]
                if uncached_entities:
                    batch_results = get_types_batch(uncached_entities)
                    if "RETRY" in batch_results:
                        # Fall back to individual queries if batch failed
                        print("Batch query failed, falling back to individual queries for entities.")
                        for entity in uncached_entities:
                            entity_types[entity] = get_types(entity)
                    else:
                        print(f"Batch query successful for {len(uncached_entities)} entities.")
                        entity_types.update(batch_results)

            for i, (subj, prop, obj) in enumerate(batch, start=batch_start):
                subj_short = subj.removeprefix("http://dbpedia.org/resource/")
                prop_short = prop.removeprefix("http://dbpedia.org/ontology/")
                obj_short  = obj.removeprefix("http://dbpedia.org/resource/")

                print(subj_short, prop_short, obj_short, f"({round((100*i)/total)}%)")

                if CACHING:
                    expected_domain, expected_range = prop_domain_and_range[prop]

                    actual_domain = entity_types[subj] if subj.startswith("http://dbpedia.org/resource/") else set()
                    actual_range  = entity_types[obj]  if obj.startswith("http://dbpedia.org/resource/")  else set()
                else:
                    expected_domain, expected_range = get_domain_and_range(prop)
                    actual_domain = get_types(subj)
                    actual_range = get_types(obj)

                # Validate literals
                if expected_range.__contains__("http://www.w3.org/2001/XMLSchema") or expected_range.__contains__("http://www.w3.org/1999/02/22-rdf-syntax-ns"):
                    validator = XSD_VALIDATORS.get(expected_range)
                    if validator and validator(obj):
                        validity = "Valid"
                    elif validator:
                        validity = "Invalid"
                    else:
                        validity = f"Unknown {expected_range}"
                else:
                    # Validate resources using their types
                    # Normalize empty values
                    domain_expected_blank = expected_domain == ''
                    range_expected_blank = expected_range == ''
                    domain_actual_blank = actual_domain == set()
                    range_actual_blank = actual_range == set()

                    # Evaluate domain check
                    if domain_expected_blank:
                        domain_result = 'skip'
                    elif domain_actual_blank:
                        domain_result = 'unknown'
                    elif expected_domain in actual_domain:
                        domain_result = 'pass'
                    else:
                        domain_result = 'fail'

                    # Evaluate range check
                    if range_expected_blank:
                        range_result = 'skip'
                    elif range_actual_blank:
                        range_result = 'unknown'
                    elif expected_range in actual_range:
                        range_result = 'pass'
                    else:
                        range_result = 'fail'

                    validity = OUTCOMES[(domain_result, range_result)]

                    if invalid_manual_fixes or undefined_manual_fixes:
                        if prop_short == "academicDiscipline" and actual_domain.__contains__("http://dbpedia.org/ontology/Scientist"):
                            validity = "Valid (Domain matches, no expected range)"
                        elif prop_short == "occupation" and actual_range.__contains__("http://dbpedia.org/ontology/TopicalConcept"):
                            validity = "Valid (No expected domain, range matches)"
                        elif prop_short == "genre" and actual_range.__contains__("http://dbpedia.org/ontology/TopicalConcept"):
                            validity = "Valid (No expected domain, range matches)"
                        elif prop_short == "place" and actual_range.__contains__("http://dbpedia.org/ontology/Place"):
                            validity = "Valid (No expected domain, range matches)"
                        elif prop_short == "mouthPlace" and actual_domain.__contains__("http://dbpedia.org/ontology/River") and actual_range.__contains__("http://dbpedia.org/ontology/Place"):
                            validity = "Valid (Domain matches, range matches)"
                        elif prop_short == "locatedInArea" and actual_domain.__contains__("http://dbpedia.org/ontology/ArchitecturalStructure") and actual_range.__contains__("http://dbpedia.org/ontology/Place"):
                            validity = "Valid (Domain matches, range matches)"
                        elif prop_short == "routeStart" and actual_domain.__contains__("http://dbpedia.org/ontology/RouteOfTransportation") and actual_range.__contains__("http://dbpedia.org/ontology/Place"):
                            validity = "Valid (Domain matches, range matches)"
                        elif prop_short == "headquarter" and actual_domain.__contains__("http://dbpedia.org/ontology/Newspaper") and actual_range.__contains__("http://dbpedia.org/ontology/Place"):
                            validity = "Valid (Domain matches, range matches)"
                        elif prop_short == "starring" and actual_domain.__contains__("http://dbpedia.org/ontology/Work") and actual_range.__contains__("http://dbpedia.org/ontology/Person"):
                            validity = "Valid (Domain matches, range matches)"
                        elif prop_short == "producer" and actual_domain.__contains__("http://dbpedia.org/ontology/Work") and actual_range.__contains__("http://dbpedia.org/ontology/Person"):
                            validity = "Valid (Domain matches, range matches)"
                        elif prop_short == "artist" and actual_domain.__contains__("http://dbpedia.org/ontology/Work") and actual_range.__contains__("http://dbpedia.org/ontology/Person"):
                            validity = "Valid (Domain matches, range matches)"
                        elif prop_short == "territory" and actual_domain.__contains__("http://dbpedia.org/ontology/MilitaryConflict") and actual_range.__contains__("http://dbpedia.org/ontology/Place"):
                            validity = "Valid (Domain matches, range matches)"
                        elif prop_short == "territory" and actual_domain.__contains__("http://dbpedia.org/ontology/AdministrativeRegion") and actual_range.__contains__("http://dbpedia.org/ontology/Place"):
                            validity = "Valid (Domain matches, range matches)"
                        elif prop_short == "team" and actual_range.__contains__("http://dbpedia.org/ontology/SportsClub"):
                            validity = "Valid (No expected domain, range matches)"
                        elif prop_short == "managerClub" and actual_domain.__contains__("http://dbpedia.org/ontology/SportsManager") and actual_range.__contains__("http://dbpedia.org/ontology/SportsClub"):
                            validity = "Valid (Domain matches, range matches)"
                        elif prop_short == "routeJunction" and actual_domain.__contains__("http://dbpedia.org/ontology/RouteOfTransportation") and actual_range.__contains__("http://dbpedia.org/ontology/Place"):
                            validity = "Valid (Domain matches, range matches)"
                        elif prop_short == "hometown" and actual_domain.__contains__("http://dbpedia.org/ontology/Person") and actual_range.__contains__("http://dbpedia.org/ontology/Settlement"):
                            validity = "Valid (Domain matches, range matches)"
                        elif prop_short == "firstDriver" and actual_domain.__contains__("http://dbpedia.org/ontology/MotorsportSeason") and actual_range.__contains__("http://dbpedia.org/ontology/Person"):
                            validity = "Valid (Domain matches, range matches)"
                        elif prop_short == "routeEnd" and actual_domain.__contains__("http://dbpedia.org/ontology/RouteOfTransportation") and actual_range.__contains__("http://dbpedia.org/ontology/Place"):
                            validity = "Valid (Domain matches, range matches)"
                    
                    if undefined_manual_fixes:
                        new_validity = "Valid (Domain matches, range matches)"

                        valid_location_domains = ["http://dbpedia.org/ontology/Place", "http://dbpedia.org/ontology/Agent", "http://dbpedia.org/ontology/Person", "http://dbpedia.org/ontology/Event", "http://dbpedia.org/ontology/ArchitecturalStructure"]
                        valid_country_domains = valid_location_domains
                        valid_city_domains = valid_location_domains
                        valid_place_domains = valid_location_domains
                        valid_locationCountry_domains = valid_location_domains
                        valid_region_domains = valid_location_domains
                        valid_product_ranges = ["http://dbpedia.org/ontology/ArchitecturalStructure", "http://dbpedia.org/ontology/Beverage", "http://dbpedia.org/ontology/Food", "http://dbpedia.org/ontology/Work"]
                        valid_service_ranges = valid_product_ranges
                        valid_ingredient_ranges = ["http://dbpedia.org/ontology/Beverage", "http://dbpedia.org/ontology/ChemicalSubstance", "http://dbpedia.org/ontology/Food"]
                        valid_battle_domains = ["http://dbpedia.org/ontology/Agent", "http://dbpedia.org/ontology/Person"]
                        valid_institution_domains = valid_battle_domains
                        valid_associatedBand_domains = valid_battle_domains
                        valid_language_domains = ["http://dbpedia.org/ontology/Agent", "http://dbpedia.org/ontology/Person", "http://dbpedia.org/ontology/Work"]
                        valid_literaryGenre_ranges =  ["http://dbpedia.org/ontology/Genre", "http://dbpedia.org/ontology/TopicalConcept"]
                        valid_genre_ranges = valid_literaryGenre_ranges
                        valid_president_domains = ["http://dbpedia.org/ontology/Country", "http://dbpedia.org/ontology/TimePeriod"]
                        valid_origin_domains = ["http://dbpedia.org/ontology/Food", "http://dbpedia.org/ontology/Beverage", "http://dbpedia.org/ontology/Species", "http://dbpedia.org/ontology/MeanOfTransportation", "http://dbpedia.org/ontology/Device"]
                        valid_predecessor_domains_and_ranges = ["http://dbpedia.org/ontology/Person", "http://dbpedia.org/ontology/TimePeriod"]
                        valid_successor_domains_and_ranges = valid_predecessor_domains_and_ranges

                        if prop_short == "location" and any(d in actual_domain for d in valid_location_domains) and "http://dbpedia.org/ontology/Place" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "country" and any(d in actual_domain for d in valid_country_domains) and "http://dbpedia.org/ontology/Country" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "industry" and "http://dbpedia.org/ontology/Company" in actual_domain and "http://dbpedia.org/ontology/TopicalConcept" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "product" and "http://dbpedia.org/ontology/Organisation" in actual_domain and any(d in actual_range for d in valid_product_ranges):
                            validity = new_validity                        
                        elif prop_short == "city" and any(d in actual_domain for d in valid_city_domains) and "http://dbpedia.org/ontology/City" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "place" and any(d in actual_domain for d in valid_place_domains) and "http://dbpedia.org/ontology/Place" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "subdivision" and "http://dbpedia.org/ontology/Place" in actual_domain and "http://dbpedia.org/ontology/Place" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "commander" and "http://dbpedia.org/ontology/MilitaryConflict" in actual_domain and "http://dbpedia.org/ontology/Person" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "education" and "http://dbpedia.org/ontology/Person" in actual_domain and "http://dbpedia.org/ontology/EducationalInstitution" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "ingredient" and any(d in actual_domain for d in valid_ingredient_ranges) and any(d in actual_range for d in valid_ingredient_ranges):
                            validity = new_validity                        
                        elif prop_short == "nonFictionSubject" and "http://dbpedia.org/ontology/Work" in actual_domain and "http://dbpedia.org/ontology/TopicalConcept" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "battle" and any(d in actual_domain for d in valid_battle_domains) and "http://dbpedia.org/ontology/MilitaryConflict" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "language" and any(d in actual_domain for d in valid_language_domains) and "http://dbpedia.org/ontology/Language" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "locationCountry" and any(d in actual_domain for d in valid_locationCountry_domains) and "http://dbpedia.org/ontology/Country" in actual_range:
                            validity = new_validity                        
                        elif (prop_short == "mainInterest" or prop_short == "academicDiscipline" or prop_short == "field") and "http://dbpedia.org/ontology/Person" in actual_domain and "http://dbpedia.org/ontology/TopicalConcept" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "citizenship" and "http://dbpedia.org/ontology/Person" in actual_domain and "http://dbpedia.org/ontology/Country" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "assembly" and "http://dbpedia.org/ontology/MeanOfTransportation" in actual_domain and "http://dbpedia.org/ontology/Place" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "institution" and any(d in actual_domain for d in valid_institution_domains) and "http://dbpedia.org/ontology/Organisation" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "service" and "http://dbpedia.org/ontology/Organisation" in actual_domain and any(d in actual_range for d in valid_service_ranges):
                            validity = new_validity                        
                        elif prop_short == "literaryGenre" and "http://dbpedia.org/ontology/WrittenWork" in actual_domain and any(d in actual_range for d in valid_literaryGenre_ranges):
                            validity = new_validity                        
                        elif prop_short == "region" and any(d in actual_domain for d in valid_region_domains) and "http://dbpedia.org/ontology/Place" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "president" and any(d in actual_domain for d in valid_president_domains) and "http://dbpedia.org/ontology/Person" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "influencedBy" and "http://dbpedia.org/ontology/Person" in actual_domain and "http://dbpedia.org/ontology/Person" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "origin" and any(d in actual_domain for d in valid_origin_domains) and "http://dbpedia.org/ontology/Place" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "genre" and "http://dbpedia.org/ontology/Work" in actual_domain and any(d in actual_range for d in valid_genre_ranges):
                            validity = new_validity                        
                        elif prop_short == "occupation" and "http://dbpedia.org/ontology/Person" in actual_domain and "http://dbpedia.org/ontology/PersonFunction" in actual_range:
                            validity = new_validity
                        elif prop_short == "timeZone" and "http://dbpedia.org/ontology/Place" in actual_domain:
                            validity = new_validity
                        elif prop_short == "predecessor" and any(d in actual_domain for d in valid_predecessor_domains_and_ranges) and any(d in actual_range for d in valid_predecessor_domains_and_ranges):
                            validity = new_validity      
                        elif (prop_short == "recordLabel" or prop_short == "distributor") and "http://dbpedia.org/ontology/Work" in actual_domain and "http://dbpedia.org/ontology/Organisation" in actual_range:
                            validity = new_validity
                        elif prop_short == "party" and "http://dbpedia.org/ontology/Person" in actual_domain and "http://dbpedia.org/ontology/PoliticalParty" in actual_range:
                            validity = new_validity                      
                        elif prop_short == "successor" and any(d in actual_domain for d in valid_successor_domains_and_ranges) and any(d in actual_range for d in valid_successor_domains_and_ranges):
                            validity = new_validity
                        elif prop_short == "manufacturer" and "http://dbpedia.org/ontology/MeanOfTransportation" in actual_domain and "http://dbpedia.org/ontology/Organisation" in actual_range:
                            validity = new_validity                        
                        elif prop_short == "album" and "http://dbpedia.org/ontology/Work" in actual_domain and "http://dbpedia.org/ontology/Album" in actual_range:
                            validity = new_validity                      
                        elif prop_short == "associatedBand" and any(d in actual_domain for d in valid_associatedBand_domains) and "http://dbpedia.org/ontology/Band" in actual_range:
                            validity = new_validity                      

                print("\t", validity)
                writer.writerow({
                    "Subject": subj_short,
                    "Property": prop_short,
                    "Object": obj_short,
                    "Validity": validity,
                    "Lists": [expected_domain, actual_domain, expected_range, actual_range]
                })

            # Flush and save caches after every batch
            if CACHING:
                validations.flush()
                with open('Testing/4.1/output/dictionaries/entity_types.txt', 'w', encoding="utf-8") as e, \
                     open('Testing/4.1/output/dictionaries/properties.txt', 'w', encoding="utf-8") as p, \
                     open('Testing/4.1/output/dictionaries/superclasses.txt', 'w', encoding="utf-8") as s:
                    e.write(str(entity_types))
                    p.write(str(prop_domain_and_range))
                    s.write(str(superclasses_for_types))

        print("\nValidation completed.")

# -------------------------
# --- Helper functions for SPARQL
# -------------------------

def get_domain_and_range(property):
    with open("Testing/4.1/output/dictionaries/properties.csv", "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for prop, domain, range in reader:
            if prop == property:
                return domain, range
        return [], []

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

def get_types(entity):
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

def get_types_batch(entities):
    """
    Returns the ontology types of a batch of entities, including all superclasses.
    Only returns types in the dbo: namespace.
    Returns a dict mapping entity URI -> set of types.
    """
    if not entities:
        return {}

    values_clause = " ".join(f"<{e}>" for e in entities)
    query = f"""
        SELECT DISTINCT ?entity ?type
        WHERE {{
            VALUES ?entity {{ {values_clause} }}
            ?entity rdf:type ?type .
            FILTER(STRSTARTS(STR(?type), "http://dbpedia.org/ontology/"))
        }}
    """
    result = run_query(query)
    if result == "RETRY":
        time.sleep(2)
        return {"RETRY": {"RETRY"}}

    entity_type_map = {e: [] for e in entities}

    if result["results"]["bindings"]:
        for binding in result["results"]["bindings"]:
            if "entity" in binding and "type" in binding:
                entity = binding["entity"]["value"]
                base_type = binding["type"]["value"]

                if base_type not in superclasses_for_types:
                    print(base_type, "not in cache")
                    superclasses_for_types[base_type] = get_superclasses(base_type)

                entity_type_map[entity].extend([base_type] + superclasses_for_types[base_type])

    return {entity: set(types) for entity, types in entity_type_map.items()}

def non_match_based_filter(category):
    """
    Filters out triples for one of three reasons:
    1. The entity is never the subject of the triple (i.e., it appears as the object).
    2. The subject or object contains "__" (double underscore), indicating a malformed value.
    3. The property is in the list of properties to ignore.
    """

    lines_removed_from_1 = 0
    ignored_property_values = 0
    values_where_entity_is_not_subject = 0

    with open(f"Testing/5.1/{category}-values.csv", newline="", encoding="utf-8") as values, \
    open (f"Testing/5.1/{category}.txt", "r", encoding="utf-8") as entity_list,\
    open(f"Testing/5.1/{category}-#1.csv", "w", newline="", encoding="utf-8") as filtered_1,\
    open(f"Testing/5.1/{category}-#2.csv", "w", newline="", encoding="utf-8") as filtered_2,\
    open(f"Testing/5.1/{category}-#3.csv", "w", newline="", encoding="utf-8") as filtered_3:
        reader = csv.reader(values)
        first_writer = csv.writer(filtered_1)
        second_writer = csv.writer(filtered_2)
        third_writer = csv.writer(filtered_3)
        values = list(reader)
        entities = entity_list.read().splitlines()

        entities_to_keep = set()


        new_lines = []

        for line in values:
            if line[1].removeprefix("http://dbpedia.org/ontology/") in metadata_properties or "wikiPage" in line[1] or line[0].__contains__("__") or line[2].__contains__("__"):
                lines_removed_from_1 += 1           # STEP 1: Count values that have a wikiPage property or similar metadata, or a double underscore value
            else:
                first_writer.writerow(line)
                if line[1].removeprefix("http://dbpedia.org/ontology/") in properties_to_ignore:
                    print(line)
                    ignored_property_values += 1        # STEP 2: Count values with ignored properties
                else:
                    new_lines.append(line)
        
        # STEP 3(a): Identify entities that are subjects in the values
        for line in new_lines:
            if line[0].removeprefix("http://dbpedia.org/resource/") in entities:
                entities_to_keep.add(line[0])
            
        print("Removing the following entities:")
        for entity in entities:
            if "http://dbpedia.org/resource/"+entity not in entities_to_keep:
                print(entity)
     
        for line in new_lines:   
                second_writer.writerow(line)
                if (line[0] in entities_to_keep or line[2] in entities_to_keep):
                    third_writer.writerow(line)
                else:
                    values_where_entity_is_not_subject += 1 # STEP 3: Count values where the entity is not the subject
        
    print(f"Total lines: {len(values)}.")
    print(lines_removed_from_1, " lines removed in first step.")
    print(ignored_property_values, " lines removed in second step.")
    print(values_where_entity_is_not_subject, " lines removed in third step.")


def filters(category, invalid_fixes=False, undefined_fixes=False):
    """
    This code uses the validation step to filter out invalid values from the CSV file.
    It creates three new CSV files:
    - {category}-#4.csv: Contains values that are "Possibly Valid".
    - {category}-#5.csv: Contains values that are "Valid" (including all valid cases).
    - {category}-#6.csv: Contains values that are "Valid (Domain matches, range matches)".
    It also counts and reports the total number of invalid lines that were filtered out.

    """

    if invalid_fixes:
        validation_file = f"Testing/5.1/{category}-validations-invalid_manual.csv"
        third_dataset = f"Testing/5.1/{category}-#7.csv"
        fourth_dataset = f"Testing/5.1/{category}-#8.csv"
        fifth_dataset = f"Testing/5.1/{category}-#9.csv"
    elif undefined_fixes:
        validation_file = f"Testing/5.1/{category}-validations-undefined_manual.csv"
        third_dataset = f"Testing/5.1/{category}-#10.csv"
        fourth_dataset = f"Testing/5.1/{category}-#11.csv"
        fifth_dataset = f"Testing/5.1/{category}-#12.csv"
    else:
        validation_file = f"Testing/5.1/{category}-validations.csv"
        third_dataset = f"Testing/5.1/{category}-#4.csv"
        fourth_dataset = f"Testing/5.1/{category}-#5.csv"
        fifth_dataset = f"Testing/5.1/{category}-#6.csv"

    lines_removed = 0

    with (
        open(validation_file, newline="", encoding="utf-8") as validations,
        open(third_dataset, "w", newline="", encoding="utf-8") as filtered_3,
        open(fourth_dataset, "w", newline="", encoding="utf-8") as filtered_4,
        open(fifth_dataset, "w", newline="", encoding="utf-8") as filtered_5,
    ):
        reader = csv.DictReader(validations)
        reader.fieldnames = ["Subject", "Property", "Object", "Validity", "Lists"]

        writers = {
            3: csv.DictWriter(filtered_3, fieldnames=["Subject", "Property", "Object"]),
            4: csv.DictWriter(filtered_4, fieldnames=["Subject", "Property", "Object"]),
            5: csv.DictWriter(filtered_5, fieldnames=["Subject", "Property", "Object"]),
        }

        for row in reader:
            validity = row["Validity"]

            cleaned_row = {
                "Subject": row["Subject"].removeprefix("http://dbpedia.org/resource/"),
                "Property": row["Property"].removeprefix("http://dbpedia.org/property/"),
                "Object": row["Object"].removeprefix("http://dbpedia.org/resource/")
            }


            if validity.startswith("Possibly Valid"):
                writers[3].writerow(cleaned_row)

            elif validity.startswith("Valid"):
                for filter in (3, 4):
                    writers[filter].writerow(cleaned_row)

                if validity == "Valid (Domain matches, range matches)" or validity == "Valid":
                    writers[5].writerow(cleaned_row)

            else:
                lines_removed += 1
        
        print(f"Filtered out {lines_removed} invalid lines.")

# -------------------------
# --- Main workflow
# -------------------------

def main():
    choice = input("Get values (1), apply a non match-based filtering (2), validate existing values automatically (A), fix invalid triples (I), fix undefined triples (U), or use the validations as filters (F)? ")

    if choice == "A":
        # Validate previously fetched CSV values
        validate(CATEGORY)
    elif choice == "1" or choice == "0":
        all_values_to_redo = []
        current_category = CATEGORY
        if current_category:
            print(current_category)
            # Read entity titles from file
            with open(f"Testing/5.1/{current_category}.txt", "r", encoding="utf-8") as f:
                titles = [line.strip() for line in f if line.strip()]
                # Fetch values for the entities and write to CSV
                if choice == "1":
                    new_titles, values_to_redo = get_values(current_category, titles)
                else:
                    new_titles, values_to_redo = get_values(current_category, titles, zero_filter=True)
                all_values_to_redo.extend(values_to_redo)

            with open(f"Testing/5.1/{current_category}.txt", "w", encoding="utf-8") as f:
                for title in new_titles:
                    f.write(title + "\n")

        print("Values to redo:", all_values_to_redo)
    elif choice == "2":
        # Apply non match-based filtering to existing values
        non_match_based_filter(CATEGORY)
    elif choice == "F":
        use_manual_data = input("What filter? None (N), Invalid (I) or Undefined (U) ")
        if use_manual_data.upper() == "I":
            filters(CATEGORY, invalid_fixes=True)
        elif use_manual_data.upper() == "U":
            filters(CATEGORY, undefined_fixes=True)
        else:
            filters(CATEGORY)
    elif choice == "I":
        # Validate previously fetched CSV values with manual fixes
        validate(CATEGORY, invalid_manual_fixes=True)
    elif choice == "U":
        validate(CATEGORY, undefined_manual_fixes=True)

if __name__ == "__main__":
    main()