#!/usr/bin/env python3
"""
Script to extract all page names from the Wikimedia "List of articles every Wikipedia should have"
Supports both the base list (1000) and expanded list (10,000):
- https://meta.wikimedia.org/wiki/List_of_articles_every_Wikipedia_should_have
- https://meta.wikimedia.org/wiki/List_of_articles_every_Wikipedia_should_have/Expanded
"""

import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import unquote, urljoin
import json
import time

def find_subpages(soup, base_url):
    """
    Find all subpages linked from the main expanded list page.
    
    Args:
        soup: BeautifulSoup object of the main page
        base_url (str): Base URL for resolving relative links
        
    Returns:
        list: List of subpage URLs
    """
    subpages = []
    
    # Look for links to subpages (usually contain "Expanded" in the path)
    links = soup.find_all('a', href=re.compile(r'/wiki/List_of_articles_every_Wikipedia_should_have/Expanded'))
    
    for link in links:
        href = link.get('href', '')
        if href and href not in ['/wiki/List_of_articles_every_Wikipedia_should_have/Expanded']:
            full_url = urljoin(base_url, href)
            subpages.append(full_url)
    
    # Also look for category-specific subpages
    category_links = soup.find_all('a', href=re.compile(r'/wiki/List_of_articles_every_Wikipedia_should_have/'))
    
    for link in category_links:
        href = link.get('href', '')
        if 'Expanded' in href or any(cat in href for cat in [
            'Biography', 'History', 'Geography', 'Arts', 'Philosophy',
            'Religion', 'Social_sciences', 'Biology', 'Chemistry',
            'Physics', 'Mathematics', 'Technology', 'Medicine'
        ]):
            full_url = urljoin(base_url, href)
            if full_url not in subpages:
                subpages.append(full_url)
    
    return list(set(subpages))  # Remove duplicates

def extract_from_tables(soup):
    """
    Extract article titles from tables (common in expanded lists).
    
    Args:
        soup: BeautifulSoup object
        
    Returns:
        set: Set of article titles
    """
    titles = set()
    
    # Find all tables
    tables = soup.find_all('table')
    
    for table in tables:
        # Look for cells containing article links
        cells = table.find_all(['td', 'th'])
        
        for cell in cells:
            links = cell.find_all('a', href=re.compile(r'/wiki/'))
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Skip non-article links
                if any(skip in href for skip in [
                    'File:', 'Category:', 'Template:', 'Help:', 'Special:',
                    'User:', 'Wikipedia:', 'Portal:', 'Talk:', 'Project:',
                    'List_of_articles_every_Wikipedia_should_have'
                ]):
                    continue
                
                if text and len(text.strip()) > 1:
                    # Clean up the text
                    clean_text = re.sub(r'\s+', ' ', text).strip()
                    titles.add(clean_text)
    
    return titles
def extract_article_titles(url, include_subpages=True):
    """
    Extract article titles from the Wikimedia vital articles page.
    
    Args:
        url (str): URL of the Wikimedia page
        include_subpages (bool): Whether to follow and extract from subpages
        
    Returns:
        list: List of article titles
    """
    
    # Headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    all_titles = set()  # Use set to avoid duplicates
    processed_urls = set()  # Track processed URLs to avoid loops
    
    def process_page(page_url, is_subpage=False):
        """Process a single page and extract titles."""
        if page_url in processed_urls:
            return set()
        
        processed_urls.add(page_url)
        page_titles = set()
        
        try:
            if is_subpage:
                print(f"  Processing subpage: {page_url.split('/')[-1]}")
                time.sleep(1)  # Be nice to the server
            
            # Fetch the page
            response = requests.get(page_url, headers=headers)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the main content div
            content_div = soup.find('div', {'id': 'mw-content-text'})
            
            if not content_div:
                print(f"Could not find main content div for {page_url}")
                return page_titles
            
            # Method 1: Extract from tables (common in expanded lists)
            table_titles = extract_from_tables(soup)
            page_titles.update(table_titles)
            
            # Method 2: Find all Wikipedia links (links containing '/wiki/')
            wiki_links = content_div.find_all('a', href=re.compile(r'/wiki/'))
            
            for link in wiki_links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Skip certain types of links
                if any(skip in href for skip in [
                    'File:', 'Category:', 'Template:', 'Help:', 'Special:',
                    'User:', 'Wikipedia:', 'Portal:', 'Talk:', 'Project:',
                    'List_of_articles_every_Wikipedia_should_have'
                ]):
                    continue
                
                # Extract article title from href
                if '/wiki/' in href and text:
                    title = text.strip()
                    
                    if title and len(title) > 1:
                        page_titles.add(title)
            
            # Method 3: Look for specific list structures (ordered/unordered lists)
            lists = content_div.find_all(['ol', 'ul'])
            
            for lst in lists:
                list_items = lst.find_all('li')
                for item in list_items:
                    # Look for links within list items
                    links = item.find_all('a', href=re.compile(r'/wiki/'))
                    for link in links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        
                        # Skip non-article links
                        if any(skip in href for skip in [
                            'File:', 'Category:', 'Template:', 'Help:', 'Special:',
                            'User:', 'Wikipedia:', 'Portal:', 'Talk:', 'Project:',
                            'List_of_articles_every_Wikipedia_should_have'
                        ]):
                            continue
                        
                        if text and len(text.strip()) > 1:
                            page_titles.add(text.strip())
            
            return page_titles
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {page_url}: {e}")
            return page_titles
        except Exception as e:
            print(f"Error parsing {page_url}: {e}")
            return page_titles
    
    try:
        # Process main page
        print(f"Processing main page: {url}")
        main_titles = process_page(url)
        all_titles.update(main_titles)
        
        # If this is the expanded list and we should include subpages
        if include_subpages and 'Expanded' in url:
            # Get the main page soup to find subpages
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find subpages
            subpages = find_subpages(soup, url)
            
            if subpages:
                print(f"Found {len(subpages)} subpages to process...")
                
                for subpage_url in subpages:
                    subpage_titles = process_page(subpage_url, is_subpage=True)
                    all_titles.update(subpage_titles)
        
        # Clean up titles
        cleaned_titles = []
        for title in all_titles:
            # Remove any remaining wiki markup
            title = re.sub(r'\[\[|\]\]', '', title)
            title = re.sub(r'\{\{|\}\}', '', title)
            title = re.sub(r'\s+', ' ', title).strip()
            
            # Skip very short titles (likely false matches)
            if len(title) < 2:
                continue
            
            # Skip titles that are clearly not articles
            if any(skip in title.lower() for skip in [
                'edit', 'citation needed', 'clarification needed',
                'main page', 'contents', 'navigation', 'expand',
                'list of articles every wikipedia should have'
            ]):
                continue
            
            # Skip purely numeric titles (likely false matches)
            if title.isdigit():
                continue
                
            cleaned_titles.append(title)
        
        # Convert to sorted list and remove duplicates
        return sorted(list(set(cleaned_titles)))
        
    except Exception as e:
        print(f"Error in main extraction: {e}")
        return []

def save_to_file(titles, filename):
    """
    Save article titles to different file formats.
    
    Args:
        titles (list): List of article titles
        filename (str): Base filename (without extension)
    """
    
    # Save as plain text
    with open(f"Wiki/{filename}.txt", 'w', encoding='utf-8') as f:
        for title in titles:
            f.write(f"{title}\n")
    
    # Save as JSON
    with open(f"Wiki/{filename}.json", 'w', encoding='utf-8') as f:
        json.dump(titles, f, indent=2, ensure_ascii=False)
    
    # Save as Python list
    with open(f"Wiki/{filename}.py", 'w', encoding='utf-8') as f:
        f.write("# Wikimedia Vital Articles List\n")
        f.write("vital_articles = [\n")
        for title in titles:
            f.write(f'    "{title.replace(chr(34), chr(92) + chr(34))}",\n')
        f.write("]\n")

def main():
    """Main function to run the scraper."""
    
    url = "https://meta.wikimedia.org/wiki/List_of_articles_every_Wikipedia_should_have"
    
    print("Extracting article titles from Wikimedia vital articles list...")
    print(f"URL: {url}")
    print("-" * 60)
    
    # Extract titles
    titles = extract_article_titles(url)
    
    if not titles:
        print("No articles found. The page structure might have changed.")
        return
    
    print(f"Found {len(titles)} unique article titles")
    print("-" * 60)
    
    # Display first 10 titles as preview
    print("Preview of extracted titles:")
    for i, title in enumerate(titles[:10]):
        print(f"{i+1:3d}. {title}")
    
    if len(titles) > 10:
        print(f"... and {len(titles) - 10} more")
    
    print("-" * 60)
    
    # Save to files
    save_to_file(titles, "wikimedia_vital_articles")
    
    print("Files saved:")
    print("- wikimedia_vital_articles.txt (plain text)")
    print("- wikimedia_vital_articles.json (JSON format)")
    print("- wikimedia_vital_articles.py (Python list)")
    
    return titles

if __name__ == "__main__":
    # Run the scraper
    articles = main()
    
    # Optional: Print statistics
    if articles:
        print(f"\nTotal articles extracted: {len(articles)}")
        
        # Basic statistics
        avg_length = sum(len(title) for title in articles) / len(articles)
        longest = max(articles, key=len)
        shortest = min(articles, key=len)
        
        print(f"Average title length: {avg_length:.1f} characters")
        print(f"Longest title: '{longest}' ({len(longest)} chars)")
        print(f"Shortest title: '{shortest}' ({len(shortest)} chars)")