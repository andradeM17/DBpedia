
import csv

def check_across_pages():
    categories = ["arts and recreation", "biography", "food and agriculture", "geography", "history", "language and literature", "measurements", "philosophy", "religion", "science", "social sciences", "technology"]
    pages = set()

    for category in categories:
        with open(f"Testing/4.1/output/pages/top-1000/{category}.txt", "r", encoding="utf-8") as f:
            pages.update(set(f.read().splitlines()))

    print("Total unique pages:", len(pages))
    with open("Testing/4.1/output/pages/random-1000/all-categorised.csv", "r", encoding="utf-8") as r:
        reader = csv.reader(r)
        for row in reader:
            page = row[1]
            if page in pages:
                print("Overlap found:", page)

#TODO def check_triple_overlap():
    categories = ["arts and recreation", "biography", "food and agriculture", "geography", "history", "language and literature", "measurements", "philosophy", "religion", "science", "social sciences", "technology"]
    for category in categories:
        with open(f"Testing/4.1/output/pages/top-1000/{category}.txt", "r", encoding="utf-8") as f:
            pages.update(set(f.read().splitlines()))
    

def main():
    check_across_pages()
    

if __name__ == "__main__":
    main()