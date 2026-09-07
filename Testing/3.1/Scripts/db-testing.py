import csv
import re
from SPARQLWrapper import SPARQLWrapper, JSON
from datetime import datetime

DATA_TYPE = "dbo"  # <-- Change to either "dbo" or "dbp"
SECTION = "History"  # <-- Change this to switch sections
PARAMETER = "" # <-- Change this to filter by incoming property
FOLDER = "Testing/3.1" # <-- Current folder

def is_yyyy_mm_dd(text: str) -> bool:
    try:
        if text.startswith('-'):
            # Strip the minus, pad year part to 4 digits if needed
            temp_text = text[1:]
            parts = temp_text.split("-")
            if len(parts[0]) < 4:  # year part shorter than 4
                parts[0] = parts[0].zfill(4)  # pad with leading zeros
            padded_text = "-".join(parts)
            datetime.strptime(padded_text, "%Y-%m-%d")
        else:
            # Positive years must be full 4-digit
            datetime.strptime(text, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def is_double(text: str) -> bool:
    try:
        float(text)
        return True
    except ValueError:
        return False

def is_year(text: str) -> bool:
    return re.fullmatch(r"-?\d+", text) is not None

def is_non_negative_integer(text: str) -> bool:
    if not text:
        return False
    text = text.strip()
    return text.isdigit()

def is_positive_integer(text: str) -> bool:
    return text.isdigit() and int(text) > 0

def is_integer(text: str) -> bool:
    return text.isdigit()

class DBpediaValidator:
    def __init__(self, data_type):
        self.sparql = SPARQLWrapper("http://dbpedia.org/sparql")
        self.sparql.setReturnFormat(JSON)
        self.invalid_instances = []  # Store invalid type instances
        self.data_type = data_type
        self.property_ranges_cache = {}
        self.property_domains_cache = {}


    def clean_name(self, name):
        """Clean resource name for DBpedia URI"""
        name = re.sub(r'^(.*?), (.*?)$', r'\2 \1', name)  # Last, First → First Last
        new_name = name.replace(" ", "_").replace("'", r"\'")
        return new_name
    
    def get_dbo_property_range_or_domain(self, prop, rdfs_type):
        """Get rdfs:range for a property"""
        query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dbo: <http://dbpedia.org/ontology/>
        SELECT DISTINCT ?{rdfs_type} WHERE {{ dbo:{prop} rdfs:{rdfs_type} ?{rdfs_type} . }}
        """
        if rdfs_type == "range":
            return [r["range"]["value"] for r in self.query(query)]
        if rdfs_type == "domain":
            return [r["domain"]["value"] for r in self.query(query)]
        
    def get_dbp_property_range_or_domain(self, prop, rdfs_type):
            query = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX dbo: <http://dbpedia.org/ontology/>
            PREFIX dbp: <http://dbpedia.org/property/>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>

            SELECT DISTINCT ?{rdfs_type} WHERE {{
                {{
                    # Try equivalent property if it exists
                    dbp:{prop} owl:equivalentProperty ?dboProp .
                    ?dboProp rdfs:{rdfs_type} ?{rdfs_type} .
                }}
                UNION
                {{
                    # Fallback: assume dbo property has the same local name
                    dbo:{prop} rdfs:{rdfs_type} ?{rdfs_type} .
                }}
            }}
            """
            results = self.query(query)

            if rdfs_type == "domain":
                types = [r["domain"]["value"] for r in results if "domain" in r]
            elif rdfs_type == "range":
                types = [r["range"]["value"] for r in results if "range" in r]
            return types if types else []

    def get_resource_types(self, resource_name):
        """Get rdf:type for a resource (dbo: only)"""
        query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT DISTINCT ?type WHERE {{
            <http://dbpedia.org/resource/{resource_name}> rdf:type ?type .
            FILTER(STRSTARTS(STR(?type), "http://dbpedia.org/ontology/"))
        }}
        """
        result = []
        for r in self.query(query):
            type = r["type"]["value"]
            if type not in result:
                result.append(type)
                superclasses = self.get_superclasses(type)
                for s in superclasses:
                    if s not in result:
                        result.append(s)
        return result
    
    def get_superclasses(self, resource_url):
        """Get all superclasses of a resource"""
        query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?superclass WHERE {{
            <{resource_url}> rdfs:subClassOf* ?superclass .
            FILTER(?superclass != <{resource_url}>)
            FILTER(STRSTARTS(STR(?superclass), "http://dbpedia.org/ontology/"))
        }}
        """
        return [r["superclass"]["value"] for r in self.query(query)]
    
    def get_all_outgoing_properties(self, page_name):
        """Get ALL dbo properties and their values pointing from this resource"""
        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        SELECT ?property ?value WHERE {{
            <http://dbpedia.org/resource/{page_name}> ?property ?value .
            FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
            FILTER(!CONTAINS(STR(?property), "wikiPage"))
            FILTER(?property NOT IN (
                dbo:abstract, dbo:bicycleInformation, dbo:boilerPressure, dbo:carNumber, dbo:careerStation, dbo:collection,
                dbo:damage, dbo:depictionDescription, dbo:description, dbo:event, dbo:imageSize, dbo:impactFactorAsOf, dbo:isHandicappedAccessible,
                dbo:leaderFunction, dbo:lengthReference, dbo:liberationDate, dbo:logo, dbo:mapCaption, dbo:militaryService,
                dbo:minister, dbo:name, dbo:note, dbo:notes, dbo:numberOfVisitorsAsOf, dbo:orderInOffice,
                dbo:other, dbo:parkingInformation, dbo:personFunction, dbo:picture, dbo:politicalLeader, dbo:projectKeyword,
                dbo:pronunciation, dbo:quote, dbo:reference, dbo:restingPlacePosition, dbo:restriction, dbo:sales,
                dbo:selection, dbo:signature, dbo:soundRecording, dbo:speaker, dbo:statisticLabel, dbo:strength,
                dbo:termPeriod, dbo:thumbnail, dbo:title, dbo:tournamentRecord, dbo:visitorStatisticsAsOf, dbo:winsAtAsia,
                dbo:winsAtAus, dbo:winsAtChallenges, dbo:winsAtChampionships, dbo:winsAtJapan, dbo:winsAtLET, dbo:winsAtNWIDE,
                dbo:winsAtOtherTournaments, dbo:winsAtPGA, dbo:winsAtSenEuro, dbo:winsInEurope
            ))
        }}
        ORDER BY ?property ?value
        """
        results = []
        for r in self.query(query):
            prop = r["property"]["value"].split("/")[-1]

            # Handle both URI resources and literal values
            value = r["value"]["value"]
            if value.startswith("http://"):
                resource = value.split("/")[-1]  # Extract resource name from URI
            else:
                resource = value  # Keep literal value as-is
            
            results.append((prop, resource))
        return results
    
    def get_all_incoming_properties(self, page_name):
        """Get ALL dbo properties pointing to this resource"""
        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        SELECT ?subject ?property WHERE {{
            ?subject ?property <http://dbpedia.org/resource/{page_name}> .
            FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
            FILTER(!CONTAINS(STR(?property), "wikiPage"))
        }}
        ORDER BY ?property ?subject
        """
        results = []
        for r in self.query(query):
            subject = r["subject"]["value"]
            if subject.startswith("http://"):
                subject = subject.split("/")[-1]  # Extract resource name from URI
            
            prop = r["property"]["value"].split("/")[-1]
            results.append((subject, prop))
        return results
        
    def get_just_incoming_properties(self, page_name):
        """Get ALL dbo properties pointing to this resource"""
        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        SELECT ?subject ?property WHERE {{
            ?subject ?property <http://dbpedia.org/resource/{page_name}> .
            FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
            FILTER(!CONTAINS(STR(?property), "wikiPage"))
        }}
        ORDER BY ?property ?subject
        """
        results = []
        for r in self.query(query):
            prop = r["property"]["value"].split("/")[-1]
            results.append(prop)
        return results
    
    def get_values_from_list(self, page_name):
        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        SELECT ?property ?value WHERE {{
            <http://dbpedia.org/resource/{page_name}> ?property ?value .
            FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
            FILTER(CONTAINS(STR(?property), "wikiPageWikiLink"))
        }}
        ORDER BY ?property ?value
        """

        results = []
        for r in self.query(query):
            # Handle both URI resources and literal values
            value = r["value"]["value"]
            if value.startswith("http://"):
                resource = value.split("/")[-1]  # Extract resource name from URI
            else:
                resource = value  # Keep literal value as-is
            
            results.append(resource)
        return results

    
    def is_valid_type(self, expected_ranges, actual_ranges, expected_domains, actual_domain, subj, prop, obj, direction):
        """Check if resource types match expected ranges (including superclasses)"""
                
        if not expected_ranges:
            return 0.5, "No defined ranges"  # No defined ranges
        
        if not expected_domains:
            return 0.5, "No defined domains"
        
        
        # Direct match
        if set(expected_ranges) & set(actual_ranges) and set(expected_domains) & set(actual_domain):
            return 1.0, ""
        
        
        checks = {
            "http://www.w3.org/2001/XMLSchema#date": is_yyyy_mm_dd,
            "http://www.w3.org/2001/XMLSchema#double": is_double,
            "http://www.w3.org/2001/XMLSchema#float": is_double,
            "http://www.w3.org/2001/XMLSchema#gYear": is_year,
            "http://www.w3.org/2001/XMLSchema#nonNegativeInteger": is_non_negative_integer,
            "http://www.w3.org/2001/XMLSchema#positiveInteger": is_positive_integer,
            "http://www.w3.org/2001/XMLSchema#integer": is_integer,
        }


        for dtype, validator in checks.items():
            if dtype in expected_ranges and validator(obj):
                return 1.0, ""

        if (
            ("http://www.w3.org/1999/02/22-rdf-syntax-ns#langString" in expected_ranges
            or "http://www.w3.org/2001/XMLSchema#string" in expected_ranges)
            and obj is not None
        ):
            return 1.0, ""


        # Record invalid instance
        self.invalid_instances.append({
            'page_name': subj or '',
            'property': prop or '',
            'target_resource': obj or '',
            'direction': direction or '',
            'expected_ranges': '; '.join(expected_ranges) if expected_ranges else '',
            'actual_ranges': '; '.join(actual_ranges) if actual_ranges else '',
            'expected_domains': '; '.join(expected_domains) if expected_domains else '',
            'actual_domains': '; '.join(actual_domain) if actual_domain else ''
        })
        
        if not(set(expected_ranges) & set(actual_ranges)):
            error = "Range mismatch"
        elif not(set(expected_domains) & set(actual_domain)):
            error = "Domain mismatch"
        return 0.0, error  # Invalid

    def query(self, query_string):
        """Execute SPARQL query and return results"""
        try:
            self.sparql.setQuery(query_string)
            return self.sparql.query().convert()["results"]["bindings"]
        except:
            return []
    
    def read_names(self, input):
        # Read page names
        with open(input, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            pages = [
                row[0].strip()
                for row in reader
                if row and row[0].strip() and not row[0].startswith("#") and row[1] == SECTION
            ]
        return pages

    def save_invalid_instances(self, filename):
        """Save all invalid instances to a CSV file"""
        if not self.invalid_instances:
            print("No invalid instances to save.")
            return
            
        with open(filename, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['page_name', 'property', 'target_resource', 'direction',
            'expected_ranges',
            'actual_ranges',
            'expected_domains',
            'actual_domains'
            ])
            writer.writeheader()
            writer.writerows(self.invalid_instances)
        print(f"Saved {len(self.invalid_instances)} invalid instances to {filename}")
    
    def validate_resource(self, page):
        """Validate a single resource and return score, total_checks"""
        clean_page = self.clean_name(page)

        print(f"\nValidating: {page}")
        print("=" * 50)

        # Fetch properties
        outgoing = self.get_all_outgoing_properties(clean_page)
        incoming = self.get_all_incoming_properties(clean_page)

        if not outgoing and not incoming:
            return "N/A", "", "", "", "", ""

        # Caches

        # Scores
        score = total = 0
        out_score = out_total = 0
        in_score = in_total = 0

        # -------------------------
        # Helper function
        # -------------------------
        def process(prop, subj, obj, direction):
            nonlocal score, total, out_score, out_total, in_score, in_total

            # Cache lookup for property range/domain
            if prop not in self.property_ranges_cache:
                getter = (self.get_dbo_property_range_or_domain
                            if self.data_type == "dbo"
                            else self.get_dbp_property_range_or_domain)
                self.property_ranges_cache[prop] = getter(prop, "range")

            if prop not in self.property_domains_cache:
                getter = (self.get_dbo_property_range_or_domain
                            if self.data_type == "dbo"
                            else self.get_dbp_property_range_or_domain)
                self.property_domains_cache[prop] = getter(prop, "domain")

            ranges = self.property_ranges_cache[prop]
            domains = self.property_domains_cache[prop]

            subj_types = self.get_resource_types(subj)
            obj_types  = self.get_resource_types(obj)

            # Validate
            validity, error = self.is_valid_type(
                ranges, obj_types, domains, subj_types, subj, prop, obj, direction
            )

            # Update scores
            score += validity
            total += 1

            if direction == "outgoing":
                out_score += validity
                out_total += 1
            else:
                in_score += validity
                in_total += 1

            # Output
            status = "✅" if validity == 1.0 else "❓" if validity == 0.5 else "❌"
            if direction == "outgoing":
                print(f"{prop}: {clean_page} → {obj} {status}")
            elif direction == "incoming":
                print(f"{prop}: {subj} → {clean_page} {status}")
            
            if error:
                print(f"\t({error})")

        # -------------------------
        # Process outgoing
        # -------------------------
        print("\n--- Outgoing Properties ---")
        for prop, obj in outgoing:
            process(prop, clean_page, obj, direction="outgoing")

        # -------------------------
        # Process incoming
        # -------------------------
        print("\n--- Incoming Properties ---")
        for prop, subj in incoming:
            process(prop, subj, clean_page, direction="incoming")

        # -------------------------
        # Final scoring
        # -------------------------
        percentage     = round(score / total * 100) if total else 0
        out_percentage = round(out_score / out_total * 100) if out_total else 0
        in_percentage  = round(in_score / in_total * 100) if in_total else 0

        print(f"\nScore: {percentage}% ({score}/{total})")
        print(f"Outgoing: {out_percentage}% ({out_score}/{out_total})")
        print(f"Incoming: {in_percentage}% ({in_score}/{in_total})")

        return percentage, total, out_percentage, out_total, in_percentage, in_total
        

    def write_to_file(self, output, invalid, pages):
        # Open both output files
        with open(output, 'w', encoding='utf-8', newline='') as out_f, open(invalid, 'w', encoding='utf-8', newline='') as fail_f:

            # CSV writers
            valid_writer = csv.writer(out_f)
            invalid_writer = csv.DictWriter(fail_f, fieldnames=['page_name', 'property', 'target_resource', 'direction',
            'expected_ranges',
            'actual_ranges',
            'expected_domains',
            'actual_domains'
            ])

            # Write headers
            valid_writer.writerow([
                "Page Name", "Score", "Datapoints", 
                "Properties Score", "Properties Checked", 
                "Incoming Score", "Incoming Checked"
            ])
            invalid_writer.writeheader()

            # Process pages
            for page in pages:
                score, datapoints, propscore, proptotal, isofscore, isoftotal = self.validate_resource(page)

                # Write validation results
                valid_writer.writerow([page, score, datapoints, propscore, proptotal, isofscore, isoftotal])
                out_f.flush()

                # Write invalid instances for this page
                if self.invalid_instances:
                    invalid_writer.writerows(self.invalid_instances)
                    fail_f.flush()
                    count = len(self.invalid_instances)
                    print(f"  → {count} invalid instances written for {page}")
                    
                    # Clear to avoid duplicates next iteration
                    self.invalid_instances.clear()

                print(f"Written {page} to CSV")
                print("=" * 100)

def main():
    validator = DBpediaValidator(DATA_TYPE)
    input_file = f'{FOLDER}/Input/files-sorted.csv'
    #input_file = f'President_of_Ireland'
    output_file = f'{FOLDER}/Output/Scores/{SECTION}_{DATA_TYPE}_scores.csv'
    invalid_file = f'{FOLDER}/Output/Fails/{SECTION}_{DATA_TYPE}_invalid_instances.csv'

    filtered_pages = []

    if input_file.__contains__(".csv"):
        pages = validator.read_names(input_file)
        filtered_pages = pages
    else:
        pages = validator.get_values_from_list(input_file)

        if PARAMETER != "":
            print(f"Checking pages for {PARAMETER} property...")
            for i, page in enumerate(pages):
                print(f"\t{round(i/len(pages)*100)}% completed ({page})", end="\r")
                just_incoming_props = set(validator.get_just_incoming_properties(validator.clean_name(page)))
                if PARAMETER in just_incoming_props:
                    filtered_pages.append(page)
        else:
            filtered_pages = pages

    validator.write_to_file(output_file, invalid_file, filtered_pages)


if __name__ == "__main__":
    main()