import csv
import re
from SPARQLWrapper import SPARQLWrapper, JSON

SECTION = "update"  # Change this to switch sections

class DBpediaValidator:
    def __init__(self):
        self.sparql = SPARQLWrapper("http://dbpedia.org/sparql")
        self.sparql.setReturnFormat(JSON)
    
    def query(self, query_string):
        """Execute SPARQL query and return results"""
        try:
            self.sparql.setQuery(query_string)
            return self.sparql.query().convert()["results"]["bindings"]
        except:
            return []
    
    def clean_name(self, name):
        """Clean resource name for DBpedia URI"""
        name = re.sub(r'^(.*?), (.*?)$', r'\2 \1', name)  # Last, First → First Last
        return name.replace(" ", "_").replace("'", r"\'").replace("(", r"\(").replace(")", r"\)")
    
    def get_property_ranges(self, prop):
        """Get rdfs:range for a property"""
        query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX dbo: <http://dbpedia.org/ontology/>
        SELECT ?range WHERE {{ dbo:{prop} rdfs:range ?range . }}
        """
        return [r["range"]["value"] for r in self.query(query)]
    
    def get_resource_types(self, resource_name):
        """Get rdf:type for a resource (dbo: only)"""
        query = f"""
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        SELECT ?type WHERE {{
            <http://dbpedia.org/resource/{resource_name}> rdf:type ?type .
            FILTER(STRSTARTS(STR(?type), "http://dbpedia.org/ontology/"))
        }}
        """
        return [r["type"]["value"] for r in self.query(query)]
    
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
    
    def get_outgoing_properties(self, page_name):
        """Get all dbo properties pointing from this resource"""
        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        SELECT ?property ?value WHERE {{
            <http://dbpedia.org/resource/{page_name}> ?property ?value .
            FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
            FILTER(!CONTAINS(STR(?property), "wikiPage"))
            FILTER(?property != dbo:thumbnail)
            FILTER(ISURI(?value))
        }}
        """
        results = []
        for r in self.query(query):
            prop = r["property"]["value"].split("/")[-1]
            resource = r["value"]["value"].split("/")[-1]
            results.append((prop, resource))
        return results
    
    def get_incoming_properties(self, page_name):
        """Get all dbo properties pointing to this resource"""
        query = f"""
        PREFIX dbo: <http://dbpedia.org/ontology/>
        SELECT DISTINCT ?subject ?property WHERE {{
            ?subject ?property <http://dbpedia.org/resource/{page_name}> .
            FILTER(STRSTARTS(STR(?property), "http://dbpedia.org/ontology/"))
            FILTER(!CONTAINS(STR(?property), "wikiPage"))
        }}
        """
        results = []
        for r in self.query(query):
            subject = r["subject"]["value"].split("/")[-1]
            prop = r["property"]["value"].split("/")[-1]
            results.append((subject, prop))
        return results
    
    def is_valid_type(self, resource_types, expected_ranges):
        """Check if resource types match expected ranges (including superclasses)"""
        if not expected_ranges:
            return 0.5  # No defined ranges
        
        # Direct match
        if set(resource_types) & set(expected_ranges):
            return 1.0
        
        # Check superclasses
        for rtype in resource_types:
            superclasses = self.get_superclasses(rtype)
            if set(superclasses) & set(expected_ranges):
                return 1.0
        
        return 0.0  # Invalid
    
    def validate_resource(self, page_name):
        """Validate a single resource and return score, total_checks"""
        clean_page = self.clean_name(page_name)
        score = 0
        total = 0
        
        print(f"\nValidating: {page_name}")
        print("=" * 50)
        
        # Check outgoing properties
        outgoing = self.get_outgoing_properties(clean_page)
        for prop, target_resource in outgoing:
            ranges = self.get_property_ranges(prop)
            target_types = self.get_resource_types(target_resource)
            
            validity = self.is_valid_type(target_types, ranges)
            score += validity
            total += 1
            
            status = "✅" if validity == 1.0 else "❓" if validity == 0.5 else "❌"
            #print(f"{prop} → {target_resource} {status}")
        
        # Check incoming properties
        incoming = self.get_incoming_properties(clean_page)
        page_types = self.get_resource_types(clean_page)
        
        processed_props = set()
        for subject, prop in incoming:
            if prop in processed_props:
                continue
            processed_props.add(prop)
            
            ranges = self.get_property_ranges(prop)
            validity = self.is_valid_type(page_types, ranges)
            score += validity
            total += 1
            
            status = "✅" if validity == 1.0 else "❓" if validity == 0.5 else "❌"
            #print(f"{subject} ({prop}) → {page_name} {status}")
        
        percentage = round((score / total * 100)) if total > 0 else 0
        print(f"\nScore: {percentage}% ({score}/{total})")
        
        return percentage, total

def main():
    validator = DBpediaValidator()
    
    with open(f'Testing/Wiki/{SECTION}.txt', 'r', encoding='utf-8') as f:
        pages = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    with open(f'Testing/1.2/{SECTION}_validations.csv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Page Name", "Score", "Datapoints"])
        
        for page in pages:
            score, datapoints = validator.validate_resource(page)
            writer.writerow([page, score, datapoints])
            print("=" * 100)

if __name__ == "__main__":
    main()