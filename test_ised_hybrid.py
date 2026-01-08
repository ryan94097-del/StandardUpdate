#!/usr/bin/env python3
"""
ISED Hybrid Scraper Test
========================
1. 從列表頁面抓取所有 RSS 標準的 URL
2. 訪問每個詳細頁面抓取 Issue 和 Date
"""
import requests
from bs4 import BeautifulSoup
import re
import time

LIST_URL = "https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/devices-and-equipment/radio-equipment-standards/radio-standards-specifications-rss"

def get_user_agent():
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def fetch_rss_links_from_list():
    """從列表頁面抓取所有 RSS 標準的連結"""
    print(f"Fetching list page: {LIST_URL}")
    headers = {"User-Agent": get_user_agent()}
    response = requests.get(LIST_URL, headers=headers, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'lxml')
    
    rss_standards = {}
    
    # 查找表格中的連結
    for row in soup.find_all('tr'):
        cells = row.find_all('td')
        if len(cells) >= 2:
            date_cell = cells[0].get_text(strip=True)  # Publication date
            title_cell = cells[1]
            link = title_cell.find('a')
            
            if link:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # 只處理 RSS 標準
                if 'rss-' in href.lower():
                    # 從 URL 提取 RSS ID (如 rss-247)
                    rss_match = re.search(r'(rss-\d+|rss-gen)', href.lower())
                    if rss_match:
                        rss_id = rss_match.group(1).upper().replace('-', '-')
                        # 修正 URL 格式
                        if href.startswith('/'):
                            full_url = f"https://ised-isde.canada.ca{href}"
                        else:
                            full_url = href
                        
                        rss_standards[rss_id] = {
                            'url': full_url,
                            'title': text,
                            'list_date': date_cell
                        }
    
    return rss_standards

def fetch_issue_from_detail(url, rss_id):
    """從詳細頁面抓取 Issue 號碼和日期"""
    print(f"  Fetching detail: {rss_id}...")
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
            return f"Issue {issue_match.group(1)} ({date_match.group(1)})"
        elif issue_match:
            return f"Issue {issue_match.group(1)}"
        else:
            return None
            
    except Exception as e:
        print(f"    Error: {e}")
        return None

def main():
    print("=" * 50)
    print("ISED Hybrid Scraper Test")
    print("=" * 50)
    
    # Step 1: 從列表頁面取得所有 RSS 連結
    rss_standards = fetch_rss_links_from_list()
    print(f"\nFound {len(rss_standards)} RSS standards from list page")
    
    # Step 2: 測試幾個標準 (RSS-247 和另一個)
    test_ids = ['RSS-247', 'RSS-GEN', 'RSS-102']
    
    print("\n" + "=" * 50)
    print("Testing Detail Page Scraping")
    print("=" * 50)
    
    for rss_id in test_ids:
        # 嘗試不同的 ID 格式
        for try_id in [rss_id, rss_id.lower(), rss_id.replace('-', '')]:
            if try_id in rss_standards:
                rss_id = try_id
                break
        
        if rss_id in rss_standards:
            info = rss_standards[rss_id]
            print(f"\n{rss_id}:")
            print(f"  URL: {info['url'][:80]}...")
            print(f"  List Date: {info['list_date']}")
            
            version = fetch_issue_from_detail(info['url'], rss_id)
            print(f"  Detail Version: {version}")
            
            time.sleep(1)  # 禮貌延遲
        else:
            print(f"\n{rss_id}: Not found in list")
            print(f"  Available keys (sample): {list(rss_standards.keys())[:5]}")

if __name__ == "__main__":
    main()
