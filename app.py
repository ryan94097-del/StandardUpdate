#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
法規標準監測系統 - Streamlit 前端介面 (Modern UI)
=====================================
功能：
1. 顯示系統健康狀態 (儀表板視圖)
2. 分類顯示所有監測標準 (互動式表格)
3. 顯示更新歷史記錄 (時間軸視圖)

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
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# 現代化樣式 (CSS)
# ============================================================

st.markdown("""
<style>
    /* 全域字體優化 */
    .stApp {
        font-family: 'Inter', '微軟正黑體', sans-serif;
    }
    
    /* 標題區域 */
    .header-container {
        padding: 1rem 0 2rem 0;
        border-bottom: 1px solid #f0f2f6;
        margin-bottom: 2rem;
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        display: inline-block;
        margin: 0;
    }
    .subtitle {
        color: #64748b;
        font-size: 1rem;
        margin-top: 0.5rem;
    }

    /* 指標卡片 (Metric Cards) */
    div[data-testid="metric-container"] {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1rem 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease-in-out;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        border-color: #cbd5e1;
    }
    div[data-testid="metric-container"] label {
        color: #64748b;
        font-size: 0.875rem;
    }

    /* 狀態標籤 */
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.875rem;
        font-weight: 600;
    }
    .badge-success { background-color: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
    .badge-warning { background-color: #fef9c3; color: #854d0e; border: 1px solid #fde047; }
    .badge-error { background-color: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }

    /* 時間軸樣式 (Timeline) */
    .timeline-container {
        position: relative;
        padding-left: 2rem;
        border-left: 2px solid #e2e8f0;
        margin-top: 1rem;
        margin-left: 0.5rem;
    }
    .timeline-item {
        position: relative;
        margin-bottom: 2rem;
    }
    .timeline-dot {
        position: absolute;
        left: -2.6rem;
        top: 0.25rem;
        width: 1rem;
        height: 1rem;
        background-color: #3b82f6;
        border: 3px solid #ffffff;
        border-radius: 50%;
        box-shadow: 0 0 0 2px #3b82f6;
    }
    .timeline-content {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #f1f5f9;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .timeline-date {
        color: #94a3b8;
        font-size: 0.85rem;
        margin-bottom: 0.25rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .timeline-title {
        font-weight: 600;
        color: #1e293b;
        font-size: 1rem;
    }
    .version-change {
        margin-top: 0.5rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
        background: #f8fafc;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        display: inline-block;
        color: #475569;
    }
    .version-new {
        color: #16a34a;
        font-weight: bold;
    }
    
    /* DataFrame 優化 */
    .stDataFrame {
        border: 1px solid #f1f5f9;
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* 頁尾 */
    .footer {
        margin-top: 3rem;
        padding-top: 2rem;
        border-top: 1px solid #f1f5f9;
        text-align: center;
        color: #94a3b8;
        font-size: 0.875rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 邏輯層 (保留原邏輯)
# ============================================================

def load_history():
    """載入歷史記錄 (模擬或讀取)"""
    history_file = "history.json"
    
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.error(f"❌ 載入資料錯誤: {e}")
            return None
    else:
        # 開發環境或無檔案時的提示
        st.warning("⚠️ 找不到 history.json 檔案")
        return None

def parse_time(time_str):
    """解析時間字串"""
    if not time_str:
        return None
    try:
        return datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except ValueError:
            return None

def get_system_status(metadata):
    """判斷系統健康狀態"""
    last_run = metadata.get("last_run_time")
    status = metadata.get("status", "pending")
    
    if not last_run:
        return "pending", "系統尚未執行", None
    
    last_run_dt = parse_time(last_run)
    if not last_run_dt:
        return "warning", "無法解析執行時間", last_run
    
    now = datetime.now()
    time_diff = now - last_run_dt
    hours_diff = time_diff.total_seconds() / 3600
    
    if status == "fail":
        return "error", "上次執行失敗", last_run
    elif hours_diff > 26:
        return "error", f"爬蟲已停止 ({int(hours_diff)}h 前)", last_run
    else:
        return "ok", "系統運作正常", last_run

# ============================================================
# UI 元件層
# ============================================================

def render_header():
    st.markdown("""
        <div class="header-container">
            <h1 class="main-title">📡 法規標準監測系統</h1>
            <div class="subtitle">自動追蹤 FCC、ISED、ETSI 法規標準更新狀態</div>
        </div>
    """, unsafe_allow_html=True)

def render_status_cards(metadata):
    status_type, status_msg, last_run = get_system_status(metadata)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if status_type == "ok":
            st.metric(label="系統狀態", value="正常運行", delta="Online", delta_color="normal")
        elif status_type == "error":
            st.metric(label="系統狀態", value="異常", delta="Error", delta_color="inverse")
        else:
            st.metric(label="系統狀態", value="檢查中", delta="Pending", delta_color="off")
            
    with col2:
        st.metric(
            label="監測標準總數",
            value=f"{metadata.get('standards_checked', 0)} 項",
            delta=None
        )
    
    with col3:
        if last_run:
            # 格式化顯示比較友善的時間
            try:
                dt = parse_time(last_run)
                time_display = dt.strftime("%m/%d %H:%M") if dt else last_run
            except:
                time_display = last_run
            st.metric(label="最後更新時間", value=time_display)
        else:
            st.metric(label="最後更新時間", value="--")

    # 顯示詳細狀態訊息條
    if status_type == "error":
        st.markdown(f'<div class="status-badge badge-error">⚠️ {status_msg}</div>', unsafe_allow_html=True)
    elif status_type == "warning":
        st.markdown(f'<div class="status-badge badge-warning">⚡ {status_msg}</div>', unsafe_allow_html=True)

def render_standards_table(standards, selected_categories, search_term):
    st.markdown("### 📚 監測標準列表")
    
    if not selected_categories:
        st.info("👈 請從側邊欄選擇至少一個類別")
        return

    # 使用 Tabs 組織類別
    tabs = st.tabs([f"🔹 {cat}" for cat in selected_categories])
    
    for tab, category in zip(tabs, selected_categories):
        with tab:
            standards_list = standards.get(category, [])
            
            # 搜尋過濾
            if search_term:
                standards_list = [
                    s for s in standards_list
                    if search_term.lower() in s.get("name", "").lower()
                    or search_term.lower() in s.get("id", "").lower()
                ]
            
            if not standards_list:
                st.caption("🔍 無符合條件的標準")
                continue
            
            # 準備 DataFrame 資料
            df_data = []
            for std in standards_list:
                df_data.append({
                    "ID": std.get("id", ""),
                    "標準名稱": std.get("name", ""),
                    "當前版本": std.get("current_version", "N/A"),
                    "最後檢查": std.get("last_checked", "N/A"),
                    # 隱藏欄位用於排序等
                    "raw_date": std.get("last_checked", "") 
                })
            
            df = pd.DataFrame(df_data)
            
            # 使用新的 dataframe column config
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.TextColumn("標準編號", width="medium"),
                    "標準名稱": st.column_config.TextColumn("名稱", width="large"),
                    "當前版本": st.column_config.TextColumn(
                        "版本號", 
                        width="small",
                        help="目前偵測到的最新版本"
                    ),
                    "最後檢查": st.column_config.TextColumn("檢查時間", width="medium"),
                    "raw_date": None # 隱藏
                }
            )
            st.caption(f"共監測 {len(standards_list)} 個項目")

def render_timeline(update_history):
    st.markdown("### 📜 近期更新動態")
    
    if not update_history:
        st.info("✨ 目前沒有偵測到更新記錄")
        return
        
    recent_updates = update_history[:15]  # 只顯示最近 15 筆
    
    st.markdown('<div class="timeline-container">', unsafe_allow_html=True)
    
    for update in recent_updates:
        name = update.get('name', 'Unknown Standard')
        old_v = update.get('old_version', 'N/A')
        new_v = update.get('new_version', 'N/A')
        date = update.get('detected_at', '')
        
        # 簡單處理日期顯示
        display_date = date.split('T')[0] if 'T' in date else date
        
        html = f"""
        <div class="timeline-item">
            <div class="timeline-dot"></div>
            <div class="timeline-content">
                <div class="timeline-date">
                    <span>📅 {display_date}</span>
                </div>
                <div class="timeline-title">{name}</div>
                <div class="version-change">
                    {old_v} ➝ <span class="version-new">{new_v}</span>
                </div>
            </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
        
    st.markdown('</div>', unsafe_allow_html=True)

def render_sidebar(standards):
    with st.sidebar:
        st.header("🛠️ 控制台")
        
        # 搜尋
        search_term = st.text_input("搜尋標準...", placeholder="輸入關鍵字 (如: 15.247)")
        
        st.markdown("---")
        
        # 篩選
        st.subheader("顯示類別")
        all_categories = list(standards.keys())
        selected_categories = st.multiselect(
            "選擇顯示的法規體系",
            all_categories,
            default=all_categories
        )
        
        st.markdown("---")
        
        # 側邊欄資訊
        st.info(
            """
            **系統說明**
            此系統每日自動爬取官方網站，比對法規版本號變更。
            
            - **綠燈**: 26小時內有執行
            - **紅燈**: 超過26小時未執行
            """
        )
        
        return selected_categories, search_term

# ============================================================
# 主程式
# ============================================================

def main():
    # 載入資料
    data = load_history()
    
    if not data:
        # 如果沒有資料，顯示歡迎畫面
        render_header()
        st.error("找不到資料檔案 (history.json)，請確認後端爬蟲是否已執行。")
        return
    
    metadata = data.get("metadata", {})
    standards = data.get("standards", {})
    update_history = data.get("update_history", [])
    
    # 渲染 UI
    render_header()
    render_status_cards(metadata)
    
    st.markdown("---")
    
    selected_categories, search_term = render_sidebar(standards)
    
    col_main, col_history = st.columns([7, 3])
    
    with col_main:
        render_standards_table(standards, selected_categories, search_term)
        
    with col_history:
        render_timeline(update_history)
    
    # 頁尾
    st.markdown("""
        <div class="footer">
            法規標準監測系統 v1.1 | Designed with Streamlit
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
