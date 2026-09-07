import csv
import re
from SPARQLWrapper import SPARQLWrapper, JSON


SECTION = "geography"

class DBpediaValidator:
    def __init__(self, output_file):
        self.sparql = SPARQLWrapper("http://dbpedia.org/sparql")
        self.sparql.setReturnFormat(JSON)
        self.output_file = output_file
        #self.checked_props = set()
        # Load existing properties from CSV if it exists
        with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["property", "dbp_property", "status"])
            f.flush()

    def query(self, query_string):
        """Execute SPARQL query and return results"""
        try:
            self.sparql.setQuery(query_string)
            return self.sparql.query().convert()["results"]["bindings"]
        except:
            return []
    
    def clean_name(self, name):
        """Clean resource name for DBpedia URI"""
        name = re.sub(r'^(.*?), (.*?)$', r'\2 \1', name)
        return name.replace(" ", "_").replace("'", r"\'").replace("(", r"\(").replace(")", r"\)")
    
    def get_property_ranges(self, dbp_prop):
        """Get expected ranges for a dbp property"""
        query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX dbp: <http://dbpedia.org/property/>
        PREFIX owl: <http://www.w3.org/2002/07/owl#>

        SELECT DISTINCT ?range WHERE {{
            {{
                dbp:{dbp_prop} owl:equivalentProperty ?dboProp .
                ?dboProp rdfs:range ?range .
            }}
            UNION
            {{
                dbo:{dbp_prop} rdfs:range ?range .
            }}
        }}
        """
        results = self.query(query)
        if not results:
            print(dbp_prop)
            return [dbp_prop, "no result"]
        ranges = [r["range"]["value"] for r in results if "range" in r]
        if not ranges:
            print(dbp_prop)
            return [dbp_prop, "no range"]
        else:
            return [dbp_prop, "valid"]

    def get_resource_types(self, resource_name):
        """Get rdf:type for a resource"""
        query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT DISTINCT ?type WHERE {{
            <http://dbpedia.org/resource/{resource_name}> rdf:type ?type .
            FILTER(STRSTARTS(STR(?type), "http://dbpedia.org/ontology/"))
        }}
        """
        return [r["type"]["value"] for r in self.query(query)]
    
    def get_all_outgoing_properties(self, page_name):
        """Get all properties and values from this resource"""
        query = f"""
        PREFIX dbp: <http://dbpedia.org/property/>
        SELECT ?property ?value WHERE {{
            <http://dbpedia.org/resource/{page_name}> ?property ?value .
            FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/property/"))
            FILTER(!CONTAINS(STR(?property), "wikiPage"))
        }}
        ORDER BY ?property ?value
        """
        results = []
        for r in self.query(query):
            prop = r["property"]["value"].split("/")[-1]
            
            value = r["value"]["value"]
            if value.startswith("http://"):
                resource = value.split("/")[-1]
            else:
                resource = value
            
            results.append((prop, resource))
        return results
    
    def get_all_incoming_properties(self, page_name):
        """Get all properties pointing to this resource"""
        query = f"""
        PREFIX dbp: <http://dbpedia.org/property/>
        SELECT ?subject ?property WHERE {{
            ?subject ?property <http://dbpedia.org/resource/{page_name}> .
            FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/property/"))
            FILTER(!CONTAINS(STR(?property), "wikiPage"))
        }}
        ORDER BY ?property ?subject
        """
        results = []
        for r in self.query(query):
            subject = r["subject"]["value"]
            if subject.startswith("http://"):
                subject = subject.split("/")[-1]
            
            prop = r["property"]["value"].split("/")[-1]
            results.append((subject, prop))
        return results
    
    def validate_resource(self, page_name):
        """Validate a single resource"""
        clean_page = self.clean_name(page_name)
        
        print(f"\nValidating: {page_name}")
        print("=" * 50)
        
        outgoing = self.get_all_outgoing_properties(clean_page)
        property_cache = {}
        new_props = set()
        
        for prop, target_resource in outgoing:
            if prop not in property_cache:
                property_cache[prop] = self.get_property_ranges(prop)
            checkedprop = property_cache[prop]
            if checkedprop:
                new_props.add(tuple(checkedprop))
        
        incoming = self.get_all_incoming_properties(clean_page)
        #page_types = self.get_resource_types(clean_page)
        
        processed_props = set()
        for subject, prop in incoming:
            if prop in processed_props:
                continue
            processed_props.add(prop)
            
            if prop not in property_cache:
                property_cache[prop] = self.get_property_ranges(prop)
            checkedprop = property_cache[prop]
            if checkedprop:
                new_props.add(tuple(checkedprop))
        
        if new_props:
            self.write_results(page_name, new_props)
    
    def write_results(self, page, props):
        """Write new properties to CSV file"""
        with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for prop in props:
                writer.writerow([page, prop[0], prop[1]])
            f.flush()


def main():
    output_file = f'Testing/2.1/{SECTION}_dbo_check.csv'
    validator = DBpediaValidator(output_file)
    
    input_file = f'Testing/1.2/Validations/{SECTION}_validations.csv'

    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)  # Skip header
        pages = [
            row[0].strip()
            for row in reader
            if row and row[0].strip() and not row[0].startswith("#")
        ]

    for page in pages:
        validator.validate_resource(page)
        print("=" * 100)
    
    print(f"\nResults written to {output_file}")


if __name__ == "__main__":
    main()