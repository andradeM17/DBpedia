import requests
import time

def get_random_titles(total=100, batch_size=50):
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
        
        time.sleep(2)  # polite pause

    return titles[:total]  # ensure exactly 'total' results

if __name__ == "__main__":
    articles = get_random_titles()

    # Print to console
    for title in articles:
        print(title)

    # Save to file
    with open("Testing/5.1/random_wikipedia_articles.txt", "w", encoding="utf-8") as f:
        for title in articles:
            f.write(title + "\n")

    print(f"\nSaved {len(articles)} article titles to random_wikipedia_articles.txt")