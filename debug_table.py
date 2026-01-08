import requests
from bs4 import BeautifulSoup

URL = 'https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/devices-and-equipment/radio-equipment-standards/radio-standards-specifications-rss'
headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get(URL, headers=headers, timeout=30)
soup = BeautifulSoup(response.text, 'lxml')

# Check table structure
tables = soup.find_all('table')
print(f'Tables found: {len(tables)}')

if tables:
    table = tables[0]
    rows = table.find_all('tr')
    print(f'Rows in first table: {len(rows)}')
    
    # Print first 5 rows
    for i, row in enumerate(rows[:5]):
        print(f'\nRow {i}: {row.get_text(separator=" | ", strip=True)[:150]}')
        # Check for links
        links = row.find_all('a')
        for link in links[:2]:
            href = link.get("href", "")
            print(f'  Link href: ...{href[-60:] if len(href) > 60 else href}')
            print(f'  Link text: {link.get_text(strip=True)[:50]}')
else:
    # No tables, check for lists or other structures
    print("No tables found. Checking for other structures...")
    # Look for any links containing 'rss'
    all_links = soup.find_all('a', href=True)
    rss_links = [l for l in all_links if 'rss-' in l.get('href', '').lower()]
    print(f"Found {len(rss_links)} links with 'rss-' in href")
    for link in rss_links[:5]:
        print(f"  {link.get_text(strip=True)[:50]} -> {link['href'][-50:]}")
