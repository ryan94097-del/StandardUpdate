
import requests
from bs4 import BeautifulSoup
import re

def analyze_detail_page(url):
    print(f"--- Analyzing Detail Page: {url} ---")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Look for "Issue" and "Date" patterns
        text = soup.get_text()
        
        # Regex for Issue X
        issue_matches = re.finditer(r"Issue\s+(\d+)", text)
        print("\nIssue Matches:")
        val_issue = None
        for m in issue_matches:
            print(f" - Found: '{m.group(0)}'")
            # Get context
            # We want the one that is likely the main header or metadata
            # usually near the top
            val_issue = m.group(1) 
            
        # Regex for Date (July 24, 2025)
        date_matches = re.finditer(r"([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})", text)
        print("\nDate Matches:")
        val_date = None
        for m in date_matches:
            print(f" - Found: '{m.group(0)}'")
            if "July 24, 2025" in m.group(0):
                 val_date = m.group(0)

        # Look for specific HTML structures (e.g. headers)
        print("\nHeader Structure:")
        for h in soup.find_all(['h1', 'h2', 'p']):
             txt = h.get_text(strip=True)
             if "Issue" in txt and "Date" in txt: # Sometimes they are together
                 print(f"HEAD/P: {txt}")
             elif "Issue" in txt and len(txt) < 50:
                 print(f"HEAD/P (Issue): {txt}")
             elif "July 24" in txt:
                 print(f"HEAD/P (Date): {txt}")

    except Exception as e:
        print(f"Error: {e}")

url_detail = "https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/devices-and-equipment/radio-equipment-standards/radio-standards-specifications-rss/rss-247-digital-transmission-systems-dtss-frequency-hopping-systems-fhss-and-licence-exempt-local"
analyze_detail_page(url_detail)
