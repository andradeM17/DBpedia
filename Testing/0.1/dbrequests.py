import requests
import xml.etree.ElementTree as ET

def check_superclass(resource_url, ranges):
    superclass = requests.get(f"http://dbpedia.org/data3/{resource_url.split('/')[-1]}.rdf")
    if superclass.status_code == 200:
        super_root = ET.fromstring(superclass.content)
        super_ns = {
            'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
            'rdfs': 'http://www.w3.org/2000/01/rdf-schema#'
        }
        for sup in super_root.findall(".//rdf:Description/rdfs:subClassOf", super_ns):
            if not(sup.attrib.get(f"{{{super_ns['rdf']}}}resource") == resource_url) and sup.attrib.get(f"{{{super_ns['rdf']}}}resource").startswith("http://dbpedia.org/ontology/"):
                sup_val = sup.attrib.get(f"{{{super_ns['rdf']}}}resource")
                if sup_val.split("/")[-1] != "owl#Thing" and not(sup_val in ranges):
                    result = check_superclass(sup_val, ranges)
                    return result
                else:
                    if sup_val in ranges:
                        return sup_val
                    return resource_url


def get_property_range(prop):
    """Fetch rdfs:range for a dbo property"""
    url = f"http://dbpedia.org/data3/{prop}.rdf"
    resp = requests.get(url)
    if resp.status_code != 200:
        return []
    root = ET.fromstring(resp.content)
    ns = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'rdfs': 'http://www.w3.org/2000/01/rdf-schema#'
    }
    ranges = []
    for r in root.findall(".//rdfs:range", ns):
        val = r.attrib.get(f"{{{ns['rdf']}}}resource")
        if val:
            ranges.append(val)
    return ranges

def get_resource_types(resource_url):
    """Fetch rdf:type(s) for a resource, only dbo: types"""
    resp = requests.get(f"http://dbpedia.org/data/{resource_url}.rdf")
    if resp.status_code != 200:
        return []
    root = ET.fromstring(resp.content)
    ns = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#'
    }
    dbo_prefix = "http://dbpedia.org/ontology/"
    types = []
    for t in root.findall(".//rdf:Description/rdf:type", ns):
        val = t.attrib.get(f"{{{ns['rdf']}}}resource")
        if val and val.startswith(dbo_prefix):
            types.append(val)
    return types


# === MAIN ===
Page = input("Enter the DBpedia page name: ").strip()

url = f"https://dbpedia.org/data/{Page}.rdf"
response = requests.get(url)

if response.status_code == 200:
    root = ET.fromstring(response.content)

    ns = {
        'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
        'dbo': 'http://dbpedia.org/ontology/'
    }

    description = root.find(f".//rdf:Description[@rdf:about='http://dbpedia.org/resource/{Page}']", ns)

    if description is not None:
        for child in description:
            tag = child.tag
            if tag.startswith(f"{{{ns['dbo']}}}"):
                prop = tag.replace(f"{{{ns['dbo']}}}", "")
                if "wikiPage" in prop or prop == "thumbnail":
                    continue

                resource = child.attrib.get(f"{{{ns['rdf']}}}resource")
                if resource:
                    resource_name = resource.split("/")[-1]
                    print(f"{prop} → {resource_name}")

                    # get property ranges
                    ranges = get_property_range(prop)

                    # get resource types
                    types = get_resource_types(resource_name)

                    # check if any match
                    if set(ranges) & set(types):
                        print("\t✅ Valid")
                    elif ranges == []:
                        print("\t❓ No defined ranges")                   
                    else:
                        valid = False
                        for t in types:
                            superclass = check_superclass(t, ranges)
                            if superclass in ranges:
                                valid = True
                                print(f"\t ✅ Valid") 
                                break 
                        if not(valid):
                            print("\t❌ Invalid")
                            for r in ranges:
                                print(f"\tExpected range: {r.split('/')[-1]}")
                            print("\tActual types:")
                            for t in types:
                                print(f"\t\t{t.split('/')[-1]}")
                            if types == []:
                                print("\t\tN/A")


    else:
        print("Description not found.")
else:
    print("Failed to download RDF.")
