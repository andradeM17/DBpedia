# DBpedia Validation

This project validates the semantic consistency and data quality of resources on [DBpedia](https://dbpedia.org/page/DBpedia).  
It evaluates whether the types of properties and relationships in DBpedia conform to their expected ontology ranges.  
The latest version is **4.5**.

---

## Versions

### Version 1

#### **1.1**
This initial version analyzes DBpedia resources derived from Wikipedia’s [“Vital Articles.”](https://meta.wikimedia.org/wiki/List_of_articles_every_Wikipedia_should_have)  
It reads article names, converts them to DBpedia-compatible formats, and queries their properties using SPARQL.  
For each property, it checks whether the type of its value matches the expected ontology range, assigning a validity score (valid, partial, invalid).  
Results are printed and saved to a CSV file containing the page name, consistency score, and number of datapoints.  
Helper functions handle name cleaning, SPARQL queries, and property extraction, enabling basic automated semantic validation.

----

#### **1.2**
This version refactors the system into a **class-based design** (`DBpediaValidator`), improving maintainability and modularity.  
It separates **outgoing** and **incoming** property checks, introduces **superclass inspection** for indirect type matching, and generalises validation logic (`is_valid_type`).  
Queries such as `get_property_ranges` and `get_resource_types` are modularised.  
Compared to v1.1, this version produces cleaner output, parameterises sections via the `SECTION` variable, and streamlines CSV export.

----

#### **1.3**
Version 1.3 adds major functionality and improves accuracy and performance:
1. **Literal type validation:** Checks whether literal values match expected XML Schema datatypes (e.g., `xsd:date`, `xsd:double`, `xsd:gYear`) using helper functions.  
2. **Invalid instance tracking:** Records all mismatches with full context (page, property, target, expected ranges, actual types, direction) in a CSV file.  
3. **Comprehensive property coverage:** Includes all outgoing properties, with expanded filtering for non-relevant ones.  
4. **Separate scoring:** Calculates distinct scores for outgoing and incoming validations.  
5. **Caching:** Implements property range caching to reduce redundant SPARQL queries and improve runtime efficiency.

----

#### **1.4**
Version 1.4 introduces a **2×2 validation matrix** for systematic testing of DBpedia entities, extending the framework to multiple datasets.

##### **DBO Top 1000 (`dbo-tk`)**
Validates ontology (`dbo`) properties for the top 1,000 entities from the Wikipedia “Vital Articles” list.  
All invalid instances are logged for further analysis.

##### **DBO Random 1000 (`dbo-rk`)**
Generates and validates a random sample of 1,200 Wikipedia entities (1,000 + buffer).  
Uses the same scoring logic as `dbo-tk` with slight variations in name preprocessing.

##### **DBP Top 1000 (`dbp-tk`)**
Performs validation on **DBpedia Properties (`dbp`)** instead of ontology properties, using similar methods as `dbo-tk`.

##### **DBP Random 1000 (`dbp-rk`)**
Combines logic from `dbo-rk` and `dbp-tk` to evaluate `dbp` properties for the same 1,200 random entities.

---

### Version 2

#### **2.1**
Version 2.1 ran the validations check for dbp, specifially checking if there are ranges given for the properties. This is run on the top 1,000 entities (`tk`).

----

#### **2.2**
This folder contains a list of 100 random articles, generated from the Wikipedia API. Version 2.2 looked at the ability of Claude Sonnet 4.5 to annotate the articles for **Section**, **Subsection** and **Subsubsection**.

---

### Version 3

#### **3.1**
Version has a more formatted structure than the previous version in 1.4. There is now a toggle between **DBpedia Ontologies (`dbo`)**  and **DBpedia Properties (`dbp`)**.

---

### Version 4

#### **4.1**

The validation is now split into three steps:
1. Creation of a list of entities to be checked. In this case it's the entities from the Wikipedia list.
2. The values are extracted for each entity. There is currently a limit of 50 attributes for each entity.
3. These values are validated through three dictionaries: property range and domain, entity types, and subclasses for different types. They are built up from API calls.


#### **4.2**

The same steps taken in 4.1 with a list of 1,200 random Wikipedia titles.

#### **4.3**

This contains tables of pairs of types that led to triples being marked as invalid.

#### **4.4**

This contains tables of properties led to triples being marked as invalid.

#### **4.5**

Work in progress - the aim for this version is to expanded entities that are directly related to other entities, marked with a double underscore **"__"**.