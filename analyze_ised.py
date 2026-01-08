#!/usr/bin/env python3
"""
分析 ISED RSS 主列表頁面結構
目標：確認是否可以從一個頁面抓取所有標準的版本資訊
"""
import requests
from bs4 import BeautifulSoup
import re

URL = "https://ised-isde.canada.ca/site/spectrum-management-telecommunications/en/devices-and-equipment/radio-equipment-standards/radio-standards-specifications-rss"

def analyze_list_page():
    print(f"Fetching: {URL}")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    response = requests.get(URL, headers=headers, timeout=30)
    print(f"Status: {response.status_code}")
    
    soup = BeautifulSoup(response.text, 'lxml')
    
    # 找出所有包含 "RSS-" 的連結
    print("\n=== 搜尋 RSS 標準連結 ===")
    rss_links = []
    for link in soup.find_all('a', href=True):
        text = link.get_text(strip=True)
        href = link['href']
        if 'rss-' in href.lower() or 'RSS-' in text:
            # 檢查父元素是否有版本資訊
            parent = link.find_parent(['tr', 'li', 'div', 'td'])
            parent_text = parent.get_text(separator=' | ', strip=True) if parent else ""
            
            # 搜尋 Issue 和 Date
            issue_match = re.search(r'Issue\s+(\d+)', parent_text)
            date_match = re.search(r'([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})', parent_text)
            
            rss_links.append({
                'text': text[:50],
                'href': href[-50:] if len(href) > 50 else href,
                'issue': issue_match.group(0) if issue_match else None,
                'date': date_match.group(0) if date_match else None
            })
    
    print(f"找到 {len(rss_links)} 個 RSS 相關連結")
    for item in rss_links[:20]:  # 只顯示前 20 個
        print(f"  {item['text']}")
        print(f"    Issue: {item['issue']}, Date: {item['date']}")
        print()

    # 額外：檢查是否有表格結構
    print("\n=== 檢查表格結構 ===")
    tables = soup.find_all('table')
    print(f"找到 {len(tables)} 個表格")
    
    for i, table in enumerate(tables):
        rows = table.find_all('tr')
        print(f"表格 {i+1}: {len(rows)} 行")
        # 顯示前幾行
        for row in rows[:3]:
            print(f"  {row.get_text(separator=' | ', strip=True)[:100]}")

if __name__ == "__main__":
    analyze_list_page()
