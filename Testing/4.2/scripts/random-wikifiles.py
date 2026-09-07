import requests
import time

def get_random_titles(total=1200, batch_size=50):
    titles = []
    endpoint = "https://en.wikipedia.org/w/api.php"
    headers = {
        "User-Agent": "eSTÓR-DCU"
    }

    while len(titles) < total:
        response = requests.get(endpoint, params={
            "action": "query",
            "list": "random",
            "rnlimit": batch_size,
            "format": "json"
        }, headers=headers)

        response.raise_for_status()
        data = response.json()
        
        # Filter out non-article titles (those containing :)
        batch_titles = [
            item["title"] for item in data["query"]["random"]
            if ":" not in item["title"] and "disambiguation" not in item["title"].lower() and "list of" not in item["title"].lower() and "index of" not in item["title"].lower()
        ]
        
        titles.extend(batch_titles)
        print(f"Collected {len(titles)} / {total} titles...")
        for title in batch_titles:
            print(f" - {title}")
        time.sleep(0.5)  # polite pause

    return titles[:total]  # ensure exactly 'total' results

if __name__ == "__main__":
    articles = get_random_titles()

    # Save to file
    with open("Testing/4.2/input/random_wikipedia_articles.txt", "w", encoding="utf-8") as f:
        for title in articles:
            f.write(title + "\n")

    print(f"\nSaved {len(articles)} article titles to random_wikipedia_articles.txt")

'''
You will be processing a list of Wikipedia titles and organizing them according to a specific classification schema.
Your task has two main components: converting titles to dbpedia URL format and classifying them into the appropriate categories.
Here is the classification schema you must use:
    <classification_schema>
        {{CLASSIFICATION_SCHEMA}}
    </classification_schema>
    
Here are the Wikipedia titles you need to process:
    <wikipedia_titles>
        {{WIKIPEDIA_TITLES}}
    </wikipedia_titles>
    
    **Step 1: Convert to dbpedia URL format**
        For each Wikipedia title, convert it to the format used in dbpedia URLs by:
            - Replacing spaces with underscores
            - Keeping the first letter of each word capitalized
            - Preserving any existing capitalization in proper nouns
            - Keeping punctuation marks as they are
            - Not adding any prefixes or suffixes
            
            For example:
                - "Albert Einstein" becomes "Albert_Einstein"
                - "New York City" becomes "New_York_City"
                - "World War II" becomes "World_War_II"

    **Step 2: Classify each title**
        For each converted title, determine which Section it belongs to based on the classification schema provided.
            
    **Step 3: Output format**
        Present your results in the following format for each title:
            ```
                Original_Title: [converted dbpedia format]
                Section: [section name]
            ```
            Then provide a blank line before the next entry.
            
    **Important guidelines:**
        - If you're unsure about a classification, choose the most appropriate category based on the primary subject matter
        - For biographical entries, focus on what the person is most famous for
        - For places, use the geographical classifications provided
        - For concepts or objects, consider their primary domain or field of study
        - If a title could fit multiple categories, choose the most specific and relevant one
    
Process all 100 titles in this manner, converting each to dbpedia format and classifying according to the schema provided.
'''