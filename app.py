#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法規標準監測系統 - Streamlit 前端介面
=====================================
功能：
1. 顯示系統健康狀態
2. 分類顯示所有監測標準
3. 顯示更新歷史記錄

部署平台：Streamlit Cloud
"""

import json
import os
from datetime import datetime, timezone, timedelta

import streamlit as st
import pandas as pd

# ============================================================
# 頁面設定
# ============================================================

st.set_page_config(
    page_title="法規標準監測系統",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 樣式設定
# ============================================================

st.markdown("""
<style>
    /* 主要容器 */
    .main {
        padding: 1rem;
    }
    
    /* 標題樣式 */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(120deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
    }
    
    /* 狀態卡片 */
    .status-card {
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .status-ok {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border-left: 5px solid #28a745;
    }
    
    .status-warning {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%);
        border-left: 5px solid #ffc107;
    }
    
    .status-error {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        border-left: 5px solid #dc3545;
    }
    
    /* 標準卡片 */
    .standard-card {
        background: #ffffff;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border: 1px solid #e0e0e0;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .standard-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    /* 類別標籤 */
    .category-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }
    
    .badge-fcc { background: #007bff; color: white; }
    .badge-ised { background: #28a745; color: white; }
    .badge-etsi { background: #6f42c1; color: white; }
    .badge-ansi { background: #fd7e14; color: white; }
    
    /* 更新歷史 */
    .update-item {
        padding: 0.75rem;
        border-left: 3px solid #007bff;
        background: #f8f9fa;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    
    /* 響應式調整 */
    @media (max-width: 768px) {
        .main-title {
            font-size: 1.8rem;
        }
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 工具函式
# ============================================================

def load_history():
    """載入歷史記錄"""
    history_file = "history.json"
    
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"載入資料錯誤: {e}")
            return None
    else:
        st.warning("找不到 history.json 檔案")
        return None

def parse_time(time_str):
    """解析時間字串"""
    if not time_str:
        return None
    try:
        # 嘗試解析 YYYY-MM-DD HH:MM:SS 格式
        return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            # 嘗試 ISO 格式
            return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except ValueError:
            return None

def get_system_status(metadata):
    """
    判斷系統健康狀態
    
    規則：
    - 若 last_run_time 距今超過 26 小時 → 異常
    - 若 status 為 fail → 異常
    - 否則 → 正常
    """
    last_run = metadata.get("last_run_time")
    status = metadata.get("status", "pending")
    
    if not last_run:
        return "pending", "系統尚未執行", None
    
    last_run_dt = parse_time(last_run)
    if not last_run_dt:
        return "warning", "無法解析執行時間", last_run
    
    # 計算距今時間
    now = datetime.now()
    time_diff = now - last_run_dt
    hours_diff = time_diff.total_seconds() / 3600
    
    if status == "fail":
        return "error", "上次執行失敗", last_run
    elif hours_diff > 26:
        return "error", f"爬蟲已停止運行 ({int(hours_diff)} 小時前)", last_run
    else:
        return "ok", "系統運作正常", last_run

def get_category_badge(category):
    """取得類別徽章 HTML"""
    badges = {
        "FCC_CFR": ("FCC CFR", "badge-fcc"),
        "ANSI": ("ANSI", "badge-ansi"),
        "ISED": ("ISED", "badge-ised"),
        "ETSI": ("ETSI", "badge-etsi"),
    }
    
    name, css_class = badges.get(category, (category, ""))
    return f'<span class="category-badge {css_class}">{name}</span>'

# ============================================================
# 主頁面
# ============================================================

def main():
    # 標題
    st.markdown('<h1 class="main-title">📋 法規標準監測系統</h1>', unsafe_allow_html=True)
    st.markdown("自動追蹤 FCC、ISED、ETSI 法規標準更新狀態")
    
    # 載入資料
    data = load_history()
    
    if not data:
        st.error("無法載入資料，請確認 history.json 檔案存在")
        return
    
    metadata = data.get("metadata", {})
    standards = data.get("standards", {})
    update_history = data.get("update_history", [])
    
    # --------------------------------------------------------
    # 系統狀態面板
    # --------------------------------------------------------
    st.markdown("---")
    
    status_type, status_msg, last_run = get_system_status(metadata)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if status_type == "ok":
            st.success(f"🟢 {status_msg}")
        elif status_type == "error":
            st.error(f"⚠️ {status_msg}")
        elif status_type == "warning":
            st.warning(f"⚠️ {status_msg}")
        else:
            st.info(f"⏳ {status_msg}")
    
    with col2:
        st.metric(
            label="已檢查標準數",
            value=metadata.get("standards_checked", 0)
        )
    
    with col3:
        if last_run:
            st.metric(
                label="最後執行時間",
                value=last_run
            )
        else:
            st.metric(label="最後執行時間", value="尚未執行")
    
    # --------------------------------------------------------
    # 側邊欄篩選
    # --------------------------------------------------------
    st.sidebar.header("🔍 篩選條件")
    
    # 類別篩選
    all_categories = list(standards.keys())
    selected_categories = st.sidebar.multiselect(
        "選擇類別",
        all_categories,
        default=all_categories
    )
    
    # 搜尋
    search_term = st.sidebar.text_input("🔎 搜尋標準", "")
    
    # --------------------------------------------------------
    # 標準列表
    # --------------------------------------------------------
    st.markdown("---")
    st.subheader("📚 監測標準列表")
    
    # 建立標籤頁
    tabs = st.tabs(selected_categories if selected_categories else ["無選擇"])
    
    for tab, category in zip(tabs, selected_categories):
        with tab:
            standards_list = standards.get(category, [])
            
            # 搜尋篩選
            if search_term:
                standards_list = [
                    s for s in standards_list
                    if search_term.lower() in s.get("name", "").lower()
                    or search_term.lower() in s.get("id", "").lower()
                ]
            
            if not standards_list:
                st.info("沒有符合條件的標準")
                continue
            
            # 轉換為 DataFrame
            df_data = []
            for std in standards_list:
                df_data.append({
                    "ID": std.get("id", ""),
                    "名稱": std.get("name", ""),
                    "當前版本": std.get("current_version", "未記錄"),
                    "最後檢查": std.get("last_checked", "未檢查")
                })
            
            df = pd.DataFrame(df_data)
            
            # 顯示表格
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.TextColumn("ID", width="medium"),
                    "名稱": st.column_config.TextColumn("名稱", width="large"),
                    "當前版本": st.column_config.TextColumn("版本", width="small"),
                    "最後檢查": st.column_config.TextColumn("最後檢查", width="medium"),
                }
            )
            
            st.caption(f"共 {len(standards_list)} 個標準")
    
    # --------------------------------------------------------
    # 更新歷史
    # --------------------------------------------------------
    st.markdown("---")
    st.subheader("📜 近期更新記錄")
    
    if update_history:
        # 只顯示最近 20 筆
        recent_updates = update_history[:20]
        
        for update in recent_updates:
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"""
                    <div class="update-item">
                        <strong>{update.get('name', 'Unknown')}</strong>
                        <br>
                        <small>
                            {update.get('old_version', 'N/A')} → 
                            <span style="color: #28a745; font-weight: bold;">{update.get('new_version', 'N/A')}</span>
                        </small>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.caption(update.get('detected_at', ''))
    else:
        st.info("目前沒有更新記錄")
    
    # --------------------------------------------------------
    # 頁尾
    # --------------------------------------------------------
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.8rem;">
        <p>法規標準監測系統 v1.0</p>
        <p>由 GitHub Actions 每日自動執行 | 程式碼託管於 GitHub</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
