#!/usr/bin/env python3
"""
ISED Scraper Test with Correct URLs
====================================
Using URLs extracted from browser inspection
"""
import requests
from bs4 import BeautifulSoup
import re
import time

# Correct URLs extracted via browser (node IDs)
ISED_STANDARDS = [
    {"id": "RSS-247", "url": "https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/node/1248", "list_date": "2025-07-24"},
    {"id": "RSS-GEN", "url": "https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/node/538", "list_date": "2021-02-11"},
    {"id": "RSS-102", "url": "https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/node/280", "list_date": "2023-12-15"},
    {"id": "RSS-216", "url": "https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/node/1197", "list_date": "2024-09-03"},
]

def get_user_agent():
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def fetch_issue_from_detail(url, rss_id):
    """從詳細頁面抓取 Issue 號碼和日期"""
    print(f"  Fetching: {rss_id}...")
    headers = {"User-Agent": get_user_agent()}
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'lxml')
        page_text = soup.get_text(separator=' ', strip=True)
        
        # 搜尋 Issue 號碼
        issue_match = re.search(r'Issue\s+(\d+)', page_text)
        # 搜尋日期 (Month DD, YYYY)
        date_match = re.search(r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})', page_text)
        
        if issue_match and date_match:
            version = f"Issue {issue_match.group(1)} ({date_match.group(1)})"
            print(f"    ✓ SUCCESS: {version}")
            return version
        elif issue_match:
            version = f"Issue {issue_match.group(1)}"
            print(f"    ⚠ Partial: {version} (no date found)")
            return version
        else:
            print(f"    ✗ No Issue found")
            return None
            
    except Exception as e:
        print(f"    ✗ Error: {e}")
        return None

def main():
    print("=" * 50)
    print("ISED Detail Page Scraper Test")
    print("=" * 50)
    
    results = []
    for std in ISED_STANDARDS:
        print(f"\n{std['id']}:")
        version = fetch_issue_from_detail(std['url'], std['id'])
        results.append({
            "id": std['id'],
            "version": version,
            "list_date": std['list_date']
        })
        time.sleep(1)  # 禮貌延遲
    
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    for r in results:
        status = "✓" if r['version'] else "✗"
        print(f"{status} {r['id']}: {r['version'] or 'FAILED'}")

if __name__ == "__main__":
    main()
