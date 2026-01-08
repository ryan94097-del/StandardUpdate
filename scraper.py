#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法規標準自動監測系統 - 爬蟲核心
=================================
功能：
1. 定期檢查 FCC/ISED/ETSI 法規標準更新
2. 發送更新通知、錯誤通報、每週心跳報告
3. 透過 GitHub Actions 自動執行

作者：自動化系統
"""

import os
import json
import time
import random
import smtplib
import traceback
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, Any, List, Tuple

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import re

# ============================================================
# 設定區
# ============================================================

# 檔案路徑
HISTORY_FILE = "history.json"

# Email 設定 (從環境變數讀取)
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENTS", "ryan94097@gmail.com")  # 從環境變數讀取，預設為備用值

# Telegram 設定 (從環境變數讀取)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# 請求設定
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

# 心跳設定 - 每週一發送
HEARTBEAT_DAY = 0  # 0 = 週一

# ============================================================
# 工具函式
# ============================================================

def get_user_agent() -> str:
    """取得隨機 User-Agent"""
    try:
        ua = UserAgent()
        return ua.random
    except Exception:
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def random_delay(min_sec: float = 1.0, max_sec: float = 3.0) -> None:
    """隨機延遲，避免被網站封鎖"""
    time.sleep(random.uniform(min_sec, max_sec))

def load_history() -> Dict[str, Any]:
    """載入歷史記錄"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"metadata": {}, "standards": {}, "update_history": []}

def save_history(data: Dict[str, Any]) -> None:
    """儲存歷史記錄"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_current_time_str() -> str:
    """取得當前時間字串 (UTC+8)"""
    utc_now = datetime.now(timezone.utc)
    taipei_tz = timezone(timedelta(hours=8))
    taipei_now = utc_now.astimezone(taipei_tz)
    return taipei_now.strftime("%Y-%m-%d %H:%M:%S")

def is_heartbeat_day() -> bool:
    """檢查今天是否為心跳發送日 (週一)"""
    utc_now = datetime.now(timezone.utc)
    taipei_tz = timezone(timedelta(hours=8))
    taipei_now = utc_now.astimezone(taipei_tz)
    return taipei_now.weekday() == HEARTBEAT_DAY

# ============================================================
# Email 功能
# ============================================================

def send_email(subject: str, html_content: str) -> bool:
    """
    發送 HTML 格式 Email
    
    Args:
        subject: 郵件主旨
        html_content: HTML 格式內容
        
    Returns:
        bool: 是否發送成功
    """
    if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
        print("[警告] 未設定 Email 環境變數，跳過發送")
        return False
    
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = EMAIL_HOST_USER
        msg["To"] = EMAIL_RECIPIENT
        
        # 添加 HTML 內容
        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)
        
        # 連接並發送
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.sendmail(EMAIL_HOST_USER, EMAIL_RECIPIENT, msg.as_string())
        
        print(f"[成功] Email 已發送: {subject}")
        return True
        
    except Exception as e:
        print(f"[錯誤] Email 發送失敗: {e}")
        return False

def send_update_notification(updates: List[Dict[str, Any]]) -> None:
    """發送標準更新通知"""
    subject = f"📋 法規標準更新通知 ({len(updates)} 項)"
    
    html = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; }
            .header { background: #4CAF50; color: white; padding: 15px; border-radius: 5px; }
            .update-item { border-left: 4px solid #2196F3; padding: 10px; margin: 10px 0; background: #f9f9f9; }
            .old-version { color: #999; text-decoration: line-through; }
            .new-version { color: #4CAF50; font-weight: bold; }
            .footer { margin-top: 20px; padding-top: 10px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>📋 法規標準更新通知</h2>
        </div>
        <p>以下標準已偵測到更新：</p>
    """
    
    for update in updates:
        html += f"""
        <div class="update-item">
            <strong>{update['name']}</strong> ({update['id']})<br>
            <span class="old-version">舊版本: {update.get('old_version', 'N/A')}</span><br>
            <span class="new-version">新版本: {update.get('new_version', 'N/A')}</span><br>
            <small>類型: {update.get('type', 'Unknown')}</small>
        </div>
        """
    
    html += f"""
        <div class="footer">
            <p>此郵件由法規標準監測系統自動發送</p>
            <p>檢測時間: {get_current_time_str()}</p>
        </div>
    </body>
    </html>
    """
    
    send_email(subject, html)

def send_error_notification(error_message: str) -> None:
    """發送錯誤通報"""
    subject = "🚨 監測系統執行失敗"
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .header {{ background: #f44336; color: white; padding: 15px; border-radius: 5px; }}
            .error-box {{ background: #ffebee; border: 1px solid #f44336; padding: 15px; margin: 15px 0; border-radius: 5px; }}
            pre {{ background: #263238; color: #aed581; padding: 15px; border-radius: 5px; overflow-x: auto; }}
            .footer {{ margin-top: 20px; padding-top: 10px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>🚨 監測系統執行失敗</h2>
        </div>
        <div class="error-box">
            <p><strong>錯誤訊息：</strong></p>
            <pre>{error_message}</pre>
        </div>
        <p>請檢查 GitHub Actions 日誌以取得更多資訊。</p>
        <div class="footer">
            <p>發生時間: {get_current_time_str()}</p>
        </div>
    </body>
    </html>
    """
    
    send_email(subject, html)

def send_heartbeat(standards_checked: int, status: str) -> None:
    """發送每週心跳報告"""
    subject = "✅ 系統每週健康報告"
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .header {{ background: #2196F3; color: white; padding: 15px; border-radius: 5px; }}
            .status-box {{ background: #e8f5e9; border: 1px solid #4CAF50; padding: 15px; margin: 15px 0; border-radius: 5px; }}
            .metric {{ display: inline-block; margin: 10px 20px; text-align: center; }}
            .metric-value {{ font-size: 24px; font-weight: bold; color: #4CAF50; }}
            .metric-label {{ font-size: 12px; color: #666; }}
            .footer {{ margin-top: 20px; padding-top: 10px; border-top: 1px solid #ddd; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>✅ 系統每週健康報告</h2>
        </div>
        <div class="status-box">
            <p>🟢 <strong>系統運作正常</strong></p>
            <div class="metric">
                <div class="metric-value">{standards_checked}</div>
                <div class="metric-label">已掃描標準數</div>
            </div>
            <div class="metric">
                <div class="metric-value">{status.upper()}</div>
                <div class="metric-label">系統狀態</div>
            </div>
        </div>
        <p>本週已完成所有標準的定期檢查，目前系統運作正常。</p>
        <div class="footer">
            <p>報告時間: {get_current_time_str()}</p>
            <p>此郵件由法規標準監測系統每週一自動發送</p>
        </div>
    </body>
    </html>
    """
    
    send_email(subject, html)

# ============================================================
# Telegram 功能
# ============================================================

def send_telegram_message(text: str) -> bool:
    """
    發送 Telegram 訊息
    
    Args:
        text: 訊息文字 (支援 Markdown 格式)
        
    Returns:
        bool: 是否發送成功
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[警告] 未設定 Telegram 環境變數，跳過發送")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        
        print(f"[成功] Telegram 訊息已發送")
        return True
        
    except Exception as e:
        print(f"[錯誤] Telegram 發送失敗: {e}")
        return False

def send_telegram_update_notification(updates: List[Dict[str, Any]]) -> None:
    """發送 Telegram 標準更新通知"""
    text = f"📋 *法規標準更新通知* ({len(updates)} 項)\n\n"
    
    for update in updates:
        text += f"🔹 *{update['name']}* ({update['id']})\n"
        text += f"   舊版本: `{update.get('old_version', 'N/A')}`\n"
        text += f"   新版本: `{update.get('new_version', 'N/A')}`\n\n"
    
    text += f"⏰ 檢測時間: {get_current_time_str()}"
    
    send_telegram_message(text)

def send_telegram_error_notification(error_message: str) -> None:
    """發送 Telegram 錯誤通報"""
    # 截斷過長的錯誤訊息 (Telegram 限制 4096 字元)
    if len(error_message) > 1500:
        error_message = error_message[:1500] + "...\n(訊息過長已截斷)"
    
    text = f"🚨 *監測系統執行失敗*\n\n"
    text += f"```\n{error_message}\n```\n\n"
    text += f"⏰ 發生時間: {get_current_time_str()}"
    
    send_telegram_message(text)

def send_telegram_heartbeat(standards_checked: int, status: str) -> None:
    """發送 Telegram 每週心跳報告"""
    text = f"✅ *系統每週健康報告*\n\n"
    text += f"🟢 系統運作正常\n\n"
    text += f"📊 已掃描標準數: *{standards_checked}*\n"
    text += f"📈 系統狀態: *{status.upper()}*\n\n"
    text += f"⏰ 報告時間: {get_current_time_str()}"
    
    send_telegram_message(text)

# ============================================================
# 爬蟲核心功能
# ============================================================

def fetch_ecfr_data(standard: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    從 eCFR API 取得 FCC CFR 標準版本資訊
    
    使用 eCFR Versioner API:
    - 結構查詢: GET /api/versioner/v1/structure/{date}/title-{title}.json
    - 版本列表: GET /api/versioner/v1/versions/title-{title}.json
    
    Args:
        standard: 標準資料字典
        
    Returns:
        (version, date) 或 (None, None) 如果失敗
    """
    title = standard.get("title", "")
    if not title:
        return None, None
    
    headers = {"User-Agent": get_user_agent()}
    
    # 使用版本列表 API 取得最新修訂日期
    versions_url = f"https://www.ecfr.gov/api/versioner/v1/versions/title-{title}.json"
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(versions_url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            data = response.json()
            
            # eCFR API 回傳版本列表
            if isinstance(data, dict) and "content_versions" in data:
                versions = data["content_versions"]
                if versions and len(versions) > 0:
                    # 取得最新版本 (列表第一個通常是最新的)
                    latest = versions[0]
                    version_date = latest.get("date", "")
                    if version_date:
                        return version_date, get_current_time_str()
            
            # 嘗試從 meta 欄位取得
            if isinstance(data, dict) and "meta" in data:
                meta = data["meta"]
                if "latest_issue_date" in meta:
                    return meta["latest_issue_date"], get_current_time_str()
                if "latest_amendment_date" in meta:
                    return meta["latest_amendment_date"], get_current_time_str()
            
            # 回傳內容 hash
            import hashlib
            content_hash = hashlib.md5(response.text.encode()).hexdigest()[:12]
            return content_hash, get_current_time_str()
            
        except requests.RequestException as e:
            print(f"[重試 {attempt + 1}/{MAX_RETRIES}] eCFR 請求失敗: {standard['id']} - {e}")
            if attempt < MAX_RETRIES - 1:
                random_delay(2, 5)
        except Exception as e:
            print(f"[錯誤] eCFR 解析失敗: {standard['id']} - {e}")
            break
    
    return None, None

def fetch_ised_data(standard: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    從 ISED 官網爬取 RSS 標準版本資訊
    
    使用標準的直接連結頁面，例如：
    https://ised-isde.canada.ca/site/.../rss-247-digital-transmission-systems-...
    
    頁面中包含版本資訊格式：
    "Issue 4 July 24, 2025"
    
    Args:
        standard: 標準資料字典，需包含 source_url
        
    Returns:
        (version_string, check_date) 或 (None, None) 如果失敗
    """
    source_url = standard.get("source_url", "")
    rss_id = standard.get("rss_id", "")
    
    if not source_url:
        return None, None
    
    headers = {"User-Agent": get_user_agent()}
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(source_url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "lxml")
            
            # Extract text with separator to handle <br> and other tags
            page_text = soup.get_text(separator=" ", strip=True)
            
            # Search for Issue number
            # Pattern: "Issue 4"
            issue_match = re.search(r"Issue\s+(\d+)", page_text)
            
            # Search for Date
            # 月份名稱列表
            months = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
            # Pattern 1: "July 24, 2025" 或 "July 24 2025" (含日期)
            date_match = re.search(rf"({months}\s+\d{{1,2}},?\s+\d{{4}})", page_text)
            if not date_match:
                # Pattern 2: "February 2019" 或 "April 2018" (只有月份年份)
                date_match = re.search(rf"({months}\s+\d{{4}})", page_text)
            
            if issue_match and date_match:
                issue_num = issue_match.group(1)
                issue_date = date_match.group(1)
                
                # Check if they are reasonably close to each other (optional validation)
                # For now, just trust if both are present in the top section
                version_str = f"Issue {issue_num} ({issue_date})"
                return version_str, get_current_time_str()
            
            # Fallback: Try raw text regex just in case (e.g. inside a script tag or attribute)
            if not issue_match:
                 raw_issue_match = re.search(r"Issue\s+(\d+)", response.text)
                 if raw_issue_match:
                     issue_num = raw_issue_match.group(1)
                     if date_match:
                        version_str = f"Issue {issue_num} ({date_match.group(1)})"
                        return version_str, get_current_time_str()

            # If specific parsing fails, fallback to content hash
            import hashlib
            content_hash = hashlib.md5(response.text.encode()).hexdigest()[:12]
            return content_hash, get_current_time_str()
            
        except requests.RequestException as e:
            print(f"[重試 {attempt + 1}/{MAX_RETRIES}] ISED 請求失敗: {standard['id']} - {e}")
            if attempt < MAX_RETRIES - 1:
                random_delay(2, 5)
        except Exception as e:
            print(f"[錯誤] ISED 解析失敗: {standard['id']} - {e}")
            break
    
    return None, None

def fetch_etsi_data(standard: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    從 ETSI 官網爬取 EN 標準版本資訊
    
    ETSI 的標準目錄結構：
    - 目錄連結格式為 XX.YY.ZZ_SS
    - XX.YY.ZZ = 版本號（例如 02.02.02）
    - SS = 狀態碼：
      - 60 = 已發布 (Published)
      - 40 = 投票中 (Vote)
      - 30 = 草稿 (Draft)
      - 20 = 早期草稿 (Early Draft)
    
    Args:
        standard: 標準資料字典
        
    Returns:
        (version, date) 或 (None, None) 如果失敗
    """
    source_url = standard.get("source_url", "")
    
    if not source_url:
        return None, None
    
    headers = {"User-Agent": get_user_agent()}
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(source_url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "lxml")
            
            # ETSI 目錄頁面解析
            # 格式: XX.YY.ZZ_SS，例如 02.02.02_60
            # 我們只關心已發布版本 (_60)
            
            published_versions = []
            
            # 尋找所有目錄連結
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                link_text = link.get_text(strip=True)
                
                # 匹配版本目錄格式: XX.YY.ZZ_60 (已發布版本)
                version_match = re.search(r"(\d{2})\.(\d{2})\.(\d{2})_60", href)
                if not version_match:
                    # 嘗試從連結文字匹配
                    version_match = re.search(r"(\d{2})\.(\d{2})\.(\d{2})_60", link_text)
                
                if version_match:
                    major = int(version_match.group(1))
                    minor = int(version_match.group(2))
                    patch = int(version_match.group(3))
                    # 使用元組儲存以便排序
                    published_versions.append((major, minor, patch))
            
            # 找出最新的已發布版本
            if published_versions:
                # 排序並取最新版本
                published_versions.sort(reverse=True)
                latest = published_versions[0]
                # 格式化為標準版本號格式: V X.Y.Z
                version_str = f"V{latest[0]}.{latest[1]}.{latest[2]}"
                return version_str, get_current_time_str()
            
            # 備用方案: 嘗試從 PDF 連結提取版本號
            for link in soup.find_all("a", href=True):
                href = link.get("href", "")
                if ".pdf" in href.lower():
                    # 從檔名中提取版本號 (例如 en_300328v020202p.pdf)
                    pdf_version_match = re.search(r"v(\d{2})(\d{2})(\d{2})", href.lower())
                    if pdf_version_match:
                        major = int(pdf_version_match.group(1))
                        minor = int(pdf_version_match.group(2))
                        patch = int(pdf_version_match.group(3))
                        version_str = f"V{major}.{minor}.{patch}"
                        return version_str, get_current_time_str()
            
            # 尋找頁面中的版本文字
            page_text = soup.get_text()
            text_version_match = re.search(r"[Vv]ersion\s*([\d.]+)|V([\d.]+)", page_text)
            if text_version_match:
                version = text_version_match.group(1) or text_version_match.group(2)
                return f"V{version}", get_current_time_str()
            
            # 最後備用: 回傳頁面內容的 hash
            import hashlib
            content_hash = hashlib.md5(response.text.encode()).hexdigest()[:12]
            print(f"[警告] ETSI 無法解析版本，使用內容 hash: {standard['id']}")
            return content_hash, get_current_time_str()
            
        except requests.RequestException as e:
            print(f"[重試 {attempt + 1}/{MAX_RETRIES}] ETSI 請求失敗: {standard['id']} - {e}")
            if attempt < MAX_RETRIES - 1:
                random_delay(2, 5)
        except Exception as e:
            print(f"[錯誤] ETSI 解析失敗: {standard['id']} - {e}")
            break
    
    return None, None

def fetch_ansi_data(standard: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    檢查 ANSI 標準更新 (需注意 ANSI 網站可能有反爬蟲機制)
    
    Args:
        standard: 標準資料字典
        
    Returns:
        (version, date) 或 (None, None) 如果失敗
    """
    source_url = standard.get("source_url", "")
    
    if not source_url:
        return None, None
    
    headers = {"User-Agent": get_user_agent()}
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(source_url, headers=headers, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # 使用頁面內容 hash 作為版本識別
            import hashlib
            content_hash = hashlib.md5(response.text.encode()).hexdigest()[:12]
            return content_hash, get_current_time_str()
            
        except requests.RequestException as e:
            print(f"[重試 {attempt + 1}/{MAX_RETRIES}] ANSI 請求失敗: {standard['id']} - {e}")
            if attempt < MAX_RETRIES - 1:
                random_delay(2, 5)
        except Exception as e:
            print(f"[錯誤] ANSI 解析失敗: {standard['id']} - {e}")
            break
    
    return None, None

# ============================================================
# 主程式邏輯
# ============================================================

def check_standard(standard: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    根據標準類型呼叫對應的爬蟲函式
    
    Args:
        standard: 標準資料字典
        
    Returns:
        (new_version, check_date) 或 (None, None) 如果失敗
    """
    standard_type = standard.get("type", "")
    
    # 加入隨機延遲避免被封鎖
    random_delay(1, 2)
    
    if standard_type == "FCC_CFR":
        return fetch_ecfr_data(standard)
    elif standard_type == "ISED":
        return fetch_ised_data(standard)
    elif standard_type == "ETSI":
        return fetch_etsi_data(standard)
    else:
        print(f"[警告] 未知的標準類型: {standard_type}")
        return None, None

def run_monitor() -> Tuple[int, List[Dict[str, Any]], str]:
    """
    執行監測主程式
    
    Returns:
        (checked_count, updates_list, status)
    """
    print("=" * 50)
    print(f"法規標準監測系統 - 開始執行")
    print(f"執行時間: {get_current_time_str()}")
    print("=" * 50)
    
    # 載入歷史記錄
    history = load_history()
    standards = history.get("standards", {})
    
    updates = []
    checked_count = 0
    error_count = 0
    
    # 遍歷所有標準類別
    for category, standards_list in standards.items():
        print(f"\n檢查類別: {category}")
        print("-" * 30)
        
        for standard in standards_list:
            std_id = standard.get("id", "Unknown")
            std_name = standard.get("name", "Unknown")
            old_version = standard.get("current_version")
            
            print(f"  檢查: {std_id}...", end=" ")
            
            try:
                new_version, check_date = check_standard(standard)
                
                if new_version:
                    checked_count += 1
                    standard["last_checked"] = check_date
                    
                    if old_version and old_version != new_version:
                        # 偵測到更新
                        print(f"⚡ 有更新! ({old_version} → {new_version})")
                        updates.append({
                            "id": std_id,
                            "name": std_name,
                            "type": standard.get("type", ""),
                            "old_version": old_version,
                            "new_version": new_version,
                            "detected_at": check_date
                        })
                        standard["current_version"] = new_version
                    elif not old_version:
                        # 首次記錄
                        print(f"✓ 首次記錄: {new_version}")
                        standard["current_version"] = new_version
                    else:
                        print("✓ 無變化")
                else:
                    print("✗ 無法取得")
                    error_count += 1
                    
            except Exception as e:
                print(f"✗ 錯誤: {e}")
                error_count += 1
    
    # 更新 metadata
    history["metadata"]["last_run_time"] = get_current_time_str()
    history["metadata"]["standards_checked"] = checked_count
    history["metadata"]["status"] = "success" if error_count == 0 else "partial"
    
    # 記錄更新歷史
    if updates:
        history.setdefault("update_history", [])
        for update in updates:
            history["update_history"].insert(0, update)
        # 只保留最近 100 筆歷史
        history["update_history"] = history["update_history"][:100]
    
    # 儲存更新後的歷史記錄
    save_history(history)
    
    # 輸出摘要
    print("\n" + "=" * 50)
    print(f"執行完成！")
    print(f"  已檢查標準數: {checked_count}")
    print(f"  偵測到更新數: {len(updates)}")
    print(f"  錯誤數: {error_count}")
    print("=" * 50)
    
    status = "success" if error_count == 0 else "partial"
    return checked_count, updates, status

def main():
    """主程式入口"""
    try:
        # 執行監測
        checked_count, updates, status = run_monitor()
        
        # 如果有更新，發送通知
        if updates:
            print("\n發送更新通知...")
            send_update_notification(updates)
            send_telegram_update_notification(updates)
        
        # 心跳機制：如果是週一且無更新，發送心跳報告
        if is_heartbeat_day():
            print("\n今天是心跳發送日 (週一)")
            if not updates:
                print("發送每週健康報告...")
                send_heartbeat(checked_count, status)
                send_telegram_heartbeat(checked_count, status)
            else:
                print("已有更新通知，跳過心跳報告")
        
        print("\n✅ 所有任務完成！")
        
    except Exception as e:
        # 捕捉所有異常，發送錯誤通報
        error_message = f"{str(e)}\n\n{traceback.format_exc()}"
        print(f"\n🚨 發生嚴重錯誤: {e}")
        print("發送錯誤通報...")
        
        # 更新狀態為失敗
        try:
            history = load_history()
            history["metadata"]["last_run_time"] = get_current_time_str()
            history["metadata"]["status"] = "fail"
            save_history(history)
        except Exception:
            pass
        
        send_error_notification(error_message)
        send_telegram_error_notification(error_message)
        raise  # 重新拋出異常讓 GitHub Actions 知道執行失敗

if __name__ == "__main__":
    main()
