import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from fake_useragent import UserAgent
import threading
from queue import Queue

# Configuration
MIN_DELAY = 0.5  # seconds between requests
MAX_DELAY = 2  
MAX_RETRIES = 3
PAGES_PER_SITE = 100
CONCURRENT_REQUESTS = 5

# Proxy configuration (add proxies if available)
PROXIES = []

def get_random_delay():
    return random.uniform(MIN_DELAY, MAX_DELAY)

def get_headers():
    ua = UserAgent()
    return {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.google.com/',
        'DNT': '1'
    }

def get_proxy():
    return random.choice(PROXIES) if PROXIES else None

def extract_links(url, headers):
    try:
        proxy = get_proxy()
        proxies = {'http': proxy, 'https': proxy} if proxy else None
        response = requests.get(url, headers=headers, timeout=10, proxies=proxies)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        table = soup.find('table', class_='table table-striped')
        return [a['href'] for a in table.find_all('a', href=True)] if table else []
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return []

def scrape_page(page, base_url, results_queue):
    url = f"{base_url}{page}"
    headers = get_headers()
    
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(get_random_delay())
            links = extract_links(url, headers)
            
            if links:
                for link in links:
                    print(f"Found: {link}")
                results_queue.put((page, links))
            else:
                results_queue.put((page, []))
            break
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                results_queue.put((page, []))
            time.sleep(2 ** (attempt + 1))

def scrape_site(base_url):
    results_queue = Queue()
    all_links = []
    threads = []
    
    for page in range(1, PAGES_PER_SITE + 1):
        t = threading.Thread(
            target=scrape_page,
            args=(page, base_url, results_queue)
        )
        t.start()
        threads.append(t)
        
        while threading.active_count() > CONCURRENT_REQUESTS:
            time.sleep(0.1)
    
    for t in threads:
        t.join()
    
    results = {}
    while not results_queue.empty():
        page, links = results_queue.get()
        results[page] = links
    
    for page in sorted(results.keys()):
        all_links.extend(results[page])
    
    return all_links

def main():
    sites = [
        "https://chartink.com/screeners/bullish-screeners?page=",
        "https://chartink.com/screeners/bearish-screeners?page=2"
    ]
    
    all_links = []
    for site in sites:
        all_links.extend(scrape_site(site))
    
    df = pd.DataFrame({'Links': all_links})
    df.to_excel('extracted_links.xlsx', index=False)
    print(f"Saved {len(all_links)} links")

if __name__ == "__main__":
    main()
