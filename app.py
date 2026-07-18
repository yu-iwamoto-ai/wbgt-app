# -*- coding: utf-8 -*-
import streamlit as st
import os
import pandas as pd
from datetime import datetime, date, time

# ページの設定
st.set_page_config(page_title="校内WBGT観測システム", page_icon="🌡️", layout="centered")

# フォルダとご指定の5地点の設定
IMAGE_DIR = "saved_images"
os.makedirs(IMAGE_DIR, exist_ok=True)
LOCATIONS = ["講堂", "柏倫館", "エントランス", "東門付近", "西館3F"]

# 簡易データベース（CSVファイル）の準備
DB_FILE = "wbgt_data.csv"
if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=["日時", "地点", "WBGT", "気温", "湿度", "判定", "画像"])
    df_init.to_csv(DB_FILE, index=False, encoding="utf-8-sig")

# 熱中症判定のルールと色設定
def judge_wbgt(val):
    if val >= 31: return "🔴 危険", "#FF4B4B"
    elif val >= 28: return "🔶 厳重警戒", "#FFA500"
    elif val >= 25: return "💛 警戒", "#F1C40F"
    else: return "🔹 注意", "#3498DB"

st.title("🌡️ 校内WBGT観測システム")
st.caption("手入力 ＋ 写真保存版（サクサク動作モード）")

tab1, tab2, tab3 = st.tabs(["📸 新規登録", "📋 地点別最新一覧", "📊 全履歴（CSV）"])

# ==========================================
# タブ1: 新規登録（日時を手入力できるようにしました！）
# ==========================================
with tab1:
    st.header("1. 測定値と日時の入力")
    
    location = st.selectbox("観測地点を選択", LOCATIONS)
    
    # --- 【新機能】日付と時刻の選択欄 ---
    c_date, c_time = st.columns(2)
    with c_date:
        input_date = st.date_input("観測日を選択", date.today())
    with c_time:
        # 現在の時刻をデフォルト値にする
        current_time = datetime.now().time()
        input_time = st.time_input("観測時刻を選択", value=current_time)
    
    # 選択された日付と時刻を合体させて「2026-07-18 15:30:00」のような文字にする
    selected_datetime_str = datetime.combine(input_date, input_time).strftime("%Y-%m-%d %H:%M:%S")
    
    st.write("---")
    
    wbgt = st.number_input("WBGT (℃)", value=25.0, step=0.1, format="%.1f")
    ta = st.number_input("気温 (℃)", value=30.0, step=0.1, format="%.1f")
    rh = st.number_input("湿度 (%)", value=60.0, step=0.1, format="%.1f")
    
    uploaded_file = st.file_uploader("証拠写真をアップロード（任意）", type=["jpg", "jpeg", "png"])
    
    if st.button("この内容で登録する", type="primary"):
        judgment, _ = judge_wbgt(wbgt)
        img_name = "-"
        
        if uploaded_file is not None:
            # 画像ファイル名にも指定された日時が反映されるように調整
            time_for_file = datetime.combine(input_date, input_time).strftime("%Y%m%d_%H%M%S")
            img_name = f"{time_for_file}_{location}.jpg"
            with open(os.path.join(IMAGE_DIR, img_name), "wb") as f:
                f.write(uploaded_file.getbuffer())
        
        # selected_datetime_str（手入力された日時）をデータベースに保存します
        new_data = pd.DataFrame([[selected_datetime_str, location, wbgt, ta, rh, judgment, img_name]], 
                                columns=["日時", "地点", "WBGT", "気温", "湿度", "判定", "画像"])
        new_data.to_csv(DB_FILE, mode="a", header=False, index=False, encoding="utf-8-sig")
        
        st.success(f"【登録完了】 {location} のデータを保存しました！ ({selected_datetime_str})")
        st.balloons()

# ==========================================
# タブ2: 地点別最新一覧
# ==========================================
with tab2:
    st.header("📋 校内各地点の最新状況")
    
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE, encoding="utf-8-sig")
        
        for loc in LOCATIONS:
            loc_df = df[df["地点"] == loc]
            
            with st.container():
                if not loc_df.empty:
                    latest_row = loc_df.iloc[-1]
                    judgment_text = latest_row["判定"]
                    wbgt_val = latest_row["WBGT"]
                    
                    _, color = judge_wbgt(wbgt_val)
                    
                    st.markdown(
                        f"""
                        <div style="border-left: 10px solid {color}; padding: 15px; margin-bottom: 12px; background-color: #f8f9fa; border-radius: 6px; box-shadow: 1px 1px 4px rgba(0,0,0,0.08);">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-size: 1.25rem; font-weight: bold; color: #333;">📍 {loc}</span>
                                <span style="background-color: {color}; color: white; padding: 4px 14px; border-radius: 50px; font-weight: bold; font-size: 0.95rem;">{judgment_text}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between; margin-top: 10px; font-size: 1rem; color: #444;">
                                <span><b>WBGT:</b> <span style="font-size: 1.1rem; color:{color}; font-weight:bold;">{wbgt_val:.1f} ℃</span></span>
                                <span><b>気温:</b> {latest_row['気温']:.1f} ℃</span>
                                <span><b>湿度:</b> {latest_row['湿度']:.1f} %</span>
                            </div>
                            <div style="font-size: 0.8rem; color: #777; text-align: right; margin-top: 6px;">
                                🕒 最終観測: {latest_row['日時']}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        """
                        <div style="border-left: 10px solid #BDC3C7; padding: 15px; margin-bottom: 12px; background-color: #f8f9fa; border-radius: 6px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-size: 1.25rem; font-weight: bold; color: #7f8c8d;">📍 {loc}</span>
                                <span style="background-color: #BDC3C7; color: white; padding: 4px 14px; border-radius: 50px; font-weight: bold; font-size: 0.95rem;">データなし</span>
                            </div>
                            <div style="margin-top: 10px; font-size: 0.9rem; color: #95a5a6; italic;">
                                まだ本日の測定データが登録されていません。
                            </div>
                        </div>
                        """.format(loc=loc),
                        unsafe_allow_html=True
                    )

# ==========================================
# タブ3: 全履歴（CSV）
# ==========================================
with tab3:
    st.header("📊 過去の全データ記録")
    if os.path.exists(DB_FILE):
        df = pd.read_csv(DB_FILE, encoding="utf-8-sig")
        if not df.empty:
            st.dataframe(df.iloc[::-1], use_container_width=True)
            
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("これまでの全データをCSVで保存", data=csv_data, file_name="wbgt_history_all.csv", mime="text/csv")
        else:
            st.info("登録されたデータはまだありません。")
