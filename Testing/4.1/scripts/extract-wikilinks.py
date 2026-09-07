import re, requests
import time

headers = {"User-Agent": "eSTÓR-DCU"}

# Read the HTML file
with open("Testing/4.1/input/example.html", "r", encoding="utf-8") as f:
    html_content = f.read()

# Regex to match href links
pattern = r'<a href="(https://www\.wikidata\.org/wiki/Q\d+)"'


# Find all matches
urls = re.findall(pattern, html_content)

with open("Testing/4.1/output/pages/all-formatted.txt", "w", encoding="utf-8") as f:
    entities = []
    for i, url in enumerate(urls):
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        current_page = response.text
        link_pattern = r'<a href="https://en\.wikipedia\.org/wiki/(.*?)"'
        en_urls = re.findall(link_pattern, current_page)
        for en_url in en_urls:
            print("\n", en_url)
            f.write(en_url + "\n")
        f.flush()
        print(f"{i}/{len(urls)}")
        time.sleep(0.001)